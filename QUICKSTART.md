# Quick Start Guide - Project Management Microservice

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.10+
- PostgreSQL 12+ (or SQLite for development)
- Git

### Step 1: Clone/Navigate to Project
```bash
cd Gerenciamento_de_projetos-users
```

### Step 2: Create Virtual Environment
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Database

#### Option A: PostgreSQL (Production)
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your PostgreSQL credentials
# Example:
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/project_mgmt_db
```

#### Option B: SQLite (Development/Testing)
```bash
# Edit .env
# DATABASE_URL=sqlite+aiosqlite:///./project_mgmt.db
```

### Step 5: Seed Database with Sample Data (Optional)
```bash
python -m app.scripts.seed_database

# This creates:
# - 5 sample users (1 admin, 2 managers, 2 contributors)
# - 3 sample teams
# - 5 sample projects
# - 100+ sample activities for testing recommendations
```

### Step 6: Run the Application
```bash
# Option 1: Direct Python
python -m app.main

# Option 2: Using uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 7: Access the Application
```
API Documentation: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
Health Check: http://localhost:8000/health
```

---

## 🧪 Testing the API

### 1. Create a User
```bash
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "securepass123",
    "full_name": "Test User",
    "role_id": 3
  }'
```

### 2. Create a Team
```bash
curl -X POST http://localhost:8000/api/teams?owner_id=1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Team",
    "description": "Test team"
  }'
```

### 3. Create a Project
```bash
curl -X POST http://localhost:8000/api/projects?owner_id=1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Project",
    "description": "Test project",
    "tags": "python,backend,api",
    "team_id": 1
  }'
```

### 4. Get Recommendations
```bash
curl http://localhost:8000/api/recommendations/users/1?top_k=5
```

### 5. List All Endpoints
```bash
# View Swagger UI for interactive testing
open http://localhost:8000/docs
```

---

## 📊 AI Recommendations

### How It Works

The recommendation system analyzes a user's:
1. **Activity History** - Last 90 days
2. **Activity Tags** - From projects they've interacted with
3. **Projects** - Available projects not yet assigned
4. **Similarity** - Using TF-IDF + cosine similarity

### Example Response
```json
{
  "user_id": 1,
  "recommendations": [
    {
      "project_id": 5,
      "project_name": "Data Analytics Dashboard",
      "description": "Real-time analytics",
      "similarity_score": 0.89,
      "reason": "Matches your interests in: database, analytics, python"
    }
  ],
  "generated_at": "2024-01-15T10:30:00"
}
```

---

## 🔐 RBAC Roles

### Admin
- Full system access
- Create other users
- Manage all resources
- Highest privilege

### Manager  
- Create projects and teams
- Manage owned resources
- Assign team members
- Cannot create other users

### Contributor
- View assigned projects
- Edit own contributions
- Limited permissions

---

## 📁 Project Structure

```
app/
├── main.py           # Application entry point
├── config.py         # Configuration
├── database.py       # Database setup
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── routes/           # API endpoints
├── services/         # Business logic (RBAC, Recommendations)
├── middleware/       # Auth & middleware
├── utils/            # Helpers
└── scripts/          # Utilities (seed_database.py)
```

---

## 🔧 Development Tips

### Add Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.info("User created: %s", user.id)
```

### Custom Validation
```python
from pydantic import field_validator

class UserCreate(BaseModel):
    email: str
    
    @field_validator('email')
    def email_valid(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v
```

### Query Examples
```python
# Get all active users
users = await db.execute(
    select(User).where(User.is_active == True)
)

# Find by email
user = await db.execute(
    select(User).where(User.email == "user@example.com")
)

# With relationships
user_with_role = await db.execute(
    select(User).where(User.id == 1)
)
```

---

## 🐛 Troubleshooting

### Database Connection Error
```
Error: psycopg2.OperationalError: could not connect to server

Solution:
- Verify PostgreSQL is running
- Check credentials in .env
- Ensure database exists
- Check connection string format
```

### Module Not Found
```
Error: ModuleNotFoundError: No module named 'app'

Solution:
- Activate virtual environment
- Install dependencies: pip install -r requirements.txt
- Run from project root: python -m app.main
```

### Port Already in Use
```
Error: Address already in use

Solution:
- Kill existing process on port 8000
- Or use different port: uvicorn app.main:app --port 8001
```

### JWT Issues (Production)
```
Error: Invalid token

Solution:
- Implement JWT middleware in app/middleware/auth.py
- Use SECRET_KEY from .env
- Ensure token format is: Bearer <token>
```

---

## 📚 Next Steps

1. **Read Full Documentation**
   - Open `README.md` for comprehensive guide
   - See `IMPLEMENTATION_SUMMARY.md` for architecture

2. **Implement Authentication**
   - Add JWT token validation in `app/middleware/auth.py`
   - Use Python `jwt` library
   - Update routes to require authentication

3. **Add Tests**
   - Create `tests/` directory
   - Use `pytest` and `httpx`
   - Test each endpoint

4. **Deploy**
   - Containerize with Docker
   - Set up CI/CD pipeline
   - Deploy to cloud platform

5. **Monitor**
   - Add application logging
   - Set up error tracking
   - Configure performance monitoring

---

## 📞 Support

- **Documentation**: See README.md
- **API Docs**: http://localhost:8000/docs
- **Issues**: Check IMPLEMENTATION_SUMMARY.md

---

## 🎉 You're Ready!

Your microservice is now configured and ready to use. Start creating projects, teams, and generating AI recommendations!

```bash
# Final check - everything working?
curl http://localhost:8000/health
# Expected response: {"status":"healthy","service":"Project Management Microservice"}
```

Happy coding! 🚀
