from sqlmodel import Session, create_engine
from dotenv import load_dotenv
import os

load_dotenv()
url=os.getenv("DATABASE_URL")
engine = create_engine(url)

def get_session():
    with Session(engine) as session:
        yield session