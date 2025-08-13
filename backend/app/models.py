from sqlalchemy import Column, Integer, String, TIMESTAMP, text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
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
    email = Column(String, nullable=True)
    form_id = Column(String, nullable=False)
    submission_id = Column(String, unique=True)  # event_id or token
    answers = Column(JSONB, nullable=False)
    received_at = Column(TIMESTAMP, server_default=text("now()"))
