from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import UserCreate, UserLogin
from app.models.auth import User, Role
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.exceptions import UserAlreadyExistsException, InvalidCredentialsException

class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = AuthRepository(db)

    async def register_user(self, user_data: UserCreate) -> User:
        # Check existing username
        existing_user = await self.repo.get_user_by_username(user_data.username)
        if existing_user:
            raise UserAlreadyExistsException("Username is already registered")

        # Check existing email
        existing_email = await self.repo.get_user_by_email(user_data.email)
        if existing_email:
            raise UserAlreadyExistsException("Email is already registered")

        # Resolve roles
        resolved_roles: List[Role] = []
        role_list = user_data.roles or ["Viewer"]
        for role_name in role_list:
            role = await self.repo.get_role_by_name(role_name)
            if not role:
                # Dynamically create role if not found to ensure resilience
                role = Role(name=role_name, description=f"{role_name} role")
                self.repo.db.add(role)
                await self.repo.db.flush()
            resolved_roles.append(role)

        hashed_password = get_password_hash(user_data.password)
        user = await self.repo.create_user(user_data, hashed_password, resolved_roles)
        return user

    async def authenticate_user(self, login_data: UserLogin) -> dict:
        user = await self.repo.get_user_by_username(login_data.username)
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise InvalidCredentialsException()

        role_names = [role.name for role in user.roles]
        token = create_access_token(subject=user.id, roles=role_names)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user
        }

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        return await self.repo.get_user_by_id(user_id)
