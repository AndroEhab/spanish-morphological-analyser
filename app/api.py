"""API route handlers. The store is fixture-backed for now (see store.py)."""

from fastapi import APIRouter, HTTPException, Query

from app import store

router = APIRouter(prefix="/api")


@router.get("/search")
def search(
    q: str = Query("", max_length=200),
    limit: int = Query(25, ge=1, le=100),
) -> dict:
    """Dropdown candidates: dictionary word forms matching a partial query."""
    return {"query": q, "results": store.search(q, limit)}


@router.get("/analyze")
def analyze(id: str = Query(..., max_length=300)) -> dict:
    """Whole morphological/derivational family for one dictionary entry."""
    data = store.analyze(id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"no entry for id {id!r}")
    return data


@router.get("/health")
def health() -> dict:
    return store.health()
