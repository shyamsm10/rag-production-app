import os

def test_pdf_exists():

    pdf_path = r"C:\Users\Shyam\Downloads\DATA-STRUCTURE-AND-ALGORITHM-MERGE.pdf"

    assert os.path.exists(pdf_path)

def test_question_validation():

    question = ""

    assert question.strip() == ""


def test_valid_question():

    question = "What is linked list?"

    assert len(question.strip()) > 3