from data_loader import embed_texts


def test_embedding_returns_vector():

    result = embed_texts(["hello world"])

    assert isinstance(result, list)

    assert len(result) == 1

    assert len(result[0]) > 0