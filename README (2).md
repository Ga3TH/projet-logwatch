# LogWatch v0 - kit de départ

Script Python de surveillance des logs web des trois clients hébergés par OctopodSec.
Il lit un fichier de logs Apache, applique six détections et écrit un rapport JSON.

> **État de la v0.** Le script tourne sans planter. Kevin a écrit quatre tests dans
> `test_logwatch.py` ; **deux sont rouges**. D'autres détections donnent des résultats
> qu'il trouve bizarres, sans avoir eu le temps de chercher. C'est votre point de départ :
> voir le sujet du projet, Sprint 1.

## Contenu du kit

| Fichier | Rôle |
|---|---|
| `logwatch.py` | le script v0, base de départ |
| `test_logwatch.py` | les quatre tests de Kevin, dont deux échouent |
| `config.example.json` | les seuils : **à copier en `config.json`** |
| `.env.example` | les chemins par défaut : **à copier en `.env`** |
| `sample-logs.log` | deux heures de logs d'un client, avec ce qu'il faut pour faire réagir chaque détection |
| `regex-apache.md` | le format des lignes et la regex qui les lit |
| `README.md` | ce fichier |

## Mise en route

```bash
python -m venv .venv
source .venv/bin/activate        # Linux / Mac
.venv\Scripts\activate           # Windows, invite cmd
.venv\Scripts\Activate.ps1       # Windows, PowerShell (terminal de VS Code)
pip install pytest
cp config.example.json config.json
cp .env.example .env
pytest test_logwatch.py -v       # 2 FAIL attendus
python logwatch.py               # ecrit reports/rapport-AAAAMMJJ-HHMMSS.json
```

Le script n'a **aucune dépendance** en dehors de la bibliothèque standard ; `pytest`
ne sert qu'aux tests. Python 3.11 ou plus.

Options de la ligne de commande (elles ont priorité sur `.env`) :

```
python logwatch.py --log sample-logs.log --config config.json --reports reports
```

## Le rapport

Un fichier JSON par exécution, dans `reports/` :

```
genere_le, fichier, total_lines, lignes_ignorees, config,
D1_requetes_par_ip, D2_brute_force, D3_scan, D4_pic_trafic, D5_erreurs_5xx, D6_rapports_purges
```

`total_lines` est le nombre de lignes **exploitées** ; les lignes qui n'ont pas la forme
attendue sont comptées à part dans `lignes_ignorees`.

## Les seuils (`config.json`)

| Clé | Défaut | Sens |
|---|---|---|
| `top_ips` | 10 | nombre d'IP affichées par D1 |
| `seuil_brute_force` | 10 | D2 : une IP est signalée **dès qu'elle atteint** ce nombre d'échecs de connexion |
| `url_login` | `/login` | D2 : la route de connexion surveillée |
| `seuil_scan` | 5 | D3 : nombre d'URL suspectes distinctes à partir duquel une IP est signalée |
| `fenetre_minutes` | 5 | D4 : largeur d'une fenêtre, en minutes ; les fenêtres se suivent sans se chevaucher (10:00-10:05, 10:05-10:10…) |
| `seuil_pic` | 100 | D4 : requêtes dans une fenêtre au-delà desquelles on parle de pic |
| `seuil_5xx` | 0.05 | D5 : part de réponses 5xx tolérée (5 %) |
| `retention_jours` | 7 | D6 : âge maximal d'un rapport avant purge (**jours**) |

## Les détections

**D1 - Requêtes par IP.** Compte **toutes** les requêtes de chaque IP, quel que soit le
code de réponse, et affiche les `top_ips` plus actives. La somme de toutes les IP doit
être égale à `total_lines`.

**D2 - Brute force.** Une IP qui enchaîne des échecs de connexion (`POST` sur `url_login`
avec un 401 ou un 403) est signalée dès que son nombre d'échecs atteint
`seuil_brute_force`.

**D3 - Scan de vulnérabilités.** Une IP qui demande au moins `seuil_scan` URL distinctes
typiques d'un scanner (`/wp-admin/`, `/phpmyadmin/`, `/.env`, `/.git/`, `../`,
`xmlrpc.php`…) est signalée. Les pages légitimes du site ne doivent jamais apparaître.

**D4 - Pic de trafic.** Le trafic est découpé en fenêtres de `fenetre_minutes` minutes ;
si une fenêtre dépasse `seuil_pic` requêtes, c'est un pic, et le rapport dit laquelle.

**D5 - Erreurs serveur.** Part des réponses 5xx sur l'ensemble des requêtes ; alerte
au-delà de `seuil_5xx`.

**D6 - Purge des rapports.** Les rapports contiennent des adresses IP : ce sont des
données personnelles. Tout rapport plus vieux que `retention_jours` **jours** est
supprimé à chaque exécution. Dans les rapports, les IP sont écrites avec le dernier
octet masqué (`203.0.113.x`).

## D7 - à ajouter (Sprint 1, étape 7)

**D7 - Requêtes lentes.** Le dernier champ de chaque ligne est la durée de traitement
en microsecondes (`%D`, voir `regex-apache.md`). D7 signale les requêtes dont la durée
dépasse `seuil_lenteur_ms` (**millisecondes**, défaut 2000, à ajouter dans la
configuration). Le rapport porte une entrée `D7_requetes_lentes` avec :

- `nb` : le nombre de requêtes lentes ;
- `requetes` : la liste des requêtes concernées, chacune avec `ip` (anonymisée), `url`,
  `methode`, `duree_ms`, triée de la plus lente à la moins lente, limitée aux 20 premières.

Une ligne sans champ durée (log combined classique) n'est jamais comptée comme lente.

## Ce que le jeu de logs contient

`sample-logs.log` couvre deux heures d'un matin ordinaire chez un client : du trafic
normal depuis une quinzaine d'adresses, une tentative de brute force sur `/login`,
un scanner qui sonde les URL classiques, un pic de trafic sur quelques minutes, une
salve d'erreurs serveur et quelques requêtes anormalement lentes. Il contient aussi
trois lignes mal formées.

## Ce qui n'est pas dans le kit

Pas de serveur, pas de base de données, pas d'envoi d'e-mail. Le script se lance à la
main ou par une tâche planifiée : ce n'est pas votre sujet.
