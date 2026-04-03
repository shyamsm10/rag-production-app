from vector_db import QdrantStorage
from data_loader import embed_texts


def test_vector_search():

    store = QdrantStorage()

    vec = embed_texts(["linked list"])[0]

    result = store.search(vec, 3)

    assert "contexts" in result