# Aide-mémoire - le format des logs et la regex qui les lit

## Le format

Les trois clients hébergés écrivent leurs logs Apache au format **combined**, auquel
OctopodSec a ajouté **un dernier champ** : la durée de traitement de la requête,
`%D`, en **microsecondes**.

```
203.0.113.7 - - [03/Sep/2026:10:15:32 +0200] "GET /index.html HTTP/1.1" 200 5123 "-" "Mozilla/5.0" 1523
```

| Champ | Exemple | Ce que c'est |
|---|---|---|
| `ip` | `203.0.113.7` | l'adresse du client. **Donnée personnelle** au sens de la CNIL |
| `-` `-` | | identité et utilisateur authentifié, jamais renseignés ici |
| `date` | `[03/Sep/2026:10:15:32 +0200]` | horodatage, fuseau compris |
| `methode` | `GET` | verbe HTTP |
| `url` | `/index.html` | chemin demandé, avec sa chaîne de requête éventuelle |
| `proto` | `HTTP/1.1` | version du protocole |
| `statut` | `200` | code de réponse HTTP |
| `taille` | `5123` | octets envoyés, ou `-` |
| `referer` | `"-"` | page d'origine, entre guillemets |
| `agent` | `"Mozilla/5.0"` | navigateur ou robot, entre guillemets |
| `duree` | `1523` | **ajout OctopodSec** : `%D`, microsecondes. `1523` = 1,5 ms ; `2500000` = 2,5 s |

Une ligne qui n'a pas cette forme est **ignorée** par le script et comptée dans
`lignes_ignorees` du rapport.

## La regex du script

```python
LIGNE = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<date>[^\]]+)\] '
    r'"(?P<methode>\S+) (?P<url>\S+) (?P<proto>[^"]*)" '
    r'(?P<statut>\d{3}) (?P<taille>\S+) "(?P<referer>[^"]*)" "(?P<agent>[^"]*)"'
    r'(?: (?P<duree>\d+))?$'
)
```

| Morceau | Se lit |
|---|---|
| `(?P<ip>\S+)` | un groupe **nommé** `ip` : une suite de caractères sans espace |
| `\[(?P<date>[^\]]+)\]` | un crochet ouvrant, puis tout sauf un crochet fermant, puis le crochet fermant |
| `"(?P<methode>\S+) (?P<url>\S+) (?P<proto>[^"]*)"` | la requête entre guillemets : trois morceaux séparés par des espaces |
| `(?P<statut>\d{3})` | exactement trois chiffres |
| `"(?P<referer>[^"]*)"` | tout sauf un guillemet, entre guillemets - le referer peut être vide |
| `(?: (?P<duree>\d+))?$` | le champ durée est **optionnel** : une ligne combined classique passe aussi, `duree` vaut alors `None` |

`m.groupdict()` rend un dictionnaire dont les clés sont les noms des groupes : c'est
ce que `parser_ligne()` renvoie, après avoir converti `statut`, `taille` et `duree`
en entiers et `date` en `datetime`.

## Pour essayer une regex

- [regex101.com](https://regex101.com), saveur **Python**, en collant une ligne de `sample-logs.log`.
- En console Python : `import re` puis `re.match(LIGNE, ligne).groupdict()`.

## Parser la date

```python
datetime.strptime("03/Sep/2026:10:15:32 +0200", "%d/%b/%Y:%H:%M:%S %z")
```

`%b` est le mois abrégé **en anglais** (`Sep`, pas `sept.`) : c'est ce qu'Apache écrit
quelle que soit la langue du serveur.
