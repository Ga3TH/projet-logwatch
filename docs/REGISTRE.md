# Registre des défauts LogWatch — relu et classé à l'étape 6

# 6 défauts consignés au 2026-11-18 (2 ouverts)

Priorité, de la plus importante à la moins importante : **fausse un résultat**,
**gêne**, **cosmétique**. Les six défauts observés faussent un résultat ; aucun
des défauts consignés ne relève seulement d'une gêne ou d'un problème
cosmétique.

| n°  | priorité            | date       | symptôme observé                                                                                 | fonction suspectée                 | test de régression                                       | état   |
| --- | ------------------- | ---------- | ------------------------------------------------------------------------------------------------ | ---------------------------------- | -------------------------------------------------------- | ------ |
| B1  | fausse un résultat  | 2026-09-30 | `test_d1_somme_egale_total_lines` rouge : attendu 6, reçu 3                                      | `d1_requetes_par_ip()`             | `test_d1_somme_egale_total_lines`                        | fermé  |
| B2  | fausse un résultat  | 2026-09-30 | `test_d3_ignore_url_legitime` rouge : attendu [], reçu une alerte                                | `d3_scan()`                        | `test_d3_ignore_url_legitime`                            | fermé  |
| B3  | fausse un résultat  | 2026-10-12 | D4 manque le pic : moyenne sous le seuil malgré 170 requêtes/min                                 | `d4_pic_trafic()`                  | `test_B3_d4_regroupe_et_signale_la_fenetre_la_plus_chargee` | fermé  |
| B4  | fausse un résultat  | 2026-11-04 | D5 affiche `alerte=False` à 6,5 % ; seuil chargé à 50 % au lieu des 5 % du modèle               | configuration D5 / `d5_erreurs_5xx()` | `test_d5_seuil_5xx_depuis_config` (à écrire)             | ouvert |
| B5  | fausse un résultat  | 2026-11-04 | D2 ne signale pas une IP qui atteint exactement 10 échecs                                         | `d2_brute_force()`                 | `test_d2_seuil_exact_declenche` (à écrire)               | fermé  |
| B6  | fausse un résultat  | 2026-11-18 | D6 conserve un rapport de 8 jours malgré une rétention configurée à 7 jours                      | `d6_purger_rapports()`             | `test_d6_retention_7_jours_garde_la_limite_et_supprime_8_jours` (à écrire) | ouvert |

## B1 - Erreurs HTTP absentes du total

Test en échec : test_d1_somme_egale_total_lines
Attendu / reçu : 6 / 3
Fonction visée : d1_requetes_par_ip(), logwatch.py ligne 116
Cause racine : le filtre sur le statut HTTP inférieur à 400 excluait les réponses supérieures ou égales à 400.
Correction observée : compter chaque entrée analysée par adresse IP, quel que soit son statut HTTP.
État : fermé le 2026-11-18 ; le code compte toutes les entrées et
`test_d1_somme_egale_total_lines` vérifie la somme.

## B2 - Pages légitimes déclenchent une alerte

Test en échec : test_d3_ignore_url_legitime
Attendu / reçu : [] / une alerte pour les 6 URL légitimes
Fonction visée : d3_scan(), logwatch.py ligne 142
Cause racine : le motif « admin » correspondait aussi à « administration » et à « admin-guide.pdf ».
Correction observée : retirer le motif générique « admin » et conserver les
motifs spécifiques aux scans, comme « wp-admin » et « phpmyadmin ».
État : fermé le 2026-11-18 ; `test_d3_ignore_url_legitime` couvre les chemins
légitimes contenant « admin ».

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
État : fermé le 2026-10-12. La régression est couverte par
`test_B3_d4_regroupe_et_signale_la_fenetre_la_plus_chargee`.

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
Correction observée : utiliser une comparaison inclusive (`>=`) pour déclencher
l'alerte dès que le seuil est atteint. Une vérification manuelle avec exactement
10 entrées produit une alerte de 10 tentatives.
État : fermé le 2026-11-18 ; le code utilise `n >= seuil`.

## B6 - D6 interprète la rétention en mois au lieu de jours

Symptôme observé : avec `retention_jours` à 7, un rapport dont la date de
dernière modification a été vieillie à 8 jours n'est pas supprimé.

Fonction visée : `d6_purger_rapports()`, `logwatch.py` ligne 224.

Cause racine : la limite est calculée avec
`limite_jours = retention_jours * 30`, alors que le paramètre et la configuration
sont exprimés en jours. La condition supprime seulement lorsque l'âge dépasse
cette limite.

Vérification manuelle isolée : le lancement avec un rapport âgé de 8 jours a
affiché `D6 rapports purges : 0` et l'a conservé ; avec un rapport âgé de
211 jours, D6 l'a supprimé. Un essai contrôlé avec des rapports de 209, 210 et
211 jours a conservé les deux premiers et supprimé le dernier. La condition
étant strictement `âge > limite`, la purge commence après 210 jours (7 × 30).

Correction prévue : supprimer le facteur 30 et comparer l'âge directement à
`retention_jours`.

Priorité : fausse un résultat — la durée réelle dépasse la durée annoncée et
laisse les rapports contenant des données IP en conservation plus longtemps.

État : ouvert, consigné à l'étape 6 sans correction du code.

## Tests de régression à compléter

- B4 : `test_d5_seuil_5xx_depuis_config` doit charger le seuil de 5 % du modèle
  et déclencher l'alerte pour 48 réponses `5xx` sur 743 (6,46 %).
- B5 : `test_d2_seuil_exact_declenche` doit déclencher l'alerte pour exactement
  10 échecs lorsque le seuil vaut 10.
- B6 : `test_d6_retention_7_jours_garde_la_limite_et_supprime_8_jours` doit
  conserver un rapport âgé de 7 jours et supprimer celui âgé de 8 jours.
