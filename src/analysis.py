"""
analysis.py - Regles d'analyse de la Phase 4, reutilisables (notebook et dashboard).

- assign_trading_day : rattache chaque article au bon jour de bourse
- daily_sentiment    : sentiment moyen par (entreprise, jour) + rendements du jour J et J+1

Test :  python -m src.analysis
"""

import numpy as np
import pandas as pd

MARKET_TZ = "America/New_York"   # fuseau horaire de la bourse de New York
MARKET_CLOSE_HOUR = 16           # cloture a 16 h, heure de New York


def assign_trading_day(df, trading_days):
    """
    Ajoute la colonne `trading_day` a df (qui doit avoir une colonne `published_at` en UTC).
    Regle : heure de New York ; apres 16 h -> lendemain ; puis premier jour de bourse
    a partir de cette date (un article du week-end va au lundi).
    Si ce jour de bourse n'est pas encore connu, trading_day = NaT ("en attente").
    """
    days = np.sort(pd.to_datetime(pd.Series(trading_days)).unique())

    ny = df["published_at"].dt.tz_convert(MARKET_TZ)
    base = ny.dt.normalize().dt.tz_localize(None)
    base = base + pd.to_timedelta((ny.dt.hour >= MARKET_CLOSE_HOUR).astype(int), unit="D")

    pos = np.searchsorted(days, base.values)   # position du premier jour de bourse >= base
    df = df.copy()
    df["trading_day"] = pd.to_datetime([days[i] if i < len(days) else pd.NaT for i in pos])
    return df


def daily_sentiment(df, prices):
    """
    Sentiment moyen par (entreprise, jour de bourse), avec le nombre d'articles,
    le prix de cloture, le rendement du jour (J) et celui du lendemain (J+1).
    `df` doit avoir les colonnes : id, ticker, trading_day, score.
    """
    prices = prices.sort_values(["ticker", "date"]).copy()
    prices["next_return"] = prices.groupby("ticker")["daily_return"].shift(-1)

    daily = (
        df.dropna(subset=["trading_day"])
          .groupby(["ticker", "trading_day"])
          .agg(n_articles=("id", "count"), sentiment=("score", "mean"))
          .reset_index()
    )
    return daily.merge(
        prices.rename(columns={"date": "trading_day"}),
        on=["ticker", "trading_day"], how="left",
    )


# --- Test : on doit retrouver les resultats du notebook 03 ---------------------
if __name__ == "__main__":
    from src.cleaning import load_clean_articles
    from src.database import get_connection

    conn = get_connection()
    sent = pd.read_sql(
        "SELECT article_id, score FROM sentiments WHERE model = 'finbert' AND field = 'title'", conn
    )
    prices = pd.read_sql("SELECT * FROM prices", conn, parse_dates=["date"])
    conn.close()

    df = load_clean_articles().merge(sent, left_on="id", right_on="article_id")
    df = assign_trading_day(df, prices["date"])
    daily = daily_sentiment(df, prices)

    print("Lignes (entreprise x jour) :", len(daily), "| articles rattaches :", daily["n_articles"].sum())
    print("Articles en attente :", df["trading_day"].isna().sum())
    print(daily[daily["ticker"] == "AAPL"].tail(3)[["trading_day", "n_articles", "sentiment", "daily_return"]])