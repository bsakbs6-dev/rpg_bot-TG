import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_BOT_TOKEN
import database as db
from handlers import router

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def set_main_menu(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Начать / Главное меню"),
        BotCommand(command="characters", description="🎭 Выбрать персонажа"),
        BotCommand(command="reset", description="🔄 Сбросить память / Начать заново"),
        BotCommand(command="custom", description="✏️ Создать своего персонажа"),
        BotCommand(command="help", description="📖 Гайд по ролевой игре и команды"),
    ]
    await bot.set_my_commands(commands)

async def main():
    logger.info("Initializing SQLite database...")
    await db.init_db()

    logger.info("Starting Telegram RP Bot...")
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=None)
    )
    dp = Dispatcher()
    dp.include_router(router)

    # Set bot commands menu in Telegram
    try:
        await set_main_menu(bot)
    except Exception as e:
        logger.warning(f"Could not set bot commands: {e}")

    # Drop any pending updates so old messages are not processed on restart
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("Bot is running and listening for Telegram updates! Press Ctrl+C to stop.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
