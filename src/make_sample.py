"""
make_sample.py - Cree data/sample.db, une copie de la base actuelle.
Cette copie est versionnee sur GitHub : l'application en ligne l'utilise.

Lancement :  python -m src.make_sample
"""

import sqlite3

from src.database import DB_PATH, SAMPLE_DB_PATH


def make_sample():
    source = sqlite3.connect(DB_PATH)
    copie = sqlite3.connect(SAMPLE_DB_PATH)
    source.backup(copie)   # copie propre de toute la base (remplace l'ancienne copie)

    for table in ["articles", "prices", "sentiments"]:
        n = copie.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:<10} : {n} lignes")

    copie.close()
    source.close()
    print(f"Taille de {SAMPLE_DB_PATH.name} : {SAMPLE_DB_PATH.stat().st_size / 1024:.0f} Ko")


if __name__ == "__main__":
    make_sample()