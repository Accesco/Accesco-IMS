from pydantic import BaseModel, ConfigDict
from typing import Optional

class ProductBase(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    category: str
    unit: str
    active: Optional[bool] = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
