"""
app.py - Dashboard NewsMood (Streamlit).

Lancement (depuis la racine du projet) :  streamlit run app.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src.analysis import assign_trading_day, daily_sentiment
from src.cleaning import load_clean_articles
from src.config import TICKERS
from src.database import get_connection

st.set_page_config(page_title="NewsMood", page_icon="📰", layout="wide")

LABELS_FR = {"positive": "🟢 positif", "neutral": "⚪ neutre", "negative": "🔴 négatif"}


# --- Chargement des donnees ------------------------------------------------
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
    st.stop()

# Meme regle que le notebook 03 : chaque article -> son jour de bourse
df = assign_trading_day(df, prices["date"])
daily = daily_sentiment(df, prices)

# --- Chiffres cles -------------------------------------------------------------
col1, col2, col3 = st.columns(3)
col1.metric("Articles analysés", len(df))
col2.metric("Sentiment moyen", f"{df['score'].mean():+.2f}")
col3.metric("Articles positifs", f"{(df['label'] == 'positive').mean() * 100:.0f} %")

# --- Graphique : sentiment par jour de bourse + cours de l'action -------------
st.subheader("Sentiment de la presse et cours de l'action")

if daily.empty:
    st.info("Pas encore de jour de bourse avec des articles pour cette entreprise.")
else:
    fig = make_subplots(specs=[[{"secondary_y": True}]])   # deux axes verticaux

    # Barres : sentiment moyen du jour (axe de gauche)
    fig.add_bar(
        x=daily["trading_day"], y=daily["sentiment"], name="Sentiment moyen",
        marker_color=["#2e7d32" if s > 0 else "#c62828" for s in daily["sentiment"]],
        customdata=daily["n_articles"],
        hovertemplate="%{x|%d/%m}<br>Sentiment : %{y:+.2f}<br>Articles : %{customdata}<extra></extra>",
        secondary_y=False,
    )

    # Courbe : prix de cloture (axe de droite), sur la meme periode
    px_t = prices[(prices["ticker"] == ticker) & (prices["date"] >= daily["trading_day"].min())]
    fig.add_scatter(
        x=px_t["date"], y=px_t["close"], name="Cours de clôture ($)",
        mode="lines+markers", line_color="#1e88e5",
        hovertemplate="%{x|%d/%m}<br>Clôture : %{y:.2f} $<extra></extra>",
        secondary_y=True,
    )

    fig.update_yaxes(title_text="Sentiment", range=[-1, 1], secondary_y=False)
    fig.update_yaxes(title_text="Prix ($)", secondary_y=True)
    fig.update_xaxes(
        rangebreaks=[dict(bounds=["sat", "mon"])],   # masque les week-ends
        tickformat="%d/%m",                          # dates au format 16/10
        dtick=86_400_000,                            # un repere par jour (en millisecondes)
    )
    fig.update_layout(height=420, margin=dict(t=30), legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig)

    st.caption(
        "Chaque barre = moyenne du score des titres rattachés à ce jour de bourse "
        "(heure de New York, report au lendemain après la clôture de 16 h). "
        "Survolez une barre pour voir le nombre d'articles."
    )

n_attente = df["trading_day"].isna().sum()
if n_attente:
    st.caption(
        f"ℹ️ {n_attente} articles publiés après la dernière clôture connue "
        "apparaîtront avec le prochain jour de bourse."
    )

# --- Tableau des articles ------------------------------------------------------
st.subheader("Derniers articles")
tableau = df.sort_values("published_at", ascending=False).copy()
tableau["Publié (Paris)"] = tableau["published_at"].dt.tz_convert("Europe/Paris").dt.strftime("%d/%m %H:%M")
tableau["Sentiment"] = tableau["label"].map(LABELS_FR)
tableau = tableau.rename(columns={"source": "Source", "title": "Titre", "score": "Score", "url": "Lien"})

st.dataframe(
    tableau[["Publié (Paris)", "Source", "Titre", "Sentiment", "Score", "Lien"]],
    hide_index=True,
    column_config={
        "Lien": st.column_config.LinkColumn("Lien", display_text="Ouvrir"),
        "Score": st.column_config.NumberColumn(format="%+.2f"),
    },
)