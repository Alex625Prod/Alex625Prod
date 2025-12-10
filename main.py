import asyncio
import logging
from os import getenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем переменные среды
TOKEN = getenv("BOT_TOKEN")
ADMIN_ID = getenv("ADMIN_ID")
CHANNEL_ID = getenv("CHANNEL_ID")

# Вместо выбрасывания ошибки сразу, проверяем при запуске
if not TOKEN:
    logger.error("❌ BOT_TOKEN не найден в переменных среды Railway")
    logger.info("👉 Добавьте BOT_TOKEN в раздел Variables вашего проекта в Railway")
if not ADMIN_ID:
    logger.error("❌ ADMIN_ID не найден в переменных среды Railway")
if not CHANNEL_ID:
    logger.error("❌ CHANNEL_ID не найден в переменных среды Railway")

# Инициализация бота и диспетчера
try:
    bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    logger.info("✅ Бот инициализирован")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации бота: {e}")
    exit(1)

moderation_storage = {}  # хранение сообщений на модерации

# --- Команда /start ---
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Привет! Анонимное подслушано школы\n\n"
        "Отправляй секреты, сплетни, мемы, фото и видео — всё пойдёт в канал только после моей проверки.\n\n"
        "<b>Мгновенно отклоняется и бан:</b>\n"
        "• Личные данные, номера, адреса, паспорта и тому подобное\n"
        "Нарушил — больше никогда не напишешь."
    )

# --- Получаем сообщения от пользователя ---
@dp.message()
async def receive_from_user(message: Message):
    if message.text and message.text.startswith('/'):
        return  # Игнорируем команды
    
    await message.answer("Спасибо, отправил на проверку. Жди.")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"ok_{message.message_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"no_{message.message_id}")
        ]
    ])

    # Пересылаем сообщение администратору
    try:
        forwarded = await message.forward(chat_id=ADMIN_ID)
        admin_msg = await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📩 Новое на модерацию\nID пользователя: {message.from_user.id}",
            reply_markup=kb
        )

        moderation_storage[forwarded.message_id] = {
            "user_id": message.from_user.id,
            "original_id": message.message_id,
            "admin_msg_id": admin_msg.message_id,
            "user_chat_id": message.chat.id
        }
        logger.info(f"Сообщение от {message.from_user.id} отправлено на модерацию")
    except Exception as e:
        logger.error(f"Ошибка при пересылке: {e}")
        await message.answer("Произошла ошибка при отправке на модерацию")

# --- Обработка кнопок админа ---
@dp.callback_query(lambda c: c.data and (c.data.startswith("ok_") or c.data.startswith("no_")))
async def process_buttons(callback: CallbackQuery):
    try:
        action, orig_msg_id = callback.data.split("_")
        orig_msg_id = int(orig_msg_id)

        info = moderation_storage.pop(orig_msg_id, None)
        if not info:
            await callback.answer("Уже обработано")
            return

        user_id = info["user_id"]
        user_chat_id = info.get("user_chat_id", user_id)

        if action == "ok":
            # Публикуем в канал
            await bot.forward_message(
                chat_id=CHANNEL_ID,
                from_chat_id=ADMIN_ID,
                message_id=orig_msg_id
            )
            await bot.send_message(chat_id=user_chat_id, text="✅ Опубликовано анонимно")
            await callback.message.edit_text("✅ Опубликовано в канал")
            logger.info(f"Сообщение {orig_msg_id} опубликовано в канал")
        else:
            # Отклоняем
            await bot.send_message(chat_id=user_chat_id, text="❌ Отклонено — нарушает правила.")
            await callback.message.edit_text("❌ Отклонено")
            logger.info(f"Сообщение {orig_msg_id} отклонено")

        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка обработки кнопки: {e}")
        await callback.answer("Произошла ошибка")

# --- Запуск бота ---
async def main():
    try:
        logger.info("🚀 Бот с модерацией запущен")
        logger.info(f"Admin ID: {ADMIN_ID}")
        logger.info(f"Channel ID: {CHANNEL_ID}")
        
        # Удаляем вебхук если был
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Запускаем поллинг
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
