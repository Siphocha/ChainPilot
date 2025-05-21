from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from chatbot import ChainPilotAgent
from typing import Optional
from dotenv import load_dotenv
import os
import logging
import logging.handlers
from datetime import datetime

# Configure logging with rotation
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler with rotation
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"chainpilot_api_{datetime.now().strftime('%Y%m%d')}.log")
file_handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=10*1024*1024, backupCount=5
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Load environment variables
load_dotenv()
logger.info(f"Dotenv file loaded: {os.getenv('WALLET_ADDRESS') is not None}")
logger.info(f"Loaded env vars: WALLET_ADDRESS={os.getenv('WALLET_ADDRESS')}, PRIVATE_KEY={os.getenv('WALLET_PRIVATE_KEY')}")

# Validate required environment variables
required_env_vars = [
    "WALLET_ADDRESS",
    "WALLET_PRIVATE_KEY",
    "NETWORK_RPC_URL",
    "NETWORK_CHAIN_ID",
    "CONTRACT_EXECUTOR_ADDRESS",
    "CONTRACT_SCHEDULER_ADDRESS",
    "ALCHEMY_API_KEY",
    "BASESCAN_API_KEY"
]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize FastAPI app
app = FastAPI(
    title="ChainPilot API",
    version="1.0.0",
    description="API for ChainPilot AI Agent on Base mainnet. Supports actions like sending tokens, scheduling transfers, and managing tasks.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
frontend_url = os.getenv("FRONTEND_URL", "https://chain-pilot-drab.vercel.app")
origins = [
    "http://localhost:3000",  # Development
    frontend_url,             # Deployed Vercel frontend
]
if os.getenv("RENDER") != "true":
    origins.append("*")  # Allow all origins for local testing

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

class CommandRequest(BaseModel):
    command: str
    confirm: Optional[bool] = None

class CommandResponse(BaseModel):
    status: str
    message: str
    tx_hash: Optional[str] = None
    jobs: Optional[list] = None

# Initialize agent
def initialize_agent(max_retries=3):
    for attempt in range(max_retries):
        try:
            agent = ChainPilotAgent()
            logger.info("ChainPilotAgent initialized successfully.")
            return agent
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to initialize ChainPilotAgent: {str(e)}")
            if attempt == max_retries - 1:
                logger.error(f"Failed to initialize ChainPilotAgent after {max_retries} attempts: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to initialize ChainPilotAgent: {str(e)}")
            continue

agent = initialize_agent()

# Custom exception handler
@app.exception_handler(Exception)
async def custom_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": f"An unexpected error occurred: {str(exc)}"},
    )

@app.get(
    "/",
    summary="Root endpoint for Render health check",
    response_model=dict,
)
async def root():
    return {"status": "healthy"}

@app.get(
    "/health",
    summary="Check API health",
    response_model=dict,
)
async def health():
    return {"status": "healthy"}

@app.options("/command")
async def options_command():
    logger.info("Received OPTIONS request for /command")
    return Response(status_code=200)

@app.post(
    "/command",
    summary="Execute a ChainPilot command",
    description="Supported commands: check_executor_permissions, check_scheduler_permissions, send_tokens, schedule_transfers, list_tasks, cancel_tasks, help.",
    response_model=CommandResponse,
)
async def command(request: CommandRequest, req: Request):
    client_ip = req.client.host
    logger.info(f"Received {req.method} request for command: {request.command} from IP: {client_ip}")
    try:
        response = agent.process_command(request.command, confirm=request.confirm)
        if response.get("status") == "error":
            logger.warning(f"Command failed: {response.get('message')} from IP: {client_ip}")
            raise HTTPException(status_code=400, detail={"error": response.get("message", "Command execution failed")})
        logger.info("Command executed successfully.")
        return CommandResponse(**response)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing command: {str(e)} from IP: {client_ip}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": f"Error processing command: {str(e)}"})

@app.on_event("startup")
async def startup_event():
    logger.info("ChainPilot API started.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("ChainPilot API shutting down.")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting Uvicorn server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)