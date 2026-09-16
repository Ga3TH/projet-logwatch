"""Tests ecrits par Kevin sur la v0 - quatre tests, deux en echec au moment de la reprise.

Lancer :  pytest test_logwatch.py -v
"""
from logwatch import parser_ligne, d1_requetes_par_ip, d2_brute_force, d3_scan

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
