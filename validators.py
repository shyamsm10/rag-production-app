from pydantic import BaseModel, Field
import os


# -------------------------------
# Pydantic request schema validator
# -------------------------------
class QueryValidator(BaseModel):
    question: str = Field(..., min_length=3)
    top_k: int = Field(default=5, ge=1, le=10)
    source_id: str


# -------------------------------
# Validate user question
# -------------------------------
def validate_question(question: str) -> bool:

    if not question:
        print("Invalid question detected: empty input")
        return False

    question = question.strip()

    if len(question) < 5:
        print("Invalid question detected: too short")
        return False

    greetings = ["hi", "hello", "hey", "hii"]

    if question.lower() in greetings:
        print("Greeting detected — not a valid RAG query")
        return False

    print("Question validation passed")
    return True


# -------------------------------
# Validate PDF path
# -------------------------------
def validate_pdf_path(pdf_path: str) -> bool:

    if not os.path.exists(pdf_path):
        print("Invalid PDF path detected")
        return False

    print("PDF path validation passed")
    return True


# -------------------------------
# Validate source id
# -------------------------------
def validate_source_id(source_id: str) -> bool:

    if not source_id or len(source_id.strip()) == 0:
        print("Invalid source_id detected")
        return False

    print("Source_id validation passed")
    return True