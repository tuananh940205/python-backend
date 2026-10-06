from models.product import Product
from services import product_service

def start() -> None:
    print("AI backend starting...")
    input_products = [
        Product(name = "A", price = 100),
        Product(name = "B", price = 500),
        Product(name = "C", price = 1000),
        Product(name = "D", price = 50),
    ]
    expensive_products = product_service.get_expensive_products(input_products, 500)
    print("expensive products:", expensive_products)

# Sau này chạy
# uvicorn app.main:app

if __name__ == "__main__":
    start()