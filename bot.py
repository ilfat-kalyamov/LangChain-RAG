import asyncio
import logging
import sys
import os

from data_manager import upload_pdf, delete_document, refresh_files
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = os.getenv("BOT_API")

dp = Dispatcher()

class Form(StatesGroup):
    doc = State()

@dp.message(Command("start"))
async def bot_welcome(message: Message) -> None:
    await message.reply("Привет!\nЯ бот для ответа на вопросы по загруженным тобою документам.\nВведи /help или откройте меню команд в левом нижнем углу для вывода и объяснения всех команд.")

@dp.message(Command("help"))
async def bot_help(message: Message) -> None:
    await message.reply("/start - Сообщение при запуске бота.\n/help - Вывод списка всех команд и их объяснение.\n/upload - Загрузка документа в базу данных.\n/delete - Удаление документа из базы данных.\n/list - Вывод списка добавленных документов.\n/ask - Начинает общение с языковой моделью. Напишите любой вопрос касательно ваших документов.\n/quit - Завершает общение с языковой моделью.")

@dp.message(Command("upload"))
async def bot_upload(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.doc)
    await message.reply("Отправьте документ.\nДля отмены введите любой текст.")

@dp.message(Form.doc)
async def bot_recieve(message: Message, state: FSMContext) -> None:
    await state.clear()
    file_id = message.document.file_id
    if file_id:
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        download_path = "D:/Programming/Projects/LangChain+RAG/data/" + f"{message.document.file_name}"
        await message.bot.download_file(file_path, download_path)
        await message.answer(f"Документ '{message.document.file_name}' получен.")
        upload_pdf(message.document.file_name)
    else:
        await message.answer("Это не документ.")

@dp.message(Command("delete"))
async def send_welcome(message: Message) -> None:
    path = "data"
    dir_list = os.listdir(path)
    builder = InlineKeyboardBuilder()
    file_count = 0
    for item in os.listdir(path):
        if os.path.isfile(os.path.join(path, item)):
            file_count += 1
    for index in range(0, file_count):
        builder.button(text=f"{index+1}. {dir_list[index]}", callback_data=f"{dir_list[index]}")
    builder.adjust(1)
    await message.reply("Выберите документ для удаления.", reply_markup=builder.as_markup())

@dp.callback_query(F.data)
async def callback_anything(callback: CallbackQuery):
    file_to_delete = callback.data
    delete_document(file_to_delete)
    await callback.message.answer(
        text=f"Документ: {file_to_delete} удален.",
        show_alert=True
    )
    await callback.answer()
    refresh_files()


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
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
