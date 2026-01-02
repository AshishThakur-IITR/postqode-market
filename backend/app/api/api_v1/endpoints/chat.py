from fastapi import APIRouter, Depends, HTTPException
from typing import List
import uuid

router = APIRouter()

# Mock Session Store
SESSIONS = {}

@router.post("/session")
def create_session(user_id: str):
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "id": session_id,
        "user_id": user_id,
        "state": "initial",
        "history": []
    }
    return SESSIONS[session_id]

@router.post("/session/{session_id}/message")
def send_message(session_id: str, message: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    session["history"].append({"role": "user", "content": message})
    
    # Simple Mock Logic for "Qode"
    response = "I am Qode. I see you said: " + message
    session["history"].append({"role": "assistant", "content": response})
    
    return session

@router.get("/session/{session_id}")
def get_session(session_id: str):
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    return SESSIONS[session_id]
