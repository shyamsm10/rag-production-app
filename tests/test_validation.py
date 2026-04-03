import pytest
from validators import QueryValidator


def test_valid_query():

    data = QueryValidator(
        question="Explain binary trees",
        top_k=5,
        source_id="dsa.pdf"
    )

    assert data.top_k == 5


def test_invalid_question():

    with pytest.raises(Exception):

        QueryValidator(
            question="",
            top_k=5,
            source_id="dsa.pdf"
        )


def test_invalid_top_k():

    with pytest.raises(Exception):

        QueryValidator(
            question="Explain trees",
            top_k=20,
            source_id="dsa.pdf"
        )