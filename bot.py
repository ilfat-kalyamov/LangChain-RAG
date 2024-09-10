import asyncio
import logging
import sys
import os
import json
import ollama
import torch
import argparse
import re

from openai import OpenAI
from data_manager import upload_pdf, delete_document, refresh_files, upload_url
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

parser = argparse.ArgumentParser(description="Ollama Chat")
parser.add_argument("--model", default="mistral", help="Ollama model to use (default: mistral)")
args = parser.parse_args()
conversation_history = []
system_message = ""
vault_content = []
vault_embeddings = []
vault_embeddings_tensor = torch.tensor(vault_embeddings)

client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='mistral'
)

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

# Function to get relevant context from the vault based on user input
def get_relevant_context(rewritten_input, vault_embeddings, vault_content, top_k=3):
    if vault_embeddings.nelement() == 0:  # Check if the tensor has any elements
        return []
    # Encode the rewritten input
    input_embedding = ollama.embeddings(model='mxbai-embed-large', prompt=rewritten_input)["embedding"]
    # Compute cosine similarity between the input and vault embeddings
    cos_scores = torch.cosine_similarity(torch.tensor(input_embedding).unsqueeze(0), vault_embeddings)
    # Adjust top_k if it's greater than the number of available scores
    top_k = min(top_k, len(cos_scores))
    # Sort the scores and get the top-k indices
    top_indices = torch.topk(cos_scores, k=top_k)[1].tolist()
    # Get the corresponding context from the vault
    relevant_context = [vault_content[idx].strip() for idx in top_indices]
    return relevant_context

def rewrite_query(user_input_json, conversation_history, ollama_model):
    user_input = json.loads(user_input_json)["Query"]
    context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history[-2:]])
    prompt = f"""Перепишите следующий запрос, включив в него соответствующий контекст из истории переписки.
    Переписанный запрос должен:
    
    - Сохранить основную цель и смысл исходного запроса
    - Расширить и уточнить запрос, чтобы сделать его более конкретным и информативным для получения соответствующего контекста.
    - Избегайте введения новых тем или запросов, которые отличаются от исходного запроса
    - НИКОГДА НЕ ОТВЕЧАЙТЕ на исходный запрос, а вместо этого сосредоточьтесь на перефразировании и расширении его в новом запросе
    
    Возвращайте ТОЛЬКО переписанный текст запроса, без какого-либо дополнительного форматирования или пояснений.
    
    История обсуждения:
    {context}
    
    Исходный запрос: [{user_input}]
    
    Переписанный запрос: 
    """
    response = client.chat.completions.create(
        model=ollama_model,
        messages=[{"role": "system", "content": prompt}],
        max_tokens=200,
        n=1,
        temperature=0.1,
    )
    rewritten_query = response.choices[0].message.content.strip()
    return json.dumps({"Rewritten Query": rewritten_query})
   
def ollama_chat(user_input, system_message, vault_embeddings, vault_content, ollama_model, conversation_history):
    conversation_history.append({"role": "user", "content": user_input})
    
    if len(conversation_history) > 1:
        query_json = {
            "Query": user_input,
            "Rewritten Query": ""
        }
        rewritten_query_json = rewrite_query(json.dumps(query_json), conversation_history, ollama_model)
        rewritten_query_data = json.loads(rewritten_query_json)
        rewritten_query = rewritten_query_data["Rewritten Query"]
    else:
        rewritten_query = user_input
    
    relevant_context = get_relevant_context(rewritten_query, vault_embeddings, vault_content)
    if relevant_context:
        context_str = "\n".join(relevant_context)
    
    user_input_with_context = user_input
    if relevant_context:
        user_input_with_context = user_input + "\n\Подходящий контекст:\n" + context_str
    
    conversation_history[-1]["content"] = user_input_with_context
    
    messages = [
        {"role": "system", "content": system_message},
        *conversation_history
    ]
    
    response = client.chat.completions.create(
        model=ollama_model,
        messages=messages,
        max_tokens=2000,
    )
    
    conversation_history.append({"role": "assistant", "content": response.choices[0].message.content})
    
    return response.choices[0].message.content

TOKEN = os.getenv("BOT_API")

dp = Dispatcher()

class Form(StatesGroup):
    doc = State()
    chat = State()

@dp.message(Command("start"))
async def bot_welcome(message: Message) -> None:
    await message.reply("Привет!\nЯ бот для ответа на вопросы по загруженным тобою документам.\nВведи /help или откройте меню команд в левом нижнем углу для вывода и объяснения всех команд.")

@dp.message(Command("help"))
async def bot_help(message: Message) -> None:
    await message.reply("/start - Сообщение при запуске бота.\n/help - Вывод списка всех команд и их объяснение.\n/upload - Загрузка документа в базу данных.\n/delete - Удаление документа из базы данных.\n/list - Вывод списка добавленных документов.\n/ask - Начинает общение с языковой моделью. Напишите любой вопрос касательно ваших документов.\n/quit - Завершает общение с языковой моделью.")

@dp.message(Command("refresh"))
async def bot_upload(message: Message) -> None:
    refresh_files()
    await message.reply("База данных пересобрана.")

@dp.message(Command("upload"))
async def bot_upload(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.doc)
    await message.reply("Отправьте документ или ссылку.\nДля отмены введите любой текст.")

@dp.message(Form.doc)
async def bot_recieve(message: Message, state: FSMContext) -> None:
    await state.clear()
    
    if message.document:
        file_id = message.document.file_id
        if file_id:
            await message.answer("Вы отправили документ.")
            file = await message.bot.get_file(file_id)
            file_path = file.file_path
            download_path = "D:/Programming/Projects/LangChain+RAG/data/" + f"{message.document.file_name}"
            await message.bot.download_file(file_path, download_path)
            await message.answer(f"Документ '{message.document.file_name}' получен.")
            upload_pdf(message.document.file_name)
        else:
            await message.answer("Это не документ и не ссылка. Действие отменено.")
    else:
        url_pattern = r"^https?://[^\s]+$"
        if re.match(url_pattern, message.text):
            await message.answer("Вы отправили ссылку.")
            upload_url(message.text)

@dp.message(Command("delete"))
async def bot_delete(message: Message) -> None:
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
async def bot_ask(message: Message, state: FSMContext) -> None:
    await state.set_state(Form.chat)

    # Load the vault content
    await message.answer("Загрузка содержимого хранилища...")
    vault_content = []
    if os.path.exists("vault.txt"):
        with open("vault.txt", "r", encoding='utf-8') as vault_file:
            vault_content = vault_file.readlines()

    # Generate embeddings for the vault content using Ollama
    await message.answer("Создание вложений для содержимого хранилища...")
    vault_embeddings = []
    for content in vault_content:
        response = ollama.embeddings(model='mxbai-embed-large', prompt=content)
        vault_embeddings.append(response["embedding"])

    # Convert to tensor and print embeddings
    await message.answer("Преобразование вложений в тензор...")
    vault_embeddings_tensor = torch.tensor(vault_embeddings)

    # Conversation loop
    print("Starting conversation loop...")
    conversation_history = []
    system_message = "Вы - полезный ассистент, который является экспертом в извлечении наиболее полезной информации из заданного текста. Также добавляйте дополнительную релевантную информацию к запросу пользователя вне данного контекста."

    await message.reply("Вы начали общение с языковой моделью. Задавайте любые вопросы касательно ваших документов.")

@dp.message(Form.chat)
async def bot_chat(message: Message, state: FSMContext) -> None:
    user_input = message.text
    if user_input == "/quit":
        await state.clear()
        await message.answer("Вы закончили общение с языковой моделью.")
    else:
        response = ollama_chat(user_input, system_message, vault_embeddings_tensor, vault_content, args.model, conversation_history)
        await message.answer("Ответ: \n\n" + response)
        
    
@dp.message(Command("quit"))
async def bot_quit(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.reply("Вы завершили общение с языковой моделью.")

@dp.message(Command("list"))
async def bot_list(message: Message) -> None:
    path = "data"
    dir_list = os.listdir(path)

    msg = "Список загруженных вами документов:\n\n"
    for i, file in enumerate(dir_list, 1):
        msg += f"({i}). {file}\n"

    await message.answer(msg)

@dp.message()
async def bot_default(message: Message) -> None:
    await message.reply("Неправильно введена команда. Воспользуйтесь командой /help.")

async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
