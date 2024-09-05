import openai
import os
from dotenv import load_dotenv

load_dotenv()

system_content = os.getenv("TEXT")

user_content = "How old is Ilfat?"

client = openai.OpenAI(
    api_key="5906f3e9b50948619db441f26d525c0e",
    base_url="https://api.aimlapi.com",
)

chat_completion = client.chat.completions.create(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    messages=[
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ],
    temperature=0.7,
    max_tokens=128,
)

response = chat_completion.choices[0].message.content
print("AI/ML API:\n", response)