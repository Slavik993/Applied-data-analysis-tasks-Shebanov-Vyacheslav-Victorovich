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
from urllib.parse import urljoin, urlparse, quote_plus
from datetime import datetime
import nltk
from nltk import word_tokenize
from nltk.corpus import stopwords
import pymorphy2
import inspect

print("🔧 Инициализация библиотек...")

# ПАТЧ ДЛЯ PYMORPHY2
def patch_pymorphy2():
    def getargspec_patch(func):
        try:
            args, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = inspect.getfullargspec(func)
            return args, varargs, varkw, defaults
        except Exception:
            return [], None, None, None
    inspect.getargspec = getargspec_patch

patch_pymorphy2()

# НАСТРОЙКА NLTK
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Загрузка ресурсов NLTK...")
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
    nltk.download('stopwords', quiet=True)
print("  ✅ NLTK готов")

# НАСТРОЙКА PYMORPHY2
morph = pymorphy2.MorphAnalyzer()
print("  ✅ Pymorphy2 готов")

# СТОП-СЛОВА
stop_words = set(stopwords.words('russian') + stopwords.words('english'))
print("  ✅ Стоп-слова загружены")

# РАСШИРЕННЫЙ СПИСОК ИГР (50+ игр)
GAMES = [
    # Популярные русскоязычные
    "Atomic Heart", "Metro Exodus", "Escape from Tarkov", "Pathfinder",
    "S.T.A.L.K.E.R.", "War Thunder", "World of Tanks", "Crossout",
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

# ФУНКЦИЯ ИЗВЛЕЧЕНИЯ АВТОРА
def extract_author(soup, url):
    """Извлекает автора статьи из HTML"""
    # Попытка 1: Мета-теги
    meta_tags = [
        soup.find('meta', {'name': 'author'}),
        soup.find('meta', {'property': 'article:author'}),
        soup.find('meta', {'name': 'article:author'}),
        soup.find('meta', {'property': 'author'}),
    ]
    
    for tag in meta_tags:
        if tag and tag.get('content'):
            return tag.get('content').strip()
    
    # Попытка 2: Класс автора
    author_classes = [
        'author', 'author-name', 'post-author', 'article-author',
        'byline', 'by-author', 'entry-author', 'writer',
        'автор', 'author_name', 'article__author'
    ]
    
    for class_name in author_classes:
        author_tag = soup.find(class_=re.compile(class_name, re.I))
        if author_tag:
            text = author_tag.get_text(strip=True)
            # Очистка от префиксов
            text = re.sub(r'^(by|автор|written by|posted by)[\s:]+', '', text, flags=re.I)
            if text and len(text) < 100:
                return text
    
    # Попытка 3: Специфичные селекторы
    selectors = [
        'a[rel="author"]',
        'span[itemprop="author"]',
        'span[itemprop="name"]',
        '[class*="author"] a',
        '.author-info a',
    ]
    
    for selector in selectors:
        author_tag = soup.select_one(selector)
        if author_tag:
            text = author_tag.get_text(strip=True)
            if text and len(text) < 100:
                return text
    
    # По умолчанию: домен сайта
    domain = urlparse(url).netloc
    return domain.replace('www.', '').split('.')[0].capitalize()

# ФУНКЦИЯ ПОИСКА ЧЕРЕЗ YANDEX (для русскоязычного контента)
def search_yandex(query, num_results=15):
    """Парсинг результатов поиска Yandex"""
    try:
        search_url = f"https://yandex.ru/search/?text={quote_plus(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9'
        }
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        links = []
        for result in soup.find_all('a', class_=re.compile('Link.*Organic'), limit=num_results):
            href = result.get('href')
            if href and href.startswith('http'):
                links.append(href)

        # Альтернативный парсинг
        if not links:
            for result in soup.find_all('li', class_=re.compile('serp-item'), limit=num_results):
                link = result.find('a')
                if link and link.get('href'):
                    href = link.get('href')
                    if href.startswith('http'):
                        links.append(href)

        print(f"    🔍 Yandex: найдено {len(links)} ссылок для '{query}'")
        return links
    except Exception as e:
        print(f"    ⚠ Ошибка поиска Yandex: {e}")
        return []

# ФУНКЦИЯ ПОИСКА ЧЕРЕЗ DUCKDUCKGO (универсальный)
def search_duckduckgo(query, num_results=15):
    """Парсинг результатов поиска DuckDuckGo"""
    try:
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
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

# СБОР БАЗОВЫХ URL (статичные источники + русскоязычные)
def get_base_urls():
    """Базовый набор проверенных источников (русскоязычные + международные)"""
    base_urls = []

    # Шаблоны для русскоязычных сайтов (расширенный список)
    ru_templates = [
        "https://stopgame.ru/search?q={game}",
        "https://dtf.ru/search?q={game}",
        "https://igromania.ru/search/?q={game}",
        "https://www.playground.ru/search?q={game}",
        "https://www.kanobu.ru/search/?q={game}",
        "https://vgtimes.ru/search/?q={game}",
        "https://gamemag.ru/search?q={game}",
        "https://cybersport.ru/search?q={game}",
        "https://habr.com/ru/search/?q={game}",
        "https://vc.ru/search?q={game}",
        "https://stopgame.ru/games/{game}",
        "https://dtf.ru/games/{game}",
    ]

    # Шаблоны для международных сайтов
    en_templates = [
        "https://ru.wikipedia.org/wiki/{game}",
        "https://store.steampowered.com/search/?term={game}",
        "https://www.metacritic.com/search/{game}",
        "https://www.ign.com/games/{game}",
        "https://www.pcgamer.com/search/?searchTerm={game}",
        "https://www.gamespot.com/search/?q={game}",
    ]

    all_templates = ru_templates + en_templates

    # УВЕЛИЧИВАЕМ: используем ВСЕ игры
    for game in GAMES:
        game_slug = game.lower().replace(' ', '-').replace("'", '')
        game_encoded = quote_plus(game)
        
        for template in all_templates:
            if '{game}' in template:
                if 'search' in template or '?' in template:
                    url = template.format(game=game_encoded)
                else:
                    url = template.format(game=game_slug)
                base_urls.append(url)

    return base_urls

# ГЛАВНАЯ ФУНКЦИЯ СБОРА URL
def collect_urls(target_count=2500):
    """Собирает URLs из разных источников до достижения target_count"""
    print(f"\n📡 Сбор URL (цель: {target_count})...")
    all_urls = set()

    # 1. Базовые URL
    print("\n1️⃣ Добавление базовых URL...")
    base_urls = get_base_urls()
    all_urls.update(base_urls)
    print(f"  ✅ Базовых URL: {len(all_urls)}")

    # 2. Поиск через Yandex и DuckDuckGo
    print("\n2️⃣ Поиск через Yandex & DuckDuckGo...")
    search_queries = []

    # Поисковые запросы для игр (русскоязычные) - УВЕЛИЧЕНО
    for game in GAMES[:50]:  # Используем больше игр
        search_queries.extend([
            f"{game} обзор игры",
            f"{game} прохождение",
            f"{game} рецензия",
            f"{game} статья",
        ])

    # Общие игровые темы (русскоязычные) - РАСШИРЕННЫЙ СПИСОК
    general_topics = [
        "обзоры инди игр", "лучшие игры 2024", "игровые новости",
        "разработка игр", "киберспорт", "игровая культура",
        "ретро игры", "геймдизайн", "история видеоигр",
        "игровая индустрия", "игровая механика", "РПГ игры",
        "экшен игры", "стратегии", "симуляторы",
        "игровые статьи", "игровая журналистика", "обзоры новинок",
        "прохождение игр", "гайды по играм", "игровые советы",
        "игровые рецензии", "лучшие РПГ", "лучшие инди",
        "игры 2025", "новые игры", "анонсы игр",
        "игровые тренды", "будущее игр", "VR игры",
        "мобильные игры", "консольные игры", "PC игры"
    ]
    search_queries.extend(general_topics)

    # Поиск - УВЕЛИЧИВАЕМ количество запросов
    for i, query in enumerate(search_queries[:100]):  # БЫЛО 60, СТАЛО 100
        if len(all_urls) >= target_count:
            break

        print(f"  🔍 Запрос {i+1}/100: '{query}'")

        # Yandex (приоритет для русскоязычного контента)
        if random.random() > 0.3:  # 70% запросов через Yandex
            yandex_links = search_yandex(query, num_results=20)  # УВЕЛИЧЕНО с 15 до 20
            all_urls.update(yandex_links)
            time.sleep(random.uniform(2, 4))

        # DuckDuckGo (дополнительно)
        if len(all_urls) < target_count:
            ddg_links = search_duckduckgo(query, num_results=20)  # УВЕЛИЧЕНО с 15 до 20
            all_urls.update(ddg_links)
            time.sleep(random.uniform(2, 4))

        if i % 10 == 0:
            print(f"  📊 Всего собрано URL: {len(all_urls)}")

    # 3. Фильтрация нежелательных доменов
    filtered_urls = []
    blocked_domains = [
        'youtube.com', 'twitter.com', 'facebook.com', 'instagram.com',
        'reddit.com', 'discord.com', 'tiktok.com', 'pinterest.com',
        'vk.com', 'ok.ru', 't.me'  # Соц. сети
    ]

    # Приоритет русскоязычным доменам
    ru_priority_domains = [
        'stopgame.ru', 'dtf.ru', 'igromania.ru', 'playground.ru',
        'kanobu.ru', 'vgtimes.ru', 'gamemag.ru', 'cybersport.ru',
        'habr.com', 'vc.ru'
    ]

    ru_urls = []
    other_urls = []

    for url in all_urls:
        domain = urlparse(url).netloc
        if any(blocked in domain for blocked in blocked_domains):
            continue
        
        if any(ru_domain in domain for ru_domain in ru_priority_domains):
            ru_urls.append(url)
        else:
            other_urls.append(url)

    # Сначала русскоязычные, потом остальные
    filtered_urls = ru_urls + other_urls

    print(f"\n✅ Итоговое количество URL: {len(filtered_urls)}")
    print(f"   📌 Русскоязычных сайтов: {len(ru_urls)}")
    print(f"   🌐 Остальных сайтов: {len(other_urls)}")
    
    return filtered_urls[:target_count]

# HTTP SESSION
def create_http_session():
    session = requests.Session()
    ua = UserAgent()
    session.headers.update({
        'User-Agent': ua.random,
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
    })
    return session

# ПАРСИНГ СТРАНИЦЫ - ИСПРАВЛЕНО: БЕЗ СЛИПАНИЯ СЛОВ
def parse_page(url, session, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=15)
            response.raise_for_status()
            
            # Определение кодировки
            if response.encoding.lower() in ['iso-8859-1', 'windows-1251']:
                response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.content, 'html.parser')

            # Удаляем скрипты и стили
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                tag.decompose()

            # Заголовок
            title = soup.title.string.strip() if soup.title else 'Без заголовка'
            
            # Автор
            author = extract_author(soup, url)
            
            # Контент - ИСПРАВЛЕНИЕ: добавляем пробелы между элементами
            content_parts = []
            for elem in soup.find_all(['p', 'article', 'div', 'section'], limit=150):
                text = elem.get_text(separator=' ', strip=True)  # separator=' ' - ключевое изменение!
                if text:
                    content_parts.append(text)
            
            raw_text = ' '.join(content_parts)  # Дополнительный пробел между блоками

            if not raw_text or len(raw_text) < 200:
                return None

            # Дата публикации (попытка извлечь)
            date = datetime.now().strftime('%Y-%m-%d')
            date_meta = soup.find('meta', {'property': 'article:published_time'}) or \
                       soup.find('meta', {'name': 'date'}) or \
                       soup.find('time')
            
            if date_meta:
                date_str = date_meta.get('content') or date_meta.get('datetime') or date_meta.get_text()
                try:
                    date = datetime.fromisoformat(date_str.split('T')[0]).strftime('%Y-%m-%d')
                except:
                    pass

            return {
                'title': title,
                'author': author,
                'raw_text': raw_text[:10000],
                'date': date
            }
        except (requests.RequestException, Exception) as e:
            if attempt < max_retries - 1:
                time.sleep(random.uniform(1, 3))
    return None

# ОЧИСТКА И ЛЕММАТИЗАЦИЯ ТЕКСТА
def clean_text(raw_text):
    """Очистка и лемматизация русского текста"""
    # Удаление HTML
    text = re.sub(r'<[^>]+>', ' ', raw_text)
    text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
    # Удаление чисел
    text = re.sub(r'\d+\.?\d*', ' ', text)
    # Удаление пунктуации
    text = re.sub(r'[{}]'.format(string.punctuation + '«»—–…""„'), ' ', text)
    # Удаление лишних пробелов
    text = re.sub(r'\s+', ' ', text.strip())

    # Токенизация
    tokens = word_tokenize(text.lower())
    
    # Лемматизация с pymorphy2
    lemmatized_tokens = []
    for token in tokens:
        if token.isalpha() and len(token) > 2 and token not in stop_words:
            parsed = morph.parse(token)[0]
            lemmatized_tokens.append(parsed.normal_form)

    return ' '.join(lemmatized_tokens[:400]), len(lemmatized_tokens[:400])

# ОПРЕДЕЛЕНИЕ ИГРЫ
def get_game_from_url(url, title):
    text_to_check = (url + ' ' + title).lower()
    for game in GAMES:
        if game.lower().replace(' ', '') in text_to_check.replace(' ', '').replace('-', ''):
            return game
    return "Игры (общее)"

# ОСНОВНОЙ ПРОЦЕСС
def main():
    print("\n" + "="*70)
    print("🎮 СБОРЩИК ТЕКСТОВОГО КОРПУСА - 1000+ ДОКУМЕНТОВ (РУССКОЯЗЫЧНЫЙ)")
    print("="*70)

    # Сбор URL
    target_docs = 1000
    target_urls = 2500  # УВЕЛИЧЕНО: было 1800, стало 2500 для гарантии 1000+ документов
    unique_urls = collect_urls(target_count=target_urls)

    print(f"\n🚀 Начало парсинга {len(unique_urls)} URL (цель: {target_docs} документов)...")
    session = create_http_session()
    corpus_data = []
    parsed_urls = set()
    doc_id = 1
    failed_count = 0
    too_short_count = 0

    random.shuffle(unique_urls)

    for i, url in enumerate(unique_urls):
        if doc_id > target_docs:
            break

        if url in parsed_urls:
            continue

        if i % 50 == 0:
            print(f"\n📊 Прогресс: {i}/{len(unique_urls)} URL | {doc_id-1} документов | Ошибок: {failed_count} | Мало текста: {too_short_count}")

        print(f"  🔍 [{doc_id}] {url[:80]}...")
        parsed = parse_page(url, session)

        if parsed and parsed['raw_text']:
            cleaned_text, token_count = clean_text(parsed['raw_text'])

            if token_count > 30:  # Минимум 30 токенов
                game = get_game_from_url(url, parsed['title'])
                corpus_data.append({
                    'doc_id': doc_id,
                    'game': game,
                    'title': parsed['title'][:200],
                    'author': parsed['author'],
                    'url': url,
                    'raw_text': parsed['raw_text'][:2000],
                    'cleaned_text': cleaned_text,
                    'tokens_count': token_count,
                    'date': parsed['date']
                })
                parsed_urls.add(url)
                print(f"    ✅ Документ {doc_id}: {token_count} токенов | Автор: {parsed['author']} | {game}")
                doc_id += 1
            else:
                too_short_count += 1
                print(f"    ⚠ Пропущено: мало текста ({token_count} токенов)")
        else:
            failed_count += 1
            print(f"    ⚠ Пропущено: ошибка парсинга")

        time.sleep(random.uniform(0.5, 2.5))

    # ФИНАЛЬНАЯ СТАТИСТИКА СБОРА
    print(f"\n{'='*70}")
    print(f"📈 РЕЗУЛЬТАТЫ СБОРА")
    print(f"{'='*70}")
    print(f"  ✅ Успешно собрано документов: {len(corpus_data)}")
    print(f"  ❌ Ошибок парсинга: {failed_count}")
    print(f"  ⚠️  Отклонено (мало текста): {too_short_count}")
    print(f"  📊 Обработано URL: {i+1}/{len(unique_urls)}")
    
    if len(corpus_data) < target_docs:
        print(f"\n⚠️  ВНИМАНИЕ: Собрано {len(corpus_data)} из {target_docs} документов")
        print(f"   Рекомендация: увеличьте target_urls или уменьшите задержки")

    # СОХРАНЕНИЕ КОРПУСА В TXT
    print(f"\n💾 Создание корпуса: game_corpus_{len(corpus_data)}.txt")
    with open(f'game_corpus_{len(corpus_data)}.txt', 'w', encoding='utf-8') as f:
        for doc in corpus_data:
            f.write(f"{'='*80}\n")
            f.write(f"ДОКУМЕНТ {doc['doc_id']} | {doc['game']}\n")
            f.write(f"{'='*80}\n")
            f.write(f"Заголовок: {doc['title']}\n")
            f.write(f"Автор: {doc['author']}\n")
            f.write(f"Дата: {doc['date']}\n")
            f.write(f"Токенов: {doc['tokens_count']}\n")
            f.write(f"URL: {doc['url']}\n")
            f.write(f"{'-'*80}\n")
            f.write(f"ИСХОДНЫЙ ТЕКСТ (первые 2000 символов):\n")
            f.write(f"{doc['raw_text']}\n")
            f.write(f"{'-'*80}\n")
            f.write(f"ОЧИЩЕННЫЙ ТЕКСТ:\n")
            f.write(f"{doc['cleaned_text']}\n")
            f.write(f"{'='*80}\n\n")
    print(f"  ✅ TXT корпус сохранён: {len(corpus_data)} документов")

    # СОХРАНЕНИЕ В CSV
    df = pd.DataFrame(corpus_data)
    df.to_csv(f'game_corpus_{len(corpus_data)}.csv', index=False, encoding='utf-8-sig')
    print(f"  ✅ CSV сохранён: game_corpus_{len(corpus_data)}.csv")

    # СТАТИСТИКА
    total_tokens = sum(doc['tokens_count'] for doc in corpus_data)
    game_counts = df['game'].value_counts()
    author_counts = df['author'].value_counts()

    print(f"\n{'='*70}")
    print(f"📊 СТАТИСТИКА КОРПУСА")
    print(f"{'='*70}")
    print(f"  📄 Документов: {len(corpus_data)}")
    print(f"  🔤 Всего токенов: {total_tokens:,}")
    print(f"  📈 Средн. токенов/документ: {total_tokens / len(corpus_data):.2f}" if corpus_data else "  Нет данных")
    print(f"  🔗 Уникальных URL: {len(parsed_urls)}")
    print(f"  ✍️  Уникальных авторов: {len(author_counts)}")
    
    print(f"\n🎮 Топ-10 игр по количеству документов:")
    for game, count in game_counts.head(10).items():
        print(f"    {game}: {count} документов")
    
    print(f"\n✍️  Топ-10 авторов:")
    for author, count in author_counts.head(10).items():
        print(f"    {author}: {count} документов")
    
    print(f"\n🎉 Корпус готов для NLP-анализа (LDA, кластеризация, тематическое моделирование)!")
    print(f"📁 Файлы: game_corpus_{len(corpus_data)}.txt, game_corpus_{len(corpus_data)}.csv")

if __name__ == "__main__":
    main()