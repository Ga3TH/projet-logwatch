"""Petit script d'exploration des logs, sans modifier logwatch.py."""
from pathlib import Path
from datetime import timedelta

from logwatch import (
    charger_config,
    compter_par_minute,
    d4_pic_trafic,
    lire_log,
    regrouper_par_fenetre,
)


if __name__ == "__main__":
    fichier_log = Path(__file__).with_name("sample-logs.log")
    configuration = charger_config(Path(__file__).with_name("config.json"))
    entrees, ignorees = lire_log(fichier_log)

    familles = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
    requetes_par_ip = {}
    echecs_par_ip = {}

    for entree in entrees:
        famille = f"{entree['statut'] // 100}xx"
        if famille not in familles:
            raise ValueError(f"Famille de statut non prise en charge : {famille}")
        familles[famille] = familles.get(famille, 0) + 1

        ip = entree["ip"]
        requetes_par_ip[ip] = requetes_par_ip.get(ip, 0) + 1

        if (
            entree["methode"] == "POST"
            and entree["url"] == configuration["url_login"]
            and entree["statut"] in (401, 403)
        ):
            echecs_par_ip[ip] = echecs_par_ip.get(ip, 0) + 1

    somme_familles = sum(familles.values())
    somme_ips = sum(requetes_par_ip.values())
    seuil_brute_force = configuration["seuil_brute_force"]
    echecs_sous_seuil = {
        ip: nombre
        for ip, nombre in echecs_par_ip.items()
        if nombre < seuil_brute_force
    }

    print(f"{len(entrees)} requêtes lues")
    print(f"{ignorees} lignes ignorées")
    print(f"Requêtes par famille de statut : {familles}")
    print(f"Somme des quatre familles : {somme_familles}")
    print(f"Requêtes par adresse IP : {requetes_par_ip}")
    print(f"Somme des requêtes par IP (D1) : {somme_ips}")
    print(f"Échecs de connexion par adresse IP : {echecs_par_ip}")
    print(f"Adresses sous le seuil D2 ({seuil_brute_force}) : {echecs_sous_seuil}")

    par_minute = compter_par_minute(entrees)
    print("Requêtes par minute :")
    for minute, nombre in sorted(par_minute.items()):
        print(f"  {minute:%Y-%m-%d %H:%M} : {nombre}")

    if par_minute:
        minute_pic = min(par_minute, key=lambda minute: (-par_minute[minute], minute))
        print(
            f"Minute la plus chargée : {minute_pic:%Y-%m-%d %H:%M} "
            f"({par_minute[minute_pic]} requêtes)"
        )

    fenetre_minutes = configuration["fenetre_minutes"]
    par_fenetre = regrouper_par_fenetre(entrees, fenetre_minutes)
    print(f"Requêtes par fenêtre de {fenetre_minutes} minutes :")
    for debut, nombre in sorted(par_fenetre.items()):
        fin = debut + timedelta(minutes=fenetre_minutes)
        print(f"  {debut:%Y-%m-%d %H:%M} - {fin:%Y-%m-%d %H:%M} : {nombre}")

    d4 = d4_pic_trafic(entrees, configuration["seuil_pic"], fenetre_minutes)
    print(
        f"D4 pic de trafic : charge={d4['charge']}/{configuration['seuil_pic']} "
        f"requêtes, alerte={d4['alerte']}, fenêtre={d4['fenetre_pic']}, "
        f"minute pic={d4['minute_pic']} ({d4['max_par_minute']} requêtes)"
    )
