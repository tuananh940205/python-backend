from fastapi import APIRouter, Depends
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService
from app.dependencies import get_chat_service

router = APIRouter(
    prefix = "/chat",
    tags = ["chat"],
)

@router.post("/", response_model = ChatRequest)
def get_chat(request: ChatRequest, service: ChatService = Depends(get_chat_service)):
    return service.chat(request)