"""Tests de la collecte : filtre de qualite et identifiants des breves."""
from src.collect import is_valid_text, make_unique_url


def test_texte_trop_court_refuse():
    assert not is_valid_text("Trop court.")


def test_texte_absent_refuse():
    assert not is_valid_text(None)


def test_page_anti_robot_refusee():
    page = "Please enable JavaScript to continue. " * 30   # assez longue, mais anti-robot
    assert not is_valid_text(page)


def test_vrai_texte_accepte():
    assert is_valid_text("Apple reported strong quarterly results. " * 20)


def test_breves_seeking_alpha_ont_des_identifiants_differents():
    lien = "https://seekingalpha.com/symbol/AAPL/news?source=feed_symbol_AAPL"
    a = make_unique_url(lien, "Apple faces risk to dominance in the UK")
    b = make_unique_url(lien, "Apple joins Nvidia in the $5T club")
    assert a != b                                                    # titres differents -> ids differents
    assert a == make_unique_url(lien, "Apple faces risk to dominance in the UK")  # meme titre -> meme id


def test_lien_normal_inchange():
    lien = "https://seekingalpha.com/article/4954568-apples-new-home-run"
    assert make_unique_url(lien, "Apple's New 'Home' Run") == lien