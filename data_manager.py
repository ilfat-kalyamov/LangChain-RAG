import os
import requests
from bs4 import BeautifulSoup
import PyPDF2
import re

path = "data"

def delete_document(file_name):
    delete_path = os.path.join(path, file_name)
    if os.path.exists(delete_path):
        os.remove(delete_path)
        print(f"Файл '{file_name}' удален.")
    else:
        print(f"Файл '{file_name}' не найден.")

def is_url(filename):
    url_pattern = r"^https[^\s]+$"
    if re.match(url_pattern, filename):
        print(filename, " Is url")
        upload_url_file(filename)
    else:
        print(filename, " Not url")
        upload_pdf(filename)

def upload_url_file(url_file):
    with open(f'{os.path.join(path, url_file)}', 'r', encoding='utf-8') as file:
        text = file.read()
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 < 1000:
            current_chunk += (sentence + " ").strip()
        else:
            chunks.append(current_chunk)
            current_chunk = sentence + " "
    if current_chunk:
        chunks.append(current_chunk)
        
    with open("vault.txt", "a", encoding="utf-8") as vault_file:
        for chunk in chunks:
            vault_file.write(chunk.strip() + "\n")
    print(f"URL file content appended to vault.txt with each chunk on a separate line.")
    

def upload_url(url):
    response = requests.get(url)
    response.raise_for_status()  # Выбрасываем исключение, если статус не 200
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text()
    text = re.sub(r'\s+', ' ', text).strip()

    filename = os.path.basename(f"{url.replace('/', '_').replace(':', '').replace('__', '_').replace('__', '_')}") + '.txt'
    filepath = os.path.join(path, filename)
    with open(filepath, 'w', encoding='utf-8') as file:
        file.write(text)

    sentences = re.split(r'(?<=[.!?]) +', text) 
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 < 1000:
            current_chunk += (sentence + " ").strip()
        else:
            chunks.append(current_chunk)
            current_chunk = sentence + " "
    if current_chunk:
        chunks.append(current_chunk)
        
    with open("vault.txt", "a", encoding="utf-8") as vault_file:
        for chunk in chunks:
            vault_file.write(chunk.strip() + "\n")
    print(f"URL content appended to vault.txt with each chunk on a separate line.")

def upload_pdf(file_name):
    file_path = os.path.join(path, file_name)
    with open(file_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        num_pages = len(pdf_reader.pages)
        text = ''
        for page_num in range(num_pages):
            page = pdf_reader.pages[page_num]
            if page.extract_text():
                text += page.extract_text() + " "
        
        # Normalize whitespace and clean up text
        text = re.sub(r'\s+', ' ', text).strip()
           
        # Split text into chunks by sentences, respecting a maximum chunk size
        sentences = re.split(r'(?<=[.!?]) +', text)  # split on spaces following sentence-ending punctuation
        chunks = []
        current_chunk = ""
        for sentence in sentences:
            # Check if the current sentence plus the current chunk exceeds the limit
            if len(current_chunk) + len(sentence) + 1 < 1000:  # +1 for the space
                current_chunk += (sentence + " ").strip()
            else:
                # When the chunk exceeds 1000 characters, store it and start a new one
                chunks.append(current_chunk)
                current_chunk = sentence + " "
        if current_chunk:  # Don't forget the last chunk!
            chunks.append(current_chunk)
        
        with open("vault.txt", "a", encoding="utf-8") as vault_file:
            for chunk in chunks:
                # Write each chunk to its own line
                vault_file.write(chunk.strip() + "\n")  # Two newlines to separate chunks
        print(f"PDF content appended to vault.txt with each chunk on a separate line.")

def refresh_files():
    if os.path.exists("vault.txt"):
        os.remove("vault.txt")
    dir_list = os.listdir(path)
    for item in dir_list:
        is_url(item)