"""Tests de la base : regle d'unicite (entreprise, url).

tmp_path est un dossier temporaire cree par pytest : la vraie base n'est jamais touchee.
"""
from src.database import count_articles, create_tables, get_connection, insert_article

ARTICLE = {
    "ticker": "AAPL", "source": "Test", "title": "Article de test", "text": None,
    "url": "https://example.com/test", "published_at": "2026-10-16",
    "collected_at": "2026-10-19T10:00:00",
}


def test_doublon_refuse_pour_la_meme_entreprise(tmp_path):
    conn = get_connection(tmp_path / "test.db")
    create_tables(conn)
    assert insert_article(conn, ARTICLE) is True
    assert insert_article(conn, ARTICLE) is False
    assert count_articles(conn) == 1
    conn.close()


def test_meme_article_accepte_pour_une_autre_entreprise(tmp_path):
    conn = get_connection(tmp_path / "test.db")
    create_tables(conn)
    insert_article(conn, ARTICLE)
    assert insert_article(conn, dict(ARTICLE, ticker="NVDA")) is True
    assert count_articles(conn) == 2
    conn.close()