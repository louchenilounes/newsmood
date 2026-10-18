"""
score.py - Calcule le sentiment des articles qui n'en ont pas encore.

Pour chaque modele (TextBlob, FinBERT) et chaque partie (titre, texte) :
1. cherche les articles qui n'ont pas encore de score,
2. calcule leur sentiment,
3. enregistre le resultat dans la table `sentiments`.

Lancement (depuis la racine du projet) :  python -m src.score
"""

from src.database import get_connection, create_tables, save_sentiments
from src.sentiment import textblob_predict, finbert_predict

MODELS = {"textblob": textblob_predict, "finbert": finbert_predict}

# Liste fermee, ecrite par nous : on peut donc mettre ces noms de colonnes
# directement dans le SQL. (Un nom de colonne ne peut pas etre un parametre "?".)
FIELDS = ["title", "text"]


def articles_to_score(conn, model, field):
    """Articles qui ont un `field` (titre ou texte) mais pas encore de score pour ce modele."""
    query = f"""
        SELECT a.id, a.{field}
        FROM articles a
        WHERE a.{field} IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM sentiments s
              WHERE s.article_id = a.id AND s.model = ? AND s.field = ?
          )
    """
    return conn.execute(query, (model, field)).fetchall()


def score_new_articles():
    conn = get_connection()
    create_tables(conn)   # cree la table `sentiments` si elle n'existe pas encore

    for model, predict in MODELS.items():
        for field in FIELDS:
            rows = articles_to_score(conn, model, field)
            if not rows:
                print(f"{model:<9} {field:<5} : rien de nouveau")
                continue

            ids = [r[0] for r in rows]
            contents = [r[1] for r in rows]
            predictions = predict(contents)

            to_save = [
                {"article_id": i, "model": model, "field": field,
                 "label": p["label"], "score": p["score"]}
                for i, p in zip(ids, predictions)
            ]
            n = save_sentiments(conn, to_save)
            print(f"{model:<9} {field:<5} : {n} articles analyses")

    total = conn.execute("SELECT COUNT(*) FROM sentiments").fetchone()[0]
    print(f"\nTotal dans la table sentiments : {total}")
    conn.close()


if __name__ == "__main__":
    score_new_articles()