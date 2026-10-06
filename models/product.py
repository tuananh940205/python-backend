# Yêu cầu: Product có name:str; price:float
from pydantic import BaseModel


class Product:
    name: str
    price: float

    def init(self, name: str, price: float) -> None:
        self.name = name
        self.price = price