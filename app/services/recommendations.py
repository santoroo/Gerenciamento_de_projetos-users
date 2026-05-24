"""Content-based recommender (TF-IDF + cosine similarity).

Designed to degrade gracefully: if the user has no activity, or scikit-learn
fails for any reason, we fall back to popularity / random sampling so the
endpoint never crashes the service."""
from datetime import datetime, timedelta
from typing import List, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, ProjectMember, UserActivity
from app.schemas import ProjectRecommendation, RecommendationResponse


class RecommendationService:

    @staticmethod
    async def _user_activity_profile(user_id: int, db: AsyncSession, days: int = 90) -> dict:
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = await db.execute(
            select(UserActivity).where(
                and_(UserActivity.user_id == user_id, UserActivity.timestamp >= cutoff)
            )
        )
        activities = result.scalars().all()

        tags: list[str] = []
        types: dict[str, int] = {}
        for a in activities:
            if a.tags:
                tags.extend(a.tags.split(","))
            types[a.activity_type] = types.get(a.activity_type, 0) + 1

        tags = [t.strip().lower() for t in tags if t and t.strip()]
        return {
            "tags": tags,
            "activity_count": len(activities),
            "activity_types": types,
            "profile_text": " ".join(tags) if tags else "",
        }

    @staticmethod
    async def _available_projects(user_id: int, db: AsyncSession) -> List[dict]:
        member_rows = (await db.execute(
            select(ProjectMember.project_id).where(ProjectMember.user_id == user_id)
        )).scalars().all()
        member_ids = set(member_rows)

        stmt = select(Project).where(Project.is_active == True)  # noqa: E712
        if member_ids:
            stmt = stmt.where(Project.id.notin_(member_ids))

        projects = (await db.execute(stmt)).scalars().all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "tags": p.tags or "",
                "profile_text": f"{p.name} {p.description or ''} {p.tags or ''}".lower(),
            }
            for p in projects
        ]

    @staticmethod
    def _compute_scores(
        user_profile_text: str,
        projects: List[dict],
        top_k: int,
        min_similarity: float = 0.05,
    ) -> List[Tuple[dict, float]]:
        """TF-IDF + cosine sim. Returns [(project, score), ...] sorted desc."""
        if not projects:
            return []
        if not user_profile_text.strip():
            # No activity yet — return projects with neutral score so the user
            # still sees something to interact with.
            return [(p, 0.0) for p in projects[:top_k]]

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            docs = [user_profile_text] + [p["profile_text"] for p in projects]
            vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), max_features=200)
            mat = vec.fit_transform(docs)
            sims = cosine_similarity(mat[0], mat[1:]).flatten()

            scored = [
                (projects[i], float(sims[i]))
                for i in range(len(projects))
                if sims[i] >= min_similarity
            ]
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k] or [(p, 0.0) for p in projects[:top_k]]
        except Exception as exc:  # noqa: BLE001
            # Fallback so a broken numpy/sklearn install doesn't 500 the API.
            import logging
            logging.getLogger(__name__).warning("Recommender fallback engaged: %s", exc)
            return [(p, 0.0) for p in projects[:top_k]]

    @staticmethod
    async def generate_recommendations(
        user_id: int,
        db: AsyncSession,
        top_k: int = 5,
    ) -> RecommendationResponse:
        profile = await RecommendationService._user_activity_profile(user_id, db)
        candidates = await RecommendationService._available_projects(user_id, db)
        scored = RecommendationService._compute_scores(profile["profile_text"], candidates, top_k)

        recommendations: list[ProjectRecommendation] = []
        top_user_tags = list(dict.fromkeys(profile["tags"]))[:3]  # unique, ordered
        for project, score in scored:
            if top_user_tags and score > 0:
                reason = f"Aligned with your recent interests: {', '.join(top_user_tags)}"
            else:
                reason = "Suggested because you haven't recorded activity yet"
            recommendations.append(
                ProjectRecommendation(
                    project_id=project["id"],
                    project_name=project["name"],
                    description=project["description"],
                    similarity_score=max(0.0, min(1.0, score)),
                    reason=reason,
                )
            )

        return RecommendationResponse(
            user_id=user_id,
            recommendations=recommendations,
            generated_at=datetime.utcnow(),
            source="tfidf",
        )
