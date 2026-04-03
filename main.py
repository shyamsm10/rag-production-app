import logging
from fastapi import FastAPI
import inngest
import inngest.fast_api
from inngest.experimental import ai
from dotenv import load_dotenv
import uuid
import os
import datetime

from data_loader import load_and_chunk_pdf, embed_texts
from vector_db import QdrantStorage
from custom_types import (
    RAGSearchResult,
    RAGUpsertResult,
    RAGChunkAndSrc
)

from reranker import rerank

# ✅ NEW: validation imports
from validators import (
    validate_question,
    validate_pdf_path,
    validate_source_id
)


# --------------------------------------------------
# LOGGING CONFIG
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# LOAD ENV
# --------------------------------------------------

load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_KEY:
    raise ValueError("❌ GROQ_API_KEY not found in .env")


# --------------------------------------------------
# INNGEST CLIENT
# --------------------------------------------------

inngest_client = inngest.Inngest(
    app_id="rag_app",
    logger=logging.getLogger("uvicorn"),
    is_production=False,
    serializer=inngest.PydanticSerializer()
)


# --------------------------------------------------
# PDF INGEST FUNCTION
# --------------------------------------------------

@inngest_client.create_function(
    fn_id="RAG: Ingest PDF",
    trigger=inngest.TriggerEvent(event="rag/ingest_pdf"),
    throttle=inngest.Throttle(
        limit=2,
        period=datetime.timedelta(minutes=1)
    ),
    rate_limit=inngest.RateLimit(
        limit=1,
        period=datetime.timedelta(hours=4),
        key="event.data.source_id",
    ),
)
async def rag_ingest_pdf(ctx: inngest.Context):

    def _load(ctx: inngest.Context) -> RAGChunkAndSrc:

        pdf_path = ctx.event.data.get("pdf_path")

        # ✅ VALIDATION MODULE USED HERE
        if not validate_pdf_path(pdf_path):
            logger.warning("Invalid PDF path detected")
            raise ValueError("Invalid PDF path provided")

        logger.info("PDF path validation passed")

        source_id = ctx.event.data.get("source_id", pdf_path)

        # ✅ VALIDATION MODULE USED HERE
        if not validate_source_id(source_id):
            logger.warning("Invalid source_id detected")
            raise ValueError("Invalid source_id provided")

        logger.info("Source ID validation passed")

        logger.info(f"Ingesting PDF: {pdf_path}")

        chunks = load_and_chunk_pdf(pdf_path)

        if not chunks:
            raise ValueError("PDF contains no readable content")

        logger.info(f"Chunks created: {len(chunks)}")

        return RAGChunkAndSrc(
            chunks=chunks,
            source_id=source_id
        )


    def _upsert(chunks_and_src: RAGChunkAndSrc) -> RAGUpsertResult:

        chunks = chunks_and_src.chunks
        source_id = chunks_and_src.source_id

        if not chunks:
            return RAGUpsertResult(ingested=0)

        vectors = embed_texts(chunks)

        ids = [
            str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}"))
            for i in range(len(chunks))
        ]

        payloads = [
            {"source": source_id, "text": chunks[i]}
            for i in range(len(chunks))
        ]

        QdrantStorage().upsert(ids, vectors, payloads)

        logger.info(f"Upserted {len(chunks)} chunks to Qdrant")

        return RAGUpsertResult(ingested=len(chunks))


    chunks_and_src = await ctx.step.run(
        "load-and-chunk",
        lambda: _load(ctx),
        output_type=RAGChunkAndSrc
    )

    ingested = await ctx.step.run(
        "embed-and-upsert",
        lambda: _upsert(chunks_and_src),
        output_type=RAGUpsertResult
    )

    return ingested.model_dump()


# --------------------------------------------------
# QUERY FUNCTION
# --------------------------------------------------

@inngest_client.create_function(
    fn_id="RAG: Query PDF",
    trigger=inngest.TriggerEvent(event="rag/query_pdf_ai")
)
async def rag_query_pdf_ai(ctx: inngest.Context):

    # ✅ NEW: RELEVANCE CHECK FUNCTION
    def is_relevant(question: str, contexts: list) -> bool:
        q_words = set(question.lower().split())
        for c in contexts:
            c_words = set(c.lower().split())
            if len(q_words & c_words) > 2:
                return True
        return False


    def _search(question: str, top_k: int = 8) -> RAGSearchResult:

        if not question.strip():
            return RAGSearchResult(contexts=[], sources=[])

        query_vec = embed_texts([question])[0]

        store = QdrantStorage()

        source_id = ctx.event.data.get("source_id")

        found = store.search(
            query_vec,
            10,
            source_filter=source_id
        )

        if not found or "contexts" not in found:
            return RAGSearchResult(contexts=[], sources=[])

        contexts = found.get("contexts", [])

        if not contexts:
            return RAGSearchResult(contexts=[], sources=[])

        reranked_contexts = rerank(
            question,
            contexts,
            min(top_k, len(contexts))
        )

        return RAGSearchResult(
            contexts=reranked_contexts,
            sources=found.get("sources", [])
        )


    # -------------------------------
    # QUESTION VALIDATION
    # -------------------------------

    question = ctx.event.data.get("question")

    if not validate_question(question):
        logger.warning("Invalid question detected")
        return {
            "answer": "Invalid question provided.",
            "sources": [],
            "num_contexts": 0
        }

    logger.info("Question validation passed")
    logger.info(f"User question: {question}")


    found = await ctx.step.run(
        "embed-and-search",
        lambda: _search(question),
        output_type=RAGSearchResult
    )

    logger.info(f"Contexts retrieved: {len(found.contexts)}")


    # -------------------------------
    # ✅ STRICT BLOCK (NEW)
    # -------------------------------
    # -------------------------------
    # ✅ STRICT BUT SAFE FILTER
    # -------------------------------
    if not found.contexts or len(found.contexts) == 0:
        logger.warning("No contexts retrieved")

        return {
            "answer": "Sorry, I am an AI agent that can only provide answers based on the document you uploaded.",
            "sources": [],
            "num_contexts": 0
        }


    # -------------------------------
    # BUILD CONTEXT
    # -------------------------------

    context_block = "\n\n".join(f"- {c}" for c in found.contexts)

    # ✅ MODIFIED USER PROMPT
    user_content = (
        f"STRICT CONTEXT:\n{context_block}\n\n"
        f"Question: {question}\n\n"
        f"Reminder: If answer is not in context, return fallback."
    )


    # -------------------------------
    # GROQ LLM CALL
    # -------------------------------

    adapter = ai.openai.Adapter(
        auth_key=GROQ_KEY,
        base_url="https://api.groq.com/openai/v1",
        model="llama-3.1-8b-instant"
    )

    res = await ctx.step.ai.infer(
        "llm-answer",
        adapter=adapter,
        body={
            "max_tokens": 500,
            "temperature": 0.0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a STRICT RAG AI assistant.\n\n"

                        "You MUST answer ONLY using the provided context.\n"
                        "You MUST NOT use any external knowledge.\n\n"

                        "IMPORTANT RULE:\n"
                        "Every part of your answer MUST be directly supported by the context.\n"
                        "Do NOT add new information.\n"
                        "Do NOT generate code unless the code is explicitly present in the context.\n\n"

                        "If the answer is not fully supported by the context, respond EXACTLY with:\n"
                        "Sorry, I am an AI agent that can only provide answers based on the document you uploaded."
                    )
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ]
        }
    )


    # -------------------------------
    # LLM RESPONSE VALIDATION
    # -------------------------------

    try:
        answer = res["choices"][0]["message"]["content"].strip()
    except Exception:
        answer = "Sorry, I am an AI agent that can only provide answers based on the document you uploaded."

    if "sorry" in answer.lower():
        answer = "Sorry, I am an AI agent that can only provide answers based on the document you uploaded."


    # -------------------------------
    # RESPONSE SCHEMA VALIDATION
    # -------------------------------

    assert isinstance(answer, str)
    assert isinstance(found.sources, list)
    assert isinstance(len(found.contexts), int)


    return {
        "answer": answer,
        "sources": found.sources,
        "num_contexts": len(found.contexts)
    }

# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------

app = FastAPI()

inngest.fast_api.serve(
    app,
    inngest_client,
    [rag_ingest_pdf, rag_query_pdf_ai]
)