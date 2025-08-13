from sqlalchemy import Column, Integer, String, TIMESTAMP, text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from .db import Base

class Ping(Base):
    __tablename__ = "ping"
    id = Column(Integer, primary_key=True, index=True)
    note = Column(String, nullable=False, default="ok")

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    email = Column(String, unique=True, index=True)
    created_at = Column(TIMESTAMP, server_default=text("now()"))
    

class TypeformResponse(Base):
    __tablename__ = "typeform_responses"
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable= True)
    form_id = Column(String, nullable=False)
    submission_id = Column(String, unique=True) 
    answers = Column(JSONB, nullable=False)
    received_at = Column(TIMESTAMP, server_default=text("now()"))

    # User profiles
    name = Column(String)
    email = Column(String, nullable=True)
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
   
