from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class RoleEnum(str, enum.Enum):
    """Application roles (RBAC).

    Mapping to the course spec:
      ADMIN       → Tech Lead / Arquiteto
      MANAGER     → Gerente de Projetos (PM)
      CONTRIBUTOR → Desenvolvedor
    """
    ADMIN = "admin"
    MANAGER = "manager"
    CONTRIBUTOR = "contributor"


# Project-member roles
PROJECT_MEMBER_ROLES = ("admin", "editor", "viewer", "contributor")


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    role = relationship("Role", back_populates="users", lazy="joined")
    teams = relationship("TeamMember", back_populates="user",
                         cascade="all, delete-orphan")
    projects = relationship("ProjectMember", back_populates="user",
                            cascade="all, delete-orphan")
    activities = relationship("UserActivity", back_populates="user",
                              cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    members = relationship("TeamMember", back_populates="team",
                           cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_member"),
    )

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="teams", lazy="joined")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tags = Column(String(500), nullable=True)  # comma-separated, used by recommender
    is_active = Column(Boolean, default=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow,
                        onupdate=datetime.utcnow, nullable=False)

    team = relationship("Team", back_populates="projects", lazy="joined")
    owner = relationship("User", lazy="joined")
    members = relationship("ProjectMember", back_populates="project",
                           cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_member"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(50), default="contributor", nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="projects", lazy="joined")


class UserActivity(Base):
    """User activity log used by the AI recommender.

    NOTE: the attribute used to be named ``metadata`` but that name is
    reserved by SQLAlchemy's declarative Base — renamed to ``extra_data``.
    """
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    activity_type = Column(String(50), nullable=False)  # view, comment, edit, assign, ...
    tags = Column(String(500), nullable=True)
    extra_data = Column(Text, nullable=True)  # free-form JSON-ish payload
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="activities")
