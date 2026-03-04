from app.db import Base, engine
from app.models import Ping, User, TypeformResponse, LearningPlan

def init_db():
    Base.metadata.create_all(bind=engine)
