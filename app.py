from fastapi import FastAPI

from services.auth.router import router as auth_router


app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router, prefix="/auth", tags=["auth"])