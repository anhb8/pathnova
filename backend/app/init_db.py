from .db import Base, engine
from .models import Ping, User, TypeformResponse, LearningPlan

def init_db():
    Base.metadata.create_all(bind=engine)
