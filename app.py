from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.database import Base, engine
from services.auth.models import User
from services.auth.router import router as auth_router
from services.unesco.routes import router as unesco_router
from services.notification.routes import router as notification_router
from services.translation.routes import router as translation_router
from services.payment.routes import router as payment_router

# Skapar databastabeller vid uppstart
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nordic Digital Solutions")

# CORS — tillåter frontend att prata med backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {
        "service": "Nordic Digital Solutions",
        "status": "running",
        "modules": ["auth", "unesco", "notification", "translation", "payment"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# Sam: Autentisering — prefix /auth
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# Sonia: UNESCO-data & Karttjänst — prefix /unesco (satt i routes.py)
app.include_router(unesco_router)

# Riyaaq: Notifikationer — prefix /notification (satt i routes.py)
app.include_router(notification_router)

# Nina: Översättning — prefix /translation (satt i routes.py)
app.include_router(translation_router)

# Nina: Betalning — prefix /payment (satt i routes.py)
app.include_router(payment_router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
