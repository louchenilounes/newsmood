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
from src.database import get_read_connection, using_sample_db
from src.sentiment import finbert_predict, textblob_predict

st.set_page_config(page_title="NewsMood", page_icon="📰", layout="wide")

LABELS_FR = {"positive": "🟢 positif", "neutral": "⚪ neutre", "negative": "🔴 négatif"}

# Resultats de l'evaluation (Phase 3, notebook 02_evaluation) : F1-score macro
EVALUATION = pd.DataFrame({
    "Jeu de données": ["Financial PhraseBank (vu par FinBERT)", "Twitter Financial News (jamais vu)"],
    "Toujours neutre": [0.254, 0.264],
    "TextBlob": [0.467, 0.385],
    "FinBERT": [0.963, 0.668],
})


# --- Chargement des donnees ------------------------------------------------
@st.cache_data(ttl=600)
def load_data():
    articles = load_clean_articles()   # memes regles de nettoyage que les notebooks
    conn = get_read_connection()
    sentiments = pd.read_sql("SELECT article_id, model, field, label, score FROM sentiments", conn)
    prices = pd.read_sql("SELECT * FROM prices", conn, parse_dates=["date"])
    conn.close()
    return articles, sentiments, prices


articles, sentiments, prices = load_data()

# --- En-tete -----------------------------------------------------------------
st.title("📰 NewsMood")
st.caption("Sentiment de la presse financière et cours de bourse — Apple, Tesla, Nvidia")
if using_sample_db():
    st.info(
        "Version de démonstration : données d'exemple collectées jusqu'au "
        f"{articles['published_at'].max():%d/%m/%Y}. La collecte continue en local."
    )

# --- Filtres (barre laterale) : utilises par l'onglet "Vue d'ensemble" -------
st.sidebar.header("Filtres")
ticker = st.sidebar.selectbox(
    "Entreprise", list(TICKERS), format_func=lambda t: f"{TICKERS[t]} ({t})"
)
model = st.sidebar.radio(
    "Modèle de sentiment", ["finbert", "textblob"],
    format_func=lambda m: {"finbert": "FinBERT (recommandé)", "textblob": "TextBlob"}[m],
)

tab_vue, tab_modeles, tab_test = st.tabs(
    ["📈 Vue d'ensemble", "🧪 Comparaison des modèles", "✍️ Testez vous-même"]
)

# ==============================================================================
# Onglet 1 : Vue d'ensemble
# ==============================================================================
with tab_vue:
    scores = sentiments[(sentiments["model"] == model) & (sentiments["field"] == "title")]
    df = articles.merge(scores, left_on="id", right_on="article_id")
    df = df[df["ticker"] == ticker]

    if df.empty:
        st.warning("Aucun article pour cette sélection.")
    else:
        df = assign_trading_day(df, prices["date"])   # meme regle que le notebook 03
        daily = daily_sentiment(df, prices)

        # --- Chiffres cles ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Articles analysés", len(df))
        col2.metric("Sentiment moyen", f"{df['score'].mean():+.2f}")
        col3.metric("Articles positifs", f"{(df['label'] == 'positive').mean() * 100:.0f} %")

        # --- Graphique ---
        st.subheader("Sentiment de la presse et cours de l'action")
        if daily.empty:
            st.info("Pas encore de jour de bourse avec des articles pour cette entreprise.")
        else:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_bar(
                x=daily["trading_day"], y=daily["sentiment"], name="Sentiment moyen",
                marker_color=["#2e7d32" if s > 0 else "#c62828" for s in daily["sentiment"]],
                customdata=daily["n_articles"],
                hovertemplate="%{x|%d/%m}<br>Sentiment : %{y:+.2f}<br>Articles : %{customdata}<extra></extra>",
                secondary_y=False,
            )
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
                dtick=86_400_000,                            # un repere par jour
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

        # --- Tableau ---
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

# ==============================================================================
# Onglet 2 : Comparaison des modeles
# ==============================================================================
with tab_modeles:
    st.subheader("Quel modèle de sentiment est le plus fiable ?")
    st.markdown(
        "Les deux modèles ont été évalués sur des textes **annotés à la main** "
        "(notebook `02_evaluation`). Métrique : **F1-score macro**, car les classes sont "
        "déséquilibrées (61 à 66 % de textes neutres). La *baseline* répond toujours « neutre »."
    )
    st.dataframe(EVALUATION, hide_index=True)

    jeu = EVALUATION.iloc[1]   # Twitter : le jeu que FinBERT n'a jamais vu
    fig_eval = go.Figure(go.Bar(
        x=["Toujours neutre", "TextBlob", "FinBERT"],
        y=[jeu["Toujours neutre"], jeu["TextBlob"], jeu["FinBERT"]],
        marker_color=["#9e9e9e", "#ef6c00", "#1e88e5"],
        text=[f"{v:.2f}" for v in [jeu["Toujours neutre"], jeu["TextBlob"], jeu["FinBERT"]]],
        textposition="outside",
    ))
    fig_eval.update_layout(
        title="F1-score macro sur Twitter Financial News (jamais vu par FinBERT)",
        yaxis=dict(range=[0, 1], title="F1-score macro"), height=380, margin=dict(t=50),
    )
    st.plotly_chart(fig_eval)

    st.markdown(
        "- **FinBERT est nettement le meilleur** sur des données qu'il n'a jamais vues (0,67 contre 0,39).\n"
        "- **Fuite de données :** FinBERT a été entraîné sur Financial PhraseBank. Son score de 0,96 "
        "sur ce jeu est gonflé : il faut regarder le jeu Twitter.\n"
        "- **Limites de FinBERT :** il surestime le négatif (précision de 0,49 sur cette classe) et "
        "se trompe sur les nouvelles mitigées (« précommandes épuisées, mais livraisons retardées »)."
    )

# ==============================================================================
# Onglet 3 : Testez vous-meme
# ==============================================================================
with tab_test:
    st.subheader("Testez les deux modèles sur votre propre phrase")
    texte = st.text_area(
        "Une phrase de presse financière, en anglais :",
        value="Apple shares plunge after weak iPhone sales disappoint investors.",
    )
    if st.button("Analyser", type="primary") and texte.strip():
        with st.spinner("Analyse en cours (le premier lancement charge FinBERT)..."):
            tb = textblob_predict([texte])[0]
            fb = finbert_predict([texte])[0]
        col_tb, col_fb = st.columns(2)
        col_tb.metric(f"TextBlob — score {tb['score']:+.2f}", LABELS_FR[tb["label"]])
        col_fb.metric(f"FinBERT — score {fb['score']:+.2f}", LABELS_FR[fb["label"]])
        st.caption("Score entre −1 (très négatif) et +1 (très positif).")