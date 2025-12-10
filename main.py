import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from os import getenv

TOKEN = getenv("BOT_TOKEN")
CHANNEL_ID = "@HoneyAcademka_podslushano"
ADMIN_ID = int(getenv("Xabib_nurmagomedoB"))            

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

moderation_storage = {}  # храним сообщения на модерации

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Привет! Анонимное подслушано школы\n\n"
        "Отправляй секреты, сплетни, мемы, фото и видео — всё пойдёт в канал только после моей проверки.\n\n"
        "<b>Мгновенно отклоняется и бан:</b>\n"
        "• Личные данные, номера, адреса, паспорта и тому подобное\n"
        "Нарушил — больше никогда не напишешь."
    )

# Пользователь прислал что угодно
@dp.message()
async def receive_from_user(message: Message):
    await message.answer("Спасибо, отправил на проверку. Жди.")

    # Кнопки для админа
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Опубликовать", callback_data=f"ok_{message.message_id}"),
            InlineKeyboardButton(text="Отклонить", callback_data=f"no_{message.message_id}")
        ]
    ])

    # Пересылаем админу
    forwarded = await message.forward(ADMIN_ID)
    admin_msg = await bot.send_message(
        ADMIN_ID,
        f"Новое на модерацию (ID пользователя: {message.from_user.id})",
        reply_markup=kb
    )

    # Запоминаем, чтобы потом отредактировать
    moderation_storage[forwarded.message_id] = {
        "user_id": message.from_user.id,
        "original_id": message.message_id,
        "admin_msg_id": admin_msg.message_id
    }

# Админ нажал кнопку
@dp.callback_query(lambda c: c.data and (c.data.startswith("ok_") or c.data.startswith("no_")))
async def process_buttons(callback: CallbackQuery):
    action, orig_msg_id = callback.data.split("_")
    orig_msg_id = int(orig_msg_id)

    info = moderation_storage.pop(orig_msg_id, None)
    if not info:
        await callback.answer("Уже обработано")
        return

    user_id = info["user_id"]

    if action == "ok":
        # Публикуем в канал
        await bot.forward_message(CHANNEL_ID, ADMIN_ID, orig_msg_id)
        await bot.send_message(user_id, "Опубликовано анонимно ✅")
        await callback.message.edit_text("Опубликовано ✅")
    else:
        await bot.send_message(user_id, "Отклонено — нарушает правила.")
        await callback.message.edit_text("Отклонено ❌")

    await callback.answer()

async def main():
    print("Бот с модерацией запущен — всё под контролем")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
