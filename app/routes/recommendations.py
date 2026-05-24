"""AI-driven project recommendations + user-activity tracking."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, UserActivity
from app.schemas import (
    RecommendationResponse,
    UserActivityCreate,
    UserActivityResponse,
)
from app.services.recommendations import RecommendationService
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/me", response_model=RecommendationResponse)
async def my_recommendations(
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI recommendations for the currently authenticated user."""
    return await RecommendationService.generate_recommendations(current_user.id, db, top_k=top_k)


@router.get("/users/{user_id}", response_model=RecommendationResponse)
async def get_user_recommendations(
    user_id: int,
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get AI recommendations for any user (admin/managers may use this for review)."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return await RecommendationService.generate_recommendations(user_id, db, top_k=top_k)


@router.post("/activities", response_model=UserActivityResponse,
             status_code=status.HTTP_201_CREATED)
async def log_activity(
    payload: UserActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a user activity (view/edit/comment/...). Feeds the recommender."""
    activity = UserActivity(
        user_id=current_user.id,
        project_id=payload.project_id,
        activity_type=payload.activity_type,
        tags=payload.tags,
        extra_data=payload.extra_data,
    )
    db.add(activity)
    await db.commit()
    await db.refresh(activity)
    return activity
