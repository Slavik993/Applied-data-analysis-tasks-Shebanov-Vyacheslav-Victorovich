import warnings
warnings.filterwarnings("ignore")

# LIBRARIES
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
import time
import random
import re
import string
import pandas as pd
import os
from urllib.parse import urljoin, urlparse, quote_plus
from datetime import datetime
import nltk
from nltk import word_tokenize
from nltk.corpus import stopwords
import pymorphy2
import spacy
import inspect

print("🔧 Initializing libraries...")

# PATCH FOR PYMORPHY2
def patch_pymorphy2():
    def getargspec_patch(func):
        try:
            args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = inspect.getfullargspec(func)
            return args, varargs, varkw, defaults
        except Exception:
            return [], None, None, None
    inspect.getargspec = getargspec_patch

patch_pymorphy2()

# NLTK SETUP
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Downloading NLTK resources...")
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('stopwords', quiet=True)
print("  ✅ NLTK ready")

# PYMORPHY2 SETUP
morph = pymorphy2.MorphAnalyzer()
print("  ✅ Pymorphy2 ready")

# SPACY SETUP
try:
    nlp = spacy.load('en_core_web_sm')
except:
    print("Downloading spaCy model: python -m spacy download en_core_web_sm")
    os.system('python -m spacy download en_core_web_sm')
    nlp = spacy.load('en_core_web_sm')
print("  ✅ spaCy ready")

# STOP WORDS
stop_words = set(stopwords.words('english') + stopwords.words('russian'))
print("  ✅ Stop words loaded")

# РАСШИРЕННЫЙ СПИСОК ИГР (50+ игр для большего охвата)
GAMES = [
    # Оригинальные
    "Hollow Knight", "Hollow Knight Silksong", "Platypus",
    "Hard Truck Apocalypse", "No Man's Sky", "Moonlighter", "Minecraft",
    # Популярные инди
    "Celeste", "Hades", "Stardew Valley", "Undertale", "Terraria",
    "Dead Cells", "Ori and the Blind Forest", "Cuphead", "Shovel Knight",
    "Subnautica", "The Binding of Isaac", "Risk of Rain 2", "Slay the Spire",
    # AAA игры
    "The Witcher 3", "Elden Ring", "Dark Souls", "Sekiro", "Bloodborne",
    "God of War", "Red Dead Redemption 2", "Cyberpunk 2077", "Skyrim",
    "Grand Theft Auto V", "The Last of Us", "Horizon Zero Dawn",
    # Стратегии
    "Civilization VI", "StarCraft II", "Age of Empires IV", "Total War",
    "XCOM 2", "Crusader Kings III", "Cities Skylines",
    # Шутеры
    "Counter-Strike 2", "Valorant", "Apex Legends", "Overwatch 2",
    "Call of Duty", "Battlefield", "Destiny 2", "Halo Infinite",
    # MMORPG/Онлайн
    "World of Warcraft", "Final Fantasy XIV", "Guild Wars 2", "Dota 2", "League of Legends"
]

# ФУНКЦИЯ ПОИСКА ССЫЛОК ЧЕРЕЗ DUCKDUCKGO (без API ключей!)
def search_duckduckgo(query, num_results=15):
    """Парсинг результатов поиска DuckDuckGo"""
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        links = []
        for result in soup.find_all('a', class_='result__a', limit=num_results):
            href = result.get('href')
            if href and href.startswith('http'):
                links.append(href)

        print(f"    🔍 DuckDuckGo: найдено {len(links)} ссылок для '{query}'")
        return links
    except Exception as e:
        print(f"    ⚠ Ошибка поиска DuckDuckGo: {e}")
        return []

# ФУНКЦИЯ ПОИСКА ЧЕРЕЗ BING (альтернатива)
def search_bing(query, num_results=15):
    """Парсинг результатов поиска Bing"""
    try:
        search_url = f"https://www.bing.com/search?q={quote_plus(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        links = []
        for result in soup.find_all('li', class_='b_algo', limit=num_results):
            link = result.find('a')
            if link and link.get('href'):
                href = link.get('href')
                if href.startswith('http'):
                    links.append(href)

        print(f"    🔍 Bing: найдено {len(links)} ссылок для '{query}'")
        return links
    except Exception as e:
        print(f"    ⚠ Ошибка поиска Bing: {e}")
        return []

# СБОР БАЗОВЫХ URL (статичные источники)
def get_base_urls():
    """Базовый набор проверенных источников"""
    base_urls = []

    # Шаблоны для каждой игры
    url_templates = [
        "https://en.wikipedia.org/wiki/{game}",
        "https://store.steampowered.com/search/?term={game}",
        "https://www.metacritic.com/search/{game}",
        "https://www.ign.com/games/{game}",
        "https://www.pcgamer.com/search/?searchTerm={game}",
        "https://www.gamespot.com/search/?q={game}",
        "https://www.gamesradar.com/search/?q={game}",
        "https://www.rockpapershotgun.com/?s={game}",
    ]

    for game in GAMES:
        game_slug = game.lower().replace(' ', '-').replace("'", '')
        for template in url_templates:
            url = template.format(game=game_slug)
            base_urls.append(url)

    return base_urls

# ГЛАВНАЯ ФУНКЦИЯ СБОРА URL
def collect_urls(target_count=1500):
    """Собирает URLs из разных источников до достижения target_count"""
    print(f"\n📡 Collecting URLs (target: {target_count})...")
    all_urls = set()

    # 1. Базовые URL
    print("\n1️⃣ Adding base URLs...")
    base_urls = get_base_urls()
    all_urls.update(base_urls)
    print(f"  ✅ Base URLs: {len(all_urls)}")

    # 2. Поиск через DuckDuckGo и Bing
    print("\n2️⃣ Searching via DuckDuckGo & Bing...")
    search_queries = []

    # Поисковые запросы для игр
    for game in GAMES[:30]:  # Первые 30 игр
        search_queries.extend([
            f"{game} game review",
            f"{game} gameplay",
            f"{game} wiki",
        ])

    # Общие игровые темы
    general_topics = [
        "indie game reviews", "best video games 2024", "gaming news",
        "game development", "esports", "gaming culture",
        "retro gaming", "game design", "video game history",
        "gaming industry", "game mechanics", "RPG games",
        "action games", "strategy games", "simulation games"
    ]
    search_queries.extend(general_topics)

    # Поиск
    for query in search_queries[:50]:  # Ограничение на 50 запросов
        if len(all_urls) >= target_count:
            break

        # DuckDuckGo
        ddg_links = search_duckduckgo(query, num_results=15)
        all_urls.update(ddg_links)
        time.sleep(random.uniform(2, 4))  # Пауза между запросами

        # Bing (для разнообразия)
        if len(all_urls) < target_count and random.random() > 0.5:
            bing_links = search_bing(query, num_results=15)
            all_urls.update(bing_links)
            time.sleep(random.uniform(2, 4))

        print(f"  📊 Total URLs collected: {len(all_urls)}")

    # 3. Фильтрация нежелательных доменов
    filtered_urls = []
    blocked_domains = ['youtube.com', 'twitter.com', 'facebook.com', 'instagram.com',
                      'reddit.com', 'discord.com', 'tiktok.com', 'pinterest.com']

    for url in all_urls:
        domain = urlparse(url).netloc
        if not any(blocked in domain for blocked in blocked_domains):
            filtered_urls.append(url)

    print(f"\n✅ Final URL count: {len(filtered_urls)} (filtered from {len(all_urls)})")
    return filtered_urls[:target_count]

# HTTP SESSION
def create_http_session():
    session = requests.Session()
    ua = UserAgent()
    session.headers.update({'User-Agent': ua.random})
    return session

# PARSE PAGE
def parse_page(url, session, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Удаляем скрипты и стили
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()

            title = soup.title.string.strip() if soup.title else 'No Title'
            content = soup.find_all(['p', 'article', 'div'], limit=100)
            raw_text = ' '.join([elem.get_text(strip=True) for elem in content if elem.get_text(strip=True)])

            if not raw_text or len(raw_text) < 150:
                return None

            date = datetime.now().strftime('%Y-%m-%d')
            return {'title': title, 'raw_text': raw_text[:8000], 'date': date}
        except (requests.RequestException, Exception) as e:
            if attempt < max_retries - 1:
                time.sleep(random.uniform(1, 3))
    return None

# CLEAN AND LEMMATIZE TEXT
def clean_text(raw_text, is_russian=False):
    text = re.sub(r'<[^>]+>', ' ', raw_text)
    text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
    text = re.sub(r'\d+\.?\d*', ' ', text)
    text = re.sub(r'[{}]'.format(string.punctuation), ' ', text)
    text = re.sub(r'\s+', ' ', text.strip())

    tokens = word_tokenize(text.lower())
    if is_russian:
        tokens = [morph.parse(token)[0].normal_form for token in tokens
                 if token.isalpha() and token not in stop_words]
    else:
        doc = nlp(' '.join(tokens[:500]))  # Ограничение для spaCy
        tokens = [token.lemma_ for token in doc
                 if token.is_alpha and token.text not in stop_words]

    return ' '.join(tokens[:300]), len(tokens[:300])

# DETERMINE GAME
def get_game_from_url(url, title):
    text_to_check = (url + ' ' + title).lower()
    for game in GAMES:
        if game.lower().replace(' ', '') in text_to_check.replace(' ', ''):
            return game
    return "Gaming General"

# MAIN PROCESS
def main():
    print("\n" + "="*60)
    print("🎮 GAME CORPUS SCRAPER - 1000+ DOCUMENTS")
    print("="*60)

    # Сбор URL
    target_docs = 1000
    target_urls = 1500  # Собираем больше, т.к. не все распарсятся
    unique_urls = collect_urls(target_count=target_urls)

    print(f"\n🚀 Starting scraping {len(unique_urls)} URLs (target: {target_docs} docs)...")
    session = create_http_session()
    corpus_data = []
    parsed_urls = set()
    doc_id = 1

    random.shuffle(unique_urls)

    for i, url in enumerate(unique_urls):
        if doc_id > target_docs:
            break

        if url in parsed_urls:
            continue

        if i % 50 == 0:
            print(f"\n📊 Progress: {i}/{len(unique_urls)} URLs | {doc_id-1} documents collected")

        print(f"  🔍 [{doc_id}] {url[:80]}...")
        parsed = parse_page(url, session)

        if parsed and parsed['raw_text']:
            is_russian = 'ru.' in url or bool(re.search('[а-яА-Я]', parsed['raw_text'][:500]))
            cleaned_text, token_count = clean_text(parsed['raw_text'], is_russian)

            if token_count > 20:  # Минимум 20 токенов
                game = get_game_from_url(url, parsed['title'])
                corpus_data.append({
                    'doc_id': doc_id,
                    'game': game,
                    'title': parsed['title'][:150],
                    'url': url,
                    'raw_text': parsed['raw_text'][:1500],
                    'cleaned_text': cleaned_text,
                    'tokens_count': token_count,
                    'date': parsed['date']
                })
                parsed_urls.add(url)
                print(f"    ✅ Doc {doc_id}: {token_count} tokens ({game})")
                doc_id += 1
            else:
                print(f"    ⚠ Skipped: insufficient text ({token_count} tokens)")
        else:
            print(f"    ⚠ Skipped: scraping failed")

        time.sleep(random.uniform(0.5, 2))  # Пауза между запросами

    # SAVE CORPUS TO TXT
    print(f"\n💾 Creating corpus: game_corpus_{len(corpus_data)}.txt")
    with open(f'game_corpus_{len(corpus_data)}.txt', 'w', encoding='utf-8') as f:
        for doc in corpus_data:
            f.write(f"=== Document {doc['doc_id']} | {doc['game']} | {doc['title']} ===\n")
            f.write(f"URL: {doc['url']}\n")
            f.write(f"Tokens: {doc['tokens_count']} | Date: {doc['date']}\n")
            f.write(f"{doc['cleaned_text']}\n")
            f.write("="*80 + "\n\n")
    print(f"  ✅ TXT corpus saved: {len(corpus_data)} documents")

    # SAVE TO CSV
    df = pd.DataFrame(corpus_data)
    df.to_csv(f'game_corpus_{len(corpus_data)}.csv', index=False, encoding='utf-8')
    print(f"  ✅ CSV saved: game_corpus_{len(corpus_data)}.csv")

    # STATISTICS
    total_tokens = sum(doc['tokens_count'] for doc in corpus_data)
    game_counts = df['game'].value_counts()

    print(f"\n" + "="*60)
    print(f"📊 CORPUS STATISTICS")
    print("="*60)
    print(f"  📄 Documents: {len(corpus_data)}")
    print(f"  🔤 Total tokens: {total_tokens:,}")
    print(f"  📈 Avg tokens/doc: {total_tokens / len(corpus_data):.2f}" if corpus_data else "  No data")
    print(f"  🔗 Unique URLs: {len(parsed_urls)}")
    print(f"\n🎮 Top 10 games by document count:")
    for game, count in game_counts.head(10).items():
        print(f"    {game}: {count} docs")
    print(f"\n🎉 Corpus ready for NLP (LDA, clustering, topic modeling)!")

if __name__ == "__main__":
    main()