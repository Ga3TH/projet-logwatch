"""Tests de LogWatch, dont la regression B3 sur le pic de trafic D4.

Lancer :  pytest test_logwatch.py -v
"""
from logwatch import (
    compter_par_minute,
    d1_requetes_par_ip,
    d2_brute_force,
    d3_scan,
    d4_pic_trafic,
    parser_ligne,
    regrouper_par_fenetre,
)

LIGNE_OK = ('203.0.113.7 - - [03/Sep/2026:10:15:32 +0200] "GET /index.html HTTP/1.1" '
            '200 5123 "-" "Mozilla/5.0" 1523')


def _ligne(ip, methode, url, statut, minute=0):
    """Fabrique une ligne de log minimale au format attendu."""
    return (f'{ip} - - [03/Sep/2026:10:{minute:02d}:00 +0200] "{methode} {url} HTTP/1.1" '
            f'{statut} 512 "-" "test" 800')


def test_parser_ligne_combined():
    """Une ligne au format combined + duree est decomposee en champs types."""
    e = parser_ligne(LIGNE_OK)
    assert e["ip"] == "203.0.113.7"
    assert e["methode"] == "GET" and e["url"] == "/index.html"
    assert e["statut"] == 200 and e["taille"] == 5123 and e["duree"] == 1523


def test_d1_somme_egale_total_lines():
    """D1 compte TOUTES les requetes : la somme par IP egale le nombre de lignes lues, erreurs comprises."""
    lignes = [
        _ligne("10.0.0.1", "GET", "/a", 200),
        _ligne("10.0.0.1", "GET", "/b", 404),
        _ligne("10.0.0.2", "GET", "/c", 200),
        _ligne("10.0.0.2", "GET", "/d", 500),
        _ligne("10.0.0.3", "POST", "/login", 401),
        _ligne("10.0.0.3", "GET", "/e", 200),
    ]
    entrees = [parser_ligne(l) for l in lignes]
    d1 = d1_requetes_par_ip(entrees, top_ips=10)
    assert d1["somme"] == len(entrees)


def test_d2_brute_force_detecte():
    """Quarante POST /login en 401 depuis la meme IP declenchent une alerte D2 (seuil 10)."""
    entrees = [parser_ligne(_ligne("198.51.100.9", "POST", "/login", 401, minute=i % 60))
               for i in range(40)]
    alertes = d2_brute_force(entrees, url_login="/login", seuil=10)
    assert len(alertes) == 1
    assert alertes[0]["tentatives"] == 40


def test_d3_ignore_url_legitime():
    """Une page legitime dont le nom ressemble a un motif suspect ne doit pas etre signalee par D3."""
    pages = ["/administration-des-reservations.html", "/administration/planning",
             "/administration/tarifs", "/administration/clients",
             "/administration/export.csv", "/admin-guide.pdf"]
    entrees = [parser_ligne(_ligne("10.0.0.5", "GET", page, 200, minute=i))
               for i, page in enumerate(pages)]
    assert d3_scan(entrees, seuil=5) == []


def test_compter_par_minute_compte_toutes_les_requetes():
    entrees = [
        parser_ligne(_ligne("10.0.0.1", "GET", "/a", 200, minute=12)),
        parser_ligne(_ligne("10.0.0.2", "GET", "/b", 404, minute=12)),
        parser_ligne(_ligne("10.0.0.3", "GET", "/c", 500, minute=13)),
    ]

    par_minute = compter_par_minute(entrees)

    assert sum(par_minute.values()) == len(entrees)
    assert max(par_minute.values()) == 2


def test_B3_d4_regroupe_et_signale_la_fenetre_la_plus_chargee():
    entrees = [
        parser_ligne(_ligne("10.0.0.1", "GET", "/a", 200, minute=14)),
        parser_ligne(_ligne("10.0.0.1", "GET", "/b", 200, minute=14)),
        parser_ligne(_ligne("10.0.0.2", "GET", "/c", 200, minute=15)),
        parser_ligne(_ligne("10.0.0.3", "GET", "/d", 200, minute=18)),
        parser_ligne(_ligne("10.0.0.4", "GET", "/e", 200, minute=20)),
    ]

    par_fenetre = regrouper_par_fenetre(entrees, fenetre_minutes=5)
    d4 = d4_pic_trafic(entrees, seuil_pic=1, fenetre_minutes=5)

    assert sum(par_fenetre.values()) == len(entrees)
    assert d4["fenetre_pic"] == "2026-09-03 10:10 - 2026-09-03 10:15"
    assert d4["charge"] == 2
    assert d4["minute_pic"] == "2026-09-03 10:14"
    assert d4["max_par_minute"] == 2
    assert d4["alerte"] is True


def test_d4_ne_declenche_pas_si_charge_egale_au_seuil():
    entrees = [
        parser_ligne(_ligne("10.0.0.1", "GET", "/a", 200, minute=1)),
        parser_ligne(_ligne("10.0.0.2", "GET", "/b", 200, minute=2)),
    ]

    assert d4_pic_trafic(entrees, seuil_pic=2, fenetre_minutes=5)["alerte"] is False
