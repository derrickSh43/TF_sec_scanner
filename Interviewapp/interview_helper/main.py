# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
import os
import json
import openai

# --- Runtime toggle (online/offline brain) ---
RUNTIME_MODE: bool = os.getenv("OFFLINE_MODE", "true").lower() in ("1","true","yes")

from database import Base, engine

# Import helper so SQLAlchemy models are registered
import helper
from helper import router as question_templates_router

# Create tables after all models are loaded
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Interview Coach API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the question-templates router
app.include_router(question_templates_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/mode")
def get_mode():
    return {"mode": "offline" if RUNTIME_MODE else "online"}

@app.post("/mode/{new_mode}")
def set_mode(new_mode: str):
    global RUNTIME_MODE
    nm = new_mode.lower()
    
    if nm not in ("online", "offline"):
        return {"error": "mode must be 'online' or 'offline'"}

    RUNTIME_MODE = (nm == "offline")
    return {"mode": "offline" if RUNTIME_MODE else "online"}


# http://127.0.0.1:8000/docs
