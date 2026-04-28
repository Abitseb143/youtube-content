from fastapi import APIRouter

from faceless import __version__

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
