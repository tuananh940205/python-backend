from app.schemas.chat import ChatRequest


class ChatService:
    def chat(self, request: ChatRequest):
        return ChatRequest(
            message = f"You asked: {request.message}",
            temperature = request.temperature,
        )