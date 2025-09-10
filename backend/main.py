from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

app = FastAPI()

# In-memory storage for bounces (replace with database later)
bounces = []

# Pydantic model for the request body
class BounceCreate(BaseModel):
    title: str
    date: datetime
    friend: Optional[str] = None

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running!"}

@app.post("/bounces", status_code=201)
async def create_bounce(bounce: BounceCreate):
    try:
        # Convert to dict and store in memory (replace with database logic)
        bounce_data = bounce.dict()
        bounces.append(bounce_data)
        return {"message": "Bounce created successfully", "bounce": bounce_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create bounce: {str(e)}")



