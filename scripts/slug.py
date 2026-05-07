import re
import unicodedata

STOP_WORDS = {"a", "an", "the", "of", "in", "on", "to", "vs", "and", "or", "with", "for"}


def make_slug(topic: str) -> str:
    normalized = unicodedata.normalize("NFKD", topic).encode("ascii", "ignore").decode("ascii")
    lowered = normalized.lower()
    no_punct = re.sub(r"[^a-z0-9\s]", "", lowered)
    words = [w for w in no_punct.split() if w not in STOP_WORDS]
    joined = "-".join(words)

    if len(joined) <= 60:
        return joined

    cut = joined.rfind("-", 0, 60)
    if cut == -1:
        return joined[:60]
    return joined[:cut]
