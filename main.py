from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from adapters.api_router import router as audio_router

load_dotenv()

app = FastAPI(title="Echo API - Hexagonal")

origins = [
    "http://localhost:3000",      # Your local Next.js development server
    "http://127.0.0.1:3000",      # Alternative localhost resolution
    # You will add your Ngrok or Vercel URLs here later during Phase 5
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # Allows specific origins
    allow_credentials=True,       # Allows cookies/session headers to be sent
    allow_methods=["*"],          # Allows all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],          # Allows all headers
)

# Include the routes from our API adapter
app.include_router(audio_router)

# Serve generated audio files so the frontend can play them
app.mount("/temp_audio", StaticFiles(directory="temp_audio"), name="audio")

@app.get("/")
async def root():
    return {"message": "Echo Backend is Online"}