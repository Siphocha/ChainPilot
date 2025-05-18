from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chatbot import ChainPilotAgent
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="ChainPilot API", version="1.0.0")

# Add CORS middleware with dynamic origins for production
origins = [
    "http://localhost:3000",  # Development
    "https://chain-pilot-drab.vercel.app"  # Production frontend
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandRequest(BaseModel):
    command: str
    confirm: Optional[bool] = None

try:
    agent = ChainPilotAgent()
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to initialize ChainPilotAgent: {str(e)}")

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/command")
async def command(request: CommandRequest):
    try:
        response = agent.process_command(request.command, confirm=request.confirm)
        if response.get("status") == "error":
            raise HTTPException(status_code=400, detail=response.get("message", "Command execution failed"))
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing command: {str(e)}")