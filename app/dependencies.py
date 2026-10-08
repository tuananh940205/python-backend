from app.services.chat_service import ChatService
from app.services.user_service import UserService

def get_user_service() -> UserService:
    return UserService()
def get_chat_service() -> ChatService:
    return ChatService()