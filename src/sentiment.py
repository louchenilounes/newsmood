"""
sentiment.py - Les deux modeles de sentiment de NewsMood.

- TextBlob : dictionnaire de mots (simple, rapide, generaliste)
- FinBERT  : Transformer entraine sur la presse financiere (ProsusAI/finbert)

Les deux fonctions renvoient le meme format, pour chaque texte :
    {"label": "positive" | "negative" | "neutral", "score": nombre entre -1 et 1}

Test :  python -m src.sentiment
"""

from functools import lru_cache

from textblob import TextBlob

# Seuil de TextBlob : en dessous de 0.05 en valeur absolue, on considere le texte neutre
TEXTBLOB_THRESHOLD = 0.05

# Nom du modele FinBERT sur Hugging Face
FINBERT_MODEL = "ProsusAI/finbert"


# --- Modele 1 : TextBlob -------------------------------------------------
def textblob_predict(texts):
    """Sentiment de chaque texte avec TextBlob."""
    results = []
    for text in texts:
        score = TextBlob(text).sentiment.polarity   # deja entre -1 et 1
        if score > TEXTBLOB_THRESHOLD:
            label = "positive"
        elif score < -TEXTBLOB_THRESHOLD:
            label = "negative"
        else:
            label = "neutral"
        results.append({"label": label, "score": round(score, 4)})
    return results


# --- Modele 2 : FinBERT ----------------------------------------------------
@lru_cache(maxsize=1)
def load_finbert():
    """
    Charge FinBERT une seule fois (lru_cache garde le resultat en memoire).
    Le premier appel telecharge le modele (environ 440 Mo), les suivants sont instantanes.
    """
    from transformers import pipeline
    # top_k=None : on veut les probabilites des 3 classes, pas seulement la meilleure
    return pipeline("text-classification", model=FINBERT_MODEL, top_k=None)


def finbert_predict(texts, batch_size=16):
    """Sentiment de chaque texte avec FinBERT."""
    pipe = load_finbert()
    # batch_size : on traite les textes par paquets de 16 (plus rapide)
    # truncation : les textes trop longs sont coupes a 512 tokens (limite de BERT)
    outputs = pipe(list(texts), batch_size=batch_size, truncation=True)

    results = []
    for scores in outputs:
        # scores = [{"label": "positive", "score": 0.91}, {"label": "neutral", ...}, ...]
        probas = {s["label"]: s["score"] for s in scores}
        label = max(probas, key=probas.get)                           # classe la plus probable
        score = probas.get("positive", 0) - probas.get("negative", 0) # entre -1 et 1
        results.append({"label": label, "score": round(score, 4)})
    return results


# --- Petit test : les deux modeles sur des phrases ecrites a la main --------
if __name__ == "__main__":
    phrases = [
        "Apple shares jumped 5% after record quarterly earnings beat expectations.",
        "Tesla stock plunged after the company missed delivery estimates.",
        "Nvidia will report its third-quarter results on November 19.",
        "Operating profit fell to EUR 2.1 million from EUR 5.4 million a year earlier.",
        "Analysts downgraded the stock to sell, citing weak demand.",
        "Revenue grew modestly, but margins remained under pressure.",
    ]

    tb = textblob_predict(phrases)
    fb = finbert_predict(phrases)

    for phrase, t, f in zip(phrases, tb, fb):
        print(f"\n{phrase}")
        print(f"  TextBlob : {t['label']:<8} ({t['score']:+.2f})   "
              f"FinBERT : {f['label']:<8} ({f['score']:+.2f})")