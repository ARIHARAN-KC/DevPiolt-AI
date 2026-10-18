from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags = ["Health"])
def health_check() -> dict[str, str]:
    """
    Health check endpoint to verify that the API is running
    """
    return {
        "status" : "ok"
    }