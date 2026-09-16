# docs/CARTE.md -- gabarit de départ, amendé à l'étape 4

# Carte LogWatch v0 - v1 du 2026-09-16 (étape 1)

## Entrées et sorties

lit : Fichier `.env`, fichier `config.json` et fichier de logs Apache. Le chemin est décidé par les priorités des arguments (Option CLI > `.env` > `access.log`).
écrit : Un rapport d'analyse au format JSON (ex: `rapport-20260916-094300.json`).
supprime : Les anciens rapports JSON expirés sur le disque.

## Les fonctions, dans l'ordre du fichier

Les quatorze lignes se generent, depuis logwatch/ :
Select-String -Path logwatch.py -Pattern '^def ' |
ForEach-Object { "| " + $\_.Line.Substring(4).TrimEnd(':') + " | |" }
Coller le resultat sous l'en-tete, puis remplir la seule colonne rend.

| fonction                                           | rend                                                   |
| -------------------------------------------------- | ------------------------------------------------------ |
| charger_env(chemin=".env")                         | `None`                                                 |
| charger_config(chemin)                             | Un dictionnaire des seuils actifs                      |
| parser_ligne(ligne)                                | Un dictionnaire à onze clés, ou `None`                 |
| lire_log(chemin, encodage="utf-8")                 | Un tuple `(entrees, ignorees)`                         |
| anonymiser_ip(ip)                                  | Une chaîne (IP masquée)                                |
| d1_requetes_par_ip(entrees, top_ips)               | Un dictionnaire à deux clés (`par_ip` et `somme`)      |
| d2_brute_force(entrees, url_login, seuil)          | Une liste de dictionnaires d'alertes (gravité haute)   |
| d3_scan(entrees, seuil)                            | Une liste de dictionnaires d'alertes (gravité moyenne) |
| d4_pic_trafic(entrees, seuil_pic, fenetre_minutes) | Un dictionnaire d'indicateurs de trafic                |
| d5_erreurs_5xx(entrees, seuil)                     | Un dictionnaire d'indicateurs de pannes                |
| d6_purger_rapports(dossier, retention_jours)       | Une liste des fichiers supprimés                       |
| analyser(entrees, config)                          | Un dictionnaire global des détections                  |
| ecrire_rapport(rapport, dossier)                   | Un objet `Path` du fichier généré                      |
| main(argv=None)                                    | `None`                                                 |

## Les détections annoncées par le README (question 7)

| détection | fonction             | ce que le README lui demande (seuil, unité, « dès que » / « au moins » / « au-delà »)        |
| --------- | -------------------- | -------------------------------------------------------------------------------------------- |
| D1        | `d1_requetes_par_ip` | Compter TOUTES les requêtes : la somme par IP doit être égale _au moins_ au total de lignes. |
| D2        | `d2_brute_force`     | Alerte "haute" _au-delà_ de X requêtes en échec (`POST` en 401/403).                         |
| D3        | `d3_scan`            | Alerte "moyenne" _dès que_ le nombre d'URLs suspectes uniques atteint le `seuil`.            |
| D4        | `d4_pic_trafic`      | Alerte _au-delà_ de X requêtes en moyenne par minute.                                        |
| D5        | `d5_erreurs_5xx`     | Alerte _au-delà_ de X % de réponses d'erreurs `5xx`.                                         |
| D6        | `d6_purger_rapports` | Suppression des rapports _au-delà_ de X jours d'ancienneté.                                  |

## Points opaques (question 8)

- ligne 92 : que vaut le compteur d'IP quand le statut est >= 400 ?
- ligne 134 : que vaut l'âge limite quand `retention_jours` est multiplié par 30 ?
