from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chatbot import ChainPilotAgent
from typing import Optional

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CommandRequest(BaseModel):
    command: str
    confirm: Optional[bool] = None

agent = ChainPilotAgent()

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/command")
async def command(request: CommandRequest):
    return agent.process_command(request.command, confirm=request.confirm)