"""Tests de LogWatch, dont la regression B3 sur le pic de trafic D4.

Lancer :  pytest test_logwatch.py -v
"""
from logwatch import (
    charger_config,
    compter_par_minute,
    d1_requetes_par_ip,
    d2_brute_force,
    d3_scan,
    d4_pic_trafic,
    d5_erreurs_5xx,
    d6_purger_rapports,
    parser_ligne,
    regrouper_par_fenetre,
)
import json
import os
from datetime import datetime, timedelta
from explorer import compter_requetes_lentes

LIGNE_OK = ('203.0.113.7 - - [03/Sep/2026:10:15:32 +0200] "GET /index.html HTTP/1.1" '
            '200 5123 "-" "Mozilla/5.0" 1523')


def _ligne(ip, methode, url, statut, minute=0, duree=800):
    """Fabrique une ligne de log minimale au format attendu."""
    ligne = (f'{ip} - - [03/Sep/2026:10:{minute:02d}:00 +0200] "{methode} {url} HTTP/1.1" '
             f'{statut} 512 "-" "test"')
    return ligne if duree is None else f"{ligne} {duree}"


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


def test_d2_seuil_exact_declenche():
    """D2 signale une IP des que le nombre d'echecs atteint exactement le seuil."""
    entrees = [
        parser_ligne(_ligne("198.51.100.9", "POST", "/login", 401, minute=i % 60))
        for i in range(10)
    ]

    alertes = d2_brute_force(entrees, url_login="/login", seuil=10)

    assert len(alertes) == 1
    assert alertes[0]["tentatives"] == 10


def test_d5_seuil_5xx_depuis_config(tmp_path):
    """D5 charge le seuil de 5 % du modele de configuration."""
    chemin_config = tmp_path / "config.json"
    chemin_config.write_text(
        json.dumps({"seuil_5xx": 0.05}),
        encoding="utf-8",
    )
    config = charger_config(chemin_config)
    entrees = [
        parser_ligne(_ligne(
            f"10.0.0.{i % 250}",
            "GET",
            "/",
            500 if i < 48 else 200,
            minute=i % 60,
        ))
        for i in range(743)
    ]

    resultat = d5_erreurs_5xx(entrees, config["seuil_5xx"])

    assert config["seuil_5xx"] == 0.05
    assert resultat["nb_5xx"] == 48
    assert resultat["alerte"] is True


def test_d6_retention_7_jours_garde_la_limite_et_supprime_8_jours(tmp_path):
    """D6 conserve un rapport de 7 jours et supprime un rapport de 8 jours."""
    rapport_7 = tmp_path / "rapport-7.json"
    rapport_8 = tmp_path / "rapport-8.json"
    rapport_7.write_text("{}", encoding="utf-8")
    rapport_8.write_text("{}", encoding="utf-8")
    maintenant = datetime.now()
    for fichier, jours in ((rapport_7, 7), (rapport_8, 8)):
        timestamp = (maintenant - timedelta(days=jours)).timestamp()
        os.utime(fichier, (timestamp, timestamp))

    supprimes = d6_purger_rapports(tmp_path, retention_jours=7)

    assert rapport_7.exists()
    assert not rapport_8.exists()
    assert supprimes == ["rapport-8.json"]


def test_d7_compte_les_durees_au_seuil_de_2000_ms():
    entrees = [
        parser_ligne(_ligne("10.0.0.1", "GET", "/a", 200, duree=1_999_999)),
        parser_ligne(_ligne("10.0.0.2", "GET", "/b", 200, duree=2_000_000)),
        parser_ligne(_ligne("10.0.0.3", "GET", "/c", 200, duree=2_000_001)),
    ]

    assert compter_requetes_lentes(entrees, seuil_ms=2000) == {
        "lentes": 2,
        "mesurees": 3,
        "sans_duree": 0,
    }


def test_d7_exclut_une_requete_sans_duree():
    entree = parser_ligne(_ligne("10.0.0.1", "GET", "/a", 200, duree=None))

    assert entree["duree"] is None
    assert compter_requetes_lentes([entree], seuil_ms=2000) == {
        "lentes": 0,
        "mesurees": 0,
        "sans_duree": 1,
    }
