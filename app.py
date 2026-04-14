from fastapi import FastAPI

from core.database import Base, engine
from services.auth.models import User


Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}