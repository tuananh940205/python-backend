# Yêu cầu: Product có name:str; price:float
from pydantic import BaseModel

class Product(BaseModel):
    name: str
    price: float