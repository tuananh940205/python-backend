from models.product import Product


def get_expensive_products(products: list[Product], min_price: float) -> list[Product]:
    return [
        product
        for product in products
        if product.price >= min_price
    ]