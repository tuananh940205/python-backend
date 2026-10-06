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

# Sau này chạy
# uvicorn app.main:app

if __name__ == "__main__":
    start()