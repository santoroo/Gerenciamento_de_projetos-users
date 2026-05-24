# API Reference - Project Management Microservice

## Base URL
```
http://localhost:8000/api
```

## Authentication
All endpoints currently accept `user_id` and `current_user_id` as query parameters.
In production, implement JWT authentication with Bearer tokens.

---

## 🔵 USERS API

### Create User
**POST** `/users`
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "role_id": 1
}
```
**Response:** 201 Created
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "role_id": 1,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

### List Users
**GET** `/users?skip=0&limit=100`
**Response:** 200 OK
```json
[
  {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    ...
  }
]
```

### Get User
**GET** `/users/{user_id}`
**Response:** 200 OK
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "role": {
    "id": 1,
    "name": "admin",
    "description": "Admin role",
    "created_at": "2024-01-15T10:30:00"
  }
}
```

### Update User
**PUT** `/users/{user_id}`
```json
{
  "full_name": "Updated Name",
  "is_active": true
}
```

### Delete User (Soft-delete)
**DELETE** `/users/{user_id}`
**Response:** 204 No Content

---

## 🟢 TEAMS API

### Create Team
**POST** `/teams?owner_id={owner_id}`
```json
{
  "name": "Backend Team",
  "description": "Handles backend services"
}
```

### List Teams
**GET** `/teams?skip=0&limit=100`

### Get Team
**GET** `/teams/{team_id}`

### Update Team
**PUT** `/teams/{team_id}?current_user_id={user_id}`
```json
{
  "name": "Updated Team Name",
  "description": "Updated description"
}
```

### Add Team Member
**POST** `/teams/{team_id}/members/{user_id}?current_user_id={user_id}`
**Response:** 201 Created
```json
{
  "message": "User added to team"
}
```

### Remove Team Member
**DELETE** `/teams/{team_id}/members/{user_id}?current_user_id={user_id}`
**Response:** 204 No Content

---

## 🟡 PROJECTS API

### Create Project (with RBAC)
**POST** `/projects?owner_id={owner_id}`
```json
{
  "name": "E-Commerce Platform",
  "description": "Main e-commerce project",
  "team_id": 1,
  "tags": "backend,database,api,python,fastapi"
}
```
**RBAC Checks:**
- Owner must be Manager or Admin
- If team_id provided, owner must have team access
- Owner auto-added as project admin

### List Projects
**GET** `/projects?skip=0&limit=100`

### Get Project
**GET** `/projects/{project_id}`

### Update Project
**PUT** `/projects/{project_id}?current_user_id={user_id}`
```json
{
  "name": "Updated Name",
  "tags": "updated,tags"
}
```

### Add Project Member
**POST** `/projects/{project_id}/members/{user_id}?current_user_id={user_id}&role=contributor`

**Roles:**
- `admin` - Full project control
- `editor` - Can edit content
- `viewer` - Read-only access
- `contributor` - Can contribute

### Remove Project Member
**DELETE** `/projects/{project_id}/members/{user_id}?current_user_id={user_id}`

---

## 🟣 RECOMMENDATIONS API

### Get Project Recommendations
**GET** `/recommendations/users/{user_id}?top_k=5`

**Parameters:**
- `user_id` - Target user ID
- `top_k` - Number of recommendations (1-20, default: 5)

**Response:** 200 OK
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
    },
    {
      "project_id": 8,
      "project_name": "ML Pipeline",
      "description": "Machine learning",
      "similarity_score": 0.76,
      "reason": "Matches your interests in: machine-learning, python, data"
    }
  ],
  "generated_at": "2024-01-15T10:30:00"
}
```

**Algorithm:**
1. Analyzes user activities from last 90 days
2. Extracts activity tags
3. Vectorizes using TF-IDF
4. Calculates cosine similarity to available projects
5. Returns top-K projects sorted by similarity

---

## 🔲 SYSTEM API

### Health Check
**GET** `/health`
**Response:** 200 OK
```json
{
  "status": "healthy",
  "service": "Project Management Microservice"
}
```

### Root Endpoint
**GET** `/`
**Response:** 200 OK
```json
{
  "message": "Welcome to Project Management Microservice",
  "version": "1.0.0",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Email already registered"
}
```

### 401 Unauthorized
```json
{
  "detail": "User not found or inactive"
}
```

### 403 Forbidden (RBAC)
```json
{
  "detail": "Only project admin can add members"
}
```

### 404 Not Found
```json
{
  "detail": "Project not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 201 | Created - Resource created |
| 204 | No Content - Successful deletion |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Authentication required |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 500 | Server Error - Unexpected error |

---

## Rate Limiting

Currently not implemented. Recommended for production:
- 100 requests/minute per user
- 1000 requests/minute per IP
- Implement with `slowapi` library

---

## Pagination

All list endpoints support:
- `skip` - Number of records to skip (default: 0)
- `limit` - Maximum records to return (default: 100)

Example:
```
GET /api/users?skip=20&limit=10
```

---

## Filtering & Search

Filtering not yet implemented. Recommended additions:
- Filter by name, email, role
- Search across projects
- Filter by date range

---

## Version History

### v1.0.0 (Current)
- Initial release
- CRUD for Users, Teams, Projects
- RBAC implementation
- AI recommendations with TF-IDF
- Database models and schemas

### Future Versions
- v1.1.0 - JWT authentication
- v1.2.0 - Advanced filtering and search
- v1.3.0 - Collaborative filtering recommendations
- v2.0.0 - GraphQL API layer

---

## Testing

Use the interactive API documentation:
```
http://localhost:8000/docs
```

Or use curl:
```bash
# Test health
curl http://localhost:8000/health

# Create user
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{"username":"test",...}'

# Get recommendations
curl http://localhost:8000/api/recommendations/users/1
```

---

## Support

For more information, see:
- [README.md](README.md) - Full documentation
- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Architecture details
