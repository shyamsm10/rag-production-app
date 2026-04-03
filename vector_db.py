from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct


class QdrantStorage:

    def __init__(self, url="http://localhost:6333", collection="docs", dim=384):

        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection

        collections = self.client.get_collections().collections
        names = [c.name for c in collections]

        if self.collection not in names:

            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(
                    size=dim,
                    distance=Distance.COSINE
                ),
            )

    # --------------------------------------------------
    # UPSERT VECTORS
    # --------------------------------------------------

    def upsert(self, ids, vectors, payloads):

        points = [
            PointStruct(
                id=ids[i],
                vector=vectors[i],
                payload=payloads[i]
            )
            for i in range(len(ids))
        ]

        self.client.upsert(
            collection_name=self.collection,
            points=points
        )

    # --------------------------------------------------
    # VECTOR SEARCH
    # --------------------------------------------------

    def search(self, query_vector, top_k=5, source_filter=None):

        query_filter = None

        if source_filter:
            query_filter = {
                "must": [
                    {
                        "key": "source",
                        "match": {"value": source_filter}
                    }
                ]
            }

        results = self.client.query_points(
            collection_name=self.collection,
            query=query_vector,
            limit=top_k,
            with_payload=True,
            query_filter=query_filter
        )

        contexts = []
        sources = set()

        if not results or not results.points:
            return {
                "contexts": [],
                "sources": []
            }

        for r in results.points:

            payload = getattr(r, "payload", None) or {}

            text = payload.get("text", "")
            source = payload.get("source", "")

            if text:
                contexts.append(text)
                sources.add(source)

        return {
            "contexts": contexts,
            "sources": list(sources)
        }