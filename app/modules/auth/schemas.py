from pydantic import BaseModel, EmailStr, ConfigDict,Field
from typing import List, Optional

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleResponse(RoleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=30)
    roles: Optional[List[str]] = ["Viewer"]  # Default role is Viewer

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    roles: List[RoleResponse] = []
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
