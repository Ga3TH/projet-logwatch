# docs/REGISTRE.md -- ouvert à l'étape 2, complété aux étapes 3 et 4,

# arrêté à l'étape 5, fermé ligne à ligne à l'étape 6

# Registre des défauts LogWatch - 5 défauts consignés au 2026-11-04 (4 ouverts)

| n°  | date       | symptôme observé                                                | fonction suspectée   | état   |
| --- | ---------- | --------------------------------------------------------------- | -------------------- | ------ |
| B1  | 2026-09-30 | test_d1_somme_egale_total_lines rouge : attendu 6, reçu 3       | d1_requetes_par_ip() | ouvert |
| B2  | 2026-09-30 | test_d3_ignore_url_legitime rouge : attendu [], reçu une alerte | d3_scan()            | ouvert |
| B3  | 2026-10-12 | D4 manque le pic : moyenne sous le seuil malgré 170 requêtes/min | d4_pic_trafic()      | fermé |
| B4  | 2026-11-04 | D5 affiche alerte=False à 6,5 % ; le seuil chargé est 50 % au lieu des 5 % du modèle | config D5 / d5_erreurs_5xx() | ouvert |
| B5  | 2026-11-04 | D2 ne signale pas une IP qui atteint exactement 10 échecs | d2_brute_force() | ouvert |

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


## B3 - Pic de trafic D4 non détecté

Symptôme observé : le rapport affiche `alerte=False` alors qu'une minute contient 170 requêtes et que la fenêtre de cinq minutes correspondante contient 190.
Fonction visée : `d4_pic_trafic()` et l'exploration D4 de `explorer.py`.
Cause racine : D4 calculait la moyenne des seules minutes présentes, puis comparait cette moyenne à `seuil_pic`. La charge totale d'une fenêtre n'était pas mesurée.
Correction appliquée : compter les requêtes par minute, les regrouper en fenêtres consécutives de `fenetre_minutes`, puis comparer la fenêtre la plus chargée à `seuil_pic`. Le rapport expose aussi la minute et la fenêtre de pic.
État : fermé le 2026-10-12. La régression est couverte par `test_B3_d4_regroupe_et_signale_la_fenetre_la_plus_chargee`.

## B4 - Seuil D5 du modèle de configuration ignoré

Test en échec : D5 affiche `alerte=False` à 6,5 % alors que la configuration attend un seuil de 5 %.
Attendu / reçu : 5 % / 6,5 % de réponses `5xx`, avec alerte non déclenchée.
Fonction visée : `charger_config()` et `d5_erreurs_5xx()`, dans `logwatch.py`.
Cause racine : le modèle de configuration utilise une clé différente du nom attendu par le programme (`seuil_erreurs_5xx` au lieu de `seuil_5xx`). La valeur par défaut de `logwatch.py` (0,5 soit 50 %) est donc conservée, ce qui masque l'alerte réellement attendue.
Correction prévue : aligner le nom de la clé sur le code (`seuil_5xx`) ou ajouter une conversion explicite lors du chargement de la configuration.
État : ouvert, consigné pendant l'étape 5 sans correction.

## B5 - D2 ne signale pas le seuil exact

Test en échec : `dix-echecs.log` contient exactement 10 échecs `POST /login` en `401` depuis la même IP, soit le seuil configuré.
Attendu / reçu : l'adresse doit être signalée dès qu'elle atteint le seuil (`>= 10`) ; résultat observé : aucune alerte.
Fonction visée : `d2_brute_force()`, dans `logwatch.py`.
Cause racine : la condition actuelle teste `n > seuil` au lieu de `n >= seuil`.
Correction prévue : utiliser une comparaison inclusive (`>=`) pour déclencher l'alerte dès que le seuil est atteint.
État : ouvert, consigné pendant l'étape 5 sans correction.
