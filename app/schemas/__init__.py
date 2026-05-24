from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


# ============= ROLE =============
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleResponse(RoleBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============= USER =============
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: Optional[str] = None


class UserRegister(UserBase):
    """Public self-registration payload.
    Role defaults to 'contributor'; only admins can create admins/managers via /users."""
    password: str = Field(..., min_length=8, max_length=128)


class UserCreate(UserBase):
    """Admin-only creation payload."""
    password: str = Field(..., min_length=8, max_length=128)
    role_id: int


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role_id: Optional[int] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    role_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(UserResponse):
    role: RoleResponse


# ============= AUTH =============
class LoginRequest(BaseModel):
    username_or_email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserDetailResponse


class TokenValidationResponse(BaseModel):
    """Returned to other microservices to validate a bearer token."""
    valid: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


# ============= TEAM =============
class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TeamMemberResponse(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: Optional[str] = None
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamResponse(TeamBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    members: List[TeamMemberResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ============= PROJECT =============
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[str] = Field(None, max_length=500,
                                description="Comma-separated tags used by the AI recommender")


class ProjectCreate(ProjectBase):
    team_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    team_id: Optional[int] = None


class ProjectMemberResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(ProjectBase):
    id: int
    team_id: Optional[int]
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    members: List[ProjectMemberResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ============= ACTIVITY =============
class UserActivityCreate(BaseModel):
    project_id: Optional[int] = None
    activity_type: str = Field(..., min_length=1, max_length=50)
    tags: Optional[str] = Field(None, max_length=500)
    extra_data: Optional[str] = None


class UserActivityResponse(UserActivityCreate):
    id: int
    user_id: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# ============= RECOMMENDATION =============
class ProjectRecommendation(BaseModel):
    project_id: int
    project_name: str
    description: Optional[str] = None
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    reason: str


class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[ProjectRecommendation]
    generated_at: datetime
    source: str = Field(default="tfidf",
                        description="Algorithm that produced the result")


# ============= GENERIC =============
class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str
