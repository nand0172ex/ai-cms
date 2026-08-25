import hashlib


def text_to_vector(text, size):
    """Deterministic generic vectorizer used when embedding provider is not configured."""
    digest = hashlib.sha256((text or "").encode("utf-8")).digest()
    base = [b / 255.0 for b in digest]
    if size <= len(base):
        return base[:size]

    result = []
    while len(result) < size:
        result.extend(base)
    return result[:size]
