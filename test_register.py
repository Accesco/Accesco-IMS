import asyncio
from app.core.database import async_session_maker
from app.modules.auth.schemas import UserCreate
from app.modules.auth.service import AuthService

async def test():
    async with async_session_maker() as db:
        service = AuthService(db)
        user_data = UserCreate(username="test_script3", email="script3@example.com", password="password", roles=["Viewer"])
        try:
            user = await service.register_user(user_data)
            await db.commit()
            print("Success:", user.id)
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test())
