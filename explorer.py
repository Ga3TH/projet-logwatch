"""Petit script d'exploration des logs, sans modifier logwatch.py."""
from pathlib import Path

from logwatch import charger_config, lire_log


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
