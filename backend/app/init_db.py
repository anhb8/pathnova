from .db import Base, engine
from .models import Ping, User, TypeformResponse 

def init_db():
    Base.metadata.create_all(bind=engine)
