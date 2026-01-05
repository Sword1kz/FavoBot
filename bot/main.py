import asyncio
import logging
import os

import asyncpg
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from bot.handlers import router
from init_db_pg import init_db

load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.include_router(router)

async def main():
    print("╔══════════════════════════════╗")
    print("║        FavoBot v2.3          ║")
    print("║  система приёма заявок       ║")
    print("║     by Alexey & Elaine       ║")
    print("╚══════════════════════════════╝")

    if not TOKEN:
        raise RuntimeError("BOT_TOKEN не найден в .env / Railway variables")

    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL не найден в .env / Railway variables")

    pool = await asyncpg.create_pool(DATABASE_URL)
    await init_db(pool)

    dp["db"] = pool  # чтобы хэндлеры могли достать pool

    try:
        await dp.start_polling(bot)
    finally:
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
