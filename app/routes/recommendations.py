from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import User
from app.services.recommendations import RecommendationService
from app.schemas import RecommendationResponse

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/users/{user_id}", response_model=RecommendationResponse)
async def get_user_recommendations(
    user_id: int,
    top_k: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI-driven project recommendations for a user

    Algorithm:
    - Analyzes user activity profile (last 90 days)
    - Uses content-based filtering with TF-IDF + cosine similarity
    - Returns top-K most relevant projects
    - Excludes projects user is already member of

    Query Parameters:
    - top_k: Number of recommendations (default: 5, max: 20)
    """
    # Verify user exists
    from sqlalchemy import select
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Limit top_k
    top_k = min(top_k, 20)

    # Generate recommendations
    recommendations = await RecommendationService.generate_recommendations(
        user_id,
        db,
        top_k=top_k
    )

    return recommendations
