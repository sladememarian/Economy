import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from app.config import BOT_TOKEN
from app.bot.handlers.start import router as start_router
from app.database.db import init_database
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode




PROXY_URL = "socks5://127.0.0.1:10808"


async def main() -> None:
   
    await init_database()

    # اتصال Telegram از طریق Proxy
    session = AiohttpSession(
        proxy=PROXY_URL,
    )

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
         ),
)   

    dp = Dispatcher()

    
    dp.include_router(start_router)

    try:
        print("🎮 بازی در حال اجراست...")
        print("💾 دیتابیس آماده شد")
        print("🤖 ربات آماده دریافت پیام است")

        await dp.start_polling(bot)

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())