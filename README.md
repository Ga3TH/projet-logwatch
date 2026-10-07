# LogWatch

LogWatch est un petit outil Python qui lit des journaux Apache, compte les
requêtes et recherche plusieurs types d'activité suspecte. Il produit un
rapport JSON dans `reports/`.

Ce guide explique comment installer et lancer le projet sous **Windows avec
PowerShell**.

## Sommaire

1. [Installer Python](#1-installer-python)
2. [Ouvrir le dossier du projet](#2-ouvrir-le-dossier-du-projet)
3. [Créer l'environnement et installer pytest](#3-créer-lenvironnement-et-installer-pytest)
4. [Préparer la configuration](#4-préparer-la-configuration)
5. [Lancer les tests](#5-lancer-les-tests)
6. [Explorer les logs](#6-explorer-les-logs)
7. [Lancer LogWatch](#7-lancer-logwatch)
8. [Résoudre les problèmes courants](#résoudre-les-problèmes-courants)

## 1. Installer Python

Installe Python 3.11 ou une version plus récente depuis
[python.org](https://www.python.org/downloads/). Pendant l'installation,
coche **Add Python to PATH** si cette option est proposée.

Ferme puis rouvre PowerShell et vérifie l'installation :

```powershell
py --version
```

La commande doit afficher la version de Python.

## 2. Ouvrir le dossier du projet

Dans PowerShell, place-toi dans le dossier `Logwatch` qui contient
`logwatch.py` :

```powershell
Set-Location "$HOME\source\projet-logwatch\Logwatch"
```

Si le projet se trouve ailleurs, remplace ce chemin par son emplacement. Pour
vérifier que tu es dans le bon dossier :

```powershell
Get-Location
Get-ChildItem
```

La liste doit notamment contenir `logwatch.py`, `test_logwatch.py` et
`sample-logs.log`. **Ne refais pas `cd .\Logwatch\`** si tu es déjà dans ce
dossier.

## 3. Créer l'environnement et installer pytest

Crée un environnement Python isolé pour ce projet, puis active-le :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Quand l'environnement est actif, `(.venv)` apparaît au début de l'invite de
commande. Installe pytest, l'outil qui exécute les tests :

```powershell
python -m pip install pytest
```

LogWatch lui-même utilise la bibliothèque standard de Python ; pytest est
nécessaire uniquement pour lancer les tests.

## 4. Préparer la configuration

Les fichiers `config.example.json` et `env.example` sont des modèles. Pour
créer les fichiers locaux utilisés par le programme, exécute dans PowerShell :

```powershell
if (-not (Test-Path config.json)) { Copy-Item config.example.json config.json }
if (-not (Test-Path .env)) { Copy-Item env.example .env }
```

`config.json` contient les seuils des détections. `.env` contient les chemins
par défaut du fichier de logs, de la configuration et des rapports. Tu peux
garder les valeurs fournies pour commencer.

## 5. Lancer les tests

Depuis le dossier `Logwatch`, avec `(.venv)` actif, exécute :

```powershell
python -m pytest test_logwatch.py -v
```

Les quatre tests actuels doivent afficher `PASSED`, puis un résumé semblable à :

```text
4 passed
```

Les tests vérifient le décodage d'une ligne Apache, le total des requêtes par
IP, la détection d'échecs de connexion et l'exclusion de pages légitimes du
scan.

## 6. Explorer les logs

Lance le script d'exploration :

```powershell
python explorer.py
```

Avec le fichier fourni `sample-logs.log`, les valeurs attendues sont :

| Vérification | Résultat attendu |
| --- | ---: |
| Requêtes lues | 743 |
| Lignes ignorées | 3 |
| Réponses 2xx | 531 |
| Réponses 3xx | 28 |
| Réponses 4xx | 136 |
| Réponses 5xx | 48 |
| Somme des familles de réponse | 743 |
| Somme des requêtes par IP (D1) | 743 |
| Échecs de connexion de `198.51.100.23` | 45 |

La liste des requêtes par IP est affichée en entier par `explorer.py`.

## 7. Lancer LogWatch

Pour analyser les logs d'exemple et créer un rapport JSON :

```powershell
python logwatch.py
```

Le programme affiche ses résultats dans le terminal et écrit un fichier
`rapport-AAAAMMJJ-HHMMSS.json` dans `reports/`.

Les chemins peuvent être fournis directement en ligne de commande :

```powershell
python logwatch.py --log sample-logs.log --config config.json --reports reports
```

Les options de la ligne de commande remplacent les chemins configurés dans
`.env`. Pour arrêter le programme une fois terminé, rien de particulier n'est
nécessaire : il revient automatiquement à l'invite PowerShell.

## Les détections

- **D1 — Requêtes par IP :** compte toutes les requêtes de chaque adresse IP.
- **D2 — Brute force :** compte les `POST` vers `/login` répondant `401` ou
  `403`, puis signale les adresses au-dessus du seuil.
- **D3 — Scan :** recherche les requêtes vers des chemins typiques de scanners,
  comme `/.env`, `/.git/` ou `/phpmyadmin/`.
- **D4 — Pic de trafic :** calcule la charge moyenne par minute et la requête
  maximale sur une minute.
- **D5 — Erreurs serveur :** calcule la proportion de réponses `5xx`.
- **D6 — Purge :** supprime les anciens rapports selon la rétention configurée.

Les seuils se trouvent dans `config.json`. Les valeurs par défaut sont définies
dans `logwatch.py`.

## Résoudre les problèmes courants

### `pytest` n'est pas reconnu

Vérifie que l'environnement est actif (`(.venv)` au début de la ligne) et
lance pytest ainsi :

```powershell
python -m pytest test_logwatch.py -v
```

Cette forme fonctionne même si la commande `pytest` seule n'est pas trouvée.

### L'activation de `.venv` est bloquée

Dans PowerShell, autorise les scripts uniquement pour le terminal courant,
puis active l'environnement :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Fermer le terminal annule cette autorisation. Il est aussi possible de ne pas
activer l'environnement et d'appeler directement ses exécutables :

```powershell
.\.venv\Scripts\python.exe -m pytest test_logwatch.py -v
.\.venv\Scripts\python.exe explorer.py
.\.venv\Scripts\python.exe logwatch.py
```

### `py` ou `python` n'est pas reconnu

Installe Python, ferme puis rouvre PowerShell, et réessaie `py --version`.

### Aucun fichier de rapport n'apparaît

Vérifie que LogWatch a lu au moins une ligne exploitable et que le dossier
indiqué par `--reports` existe ou peut être créé.

## Fichiers principaux

| Fichier | Rôle |
| --- | --- |
| `logwatch.py` | Lecture des logs, détections et création du rapport |
| `explorer.py` | Comptages exploratoires indépendants |
| `test_logwatch.py` | Tests automatisés |
| `sample-logs.log` | Fichier de logs d'exemple |
| `config.example.json` | Modèle des seuils de détection |
| `env.example` | Modèle des chemins par défaut |
| `regex-apache.md` | Format des lignes de log reconnu |
