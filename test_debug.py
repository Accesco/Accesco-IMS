import asyncio
from app.core.database import async_session_maker
from app.modules.auth.schemas import UserCreate
from app.modules.auth.service import AuthService
from app.models.auth import Role

async def test():
    async with async_session_maker() as db:
        service = AuthService(db)
        user_data = UserCreate(username="test_script_debug", email="debug@example.com", password="password", roles=["Viewer"])
        try:
            # Replicating AuthService.register_user
            resolved_roles = []
            role_list = user_data.roles or ["Viewer"]
            for role_name in role_list:
                role = await service.repo.get_role_by_name(role_name)
                print(f"Role from DB: {type(role)} - {role}")
                if not role:
                    role = Role(name=role_name, description=f"{role_name} role")
                    service.repo.db.add(role)
                    await service.repo.db.flush()
                    print(f"Role after flush: {type(role)} - {role.id} - {role.name}")
                resolved_roles.append(role)
            
            print(f"Resolved roles: {resolved_roles}")
            hashed_password = "hashed"
            
            # Replicating create_user
            db_user = await service.repo.create_user(user_data, hashed_password, resolved_roles)
            print("Successfully created user")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test())
