"""
cleaning.py - Nettoyage des articles pour l'analyse.

Regles decidees en Phase 2 (notebook 01_exploration) :
1. Dedoublonnage : un seul exemplaire par (entreprise, titre),
   en gardant la version qui a le texte le plus long.
   (Nasdaq republie des articles du Motley Fool deja presents dans Yahoo.)
2. Pertinence : on garde un article seulement s'il cite le nom
   ou le symbole de l'entreprise (dans le titre ou le texte).
   (Le flux Yahoo "NVDA" contient surtout des articles hors sujet.)

La base brute n'est jamais modifiee : on nettoie au moment de l'analyse.

Test :  python -m src.cleaning
"""

from urllib.parse import urlparse

import pandas as pd

from src.config import TICKERS
from src.database import get_connection


def load_articles():
    """Charge la table articles et convertit les dates de publication."""
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM articles", conn)
    conn.close()
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    return df


def add_columns(df):
    """Ajoute les colonnes utiles a l'analyse : editeur, longueurs, titre normalise."""
    df = df.copy()
    df["publisher"] = df["url"].apply(lambda u: urlparse(u).netloc.replace("www.", ""))
    df["text_len"] = df["text"].str.len()
    df["title_len"] = df["title"].str.len()
    df["title_norm"] = df["title"].str.strip().str.lower()
    return df


def deduplicate(df):
    """Regle 1 : un exemplaire par (entreprise, titre), en priorite celui avec texte."""
    return (
        df.sort_values("text_len", ascending=False, na_position="last", kind="stable")
          .drop_duplicates(subset=["ticker", "title_norm"], keep="first")
          .sort_values("id")
    )


def mentions_company(row):
    """True si le titre ou le texte cite le nom de l'entreprise ou son symbole."""
    nom = TICKERS[row["ticker"]].lower()
    symbole = row["ticker"].lower()
    texte = row["text"] if isinstance(row["text"], str) else ""
    contenu = (row["title"] + " " + texte).lower()
    return nom in contenu or symbole in contenu


def filter_relevant(df):
    """Regle 2 : on garde seulement les articles pertinents."""
    df = df.copy()
    df["pertinent"] = df.apply(mentions_company, axis=1)
    return df[df["pertinent"]].copy()


def load_clean_articles():
    """Charge les articles et applique toutes les regles de nettoyage."""
    df = add_columns(load_articles())
    df = deduplicate(df)
    df = filter_relevant(df)
    return df


if __name__ == "__main__":
    brut = add_columns(load_articles())
    dedup = deduplicate(brut)
    final = filter_relevant(dedup)
    print(f"Brut : {len(brut)} | Apres dedoublonnage : {len(dedup)} | Apres pertinence : {len(final)}")
    print(pd.crosstab(final["source"], final["ticker"], margins=True, margins_name="Total"))