from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class RoleEnum(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    MANAGER = "manager"
    CONTRIBUTOR = "contributor"


class Role(Base):
    """Role model for RBAC"""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    users = relationship("User", back_populates="role")


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    role = relationship("Role", back_populates="users")
    teams = relationship("TeamMember", back_populates="user",
                         cascade="all, delete-orphan")
    projects = relationship(
        "ProjectMember", back_populates="user", cascade="all, delete-orphan")
    activities = relationship(
        "UserActivity", back_populates="user", cascade="all, delete-orphan")


class Team(Base):
    """Team model"""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    members = relationship(
        "TeamMember", back_populates="team", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="team")


class TeamMember(Base):
    """Association table for team members"""
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="teams")


class Project(Base):
    """Project model"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # Comma-separated tags for recommendations
    tags = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="projects")
    owner = relationship("User")
    members = relationship(
        "ProjectMember", back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    """Association table for project members"""
    __tablename__ = "project_members"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(50), default="contributor",
                  nullable=False)  # admin, editor, viewer
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="projects")


class UserActivity(Base):
    """User activity tracking for AI recommendations"""
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    # view, comment, edit, assign, etc.
    activity_type = Column(String(50), nullable=False)
    tags = Column(String(500), nullable=True)  # Tags associated with activity
    metadata = Column(Text, nullable=True)  # JSON-like metadata
    timestamp = Column(DateTime, default=datetime.utcnow,
                       nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="activities")
