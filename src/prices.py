"""
prices.py - Recuperation des prix des actions avec yfinance.

Pour chaque entreprise suivie :
1. telecharge les prix journaliers des derniers mois,
2. calcule le rendement journalier (variation en % par rapport a la veille),
3. enregistre tout dans la table `prices`.

Lancement (depuis la racine du projet) :  python -m src.prices
"""

import pandas as pd
import yfinance as yf

from src.config import TICKERS
from src.database import get_connection, create_tables, save_prices, count_prices

# Periode telechargee : 3 derniers mois ("1mo", "6mo", "1y"... sont possibles)
PERIOD = "3mo"


def fetch_prices(ticker, period=PERIOD):
    """
    Telecharge les prix d'une entreprise et renvoie une liste de dictionnaires,
    prets a etre enregistres avec save_prices().
    """
    # auto_adjust=True : prix corriges des dividendes et des divisions d'actions
    history = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    if history.empty:
        return []

    # Rendement journalier en % : (prix du jour - prix de la veille) / prix de la veille * 100
    # pct_change() fait exactement ce calcul. Le 1er jour n'a pas de veille -> NaN.
    history["daily_return"] = history["Close"].pct_change() * 100

    rows = []
    for date, row in history.iterrows():
        ret = row["daily_return"]
        rows.append({
            "ticker": ticker,
            "date": date.strftime("%Y-%m-%d"),          # ex : 2026-10-16
            "close": round(float(row["Close"]), 4),
            # NaN (1er jour) -> None, qui devient NULL dans la base
            "daily_return": None if pd.isna(ret) else round(float(ret), 4),
        })
    return rows


def update_prices():
    conn = get_connection()
    create_tables(conn)

    for ticker, company in TICKERS.items():
        rows = fetch_prices(ticker)
        if not rows:
            print(f"{ticker} ({company}) : aucun prix recu")
            continue

        n = save_prices(conn, rows)
        last = rows[-1]  # le jour le plus recent
        print(
            f"{ticker} ({company}) : {n} jours | dernier : {last['date']}  "
            f"cloture = {last['close']:.2f} $  rendement = {last['daily_return']:+.2f} %"
        )

    print(f"\nTotal dans la table prices : {count_prices(conn)}")
    conn.close()


if __name__ == "__main__":
    update_prices()