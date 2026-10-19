"""Tests de la regle des jours de bourse (heures en UTC ; New York = UTC-4 en octobre)."""
import pandas as pd

from src.analysis import assign_trading_day

JOURS_DE_BOURSE = ["2026-10-16", "2026-10-19"]   # vendredi 16 et lundi 19 octobre


def jour_de_bourse(publie_utc):
    """Jour de bourse d'un article publie a l'heure `publie_utc`."""
    df = pd.DataFrame({"published_at": pd.to_datetime([publie_utc], utc=True)})
    return assign_trading_day(df, JOURS_DE_BOURSE)["trading_day"].iloc[0]


def test_pendant_la_seance_meme_jour():
    assert jour_de_bourse("2026-10-16 14:00") == pd.Timestamp("2026-10-16")   # 10 h a New York


def test_apres_la_cloture_jour_de_bourse_suivant():
    assert jour_de_bourse("2026-10-16 21:00") == pd.Timestamp("2026-10-19")   # vendredi 17 h -> lundi


def test_week_end_reporte_au_lundi():
    assert jour_de_bourse("2026-10-17 12:00") == pd.Timestamp("2026-10-19")   # samedi -> lundi


def test_jour_pas_encore_connu():
    assert pd.isna(jour_de_bourse("2026-10-19 22:00"))   # lundi 18 h -> mardi, pas encore de prix