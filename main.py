from fastapi import FastAPI

app = FastAPI(title="Echo API")

@app.get("/")
async def root():
    return {"message": "Echo Backend is Online"}