# AVANTEMPS

**Comprendre les signaux. Préparer les territoires.**

AVANTEMPS est un projet libre de SillageLabs : rendre les données climatiques compréhensibles, vérifiables et utiles à la préparation, sans prétendre prédire une catastrophe locale à partir d'un indice global.

> **Prototype de recherche — pas un service d'alerte.** Pour toute situation dangereuse, consulter les autorités et les bulletins officiels. Aucun indicateur ENSO ne constitue une vigilance météorologique.

## Ce qui fonctionne dans cette première version

- Ingestion manuelle de l'indice **RONI** (NOAA/CPC), nouveau référentiel ENSO opérationnel depuis 2026.
- Validation stricte du fichier source officiel, conservation de la version brute et de son empreinte SHA-256.
- Archives immuables avec contrôle d'intégrité SHA-256 et date de dernière vérification indépendante de la date de première collecte.
- Journal des ajouts, retraits et corrections des observations entre deux versions, visible dans l'interface.
- API HTTP locale en lecture seule et interface mobile simple, sans services tiers ni compte.
- **Dossiers territoriaux sourcés** : Nouvelle-Calédonie (relations historiques et bulletins datés), Nantes et Guyane (absence d'évaluation explicite). Aucun calcul de risque local.
- Tests automatiques, fonctionnement sans Docker et sans accès réseau une fois les données récupérées.

Le prototype ne comporte **ni détection de catastrophe, ni prédiction régionale automatisée, ni notification d'urgence**. Les fiches territoriales sont des documents statiques datés, non un suivi en temps réel.

## Démarrer (Python 3.11+)

Depuis la racine du dépôt :

```sh
python3 -m unittest discover -s tests -v
python3 -m avantemps.ingest --data-dir var/data
python3 -m avantemps.server --data-dir var/data --host 127.0.0.1 --port 18767
```

Ouvrir ensuite http://127.0.0.1:18767/ . Le serveur ne télécharge aucune donnée : la commande d'ingestion effectue seule la récupération NOAA. Un premier lancement du serveur sans ingestion affiche un message d'absence de données. L'ingestion nécessite un accès sortant HTTPS vers la NOAA. Pour contrôler **sans archiver** un fichier déjà téléchargé : `python3 -m avantemps.ingest --check-file /chemin/RONI.ascii.txt`. Un contrôle de format d'un fichier local ne prouve pas qu'il provient effectivement de la NOAA.

### API

- `GET /api/health` : fonctionnement local et présence d'archives.
- `GET /api/territories` : liste des territoires et état de l'étude.
- `GET /api/territories/nouvelle-caledonie` : sources officielles, climatologie et bulletins datés ; fonctionne même sans archive NOAA.
- `GET /api/territories/nantes` et `/api/territories/guyane` : **abstention explicite**, aucune conclusion régionale.
- `GET /api/roni/latest` : dernier indice disponible, provenance et précautions.
- `GET /api/roni/history?limit=24` : observations historiques récentes (maximum 120).
- `GET /api/roni/versions` : versions archivées du fichier NOAA.
- `GET /api/roni/changes` : différences entre les deux versions pertinentes les plus récentes, ou statut indiquant qu'une seule version est disponible.
- `GET /api/roni/changes?before=<sha256>&after=<sha256>` : comparaison explicite de deux archives existantes.

Le statut « signal chaud/froid/neutre » ne prouve pas à lui seul un épisode ENSO : l'atmosphère, la persistance et les bulletins d'experts comptent aussi. Les dernières données peuvent être révisées par la NOAA. Les saisons (`DJF`, `NDJ`, etc.) sont reprises **telles quelles** depuis la source.

## Documents

- [Vision et non-objectifs](docs/vision.md)
- [Sources et qualité scientifique](docs/sources.md)
- [Contrat du journal de révisions](docs/revisions.md)
- [Première enquête territoriale : Nouvelle-Calédonie](docs/territorial-pilot.md)
- [Charte de sûreté et de traçabilité](docs/principles.md)
- [Différenciation et concurrents](docs/competition.md)
- [Feuille de route](docs/roadmap.md)
- [Décision technique](docs/adr-0001.md)

## Gouvernance

Projet expérimental, ouvert aux relectures scientifiques et aux contributions. Licence et modalités de contribution à arrêter avant diffusion de composants réutilisables. Aucun partenariat institutionnel revendiqué.

© Contributeurs AVANTEMPS / SillageLabs.
