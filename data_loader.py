import fitz
from llama_index.core.node_parser import SentenceSplitter
from sentence_transformers import SentenceTransformer

# --------------------------------------------------
# EMBEDDING MODEL
# --------------------------------------------------

model = SentenceTransformer("all-MiniLM-L6-v2")

EMBED_DIM = 384

# --------------------------------------------------
# TEXT SPLITTER
# --------------------------------------------------

splitter = SentenceSplitter(
    chunk_size=700,
    chunk_overlap=150
)

# --------------------------------------------------
# LOAD + CHUNK PDF
# --------------------------------------------------

def load_and_chunk_pdf(path: str):

    print(f"Loading PDF: {path}")

    doc = fitz.open(path)

    texts = []

    for page in doc:
        text = page.get_text()

        if text and text.strip():
            texts.append(text)

    print("Pages with text:", len(texts))

    chunks = []

    for t in texts:
        split_chunks = splitter.split_text(t)
        chunks.extend(split_chunks)

    print("TOTAL CHUNKS CREATED:", len(chunks))

    if chunks:
        print("FIRST CHUNK SAMPLE:\n", chunks[0][:300])

    return chunks


# --------------------------------------------------
# EMBEDDINGS
# --------------------------------------------------

def embed_texts(texts: list[str]):

    if not texts:
        return []

    embeddings = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True
    )

    return embeddings.tolist()