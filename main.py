from fastapi import FastAPI
from dotenv import load_dotenv
from adapters.api_router import router as audio_router

load_dotenv()

app = FastAPI(title="Echo API - Hexagonal")

# Include the routes from our API adapter
app.include_router(audio_router)

@app.get("/")
async def root():
    return {"message": "Echo Backend is Online"}