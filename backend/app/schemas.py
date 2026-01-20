from pydantic import BaseModel
from typing import Optional, Dict, Any


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    meta: Dict[str, Any]


class IngestRequest(BaseModel):
    files: Optional[list[str]] = None


class IngestResponse(BaseModel):
    indexed: int


class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str
