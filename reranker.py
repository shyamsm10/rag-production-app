from sentence_transformers import CrossEncoder

# Load reranker model
reranker_model = CrossEncoder("BAAI/bge-reranker-base")

def rerank(question, contexts, top_k=8):

    # Prevent errors if no contexts
    if not contexts:
        return []

    pairs = [[question, c] for c in contexts]

    scores = reranker_model.predict(pairs)

    ranked = sorted(
        zip(contexts, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return [c for c, _ in ranked[:top_k]]