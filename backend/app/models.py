from sqlalchemy import Column, Integer, String, TIMESTAMP, text, ForeignKey, UniqueConstraint, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from .db import Base
from sqlalchemy.orm import relationship

class Ping(Base):
    __tablename__ = "ping"
    id = Column(Integer, primary_key=True, index=True)
    note = Column(String, nullable=False, default="ok")

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String)
    email = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP, server_default=text("now()"))
    responses = relationship("TypeformResponse", backref="user", cascade="all, delete-orphan")
    providers = relationship("AuthProvider", back_populates="user", cascade="all, delete-orphan")

class TypeformResponse(Base):
    __tablename__ = "typeform_responses"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable= True)
    form_id = Column(String, nullable=False)
    submission_id = Column(String, unique=True) 
    answers = Column(JSONB, nullable=False)
    received_at = Column(TIMESTAMP, server_default=text("now()"))

    # User profiles
    career_level = Column(String, nullable=True)
    career_goal = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    target_role = Column(String, nullable=True)
    skills = Column(ARRAY(String), nullable=True)
    career_challenges = Column(ARRAY(String), nullable=True)
    coaching_style = Column(String, nullable=True)
    target_timeline = Column(String, nullable=True)
    study_time = Column(String, nullable=True)
    pressure_response = Column(String, nullable=True)

class LearningPlan(Base):
    __tablename__ = "learning_plans"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))     
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    plan = Column(JSONB, nullable=False)
    model = Column(String, default="gpt-4o")
    input_signature = Column(String, index=True)
    created_at = Column(TIMESTAMP, server_default=text("now()"))

class AuthProvider(Base):
    __tablename__ = "auth_providers"
    provider = Column(Text, primary_key=True)
    provider_user_id = Column(Text, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    email_at_link_time = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="providers")
