from fastapi import APIRouter, Depends
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService

router = APIRouter(
    prefix = "/chat",
    tags = ["chat"],
)

def get_chat_service() -> ChatService:
    return ChatService()

@router.post("/", response_model = ChatRequest)
def get_chat(request: ChatRequest, service: ChatService = Depends(get_chat_service)):
    return service.chat(request)