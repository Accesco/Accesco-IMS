import asyncio
from app.core.database import async_session_maker
from sqlalchemy import text

async def test():
    async with async_session_maker() as db:
        result = await db.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'roles'"))
        columns = result.fetchall()
        for col in columns:
            print(col)

if __name__ == "__main__":
    asyncio.run(test())
