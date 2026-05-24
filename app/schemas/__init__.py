from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ============= COMMON SCHEMAS =============
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleResponse(RoleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============= USER SCHEMAS =============
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role_id: int


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    role_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(UserResponse):
    role: RoleResponse


# ============= TEAM SCHEMAS =============
class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TeamMemberResponse(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: Optional[str]
    joined_at: datetime

    class Config:
        from_attributes = True


class TeamResponse(TeamBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    members: List[TeamMemberResponse] = []

    class Config:
        from_attributes = True


# ============= PROJECT SCHEMAS =============
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tags: Optional[str] = None


class ProjectCreate(ProjectBase):
    team_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectMemberResponse(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class ProjectResponse(ProjectBase):
    id: int
    team_id: Optional[int]
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    members: List[ProjectMemberResponse] = []

    class Config:
        from_attributes = True


# ============= ACTIVITY SCHEMAS =============
class UserActivityCreate(BaseModel):
    project_id: Optional[int] = None
    activity_type: str = Field(..., min_length=1, max_length=50)
    tags: Optional[str] = None
    metadata: Optional[str] = None


class UserActivityResponse(UserActivityCreate):
    id: int
    user_id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# ============= RECOMMENDATION SCHEMAS =============
class ProjectRecommendation(BaseModel):
    project_id: int
    project_name: str
    description: Optional[str]
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    reason: str


class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[ProjectRecommendation]
    generated_at: datetime
