from fastapi import FastAPI

from core.database import Base, engine
from services.auth.models import User
from services.auth.router import router as auth_router
from services.unesco.routes import router as unesco_router


Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(unesco_router)
