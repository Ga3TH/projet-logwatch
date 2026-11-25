"""Exploration indépendante des logs, sans modifier logwatch.py."""
import json
import argparse
from datetime import timedelta
from pathlib import Path

from logwatch import charger_config, lire_log


def compter_par_minute(entrees):
    """Compte les requêtes de chaque minute présente dans les entrées."""
    par_minute = {}
    for entree in entrees:
        minute = entree["horodatage"].replace(second=0, microsecond=0)
        par_minute[minute] = par_minute.get(minute, 0) + 1
    return par_minute


def regrouper_par_fenetre(entrees, fenetre_minutes):
    """Compte les requêtes dans des fenêtres fixes alignées sur minuit."""
    if isinstance(fenetre_minutes, bool) or not isinstance(fenetre_minutes, int) or fenetre_minutes <= 0:
        raise ValueError("fenetre_minutes doit être un entier strictement positif")

    par_fenetre = {}
    for entree in entrees:
        horodatage = entree["horodatage"]
        minutes_jour = horodatage.hour * 60 + horodatage.minute
        debut = horodatage.replace(hour=0, minute=0, second=0, microsecond=0)
        debut += timedelta(minutes=minutes_jour - minutes_jour % fenetre_minutes)
        par_fenetre[debut] = par_fenetre.get(debut, 0) + 1
    return par_fenetre


def cle_du_maximum(comptages):
    """Rend la clé du plus grand comptage, première clé en cas d'égalité."""
    if not comptages:
        return None
    return min(comptages, key=lambda cle: (-comptages[cle], cle))


def compter_requetes_lentes(entrees, seuil_ms):
    """Compte les durées connues au seuil D7, dont l'unité source est la microseconde."""
    if isinstance(seuil_ms, bool) or not isinstance(seuil_ms, int) or seuil_ms <= 0:
        raise ValueError("seuil_ms doit être un entier strictement positif")

    durees = [entree["duree"] for entree in entrees if entree["duree"] is not None]
    return {
        "lentes": sum(duree >= seuil_ms * 1000 for duree in durees),
        "mesurees": len(durees),
        "sans_duree": len(entrees) - len(durees),
    }


if __name__ == "__main__":
    dossier = Path(__file__).parent
    parser = argparse.ArgumentParser(description="Exploration indépendante des logs LogWatch")
    parser.add_argument(
        "--log", type=Path, default=dossier / "sample-logs.log",
        help="fichier de logs à explorer (par défaut : sample-logs.log)",
    )
    parser.add_argument(
        "--reports", type=Path, default=dossier / "reports",
        help="dossier des rapports LogWatch à comparer (par défaut : reports)",
    )
    args = parser.parse_args()
    fichier_log = args.log if args.log.is_absolute() else dossier / args.log
    dossier_rapports = args.reports if args.reports.is_absolute() else dossier / args.reports
    configuration = charger_config(dossier / "config.json")
    entrees, ignorees = lire_log(fichier_log)

    familles = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}
    requetes_par_ip = {}
    echecs_par_ip = {}

    for entree in entrees:
        famille = f"{entree['statut'] // 100}xx"
        if famille not in familles:
            raise ValueError(f"Famille de statut non prise en charge : {famille}")
        familles[famille] += 1

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
    alertes_d2_exploration = {
        ip: nombre
        for ip, nombre in echecs_par_ip.items()
        if nombre > seuil_brute_force
    }
    atteint_seuil = {
        ip: nombre
        for ip, nombre in echecs_par_ip.items()
        if nombre >= seuil_brute_force
    }
    print(
        f"D2 si le seuil est atteint (>= {seuil_brute_force}, comme formulé dans la fiche) : "
        f"{atteint_seuil}"
    )

    total_requetes = len(entrees)
    nb_5xx = familles["5xx"]
    ratio_5xx = nb_5xx / total_requetes if total_requetes else 0.0
    seuil_5xx = configuration["seuil_5xx"]
    alerte_5xx = ratio_5xx > seuil_5xx
    print(
        f"D5 erreurs 5xx : {nb_5xx}/{total_requetes} = {ratio_5xx:.2%}, "
        f"seuil chargé={seuil_5xx:.2%}, alerte={alerte_5xx}"
    )

    seuil_requete_lente_ms = configuration["seuil_requete_lente_ms"]
    d7 = compter_requetes_lentes(entrees, seuil_requete_lente_ms)
    print(
        f"D7 exploration des requêtes lentes (>= {seuil_requete_lente_ms} ms) : "
        f"{d7['lentes']}/{d7['mesurees']} ; durées absentes : {d7['sans_duree']}"
    )

    par_minute = compter_par_minute(entrees)
    print("Requêtes par minute :")
    for minute, nombre in sorted(par_minute.items()):
        print(f"  {minute:%Y-%m-%d %H:%M} : {nombre}")

    minute_pic = cle_du_maximum(par_minute)
    if minute_pic is not None:
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

    fenetre_pic = cle_du_maximum(par_fenetre)
    seuil_pic = configuration["seuil_pic"]
    charge_pic = par_fenetre[fenetre_pic] if fenetre_pic is not None else 0
    alerte = charge_pic > seuil_pic
    if fenetre_pic is None:
        texte_fenetre = "aucune"
        valeur_fenetre_rapport = None
    else:
        fin_fenetre = fenetre_pic + timedelta(minutes=fenetre_minutes)
        texte_fenetre = (
            f"{fenetre_pic:%Y-%m-%d %H:%M} - {fin_fenetre:%Y-%m-%d %H:%M}"
        )
        valeur_fenetre_rapport = texte_fenetre
    texte_minute = minute_pic.strftime("%Y-%m-%d %H:%M") if minute_pic else "aucune"
    compte_minute_pic = par_minute[minute_pic] if minute_pic is not None else 0
    print(
        f"D4 pic de trafic : charge={charge_pic}/{seuil_pic} requêtes, "
        f"alerte={alerte}, fenêtre={texte_fenetre}, "
        f"minute pic={texte_minute} ({compte_minute_pic} requêtes)"
    )

    # Une comparaison n'est possible qu'après la création d'un rapport LogWatch.
    rapports = sorted(
        dossier_rapports.glob("rapport-*.json"), key=lambda chemin: chemin.stat().st_mtime
    )
    if rapports:
        with rapports[-1].open(encoding="utf-8") as fichier:
            rapport = json.load(fichier)
        config_rapport = rapport.get("config", {})
        print(
            "Seuil D5 copié dans le rapport : "
            f"{config_rapport.get('seuil_5xx', 'absent')} "
            "(clé attendue par logwatch.py : seuil_5xx)"
        )
        d4_rapport = rapport.get("D4_pic_trafic", {})
        concorde = (
            d4_rapport.get("charge") == charge_pic
            and d4_rapport.get("alerte") == alerte
            and d4_rapport.get("fenetre_pic") == valeur_fenetre_rapport
            and d4_rapport.get("minute_pic") == (
                minute_pic.strftime("%Y-%m-%d %H:%M") if minute_pic is not None else None
            )
            and d4_rapport.get("max_par_minute") == compte_minute_pic
        )
        resultat = "concorde" if concorde else "DIFFÉRENCE"
        print(f"Comparaison D4 avec {rapports[-1].name} : {resultat}")

        d5_rapport = rapport.get("D5_erreurs_5xx", {})
        d5_concorde = (
            d5_rapport.get("nb_5xx") == nb_5xx
            and d5_rapport.get("total") == total_requetes
            and d5_rapport.get("ratio") == round(ratio_5xx, 4)
            and d5_rapport.get("alerte") == alerte_5xx
        )
        print(
            f"Comparaison D5 avec {rapports[-1].name} : "
            f"{'concorde' if d5_concorde else 'DIFFÉRENCE'}"
        )

        alertes_d2_rapport = {
            alerte.get("ip"): alerte.get("tentatives")
            for alerte in rapport.get("D2_brute_force", [])
        }
        ips_d2_exploration = {
            ip: nombre for ip, nombre in alertes_d2_exploration.items()
        }
        # LogWatch anonymise la dernière partie des IPv4 dans son rapport.
        alertes_d2_anonymisees = {
            ".".join(ip.split(".")[:-1] + ["x"]): nombre
            for ip, nombre in ips_d2_exploration.items()
            if len(ip.split(".")) == 4
        }
        print(
            f"Comparaison D2 avec {rapports[-1].name} : "
            f"{'concorde' if alertes_d2_rapport == alertes_d2_anonymisees else 'DIFFÉRENCE'} "
            f"(le script déclenche si le nombre est strictement supérieur au seuil)"
        )
    else:
        print("Comparaison D4 : aucun rapport trouvé ; lancez logwatch.py d'abord.")
