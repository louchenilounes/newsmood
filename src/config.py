"""
config.py - Reglages du projet NewsMood.

Ici on definit :
- les entreprises suivies,
- les adresses des flux RSS pour chaque entreprise.
Pour ajouter une entreprise, il suffit d'ajouter une ligne dans TICKERS.
"""

# --- Entreprises suivies -----------------------------------------------
# cle = symbole boursier (ticker), valeur = nom de l'entreprise
TICKERS = {
    "AAPL": "Apple",
    "TSLA": "Tesla",
    "NVDA": "Nvidia",
}

# --- Flux RSS ------------------------------------------------------------
# {ticker} sera remplace par AAPL, TSLA ou NVDA.
FEED_TEMPLATES = {
    "Yahoo Finance": "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
    "Nasdaq": "https://www.nasdaq.com/feed/rssoutbound?symbol={ticker}",
    "Seeking Alpha": "https://seekingalpha.com/api/sa/combined/{ticker}.xml",
}

# Certains sites refusent les programmes qui ne se presentent pas.
# On se presente donc comme un navigateur classique.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"  
)


# --- Qualite du texte ----------------------------------------------------
# Sources dont on telecharge le texte complet (les autres : titre seulement).
# Mesure faite a l'etape 4 : Nasdaq renvoie 403, Seeking Alpha une page anti-robot.
FULL_TEXT_SOURCES = {"Yahoo Finance"}

# Un texte plus court est considere comme incomplet (paywall, page d'erreur...).
MIN_TEXT_LENGTH = 500

# Phrases typiques des pages anti-robot ou d'erreur (en minuscules).
BLOCKED_PHRASES = [
    "enable javascript",
    "access denied",
    "are you a robot",
    "subscribe to continue",
]

def get_feeds(ticker):
    """
    Renvoie la liste des flux pour une entreprise.
    Exemple : get_feeds("AAPL") -> [("Yahoo Finance", "https://..."), ...]
    """
    return [
        (source, template.format(ticker=ticker))
        for source, template in FEED_TEMPLATES.items()
    ]


# --- Petit test : quels flux repondent vraiment ? ------------------------
if __name__ == "__main__":
    import feedparser

    for ticker, company in TICKERS.items():
        print(f"\n=== {ticker} ({company}) ===")
        for source, url in get_feeds(ticker):
            # feedparser telecharge et lit le flux RSS
            feed = feedparser.parse(url, agent=USER_AGENT)
            nb = len(feed.entries)  # nombre d'articles dans le flux
            if nb > 0:
                first_title = feed.entries[0].title[:60]  # 60 premiers caracteres
                print(f"  OK  {source:<14} {nb:>3} articles | ex : {first_title}")
            else:
                print(f"  --  {source:<14}   0 article (flux vide ou bloque)")