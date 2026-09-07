"""
Botni va FastAPI serverni bitta jarayonda birgalikda ishga tushirish uchun skript.
Foydalanish: python run_all.py
(Yoki ularni alohida-alohida ham ishga tushirish mumkin — README.md ga qarang)
"""
import asyncio
import os
import uvicorn
from dotenv import load_dotenv

from bot.bot import main as run_bot
from webapp.server import app as fastapi_app

load_dotenv()
PORT = int(os.getenv("PORT", "8000"))


async def run_server():
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    await asyncio.gather(run_bot(), run_server())


if __name__ == "__main__":
    asyncio.run(main())
