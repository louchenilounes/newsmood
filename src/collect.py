"""
collect.py - Collecte des articles de presse financiere.

Pour chaque entreprise et chaque source :
1. lit le flux RSS (titre, lien, date),
2. saute les articles deja en base,
3. telecharge le texte complet si la source le permet, et verifie sa qualite,
4. enregistre l'article dans la base SQLite.

Lancement (depuis la racine du projet) :  python -m src.collect
"""
import hashlib
import time
from datetime import datetime, timezone

import feedparser
from newspaper import Article, Config

from src.config import (
    TICKERS, USER_AGENT, FULL_TEXT_SOURCES, MIN_TEXT_LENGTH,
    BLOCKED_PHRASES, get_feeds,
)
from src.database import (
    get_connection, create_tables, insert_article, article_exists, count_articles,
)


def make_newspaper_config():
    """Reglages de newspaper4k : se presenter comme un navigateur, timeout 15 s."""
    config = Config()
    config.browser_user_agent = USER_AGENT
    config.request_timeout = 15
    return config


def parse_date(entry):
    """
    Renvoie la date de publication au format ISO (ex : 2026-10-18T09:30:00+00:00),
    ou None si le flux ne la donne pas.
    """
    parsed = entry.get("published_parsed")  # date deja decoupee par feedparser (UTC)
    if parsed is None:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc).isoformat()

def make_unique_url(link, title):
    """
    Certains flux (Seeking Alpha) donnent le meme lien generique
    (.../symbol/AAPL/news) pour des breves differentes.
    Dans ce cas, on ajoute a la fin du lien une empreinte du titre (#...),
    pour que chaque breve ait un identifiant unique. Le lien reste cliquable.
    """
    if "/symbol/" in link:
        empreinte = hashlib.md5(title.encode("utf-8")).hexdigest()[:10]
        return f"{link}#{empreinte}"
    return link

def is_valid_text(text):
    """Filtre de qualite : assez long, et pas une page anti-robot ou d'erreur."""
    if text is None or len(text) < MIN_TEXT_LENGTH:
        return False
    lower = text.lower()
    return not any(phrase in lower for phrase in BLOCKED_PHRASES)


def download_text(url, np_config):
    """Telecharge l'article et renvoie son texte s'il est valide, sinon None."""
    try:
        article = Article(url, config=np_config)
        article.download()
        article.parse()
        text = article.text.strip()
        return text if is_valid_text(text) else None
    except Exception:
        # Site qui bloque, timeout... on garde l'article avec son titre seulement.
        return None


def collect():
    conn = get_connection()
    create_tables(conn)
    np_config = make_newspaper_config()

    # Un meme article peut apparaitre pour plusieurs entreprises :
    # on garde son texte en memoire pour ne le telecharger qu'une fois.
    text_cache = {}

    stats = {"nouveaux": 0, "avec_texte": 0, "deja_en_base": 0}

    for ticker, company in TICKERS.items():
        print(f"\n=== {ticker} ({company}) ===")

        for source, feed_url in get_feeds(ticker):
            feed = feedparser.parse(feed_url, agent=USER_AGENT)
            nouveaux = 0

            for entry in feed.entries:
                url = entry.get("link")
                title = entry.get("title", "").strip()
                if not url or not title:
                    continue  # entree incomplete : on l'ignore
                url = make_unique_url(url, title)
                
                if article_exists(conn, ticker, url):
                    stats["deja_en_base"] += 1
                    continue

                # Texte complet seulement pour les sources qui le permettent
                text = None
                if source in FULL_TEXT_SOURCES:
                    if url not in text_cache:
                        text_cache[url] = download_text(url, np_config)
                        time.sleep(1)  # pause d'1 seconde : on reste poli avec le site
                    text = text_cache[url]

                article = {
                    "ticker": ticker,
                    "source": source,
                    "title": title,
                    "text": text,
                    "url": url,
                    "published_at": parse_date(entry),
                    "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }

                if insert_article(conn, article):
                    nouveaux += 1
                    stats["nouveaux"] += 1
                    if text:
                        stats["avec_texte"] += 1

            print(f"  {source:<14} {len(feed.entries):>3} dans le flux | {nouveaux:>3} nouveaux")

    print("\n--- Bilan ---")
    print(f"Nouveaux articles      : {stats['nouveaux']}")
    print(f"  dont avec texte      : {stats['avec_texte']}")
    print(f"Deja en base (ignores) : {stats['deja_en_base']}")
    print(f"Total dans la base     : {count_articles(conn)}")
    conn.close()


if __name__ == "__main__":
    collect()