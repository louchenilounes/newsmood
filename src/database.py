"""
database.py - Gestion de la base de donnees SQLite de NewsMood.

Ce fichier contient toutes les fonctions qui "parlent" a la base :
creer les tables, ajouter un article, compter les articles.
Les autres fichiers du projet (collect.py, prices.py...) les reutiliseront.
"""

import sqlite3
from pathlib import Path

# --- Emplacement de la base de donnees ---------------------------------
# Path(__file__) = le chemin de CE fichier (src/database.py)
# .parent        = le dossier src/
# .parent.parent = la racine du projet (newsmood/)
# Comme ca, le chemin est bon sur n'importe quel PC.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "newsmood.db"


def get_connection(db_path=DB_PATH):
    """Ouvre une connexion a la base (le fichier est cree s'il n'existe pas)."""
    return sqlite3.connect(db_path)


def create_tables(conn):
    """Cree les tables si elles n'existent pas encore."""
    # IF NOT EXISTS : on peut lancer cette fonction plusieurs fois sans erreur.
    conn.executescript("""
        -- Une ligne = un article de presse
        CREATE TABLE IF NOT EXISTS articles (
            id           INTEGER PRIMARY KEY,   -- numero unique, donne automatiquement
            ticker       TEXT NOT NULL,         -- entreprise : AAPL, TSLA ou NVDA
            source       TEXT,                  -- nom du journal
            title        TEXT NOT NULL,         -- titre de l'article
            text         TEXT,                  -- texte complet
            url          TEXT NOT NULL,         -- adresse de l'article
            published_at TEXT,                  -- date de publication (format ISO)
            collected_at TEXT NOT NULL,         -- date a laquelle on l'a collecte
            UNIQUE (ticker, url)                -- un article par entreprise, sans doublon   
        );

        -- Une ligne = le prix d'une action pour un jour
        CREATE TABLE IF NOT EXISTS prices (
            ticker       TEXT NOT NULL,
            date         TEXT NOT NULL,
            close        REAL NOT NULL,         -- prix de cloture
            daily_return REAL,                  -- rendement du jour (en %)
            PRIMARY KEY (ticker, date)          -- un seul prix par entreprise et par jour
        );
        
        -- Une ligne = le sentiment d'un article, pour un modele et une partie (titre ou texte)
        CREATE TABLE IF NOT EXISTS sentiments (
            article_id INTEGER NOT NULL REFERENCES articles(id),  -- lien vers la table articles
            model      TEXT NOT NULL,                             -- 'textblob' ou 'finbert'
            field      TEXT NOT NULL,                             -- 'title' ou 'text'
            label      TEXT NOT NULL,                             -- positive / negative / neutral
            score      REAL NOT NULL,                             -- entre -1 et 1
            PRIMARY KEY (article_id, model, field)                -- un seul score par combinaison
        );
    """)
    conn.commit()


def insert_article(conn, article):
    """
    Ajoute un article dans la base.
    `article` est un dictionnaire avec les cles :
    ticker, source, title, text, url, published_at, collected_at.

    Renvoie True si l'article a ete ajoute,
    False s'il existait deja (meme entreprise et meme url).
    """
    try:
        # :ticker, :source... sont remplaces par les valeurs du dictionnaire.
        # C'est plus sur que de coller les valeurs dans le texte SQL.
        conn.execute(
            """
            INSERT INTO articles (ticker, source, title, text, url, published_at, collected_at)
            VALUES (:ticker, :source, :title, :text, :url, :published_at, :collected_at)
            """,
            article,
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Erreur levee par la contrainte UNIQUE : l'url est deja dans la base.
        return False

def article_exists(conn, ticker, url):
    """Renvoie True si l'article est deja en base pour cette entreprise."""
    row = conn.execute(
        "SELECT 1 FROM articles WHERE ticker = ? AND url = ?", (ticker, url)
    ).fetchone()
    return row is not None

def save_prices(conn, rows):
    """
    Enregistre une liste de prix.
    `rows` = liste de dictionnaires avec les cles : ticker, date, close, daily_return.

    INSERT OR REPLACE : si le prix de ce jour existe deja (meme ticker et meme date),
    il est remplace. On peut donc relancer le script sans creer de doublons.
    Renvoie le nombre de lignes enregistrees.
    """
    conn.executemany(
        """
        INSERT OR REPLACE INTO prices (ticker, date, close, daily_return)
        VALUES (:ticker, :date, :close, :daily_return)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def count_prices(conn):
    """Renvoie le nombre de lignes dans la table prices."""
    return conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]

def save_sentiments(conn, rows):
    """
    Enregistre des scores de sentiment.
    `rows` = liste de dictionnaires avec : article_id, model, field, label, score.
    """
    conn.executemany(
        """
        INSERT OR REPLACE INTO sentiments (article_id, model, field, label, score)
        VALUES (:article_id, :model, :field, :label, :score)
        """,
        rows,
    )
    conn.commit()
    return len(rows)

def count_articles(conn):
    """Renvoie le nombre d'articles dans la base."""
    return conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]


# --- Petit test ------------------------------------------------------------
# Ce bloc s'execute seulement si on lance CE fichier directement
# (python src/database.py), pas quand un autre fichier l'importe.
if __name__ == "__main__":
    from datetime import datetime

    conn = get_connection()
    create_tables(conn)
    print("Base de donnees :", DB_PATH)

    # Liste des tables creees
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    print("Tables :", [t[0] for t in tables])

    # Un faux article pour tester
    test_article = {
        "ticker": "AAPL",
        "source": "Test",
        "title": "Article de test",
        "text": "Ceci est un texte de test.",
        "url": "https://example.com/article-de-test",
        "published_at": "2026-10-18",
        "collected_at": datetime.now().isoformat(timespec="seconds"),
    }

    print("1er ajout :", insert_article(conn, test_article))             # attendu : True
    print("2e ajout (doublon) :", insert_article(conn, test_article))    # attendu : False
    # Le meme article, mais pour une autre entreprise : il doit etre accepte
    article_nvda = dict(test_article, ticker="NVDA")  # copie avec ticker = NVDA
    print("Meme article pour NVDA :", insert_article(conn, article_nvda))  # attendu : True
    print("Nombre d'articles :", count_articles(conn))                   # attendu : 2

    # On supprime l'article de test pour garder une base propre
    conn.execute("DELETE FROM articles WHERE url = ?", (test_article["url"],))
    conn.commit()
    print("Apres nettoyage :", count_articles(conn))                     # attendu : 0

    conn.close()