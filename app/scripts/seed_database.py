"""
Database seeding script to populate initial data for testing
Run this after setting up the database to create sample roles and users
"""

import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models import Role, User, Team, Project, UserActivity, TeamMember, ProjectMember
from datetime import datetime, timedelta
import random


async def seed_database():
    """Populate database with sample data"""

    print("🔄 Initializing database...")
    await init_db()
    print("✅ Database initialized")

    async with AsyncSessionLocal() as session:

        # ============ 1. CREATE ROLES ============
        print("\n📝 Creating roles...")
        roles_data = [
            {"name": "admin", "description": "Administrator with full access"},
            {"name": "manager", "description": "Project manager with team management rights"},
            {"name": "contributor", "description": "Team contributor with limited access"}
        ]

        roles = {}
        for role_data in roles_data:
            existing = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            if not existing.scalar_one_or_none():
                role = Role(**role_data)
                session.add(role)
                roles[role_data["name"]] = role
                print(f"  ✓ Created role: {role_data['name']}")

        await session.commit()

        # Re-fetch roles to get IDs
        for role_name in ["admin", "manager", "contributor"]:
            result = await session.execute(
                select(Role).where(Role.name == role_name)
            )
            roles[role_name] = result.scalar_one()

        # ============ 2. CREATE USERS ============
        print("\n👥 Creating users...")
        users_data = [
            {
                "username": "admin_user",
                "email": "admin@example.com",
                "full_name": "Admin User",
                "hashed_password": "hashed_admin_pass_123",  # TODO: Hash this!
                "role": "admin"
            },
            {
                "username": "manager_alice",
                "email": "alice@example.com",
                "full_name": "Alice Manager",
                "hashed_password": "hashed_alice_pass_123",
                "role": "manager"
            },
            {
                "username": "contributor_bob",
                "email": "bob@example.com",
                "full_name": "Bob Contributor",
                "hashed_password": "hashed_bob_pass_123",
                "role": "contributor"
            },
            {
                "username": "contributor_charlie",
                "email": "charlie@example.com",
                "full_name": "Charlie Developer",
                "hashed_password": "hashed_charlie_pass_123",
                "role": "contributor"
            },
            {
                "username": "manager_diana",
                "email": "diana@example.com",
                "full_name": "Diana Team Lead",
                "hashed_password": "hashed_diana_pass_123",
                "role": "manager"
            }
        ]

        users = {}
        for user_data in users_data:
            role = user_data.pop("role")
            existing = await session.execute(
                select(User).where(User.username == user_data["username"])
            )
            if not existing.scalar_one_or_none():
                user = User(
                    **user_data,
                    role_id=roles[role].id,
                    is_active=True
                )
                session.add(user)
                users[user_data["username"]] = user
                print(f"  ✓ Created user: {user_data['username']} ({role})")

        await session.commit()

        # Re-fetch users to get IDs
        for username in ["admin_user", "manager_alice", "contributor_bob", "contributor_charlie", "manager_diana"]:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            users[username] = result.scalar_one()

        # ============ 3. CREATE TEAMS ============
        print("\n🏢 Creating teams...")
        teams_data = [
            {
                "name": "Backend Team",
                "description": "Handles backend services and APIs",
                "owner": "manager_alice"
            },
            {
                "name": "Frontend Team",
                "description": "Frontend and UI development",
                "owner": "manager_diana"
            },
            {
                "name": "Data Team",
                "description": "Data engineering and analytics",
                "owner": "manager_alice"
            }
        ]

        teams = {}
        for team_data in teams_data:
            owner = team_data.pop("owner")
            existing = await session.execute(
                select(Team).where(Team.name == team_data["name"])
            )
            if not existing.scalar_one_or_none():
                team = Team(
                    **team_data,
                    owner_id=users[owner].id,
                    is_active=True
                )
                session.add(team)
                teams[team_data["name"]] = team
                print(f"  ✓ Created team: {team_data['name']}")

        await session.commit()

        # Re-fetch teams
        for team_name in ["Backend Team", "Frontend Team", "Data Team"]:
            result = await session.execute(
                select(Team).where(Team.name == team_name)
            )
            teams[team_name] = result.scalar_one()

        # ============ 4. ADD TEAM MEMBERS ============
        print("\n👫 Adding team members...")
        team_memberships = [
            ("Backend Team", "contributor_bob"),
            ("Backend Team", "contributor_charlie"),
            ("Frontend Team", "contributor_bob"),
            ("Data Team", "contributor_charlie"),
        ]

        for team_name, username in team_memberships:
            existing = await session.execute(
                select(TeamMember).where(
                    (TeamMember.team_id == teams[team_name].id) &
                    (TeamMember.user_id == users[username].id)
                )
            )
            if not existing.scalar_one_or_none():
                member = TeamMember(
                    team_id=teams[team_name].id,
                    user_id=users[username].id
                )
                session.add(member)
                print(f"  ✓ Added {username} to {team_name}")

        await session.commit()

        # ============ 5. CREATE PROJECTS ============
        print("\n📦 Creating projects...")
        projects_data = [
            {
                "name": "FastAPI REST API",
                "description": "High-performance REST API service",
                "tags": "fastapi,backend,api,python,rest,microservices",
                "team": "Backend Team",
                "owner": "manager_alice"
            },
            {
                "name": "Database Migration System",
                "description": "Automated database migration and versioning",
                "tags": "database,migration,python,sqlalchemy,devops",
                "team": "Backend Team",
                "owner": "manager_alice"
            },
            {
                "name": "React Dashboard",
                "description": "Interactive dashboard with real-time updates",
                "tags": "react,frontend,javascript,ui,dashboard",
                "team": "Frontend Team",
                "owner": "manager_diana"
            },
            {
                "name": "Data Pipeline",
                "description": "ETL pipeline for data processing",
                "tags": "python,data,etl,analytics,pandas,spark",
                "team": "Data Team",
                "owner": "manager_alice"
            },
            {
                "name": "Machine Learning Model",
                "description": "ML model for recommendations",
                "tags": "python,machine-learning,sklearn,ai,models",
                "team": "Data Team",
                "owner": "manager_alice"
            }
        ]

        projects = {}
        for proj_data in projects_data:
            team_name = proj_data.pop("team")
            owner = proj_data.pop("owner")
            existing = await session.execute(
                select(Project).where(Project.name == proj_data["name"])
            )
            if not existing.scalar_one_or_none():
                project = Project(
                    **proj_data,
                    team_id=teams[team_name].id if team_name else None,
                    owner_id=users[owner].id,
                    is_active=True
                )
                session.add(project)
                projects[proj_data["name"]] = project
                print(f"  ✓ Created project: {proj_data['name']}")

        await session.commit()

        # Re-fetch projects
        for proj_name in [
            "FastAPI REST API",
            "Database Migration System",
            "React Dashboard",
            "Data Pipeline",
            "Machine Learning Model"
        ]:
            result = await session.execute(
                select(Project).where(Project.name == proj_name)
            )
            projects[proj_name] = result.scalar_one()

        # ============ 6. ADD PROJECT MEMBERS ============
        print("\n🚀 Adding project members...")
        project_memberships = [
            ("FastAPI REST API", "contributor_bob", "admin"),
            ("FastAPI REST API", "contributor_charlie", "contributor"),
            ("Database Migration System", "contributor_charlie", "editor"),
            ("React Dashboard", "contributor_bob", "admin"),
            ("Data Pipeline", "contributor_charlie", "admin"),
            ("Machine Learning Model", "contributor_bob", "contributor"),
        ]

        for proj_name, username, role in project_memberships:
            existing = await session.execute(
                select(ProjectMember).where(
                    (ProjectMember.project_id == projects[proj_name].id) &
                    (ProjectMember.user_id == users[username].id)
                )
            )
            if not existing.scalar_one_or_none():
                member = ProjectMember(
                    project_id=projects[proj_name].id,
                    user_id=users[username].id,
                    role=role
                )
                session.add(member)
                print(f"  ✓ Added {username} to {proj_name} (role: {role})")

        await session.commit()

        # ============ 7. CREATE USER ACTIVITIES ============
        print("\n📊 Creating user activities...")
        activity_types = ["view", "edit", "comment", "assign", "submit"]
        activity_tags = [
            "backend", "api", "python", "fastapi", "database",
            "frontend", "react", "javascript", "ui",
            "data", "analytics", "machine-learning", "sklearn"
        ]

        now = datetime.utcnow()
        activities_created = 0

        # Create activities for each user
        for username in ["contributor_bob", "contributor_charlie"]:
            user = users[username]

            # Create 20-30 activities spread over last 90 days
            for i in range(random.randint(20, 30)):
                days_ago = random.randint(1, 90)
                activity_time = now - \
                    timedelta(days=days_ago, hours=random.randint(0, 24))

                # Pick a random project
                assigned_projects = list(projects.values())
                project = random.choice(assigned_projects)

                # Pick random tags (1-4 tags per activity)
                tags = ",".join(random.sample(
                    activity_tags, random.randint(1, 4)))

                activity = UserActivity(
                    user_id=user.id,
                    project_id=project.id,
                    activity_type=random.choice(activity_types),
                    tags=tags,
                    timestamp=activity_time
                )
                session.add(activity)
                activities_created += 1

        await session.commit()
        print(f"  ✓ Created {activities_created} user activities")

        # ============ SUMMARY ============
        print("\n" + "="*50)
        print("✅ DATABASE SEEDING COMPLETE!")
        print("="*50)

        # Print summary statistics
        admin_count = await session.execute(select(Role).where(Role.name == "admin"))
        print(f"\n📈 Summary:")
        print(f"  Roles: {len(roles_data)}")
        print(f"  Users: {len(users_data)}")
        print(f"  Teams: {len(teams_data)}")
        print(f"  Projects: {len(projects_data)}")
        print(f"  Activities: {activities_created}")

        print(f"\n🔐 Test Credentials (for development only):")
        print(f"  Admin: admin_user / admin@example.com")
        print(f"  Manager: manager_alice / alice@example.com")
        print(f"  Contributor: contributor_bob / bob@example.com")

        print(f"\n🚀 You can now test the API!")
        print(f"  Start the server: python -m app.main")
        print(f"  API Docs: http://localhost:8000/docs")
        print(f"  Get recommendations: http://localhost:8000/api/recommendations/users/3")


if __name__ == "__main__":
    asyncio.run(seed_database())
