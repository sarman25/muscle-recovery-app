from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import users, workouts, heatmap, exercises

app = FastAPI(title="Muscle Recovery API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(workouts.router)
app.include_router(heatmap.router)
app.include_router(exercises.router)


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok"}