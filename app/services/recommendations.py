import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from app.models import UserActivity, Project, User
from app.schemas import ProjectRecommendation, RecommendationResponse
from typing import List


class RecommendationService:
    """AI-driven recommendation engine for projects"""

    @staticmethod
    async def get_user_activity_profile(
        user_id: int,
        db: AsyncSession,
        days: int = 90
    ) -> dict:
        """
        Build user activity profile from recent activities
        Returns tags and activity frequency
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        query = select(UserActivity).where(
            and_(
                UserActivity.user_id == user_id,
                UserActivity.timestamp >= cutoff_date
            )
        ).order_by(UserActivity.timestamp.desc())

        result = await db.execute(query)
        activities = result.scalars().all()

        # Aggregate tags from all activities
        all_tags = []
        activity_types = {}

        for activity in activities:
            if activity.tags:
                all_tags.extend(activity.tags.split(","))

            activity_types[activity.activity_type] = activity_types.get(
                activity.activity_type, 0) + 1

        # Clean and normalize tags
        all_tags = [tag.strip().lower() for tag in all_tags if tag.strip()]

        return {
            "tags": all_tags,
            "activity_count": len(activities),
            "activity_types": activity_types,
            "profile_text": " ".join(all_tags) if all_tags else "general"
        }

    @staticmethod
    async def get_available_projects(
        user_id: int,
        db: AsyncSession,
        exclude_existing: bool = True
    ) -> List[dict]:
        """Get projects available for recommendation"""
        from app.models import ProjectMember

        # Get projects user is already member of
        user_project_ids = set()
        if exclude_existing:
            query = select(ProjectMember.project_id).where(
                ProjectMember.user_id == user_id
            )
            result = await db.execute(query)
            user_project_ids = set(result.scalars().all())

        # Get all active projects not already assigned
        query = select(Project).where(
            and_(
                Project.is_active == True,
                Project.id.notin_(
                    user_project_ids) if user_project_ids else True
            )
        )

        result = await db.execute(query)
        projects = result.scalars().all()

        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "tags": p.tags or "general",
                "profile_text": f"{p.name} {p.description or ''} {p.tags or ''}".lower()
            }
            for p in projects
        ]

    @staticmethod
    async def compute_content_based_recommendations(
        user_profile: dict,
        projects: List[dict],
        top_k: int = 5,
        min_similarity: float = 0.1
    ) -> List[tuple]:
        """
        Content-based filtering using TF-IDF and cosine similarity

        Args:
            user_profile: User's activity profile
            projects: List of available projects
            top_k: Number of recommendations to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (project_dict, similarity_score) tuples
        """
        if not projects:
            return []

        # Prepare documents for vectorization
        documents = [user_profile["profile_text"]] + \
            [p["profile_text"] for p in projects]

        try:
            # TF-IDF vectorization
            vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                max_features=100
            )
            tfidf_matrix = vectorizer.fit_transform(documents)

            # Compute cosine similarity between user and projects
            user_vector = tfidf_matrix[0]
            project_vectors = tfidf_matrix[1:]

            similarities = cosine_similarity(
                user_vector, project_vectors).flatten()

            # Filter by minimum similarity and sort
            recommendations = [
                (projects[i], float(similarities[i]))
                for i in range(len(projects))
                if similarities[i] >= min_similarity
            ]

            recommendations.sort(key=lambda x: x[1], reverse=True)
            return recommendations[:top_k]

        except Exception as e:
            # Fallback: return random projects if vectorization fails
            print(f"Error in recommendation computation: {str(e)}")
            return [(p, 0.5) for p in projects[:top_k]]

    @staticmethod
    async def generate_recommendations(
        user_id: int,
        db: AsyncSession,
        top_k: int = 5
    ) -> RecommendationResponse:
        """
        Generate project recommendations for a user

        Main recommendation pipeline:
        1. Build user activity profile
        2. Get available projects
        3. Compute content-based recommendations
        4. Return ranked projects
        """
        # Step 1: Get user activity profile
        user_profile = await RecommendationService.get_user_activity_profile(
            user_id,
            db,
            days=90
        )

        # Step 2: Get available projects
        available_projects = await RecommendationService.get_available_projects(
            user_id,
            db,
            exclude_existing=True
        )

        # Step 3: Compute recommendations
        scored_projects = await RecommendationService.compute_content_based_recommendations(
            user_profile,
            available_projects,
            top_k=top_k,
            min_similarity=0.1
        )

        # Step 4: Build response
        recommendations = []
        for project, score in scored_projects:
            reason = f"Matches your interests in: {', '.join(set(user_profile['tags'][:3]))}"

            recommendations.append(
                ProjectRecommendation(
                    project_id=project["id"],
                    project_name=project["name"],
                    description=project["description"],
                    similarity_score=score,
                    reason=reason
                )
            )

        return RecommendationResponse(
            user_id=user_id,
            recommendations=recommendations,
            generated_at=datetime.utcnow()
        )
