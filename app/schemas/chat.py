from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    temperature: float = 0.7
