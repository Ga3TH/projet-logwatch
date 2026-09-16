#!/usr/bin/env python3
"""LogWatch v0 - surveillance des logs web Apache des clients OctopodSec.

Usage :
    python logwatch.py --log sample-logs.log --config config.json --reports reports

Le script lit un fichier de logs Apache (format combined + duree, voir
regex-apache.md), applique les detections D1 a D6 et ecrit un rapport JSON
date dans le dossier reports/. Les seuils viennent de config.json ; les
chemins peuvent aussi venir de .env (voir .env.example).

v0 - ecrite par le stagiaire precedent, reprise par Kevin.
"""
import argparse
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# Format Apache "combined", plus un dernier champ : la duree de traitement
# de la requete (%D, en microsecondes). Voir regex-apache.md.
LIGNE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<date>[^\]]+)\] '
    r'"(?P<methode>\S+) (?P<url>\S+) (?P<proto>[^"]*)" '
    r'(?P<statut>\d{3}) (?P<taille>\S+) "(?P<referer>[^"]*)" "(?P<agent>[^"]*)"'
    r'(?: (?P<duree>\d+))?$'
)
FORMAT_DATE = "%d/%b/%Y:%H:%M:%S %z"

# Valeurs par defaut, ecrasees par config.json
DEFAUTS = {
    "top_ips": 10,
    "seuil_brute_force": 10,
    "url_login": "/login",
    "seuil_scan": 5,
    "fenetre_minutes": 5,
    "seuil_pic": 100,
    "seuil_5xx": 0.5,
    "retention_jours": 7,
}

# Fragments d'URL typiques d'un scan de vulnerabilites
MOTIFS_SCAN = ["wp-admin", "wp-login", "phpmyadmin", ".env", ".git", "../", "xmlrpc", "admin"]


# ---------------------------------------------------------------- configuration
def charger_env(chemin=".env"):
    """Lit un fichier .env (CLE=valeur) et pose les variables absentes de l'environnement."""
    p = Path(chemin)
    if not p.exists():
        return
    for ligne in p.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, valeur = ligne.split("=", 1)
        os.environ.setdefault(cle.strip(), valeur.strip())


def charger_config(chemin):
    """Rend les seuils : les defauts, ecrases par le contenu de config.json s'il existe."""
    config = dict(DEFAUTS)
    p = Path(chemin)
    if p.exists():
        with p.open(encoding="utf-8") as f:
            config.update(json.load(f))
    return config


# ---------------------------------------------------------------- lecture du log
def parser_ligne(ligne):
    """Decompose une ligne de log en dictionnaire. Rend None si la ligne n'a pas la forme attendue."""
    m = LIGNE.match(ligne.rstrip("\n"))
    if not m:
        return None
    e = m.groupdict()
    e["statut"] = int(e["statut"])
    e["taille"] = 0 if e["taille"] == "-" else int(e["taille"])
    e["duree"] = int(e["duree"]) if e["duree"] is not None else None
    try:
        e["horodatage"] = datetime.strptime(e["date"], FORMAT_DATE)
    except ValueError:
        return None                    # date illisible : la ligne est ignoree
    return e


def lire_log(chemin, encodage="utf-8"):
    """Lit le fichier et rend (entrees parsees, nombre de lignes ignorees)."""
    entrees, ignorees = [], 0
    with open(chemin, encoding="utf-8", errors="replace") as f:
        for ligne in f:
            if not ligne.strip():
                continue
            e = parser_ligne(ligne)
            if e is None:
                ignorees += 1
            else:
                entrees.append(e)
    return entrees, ignorees


def anonymiser_ip(ip):
    """Masque le dernier octet d'une IPv4 : 203.0.113.7 -> 203.0.113.x (RGPD)."""
    morceaux = ip.split(".")
    if len(morceaux) == 4:
        morceaux[-1] = "x"
        return ".".join(morceaux)
    return ip


# ---------------------------------------------------------------- detections
def d1_requetes_par_ip(entrees, top_ips):
    """D1 - nombre de requetes par IP, les top_ips plus actives en tete, et la somme de toutes."""
    compteur = Counter()
    for e in entrees:
        if e["statut"] < 400:          # on ne compte que les requetes servies
            compteur[e["ip"]] += 1
    top = compteur.most_common(top_ips)
    return {
        "par_ip": {anonymiser_ip(ip): n for ip, n in top},
        "somme": sum(compteur.values()),
    }


def d2_brute_force(entrees, url_login, seuil):
    """D2 - IPs qui enchainent les echecs de connexion (POST url_login en 401/403)."""
    echecs = Counter()
    for e in entrees:
        if e["methode"] == "POST" and e["url"] == url_login and e["statut"] in (401, 403):
            echecs[e["ip"]] += 1
    alertes = []
    for ip, n in echecs.most_common():
        if n > seuil:
            alertes.append({"ip": anonymiser_ip(ip), "tentatives": n, "gravite": "haute"})
    return alertes


def d3_scan(entrees, seuil):
    """D3 - IPs qui sondent des URLs typiques d'un scan de vulnerabilites."""
    suspects = defaultdict(set)
    for e in entrees:
        url = e["url"].lower()
        if any(motif in url for motif in MOTIFS_SCAN):
            suspects[e["ip"]].add(e["url"])
    alertes = []
    for ip, urls in suspects.items():
        if len(urls) >= seuil:
            alertes.append({"ip": anonymiser_ip(ip), "nb_urls": len(urls),
                            "urls": sorted(urls)[:10], "gravite": "moyenne"})
    return sorted(alertes, key=lambda a: -a["nb_urls"])


def d4_pic_trafic(entrees, seuil_pic, fenetre_minutes):
    """D4 - pic de trafic : plus de seuil_pic requetes dans une fenetre de fenetre_minutes minutes."""
    par_minute = Counter()
    for e in entrees:
        par_minute[e["horodatage"].strftime("%Y-%m-%d %H:%M")] += 1
    if not par_minute:
        return {"alerte": False, "charge": 0, "max_par_minute": 0, "minute_pic": None}
    charge = statistics.mean(par_minute.values())
    minute_pic, maxi = par_minute.most_common(1)[0]
    return {
        "alerte": charge > seuil_pic,
        "charge": round(charge, 1),
        "max_par_minute": maxi,
        "minute_pic": minute_pic,
    }


def d5_erreurs_5xx(entrees, seuil):
    """D5 - part des reponses en erreur serveur (5xx) sur l'ensemble des requetes."""
    total = len(entrees)
    nb_5xx = sum(1 for e in entrees if 500 <= e["statut"] <= 599)
    ratio = nb_5xx / total if total else 0.0
    return {"nb_5xx": nb_5xx, "total": total, "ratio": round(ratio, 4), "alerte": ratio > seuil}


def d6_purger_rapports(dossier, retention_jours):
    """D6 - supprime les rapports plus vieux que la retention (RGPD : les rapports contiennent des IP)."""
    dossier = Path(dossier)
    supprimes = []
    if not dossier.exists():
        return supprimes
    limite_jours = retention_jours * 30     # retention exprimee en mois
    maintenant = datetime.now()
    for fichier in dossier.glob("rapport-*.json"):
        age = maintenant - datetime.fromtimestamp(fichier.stat().st_mtime)
        if age > timedelta(days=limite_jours):
            fichier.unlink()
            supprimes.append(fichier.name)
    return supprimes


# ---------------------------------------------------------------- rapport
def analyser(entrees, config):
    """Applique toutes les detections et rend le corps du rapport."""
    return {
        "D1_requetes_par_ip": d1_requetes_par_ip(entrees, config["top_ips"]),
        "D2_brute_force": d2_brute_force(entrees, config["url_login"], config["seuil_brute_force"]),
        "D3_scan": d3_scan(entrees, config["seuil_scan"]),
        "D4_pic_trafic": d4_pic_trafic(entrees, config["seuil_pic"], config["fenetre_minutes"]),
        "D5_erreurs_5xx": d5_erreurs_5xx(entrees, config["seuil_5xx"]),
    }


def ecrire_rapport(rapport, dossier):
    """Ecrit le rapport JSON date dans le dossier et rend son chemin."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / datetime.now().strftime("rapport-%Y%m%d-%H%M%S.json")
    with chemin.open("w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    return chemin


def main(argv=None):
    charger_env()
    ap = argparse.ArgumentParser(description="LogWatch v0 - analyse d'un fichier de logs Apache")
    ap.add_argument("--log", default=os.environ.get("LOGWATCH_LOG", "sample-logs.log"))
    ap.add_argument("--config", default=os.environ.get("LOGWATCH_CONFIG", "config.json"))
    ap.add_argument("--reports", default=os.environ.get("LOGWATCH_REPORTS", "reports"))
    args = ap.parse_args(argv)

    config = charger_config(args.config)
    entrees, ignorees = lire_log(args.log)
    if not entrees:
        print(f"Aucune ligne exploitable dans {args.log}", file=sys.stderr)
        return 1

    rapport = {
        "genere_le": datetime.now().isoformat(timespec="seconds"),
        "fichier": str(args.log),
        "total_lines": len(entrees),
        "lignes_ignorees": ignorees,
        "config": config,
    }
    rapport.update(analyser(entrees, config))
    rapport["D6_rapports_purges"] = d6_purger_rapports(args.reports, config["retention_jours"])
    chemin = ecrire_rapport(rapport, args.reports)

    print(f"LogWatch v0 - {rapport['total_lines']} requetes lues, {ignorees} ligne(s) ignoree(s)")
    print(f"  D1 somme par IP        : {rapport['D1_requetes_par_ip']['somme']}")
    print(f"  D2 brute force         : {len(rapport['D2_brute_force'])} IP(s)")
    print(f"  D3 scan                : {len(rapport['D3_scan'])} IP(s)")
    print(f"  D4 pic de trafic       : alerte={rapport['D4_pic_trafic']['alerte']} "
          f"(max {rapport['D4_pic_trafic']['max_par_minute']}/min)")
    print(f"  D5 erreurs 5xx         : {rapport['D5_erreurs_5xx']['ratio']:.1%} "
          f"alerte={rapport['D5_erreurs_5xx']['alerte']}")
    print(f"  D6 rapports purges     : {len(rapport['D6_rapports_purges'])}")
    print(f"Rapport : {chemin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
