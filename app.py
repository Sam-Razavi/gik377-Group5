from fastapi import FastAPI
import uvicorn
# Vi importerar din router (som vi ändrar i nästa steg)
from services.notification.routes import notification_router

app = FastAPI(title="Nordic Digital Solutions")

# Registrera modulen med FastAPI:s motsvarighet till Blueprints
app.include_router(notification_router)

@app.get("/")
async def root():
    return {
        "service": "Nordic Digital Solutions",
        "status": "running",
        "modules": ["notification"],
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
