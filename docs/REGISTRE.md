# docs/REGISTRE.md -- ouvert à l'étape 2, complété aux étapes 3 et 4,

# arrêté à l'étape 5, fermé ligne à ligne à l'étape 6

# Registre des défauts LogWatch - 2 défauts ouverts au 2026-09-30

| n°  | date       | symptôme observé                                                | fonction suspectée   | état   |
| --- | ---------- | --------------------------------------------------------------- | -------------------- | ------ |
| B1  | 2026-09-30 | test_d1_somme_egale_total_lines rouge : attendu 6, reçu 3       | d1_requetes_par_ip() | ouvert |
| B2  | 2026-09-30 | test_d3_ignore_url_legitime rouge : attendu [], reçu une alerte | d3_scan()            | ouvert |

## B1 - Erreurs HTTP absentes du total

Test en échec : test_d1_somme_egale_total_lines
Attendu / reçu : 6 / 3
Fonction visée : d1_requetes_par_ip(), logwatch.py ligne 116
Cause racine : le filtre sur le statut HTTP inférieur à 400 excluait les réponses supérieures ou égales à 400.
Correction prévue : compter chaque entrée analysée par adresse IP, quel que soit son statut HTTP.

## B2 - Pages légitimes déclenchent une alerte

Test en échec : test_d3_ignore_url_legitime
Attendu / reçu : [] / une alerte pour les 6 URL légitimes
Fonction visée : d3_scan(), logwatch.py ligne 142
Cause racine : le motif « admin » correspondait aussi à « administration » et à « admin-guide.pdf ».
Correction prévue : retirer le motif générique « admin » et conserver les motifs spécifiques aux scans, comme « wp-admin » et « phpmyadmin ».

## Question 5 - Etape 2 - Consolidation : lignes ignorées (pas un défaut)

`sample-logs.log` contient 746 lignes physiques. `parser_ligne()` renvoie `None` pour les trois lignes ci-dessous, comme annoncé dans le README. Ce sont des lignes mal formées, pas un défaut supplémentaire.

| Ligne | Extrait                                                                                       | Retour de `parser_ligne()` et cause                                                                                                                              |
| ----- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 121   | `192.0.2.14 - - [03/Sep/2026:10:21:07 +0200] "GET /chambres HTTP/1.1" 200`                    | `None` : la ligne ne correspond pas à la regex `LIGNE` (`logwatch.py` ligne 26); taille, référent et agent manquent.                                             |
| 301   | `<<< rotation du journal 03/Sep/2026 >>>`                                                     | `None` : c'est une note de rotation, pas une ligne au format Apache attendu par `LIGNE` (`logwatch.py` ligne 26).                                                |
| 521   | `192.0.2.31 - - [03/Sep/2026:11:2x:15 +0200] "GET / HTTP/1.1" 200 4200 "-" "Mozilla/5.0" 900` | `None` : la regex correspond, mais `datetime.strptime()` (`logwatch.py` ligne 86) rejette la date, car `2x` n'est pas une valeur valide pour les minutes (`%M`). |
