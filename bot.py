import asyncio
import logging
import sys
import os

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

TOKEN = os.getenv("BOT_API")

dp = Dispatcher()

@dp.message(Command("start"))
async def send_welcome(message: Message) -> None:
    await message.reply("Привет!\nЯ бот для ответа на вопросы по загруженным тобою документам.\nВведи /help или откройте меню команд в левом нижнем углу для вывода и объяснения всех команд.")

@dp.message(Command("help"))
async def send_welcome(message: Message) -> None:
    await message.reply("/start - Сообщение при запуске бота.\n/help - Вывод списка всех команд и их объяснение.\n/upload - Загрузка документа в базу данных.\n/delete - Удаление документа из базы данных.\n/list - Вывод списка добавленных документов.\n/ask - Начинает общение с языковой моделью. Напишите любой вопрос касательно ваших документов.\n/quit - Завершает общение с языковой моделью.")

@dp.message(Command("upload"))
async def send_welcome(message: Message) -> None:
    await message.reply("Отправьте документ.")

@dp.message(Command("delete"))
async def send_welcome(message: Message) -> None:
    await message.reply("Выберите документ для удаления.")

@dp.message(Command("ask"))
async def send_welcome(message: Message) -> None:
    await message.reply("Вы начали общение с языковой моделью. Задавайте любые вопросы касательно ваших документов.")

@dp.message(Command("quit"))
async def send_welcome(message: Message) -> None:
    await message.reply("Вы завершили общение с языковой моделью.")

@dp.message(Command("list"))
async def send_welcome(message: Message) -> None:
    path = "data"
    dir_list = os.listdir(path)

    msg = "Список загруженных вами документов:\n\n"
    for i, file in enumerate(dir_list, 1):
        msg += f"{i}. {file}\n"

    await message.answer(msg) 

@dp.message()
async def send_welcome(message: Message) -> None:
    await message.reply("Сообщение получено. Пожалуйста, ожидайте ответа.")
    await message.answer(message.text)

async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
