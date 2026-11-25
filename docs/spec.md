# Spécification mesurable des détections LogWatch

Cette spécification décrit les résultats attendus sur `sample-logs.log` et les
tests qui doivent prouver les corrections. Les chiffres D1 à D5 viennent de
`python explorer.py` et des fonctions LogWatch. D6 nécessite des fichiers de
rapport de test ; le journal d'exemple ne permet pas de vérifier la rétention.
D7 est spécifié et exploré, mais n'est pas encore une alerte produite par
`logwatch.py`.

## Jeu de données et configuration

Le journal comporte 746 lignes physiques : 743 requêtes analysées et 3 lignes
ignorées. Les 743 requêtes analysées ont toutes un statut et une durée `%D`.
Les seuils pertinents sont : 10 échecs pour D2, 5 URL suspectes pour D3,
100 requêtes sur 5 minutes pour D4, 5 % pour D5, 7 jours pour D6 et 2 000 ms
pour l'exploration D7.

| Mesure de référence | Résultat |
| --- | ---: |
| Requêtes analysées / lignes ignorées | 743 / 3 |
| Réponses 2xx / 3xx / 4xx / 5xx | 531 / 28 / 136 / 48 |
| Somme des requêtes par IP (D1) | 743 |
| Échecs `POST /login` en 401/403 (D2) | 45 depuis une IP |
| Durée connue / absente (D7) | 743 / 0 |
| Requêtes lentes à partir de 2 000 ms (D7) | 9 |

## Résultats attendus par détection

### D1 — Requêtes par IP

- **Attendu :** compter tous les statuts, y compris les erreurs. La somme des
  comptages par IP est exactement **743**, le nombre de requêtes analysées.
- **Régression :** `test_d1_somme_egale_total_lines` vérifie que les réponses
  4xx et 5xx ne sont pas exclues. Ce test existe.
- **Défaut lié :** B1, fermé.

### D2 — Brute force

- **Attendu sur l'exemple :** une IP a **45** échecs `POST /login` en 401/403.
  Avec un seuil de **10**, elle déclenche une alerte de gravité `haute`.
- **Limite :** exactement **10** échecs doivent aussi déclencher l'alerte
  (`nombre >= seuil`).
- **Régressions :** `test_d2_brute_force_detecte` vérifie le cas à 40 échecs ;
  `test_d2_seuil_exact_declenche` vérifie la limite exacte.
- **Défaut lié :** B5, fermé.

### D3 — Scan

- **Attendu sur l'exemple :** **1** IP déclenche une alerte, avec **13** URL
  suspectes distinctes au seuil de 5. L'adresse est anonymisée dans le rapport.
- **Régression :** `test_d3_ignore_url_legitime` vérifie qu'au moins 5 chemins
  légitimes contenant « admin » ne déclenchent pas d'alerte. Ce test existe.
- **Défaut lié :** B2, fermé.

### D4 — Pic de trafic

- **Attendu sur l'exemple :** la fenêtre de **5 minutes** la plus chargée
  contient **190** requêtes, au-dessus du seuil de 100 ; `alerte` vaut `true`.
  La minute la plus chargée est **11:17** avec **170** requêtes.
- **Régression :** `test_B3_d4_regroupe_et_signale_la_fenetre_la_plus_chargee`
  vérifie l'agrégation par fenêtre et les valeurs du pic. Ce test existe.
- **Défaut lié :** B3, fermé.

### D5 — Erreurs serveur

- **Attendu sur l'exemple :** **48 / 743 = 6,46 %** de réponses 5xx. Avec le
  seuil du modèle de configuration de **5 %**, l'alerte vaut `true` (la règle
  est strictement supérieure au seuil).
- **État actuel :** B4 est fermé : `charger_config()` accepte la clé du modèle
  `seuil_erreurs_5xx`, la convertit en `seuil_5xx`, et les fichiers de modèle
  utilisent directement `seuil_5xx`.
- **Régression :** `test_d5_seuil_5xx_depuis_config` charge 5 %
  depuis le modèle et obtenir une alerte pour 48 réponses 5xx sur 743.
- **Défaut lié :** B4, fermé.

### D6 — Rétention des rapports

- **Attendu avec une rétention de 7 jours :** un rapport âgé de 7 jours est
  conservé ; un rapport âgé de **8 jours** est supprimé.
- **État actuel :** B6 est fermé. Le code compare la rétention en jours
  directement, sans facteur 30.
- **Régression :**
  `test_d6_retention_7_jours_garde_la_limite_et_supprime_8_jours` doit créer
  des rapports contrôlés âgés de 7 et 8 jours, puis vérifier leur présence
  respective après purge.
- **Défaut lié :** B6, fermé.

### D7 — Requêtes lentes (spécification à venir)

D7 n'est pas encore intégré au rapport de `logwatch.py`. L'exploration utilise
le champ Apache `%D`, exprimé en microsecondes, et un seuil de **2 000 ms**.
Une requête est lente lorsque sa durée est supérieure ou égale à
**2 000 000 µs**. Le paramètre d'exploration est
`seuil_requete_lente_ms`.

| Cas | Entrée | Résultat attendu |
| --- | --- | --- |
| Nominal | `sample-logs.log` : 743 durées connues | **9** requêtes lentes sur 743 ; 0 durée absente |
| Limite | durée exactement égale à 2 000 ms | comptée comme lente ; 1 durée mesurée, 1 lente |
| Erreur / champ absent | ligne Apache valide sans champ `%D` | ligne analysée avec `duree=None`, non comptée comme lente ; 0 mesurée, 1 sans durée |

Les tests de l'exploration sont `test_d7_compte_les_durees_au_seuil_de_2000_ms`
et `test_d7_exclut_une_requete_sans_duree`. Le cas sans durée doit être fabriqué
dans le test : les 743 requêtes analysées de `sample-logs.log` ont toutes une
durée.
