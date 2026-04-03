from data_loader import load_and_chunk_pdf


def test_pdf_chunking():

    pdf_path = r"C:\Users\Shyam\Downloads\DATA-STRUCTURE-AND-ALGORITHM-MERGE.pdf"

    chunks = load_and_chunk_pdf(pdf_path)

    assert isinstance(chunks, list)

    assert len(chunks) > 0