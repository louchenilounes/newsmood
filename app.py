"""
app.py - Dashboard NewsMood (Streamlit).

Lancement (depuis la racine du projet) :  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from src.cleaning import load_clean_articles
from src.config import TICKERS
from src.database import get_connection

st.set_page_config(page_title="NewsMood", page_icon="📰", layout="wide")


# --- Chargement des donnees ------------------------------------------------
# @st.cache_data : Streamlit garde le resultat en memoire pendant 10 minutes (ttl=600).
# Sans ca, la base serait relue a CHAQUE clic sur un filtre.
@st.cache_data(ttl=600)
def load_data():
    articles = load_clean_articles()   # memes regles de nettoyage que les notebooks
    conn = get_connection()
    sentiments = pd.read_sql("SELECT article_id, model, field, label, score FROM sentiments", conn)
    prices = pd.read_sql("SELECT * FROM prices", conn, parse_dates=["date"])
    conn.close()
    return articles, sentiments, prices


articles, sentiments, prices = load_data()

# --- En-tete -----------------------------------------------------------------
st.title("📰 NewsMood")
st.caption("Sentiment de la presse financière et cours de bourse — Apple, Tesla, Nvidia")

# --- Filtres (barre laterale) --------------------------------------------------
st.sidebar.header("Filtres")
ticker = st.sidebar.selectbox(
    "Entreprise", list(TICKERS), format_func=lambda t: f"{TICKERS[t]} ({t})"
)
model = st.sidebar.radio(
    "Modèle de sentiment", ["finbert", "textblob"],
    format_func=lambda m: {"finbert": "FinBERT (recommandé)", "textblob": "TextBlob"}[m],
)

# --- Donnees filtrees : score du TITRE pour le modele choisi -----------------
scores = sentiments[(sentiments["model"] == model) & (sentiments["field"] == "title")]
df = articles.merge(scores, left_on="id", right_on="article_id")
df = df[df["ticker"] == ticker]

if df.empty:
    st.warning("Aucun article pour cette sélection.")
    st.stop()   # arrete le script ici : rien d'autre n'est affiche

# --- Chiffres cles -------------------------------------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Articles analysés", len(df))
col2.metric("Sentiment moyen", f"{df['score'].mean():+.2f}")
col3.metric("Articles positifs", f"{(df['label'] == 'positive').mean() * 100:.0f} %")

# --- Tableau des articles ------------------------------------------------------
st.subheader("Derniers articles")
tableau = df.sort_values("published_at", ascending=False)[
    ["published_at", "source", "title", "label", "score"]
]
st.dataframe(tableau, hide_index=True)