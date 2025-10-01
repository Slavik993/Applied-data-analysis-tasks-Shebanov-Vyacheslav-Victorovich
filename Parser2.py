import warnings
warnings.filterwarnings("ignore")

# БИБЛИОТЕКИ
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import time
import random
import re
import string
import pandas as pd
import os
from urllib.parse import urljoin
from datetime import datetime
import nltk
from nltk import word_tokenize
from nltk.corpus import stopwords
import pymorphy2
import spacy
import inspect
from googleapiclient.discovery import build  # Для Google Search API

print("🔧 Инициализация библиотек...")

# ФИКС NLTK
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Скачиваем NLTK ресурсы...")
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('stopwords', quiet=True)
print("  ✅ NLTK готов")

# ФИКС PYMORPHY2
original_getargspec = inspect.getargspec
def getargspec_patch(func):
    if func.__name__ == '__init__':
        full_args = inspect.getfullargspec(func)
        return full_args.args, full_args.varargs, full_args.varkw, full_args.defaults
    else:
        return original_getargspec(func)
inspect.getargspec = getargspec_patch

morph = pymorphy2.MorphAnalyzer()
print("  ✅ Pymorphy2 готов")

# SPACY ДЛЯ АНГЛИЙСКОГО
try:
    nlp = spacy.load('en_core_web_sm')
except:
    print("Скачиваем spaCy модель: python -m spacy download en_core_web_sm")
    os.system('python -m spacy download en_core_web_sm')
    nlp = spacy.load('en_core_web_sm')
print("  ✅ spaCy готов")

# СТОП-СЛОВА
stop_words = set(stopwords.words('english') + stopwords.words('russian'))
print("  ✅ Стоп-слова загружены")

# СПИСОК ИГР
GAMES = [
    "Hollow Knight", "Hollow Knight Silksong", "Platypus",
    "Hard Truck Apocalypse", "No Man's Sky", "Moonlighter", "Minecraft"
]

# GOOGLE SEARCH API (для 1000 URL)
def get_search_urls(query, api_key, cse_id, num_results=10):
    try:
        service = build("customsearch", "v1", developerKey=api_key)
        result = service.cse().list(q=query, cx=cse_id, num=num_results).execute()
        urls = [item['link'] for item in result.get('items', [])]
        return urls
    except Exception as e:
        print(f"⚠ Ошибка Google Search API: {e}")
        return []

# ЗАГЛУШКА URL (для демонстрации без API)
BASE_URLS = [
    # Hollow Knight
    "https://en.wikipedia.org/wiki/Hollow_Knight",
    "https://hollowknight.fandom.com/wiki/Hollow_Knight",
    "https://store.steampowered.com/app/367520/Hollow_Knight",
    "https://www.metacritic.com/game/pc/hollow-knight",
    "https://www.ign.com/articles/2018/06/22/hollow-knight-review",
    "https://www.pcgamer.com/hollow-knight-review",
    "https://www.gamespot.com/reviews/hollow-knight-review-an-exceptional-adventure/1900-6416972",
    # Hollow Knight Silksong
    "https://hollowknight.fandom.com/wiki/Silksong",
    "https://www.pcgamer.com/games/action/hollow-knight-silksong-review",
    "https://www.metacritic.com/game/pc/hollow-knight-silksong",
    # Platypus
    "https://en.wikipedia.org/wiki/Platypus_(video_game)",
    "https://store.steampowered.com/app/307340/Platypus",
    "https://www.mobygames.com/game/10766/platypus",
    # Hard Truck Apocalypse
    "https://en.wikipedia.org/wiki/Hard_Truck_Apocalypse",
    "https://store.steampowered.com/app/307320/Hard_Truck_Apocalypse",
    "https://www.mobygames.com/game/14994/hard-truck-apocalypse",
    # No Man's Sky
    "https://en.wikipedia.org/wiki/No_Man%27s_Sky",
    "https://www.nomanssky.com/news",
    "https://store.steampowered.com/app/275850/No_Mans_Sky",
    "https://www.ign.com/articles/no-mans-sky-review",
    # Moonlighter
    "https://en.wikipedia.org/wiki/Moonlighter_(video_game)",
    "https://store.steampowered.com/app/606150/Moonlighter",
    "https://www.ign.com/games/moonlighter",
    # Minecraft
    "https://en.wikipedia.org/wiki/Minecraft",
    "https://www.minecraft.net/en-us",
    "https://minecraft.fandom.com/wiki/Minecraft_Wiki",
    "https://www.ign.com/games/minecraft",
] * 40  # ~1000 URL (для примера)

# ПОЛУЧЕНИЕ 1000 URL ЧЕРЕЗ GOOGLE SEARCH API
# Замените на свои ключи:
# API_KEY = "YOUR_GOOGLE_API_KEY"
# CSE_ID = "YOUR_CUSTOM_SEARCH_ENGINE_ID"
# urls = []
# for game in GAMES:
#     urls.extend(get_search_urls(game + " game review", API_KEY, CSE_ID, num_results=30))
# unique_urls = list(dict.fromkeys(urls))[:1000]  # 1000 уникальных
unique_urls = list(dict.fromkeys(BASE_URLS))[:1000]  # Заглушка
print(f"\n📚 Уникальных URL для парсинга: {len(unique_urls)}")

# HTTP СЕССИЯ
def create_http_session():
    session = requests.Session()
    ua = UserAgent()
    session.headers.update({'User-Agent': ua.random})
    return session

# ПАРСИНГ СТРАНИЦЫ
def parse_page(url, session, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string.strip() if soup.title else 'No Title'
            content = soup.find_all(['p', 'div', 'article'])
            raw_text = ' '.join([elem.get_text(strip=True) for elem in content if elem.get_text(strip=True)])
            if not raw_text or len(raw_text) < 100:
                return None
            date = datetime.now().strftime('%Y-%m-%d')  # Заглушка
            return {'title': title, 'raw_text': raw_text[:5000], 'date': date}
        except (requests.RequestException, Exception) as e:
            print(f"⚠ Ошибка при парсинге {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(random.uniform(1, 3))
    return None

# ОЧИСТКА И ЛЕММАТИЗАЦИЯ
def clean_text(raw_text, is_russian=False):
    # Удаление HTML-тегов, чисел, пунктуации
    text = re.sub(r'<[^>]+>', ' ', raw_text)
    text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
    text = re.sub(r'\d+\.?\d*', ' ', text)
    text = re.sub(r'[{}]'.format(string.punctuation), ' ', text)
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Токенизация
    tokens = word_tokenize(text.lower())
    
    # Лемматизация
    if is_russian:
        tokens = [morph.parse(token)[0].normal_form for token in tokens if token.isalpha() and token not in stop_words]
    else:
        doc = nlp(' '.join(tokens))
        tokens = [token.lemma_ for token in doc if token.is_alpha and token.text not in stop_words]
    
    return ' '.join(tokens[:200]), len(tokens[:200])

# ОСНОВНОЙ ПРОЦЕСС
def main():
    print(f"\n🚀 Запуск парсинга {len(unique_urls)} статей...")
    session = create_http_session()
    corpus_data = []
    parsed_urls = set()
    doc_id = 1

    for url in unique_urls:
        if doc_id > 1000:
            break
        if url in parsed_urls:
            continue
        print(f"  🔍 Парсинг {url}...")
        parsed = parse_page(url, session)
        if parsed and parsed['raw_text']:
            # Определяем игру
            game = next((g for g in GAMES if g.lower() in url.lower() or g.lower() in parsed['title'].lower()), "Unknown")
            # Определяем язык (русский, если URL содержит "ru.")
            is_russian = 'ru.' in url or 'russian' in parsed['raw_text'].lower()
            cleaned_text, token_count = clean_text(parsed['raw_text'], is_russian)
            if token_count > 10:
                corpus_data.append({
                    'doc_id': doc_id,
                    'game': game,
                    'title': parsed['title'][:100],
                    'url': url,
                    'raw_text': parsed['raw_text'][:1000],
                    'cleaned_text': cleaned_text,
                    'tokens_count': token_count,
                    'date': parsed['date']
                })
                parsed_urls.add(url)
                print(f"    ✅ Документ {doc_id} добавлен: {token_count} токенов")
                doc_id += 1
        time.sleep(random.uniform(0.5, 1.5))  # Анти-бан

    # СОХРАНЕНИЕ КОРПУСА В TXT
    print(f"\n💾 Создание корпуса: game_corpus_1000.txt")
    with open('game_corpus_1000.txt', 'w', encoding='utf-8') as f:
        for doc in corpus_data:
            f.write(f"=== Document {doc['doc_id']} | {doc['game']} | {doc['title']} | {doc['url']} ===\n")
            f.write(f"Tokens: {doc['tokens_count']} | Date: {doc['date']}\n")
            f.write(f"{doc['cleaned_text']}\n---\n")
    print(f"  ✅ TXT-корпус сохранён: {len(corpus_data)} документов")

    # СОХРАНЕНИЕ В CSV
    df = pd.DataFrame(corpus_data)
    df.to_csv('game_corpus_1000.csv', index=False, encoding='utf-8')
    print(f"  ✅ CSV сохранён: game_corpus_1000.csv")

    # СТАТИСТИКА
    total_tokens = sum(doc['tokens_count'] for doc in corpus_data)
    print(f"\n📊 Статистика корпуса:")
    print(f"  Документов: {len(corpus_data)}")
    print(f"  Токенов: {total_tokens}")
    print(f"  Среднее токенов/документ: {total_tokens / len(corpus_data):.2f}" if corpus_data else "  Нет данных")
    print(f"  Уникальных URL: {len(parsed_urls)}")
    print(f"\n🎉 Корпус готов для NLP (LDA, кластеризация)!")

if __name__ == "__main__":
    main()