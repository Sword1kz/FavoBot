import asyncio
import logging
from aiogram import Bot, Dispatcher
from bot.handlers import router
from dotenv import load_dotenv
import os

load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.include_router(router)

async def main():
    print("╔══════════════════════════════╗")
    print("║        FavoBot v2.3          ║")
    print("║  система приёма заявок       ║")
    print("║     by Alexey & Elaine       ║")
    print("╚══════════════════════════════╝")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
