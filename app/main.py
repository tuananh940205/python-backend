from pydantic import BaseModel
from models.product import Product
from services import product_service
from fastapi import FastAPI


def start() -> None:
    print("AI backend starting...")
    # input_products = [
    #     Product(name = "A", price = 100),
    #     Product(name = "B", price = 500),
    #     Product(name = "C", price = 1000),
    #     Product(name = "D", price = 50),
    # ]
    # expensive_products = product_service.get_expensive_products(input_products, 500)
    # print("expensive products:", expensive_products)
    # uvicorn app.main:app --reload


# Dùng command `uvicorn app.main:create_app --factory --reload`
def create_app() -> FastAPI:
    app = FastAPI()
    @app.get("/")
    def root():
        return {
            "message": "Hello World"
        }
    return app

# uvicorn app.main:create_app_say_hello --factory --reload
def create_app_say_hello() -> FastAPI:
    app = FastAPI()
    @app.get("/hello")
    def root():
        return {
            "message": "Hello New AI engineer"
        }
    return app

# uvicorn app.main:create_app_say_hello_query_parameter --factory --reload
# http://127.0.0.1:8000/hello?name=Tuan%20Anh
def create_app_say_hello_query_parameter() -> FastAPI:
    app = FastAPI()
    @app.get("/hello")
    def root(name: str):
        return {
            "message": f"Hello {name}"
        }
    return app

# uvicorn app.main:create_app_say_hello_query_with_default --factory --reload
# http://127.0.0.1:8000/hello?name=Tuan%20Anh
def create_app_say_hello_query_with_default() -> FastAPI:
    app = FastAPI()
    @app.get("/hello")
    def root(name: str = "World"):
        return {
            "message": f"Hello {name}"
        }
    return app

# path parameter
# uvicorn app.main:create_app_query_parameter --factory --reload
# http://127.0.0.1:8000/users/15
# Tự validate parameter type
def create_app_query_parameter() -> FastAPI:
    app = FastAPI()
    @app.get("/users/{user_id}")
    def root(user_id: int):
        return {
            "user_id": user_id
        }
    return app

# Path + Query kết hợp
# uvicorn app.main:create_app_path_query_combination --factory --reload
# http://127.0.0.1:8000/users/15?verbose=true
def create_app_path_query_combination() -> FastAPI:
    app = FastAPI()
    @app.get("/users/{user_id}")
    def get_user(user_id: int, verbose: bool = False):
        return {
            "user_id": user_id,
            "verbose": verbose
        }

    return app

# POST method
# uvicorn app.main:create_app_post --factory --reload
# http://127.0.0.1:8000/docs#/default/chat_chat_post
def create_app_post() -> FastAPI:
    app = FastAPI()
    @app.post("/chat")
    def chat(request: ChatRequest):
        return {
            "message": f"You just chat: {request.text}"
        }
    return app

class ChatRequest(BaseModel):
    text: str

# Chatbot
class ChatRequest_2(BaseModel):
    message: str
    conversation_id: int
# uvicorn app.main:create_app_post_2 --factory --reload
# http://127.0.0.1:8000/docs#/default/chat_chat_post
def create_app_post_2() -> FastAPI:
    app = FastAPI()
    @app.post("/chat")
    def chat(request: ChatRequest_2):
        return {
            "message": f"{request.message} là",
            "conversation_id": request.conversation_id
        }
    return app

# Sau này chạy
# uvicorn app.main:app

if __name__ == "__main__":
    start()