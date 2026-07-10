from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = None
    category: str = Field(min_length=2, max_length=50)
    unit: str = Field(min_length=1, max_length=20)
    active: Optional[bool] = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, min_length=2, max_length=50)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=20)
    active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
