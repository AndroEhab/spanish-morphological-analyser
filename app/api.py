"""API route handlers. The store is fixture-backed for now (see store.py)."""

from fastapi import APIRouter, HTTPException, Query

from app import store
from pipeline.normalize import fold

router = APIRouter(prefix="/api")


@router.get("/search")
def search(
    q: str = Query("", max_length=200),
    limit: int = Query(25, ge=1, le=100),
) -> dict:
    """Dropdown candidates: dictionary word forms matching a partial query."""
    return {"query": q, "results": store.search(q, limit)}


@router.get("/analyze")
def analyze(
    id: str | None = Query(None, max_length=300),
    word: str | None = Query(None, max_length=300),
) -> dict:
    """Family view for one dictionary entry.

    ``id`` — an existing form entry id (unchanged contract). ``word`` —
    deep-link / "Analizar" resolution: the exact folded word is resolved to
    the top-ranked entry using the dropdown's own ranking (ruling F4), and
    multi-lemma ambiguity surfaces as ``morphology.alternatives``. Exactly
    one of the two must be provided.
    """
    if (id is None) == (word is None):
        raise HTTPException(
            status_code=422,
            detail="provide exactly one of 'id' or 'word'",
        )
    entry_id = id
    if word is not None:
        folded = fold(word)
        rows = store.search(word, 100)
        exact = [r for r in rows if fold(r["form"]) == folded]
        if not exact:
            raise HTTPException(status_code=404, detail=f"no entry for {word!r}")
        entry_id = exact[0]["id"]
    data = store.analyze(entry_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"no entry for id {entry_id!r}")
    return data


@router.get("/health")
def health() -> dict:
    return store.health()
