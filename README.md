# Project and User Management Microservice

A high-performance FastAPI backend microservice featuring AI-driven project recommendations, Role-Based Access Control (RBAC), and comprehensive team/project management.

## Features

✅ **User & Access Control (RBAC)**
- Three roles: Admin, Manager, Contributor
- Fine-grained permission checks on all endpoints
- Secure role-based authorization

✅ **Team Management**
- Create and manage teams
- Add/remove team members
- Team ownership and membership tracking

✅ **Project Management**
- Create projects linked to teams or individual users
- Complex RBAC validation for project access
- Project member management with roles (admin, editor, viewer, contributor)
- Tag-based metadata for AI recommendations

✅ **AI-Driven Recommendations**
- Content-based filtering using TF-IDF vectorization
- Cosine similarity for project relevance scoring
- Analyzes 90-day user activity history
- Excludes already-assigned projects

---

## Project Structure

```
Gerenciamento_de_projetos-users/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration and settings
│   ├── database.py             # SQLAlchemy async setup
│   │
│   ├── models/
│   │   └── __init__.py         # SQLAlchemy ORM models
│   │                            # - Role, User, Team, Project
│   │                            # - TeamMember, ProjectMember
│   │                            # - UserActivity
│   │
│   ├── schemas/
│   │   └── __init__.py         # Pydantic validation schemas
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── users.py            # User CRUD endpoints
│   │   ├── teams.py            # Team management endpoints
│   │   ├── projects.py         # Project management + RBAC logic
│   │   └── recommendations.py  # AI recommendation endpoint
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rbac.py             # RBAC service & permission checks
│   │   └── recommendations.py  # AI recommendation engine
│   │
│   ├── middleware/
│   │   └── __init__.py         # Future: JWT auth middleware
│   │
│   └── utils/
│       ├── __init__.py
│       └── dependencies.py     # FastAPI dependency injection
│
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
└── README.md
```

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- PostgreSQL 12+ (or another SQLAlchemy-supported DB)
- pip/poetry for dependency management

### Step 1: Environment Setup

```bash
# Clone/navigate to project
cd Gerenciamento_de_projetos-users

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Database Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your database credentials
# Example for PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/project_management_db
```

### Step 3: Run Application

```bash
# Start the server
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access API documentation
# Swagger UI: http://localhost:8000/docs
# ReDoc:      http://localhost:8000/redoc
```

---

## Database Schema

### Models Overview

#### **Role**
```
id (PK)          - Integer
name             - String (unique) - admin, manager, contributor
description      - Text
created_at       - DateTime
```

#### **User**
```
id (PK)          - Integer
username         - String (unique)
email            - String (unique)
hashed_password  - String
full_name        - String
is_active        - Boolean (default: True)
role_id (FK)     - Integer -> Role.id
created_at       - DateTime
updated_at       - DateTime
```

#### **Team**
```
id (PK)          - Integer
name             - String
description      - Text
owner_id (FK)    - Integer -> User.id
is_active        - Boolean (default: True)
created_at       - DateTime
updated_at       - DateTime
```

#### **TeamMember** (Junction Table)
```
id (PK)          - Integer
team_id (FK)     - Integer -> Team.id
user_id (FK)     - Integer -> User.id
joined_at        - DateTime
```

#### **Project**
```
id (PK)          - Integer
name             - String
description      - Text
team_id (FK)     - Integer -> Team.id (nullable)
owner_id (FK)    - Integer -> User.id
tags             - String (comma-separated for AI)
is_active        - Boolean (default: True)
created_at       - DateTime
updated_at       - DateTime
```

#### **ProjectMember** (Junction Table)
```
id (PK)          - Integer
project_id (FK)  - Integer -> Project.id
user_id (FK)     - Integer -> User.id
role             - String (admin, editor, viewer, contributor)
joined_at        - DateTime
```

#### **UserActivity** (For AI Recommendations)
```
id (PK)          - Integer
user_id (FK)     - Integer -> User.id
project_id (FK)  - Integer -> Project.id (nullable)
activity_type    - String (view, comment, edit, assign, etc.)
tags             - String (comma-separated activity tags)
metadata         - Text (JSON-like additional info)
timestamp        - DateTime
```

---

## API Endpoints

### Authentication Headers
In production, include JWT token:
```
Authorization: Bearer <jwt_token>
```

Current implementation uses simple user_id parameter for demo purposes.

### Users

#### Create User (Admin only)
```http
POST /api/users
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "role_id": 2
}
```

#### List Users
```http
GET /api/users?skip=0&limit=100
```

#### Get User Details
```http
GET /api/users/{user_id}
```

#### Update User
```http
PUT /api/users/{user_id}
Content-Type: application/json

{
  "full_name": "Updated Name",
  "is_active": true
}
```

#### Delete User (Soft-delete)
```http
DELETE /api/users/{user_id}
```

---

### Teams

#### Create Team
```http
POST /api/teams?owner_id=1
Content-Type: application/json

{
  "name": "Backend Team",
  "description": "Handles all backend services"
}
```

#### List Teams
```http
GET /api/teams?skip=0&limit=100
```

#### Get Team Details
```http
GET /api/teams/{team_id}
```

#### Update Team (Team owner or admin only)
```http
PUT /api/teams/{team_id}?current_user_id=1
Content-Type: application/json

{
  "name": "Updated Team Name",
  "description": "Updated description"
}
```

#### Add Team Member (Team owner or admin only)
```http
POST /api/teams/{team_id}/members/{user_id}?current_user_id=1
```

#### Remove Team Member
```http
DELETE /api/teams/{team_id}/members/{user_id}?current_user_id=1
```

---

### Projects

#### Create Project (Complex RBAC Example)
```http
POST /api/projects?owner_id=1
Content-Type: application/json

{
  "name": "E-Commerce Platform",
  "description": "Main e-commerce project",
  "team_id": 1,
  "tags": "backend,database,api,python,fastapi"
}
```

**RBAC Logic Applied:**
1. Verifies owner_id is a Manager or Admin
2. If team_id provided:
   - Verifies team exists
   - Verifies user has access to team
3. Creates project
4. Automatically adds owner as project member with admin role

#### List Projects
```http
GET /api/projects?skip=0&limit=100
```

#### Get Project Details
```http
GET /api/projects/{project_id}
```

#### Update Project (Owner or Admin only)
```http
PUT /api/projects/{project_id}?current_user_id=1
Content-Type: application/json

{
  "name": "Updated Project Name",
  "tags": "updated,tags,here"
}
```

#### Add Project Member (Project admin only)
```http
POST /api/projects/{project_id}/members/{user_id}?current_user_id=1&role=contributor
```

Available roles: `admin`, `editor`, `viewer`, `contributor`

#### Remove Project Member
```http
DELETE /api/projects/{project_id}/members/{user_id}?current_user_id=1
```

---

### AI Recommendations

#### Get Project Recommendations for User
```http
GET /api/recommendations/users/{user_id}?top_k=5
```

**Response:**
```json
{
  "user_id": 1,
  "recommendations": [
    {
      "project_id": 5,
      "project_name": "Data Analytics Dashboard",
      "description": "Real-time analytics",
      "similarity_score": 0.85,
      "reason": "Matches your interests in: database, analytics, python"
    },
    {
      "project_id": 8,
      "project_name": "Machine Learning Pipeline",
      "description": "ML model training",
      "similarity_score": 0.72,
      "reason": "Matches your interests in: machine-learning, python, data"
    }
  ],
  "generated_at": "2024-01-15T10:30:00"
}
```

---

## RBAC (Role-Based Access Control)

### Roles

1. **Admin**
   - Can perform all operations
   - Can create other users
   - Can manage all teams and projects
   - Highest privilege level

2. **Manager**
   - Can create projects and teams
   - Can manage teams they own
   - Can manage projects they own
   - Cannot manage other users

3. **Contributor**
   - Can view projects they're assigned to
   - Can create personal projects
   - Read-only access to shared resources

### RBAC Service Functions

```python
# Check if user has specific role
await RBACService.check_user_role(
    user_id=1, 
    required_roles=["admin", "manager"], 
    db=db
)

# Ensure user is admin (raises HTTPException if not)
await RBACService.ensure_admin(user_id=1, db=db)

# Ensure user is manager or admin
await RBACService.ensure_manager_or_admin(user_id=1, db=db)

# Verify project access
await RBACService.verify_project_access(
    user_id=1, 
    project_id=5, 
    db=db
)

# Verify team access
await RBACService.verify_team_access(
    user_id=1, 
    team_id=3, 
    db=db
)
```

---

## AI Recommendation Algorithm

### Overview

The recommendation engine uses **Content-Based Filtering** with TF-IDF vectorization and cosine similarity to suggest relevant projects to users based on their activity profile.

### Algorithm Steps

#### 1. Build User Activity Profile
```python
async def get_user_activity_profile(user_id, db, days=90):
    """
    - Retrieves all user activities from last 90 days
    - Aggregates tags from activities
    - Returns normalized tag list and activity metadata
    """
```

**Example Profile:**
```python
{
    "tags": ["database", "api", "python", "backend", "sql"],
    "activity_count": 42,
    "activity_types": {
        "view": 15,
        "edit": 12,
        "comment": 10,
        "assign": 5
    },
    "profile_text": "database api python backend sql"
}
```

#### 2. Get Available Projects
```python
async def get_available_projects(user_id, db, exclude_existing=True):
    """
    - Fetches all active projects
    - Excludes projects user is already member of
    - Returns project metadata with normalized text
    """
```

#### 3. TF-IDF Vectorization
```python
# Create document vectors from text
vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2),      # Unigrams and bigrams
    max_features=100
)
tfidf_matrix = vectorizer.fit_transform(documents)
```

#### 4. Cosine Similarity Calculation
```python
# Calculate similarity between user profile and each project
similarities = cosine_similarity(user_vector, project_vectors)

# Results in scores between 0.0 and 1.0
# 1.0 = perfect match, 0.0 = no similarity
```

#### 5. Ranking and Filtering
```python
# Filter by minimum similarity (default: 0.1)
# Sort by similarity score (highest first)
# Return top-K recommendations (default: 5)
recommendations = sorted(recommendations, key=lambda x: x[1], reverse=True)[:top_k]
```

### Example Recommendation Scenario

**User Profile (90-day activity):**
- Tags: `["backend", "api", "python", "database", "fastapi"]`
- Recent activities: Edited 12 documents, viewed 15 projects, assigned to 3 projects

**Available Projects:**
1. "Frontend Dashboard" - Tags: `"react,javascript,ui"`
   - Similarity: 0.05 (LOW - different tech stack)

2. "Data Analytics Service" - Tags: `"python,database,analytics,sql"`
   - Similarity: 0.82 (HIGH - overlaps in python, database)

3. "API Gateway" - Tags: `"fastapi,python,backend,microservices"`
   - Similarity: 0.91 (VERY HIGH - strong match)

4. "Mobile App" - Tags: `"flutter,mobile,ui"`
   - Similarity: 0.02 (VERY LOW - completely different)

**Top-K Recommendations (k=3):**
```
1. API Gateway (0.91)
2. Data Analytics Service (0.82)
```

---

## Extending the System

### Adding New Recommendation Strategy

```python
# In app/services/recommendations.py

class RecommendationService:
    @staticmethod
    async def collaborative_filtering_recommendations(user_id, db, top_k=5):
        """
        Alternative: Collaborative Filtering
        Find users similar to target user
        Recommend projects liked by similar users
        """
        pass
    
    @staticmethod
    async def hybrid_recommendations(user_id, db, top_k=5):
        """
        Combine content-based and collaborative approaches
        """
        pass
```

### Adding JWT Authentication

```python
# In app/middleware/auth.py

from fastapi import Security, HTTPBearer
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_jwt_token(credentials = Security(security)):
    """Verify JWT token and extract user_id"""
    pass
```

---

## Error Handling

All endpoints return standard HTTP status codes:

- **200 OK** - Successful GET request
- **201 Created** - Successful resource creation
- **204 No Content** - Successful deletion
- **400 Bad Request** - Invalid input data
- **401 Unauthorized** - Missing/invalid authentication
- **403 Forbidden** - Insufficient permissions (RBAC)
- **404 Not Found** - Resource doesn't exist
- **500 Internal Server Error** - Unexpected server error

Example Error Response:
```json
{
  "detail": "Only project admin can add members"
}
```

---

## Development & Testing

### Create Sample Data

```python
# Script to populate initial roles and sample users
# Place in app/scripts/seed.py

from sqlalchemy import select
from app.models import Role, User
from app.database import AsyncSessionLocal

async def seed_roles(db):
    roles = ["admin", "manager", "contributor"]
    for role_name in roles:
        existing = await db.execute(select(Role).where(Role.name == role_name))
        if not existing.scalar_one_or_none():
            role = Role(name=role_name, description=f"{role_name.capitalize()} role")
            db.add(role)
    await db.commit()
```

### Testing Endpoints

```bash
# Test health check
curl http://localhost:8000/health

# Create user
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"pass123","role_id":3}'

# Get recommendations
curl http://localhost:8000/api/recommendations/users/1?top_k=5
```

---

## Performance Considerations

1. **Database Indexing**
   - Added indexes on: `username`, `email`, `is_active`, `tags`, `timestamp`
   - Consider composite indexes for frequent joins

2. **Async Operations**
   - All database operations are async (asyncio + asyncpg)
   - Handles concurrent requests efficiently

3. **Caching Recommendations**
   - Consider caching results for users with stable activity
   - Implement Redis caching for frequently accessed data

4. **Pagination**
   - Use `skip` and `limit` parameters on list endpoints
   - Prevents loading excessive data

---

## Production Deployment Checklist

- [ ] Implement JWT authentication middleware
- [ ] Hash user passwords using bcrypt
- [ ] Configure proper CORS origins
- [ ] Set up database migrations (Alembic)
- [ ] Add input validation and sanitization
- [ ] Implement rate limiting
- [ ] Add comprehensive logging
- [ ] Set up monitoring and alerting
- [ ] Configure environment-specific settings
- [ ] Add automated testing suite
- [ ] Implement API versioning
- [ ] Set up CI/CD pipeline

---

## License

[Specify your license]

## Support

For issues or questions, contact: [Your contact info]
