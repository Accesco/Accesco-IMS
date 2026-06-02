from fastapi import APIRouter, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.models.auth import User
from app.modules.auth.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
security_scheme = HTTPBearer(auto_error=False)


# Dependency to get current user from token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not credentials:
        raise UnauthorizedException("Missing authentication token")
    
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise UnauthorizedException("Invalid or expired authentication token")
    
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Token payload missing user identifier")
        
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(int(user_id_str))
    if not user:
        raise UnauthorizedException("User not found")
        
    return user


# Class-based role checker dependency
class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        user_roles = [role.name for role in current_user.roles]
        # Admin bypasses role checks
        if "Admin" in user_roles:
            return current_user
            
        for role in self.allowed_roles:
            if role in user_roles:
                return current_user
                
        raise ForbiddenException(f"Role requires one of: {self.allowed_roles}")


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    return await auth_service.register_user(user_data)


@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    return await auth_service.authenticate_user(login_data)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
