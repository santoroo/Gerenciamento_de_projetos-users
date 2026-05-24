"""Populate the database with example roles, users, teams, projects and activities.

Run with:  python -m app.scripts.seed_database

All test users share the password ``password123`` (intentionally weak — dev only).
"""
import asyncio
import random
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import AsyncSessionLocal, init_db
from app.models import (
    Project,
    ProjectMember,
    Role,
    RoleEnum,
    Team,
    TeamMember,
    User,
    UserActivity,
)
from app.utils.security import hash_password

DEFAULT_PASSWORD = "password123"


async def seed_database() -> None:
    print("Initializing database...")
    await init_db()
    print("Database initialized")

    async with AsyncSessionLocal() as session:
        # ---- roles ----
        print("\nCreating roles...")
        roles_data = [
            (RoleEnum.ADMIN.value, "Tech Lead / Arquiteto — full access"),
            (RoleEnum.MANAGER.value, "Gerente de Projetos — manages teams and projects"),
            (RoleEnum.CONTRIBUTOR.value, "Desenvolvedor — limited access"),
        ]
        for name, desc in roles_data:
            existing = (await session.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
            if not existing:
                session.add(Role(name=name, description=desc))
                print(f"  + role {name}")
        await session.commit()

        roles = {
            r.name: r
            for r in (await session.execute(select(Role))).scalars().all()
        }

        # ---- users ----
        print("\nCreating users...")
        users_seed = [
            ("admin_user",         "admin@example.com",   "Admin User",       "admin"),
            ("manager_alice",      "alice@example.com",   "Alice Manager",    "manager"),
            ("contributor_bob",    "bob@example.com",     "Bob Contributor",  "contributor"),
            ("contributor_charlie","charlie@example.com", "Charlie Developer","contributor"),
            ("manager_diana",      "diana@example.com",   "Diana Team Lead",  "manager"),
        ]
        hashed = hash_password(DEFAULT_PASSWORD)
        for username, email, full_name, role_name in users_seed:
            existing = (await session.execute(
                select(User).where(User.username == username)
            )).scalar_one_or_none()
            if not existing:
                session.add(User(
                    username=username,
                    email=email,
                    full_name=full_name,
                    hashed_password=hashed,
                    role_id=roles[role_name].id,
                    is_active=True,
                ))
                print(f"  + user {username} ({role_name})")
        await session.commit()

        users = {
            u.username: u
            for u in (await session.execute(select(User))).scalars().all()
        }

        # ---- teams ----
        print("\nCreating teams...")
        teams_seed = [
            ("Backend Team",  "Handles backend services and APIs",   "manager_alice"),
            ("Frontend Team", "Frontend and UI development",         "manager_diana"),
            ("Data Team",     "Data engineering and analytics",      "manager_alice"),
        ]
        for name, desc, owner in teams_seed:
            existing = (await session.execute(
                select(Team).where(Team.name == name)
            )).scalar_one_or_none()
            if not existing:
                session.add(Team(name=name, description=desc, owner_id=users[owner].id, is_active=True))
                print(f"  + team {name}")
        await session.commit()

        teams = {
            t.name: t
            for t in (await session.execute(select(Team))).scalars().all()
        }

        # ---- team memberships ----
        print("\nAdding team members...")
        memberships = [
            ("Backend Team",  "contributor_bob"),
            ("Backend Team",  "contributor_charlie"),
            ("Frontend Team", "contributor_bob"),
            ("Data Team",     "contributor_charlie"),
        ]
        for team_name, username in memberships:
            existing = (await session.execute(
                select(TeamMember).where(
                    TeamMember.team_id == teams[team_name].id,
                    TeamMember.user_id == users[username].id,
                )
            )).scalar_one_or_none()
            if not existing:
                session.add(TeamMember(team_id=teams[team_name].id, user_id=users[username].id))
                print(f"  + {username} -> {team_name}")
        await session.commit()

        # ---- projects ----
        print("\nCreating projects...")
        projects_seed = [
            ("FastAPI REST API",        "High-performance REST API service",         "fastapi,backend,api,python,rest,microservices", "Backend Team",  "manager_alice"),
            ("Database Migration System","Automated database migration and versioning","database,migration,python,sqlalchemy,devops",  "Backend Team",  "manager_alice"),
            ("React Dashboard",         "Interactive dashboard with real-time updates","react,frontend,javascript,ui,dashboard",        "Frontend Team", "manager_diana"),
            ("Data Pipeline",           "ETL pipeline for data processing",          "python,data,etl,analytics,pandas,spark",        "Data Team",     "manager_alice"),
            ("Machine Learning Model",  "ML model for recommendations",              "python,machine-learning,sklearn,ai,models",     "Data Team",     "manager_alice"),
        ]
        for name, desc, tags, team_name, owner in projects_seed:
            existing = (await session.execute(
                select(Project).where(Project.name == name)
            )).scalar_one_or_none()
            if not existing:
                session.add(Project(
                    name=name, description=desc, tags=tags,
                    team_id=teams[team_name].id if team_name else None,
                    owner_id=users[owner].id, is_active=True,
                ))
                print(f"  + project {name}")
        await session.commit()

        projects = {
            p.name: p
            for p in (await session.execute(select(Project))).scalars().all()
        }

        # ---- project memberships ----
        print("\nAdding project members...")
        proj_members = [
            ("FastAPI REST API",         "contributor_bob",     "admin"),
            ("FastAPI REST API",         "contributor_charlie", "contributor"),
            ("Database Migration System","contributor_charlie", "editor"),
            ("React Dashboard",          "contributor_bob",     "admin"),
            ("Data Pipeline",            "contributor_charlie", "admin"),
            ("Machine Learning Model",   "contributor_bob",     "contributor"),
        ]
        for proj_name, username, role in proj_members:
            existing = (await session.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == projects[proj_name].id,
                    ProjectMember.user_id == users[username].id,
                )
            )).scalar_one_or_none()
            if not existing:
                session.add(ProjectMember(
                    project_id=projects[proj_name].id,
                    user_id=users[username].id,
                    role=role,
                ))
                print(f"  + {username} -> {proj_name} ({role})")
        await session.commit()

        # ---- activities ----
        print("\nCreating user activities...")
        activity_types = ["view", "edit", "comment", "assign", "submit"]
        activity_tags = [
            "backend", "api", "python", "fastapi", "database",
            "frontend", "react", "javascript", "ui",
            "data", "analytics", "machine-learning", "sklearn",
        ]
        now = datetime.utcnow()
        created = 0
        # Only seed activities when none exist (idempotent runs).
        existing_count = (await session.execute(select(UserActivity))).scalars().first()
        if not existing_count:
            for username in ("contributor_bob", "contributor_charlie"):
                user = users[username]
                for _ in range(random.randint(20, 30)):
                    days_ago = random.randint(1, 90)
                    when = now - timedelta(days=days_ago, hours=random.randint(0, 24))
                    project = random.choice(list(projects.values()))
                    tags = ",".join(random.sample(activity_tags, random.randint(1, 4)))
                    session.add(UserActivity(
                        user_id=user.id,
                        project_id=project.id,
                        activity_type=random.choice(activity_types),
                        tags=tags,
                        timestamp=when,
                    ))
                    created += 1
            await session.commit()
        print(f"  + {created} activities created (0 if seed already ran)")

        print("\n" + "=" * 50)
        print("Seed complete.")
        print("=" * 50)
        print(f"\nTest credentials (all use password: {DEFAULT_PASSWORD}):")
        print("  admin_user / admin@example.com          (admin)")
        print("  manager_alice / alice@example.com       (manager)")
        print("  contributor_bob / bob@example.com       (contributor)")
        print("\nStart the server:  uvicorn app.main:app --reload")
        print("Open the UI:       http://localhost:8000/")
        print("Swagger docs:      http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(seed_database())
