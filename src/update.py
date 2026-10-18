"""
update.py - Mise a jour quotidienne de NewsMood : articles + prix.

C'est la seule commande a lancer chaque jour :
    python -m src.update
"""

import time
from datetime import datetime

from src.collect import collect
from src.prices import update_prices


def main():
    start = time.time()
    print(f"=== Mise a jour NewsMood - {datetime.now():%Y-%m-%d %H:%M} ===")

    print("\n[1/2] Collecte des articles")
    collect()

    print("\n[2/2] Mise a jour des prix")
    update_prices()

    duree = time.time() - start
    print(f"\nTermine en {duree:.0f} secondes.")


if __name__ == "__main__":
    main()