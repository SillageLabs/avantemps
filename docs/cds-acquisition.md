# Acquisition C3S / ERA5 — protocole reproductible v0.1

Mis en place le 11 octobre 2026. **Aucune série Copernicus réelle téléchargée ou évaluée par le dépôt à ce stade.**

## Chaîne reproductible

1. Générer un plan de requêtes C3S hindcasts et ERA5 avec une emprise limitée à la Nouvelle-Calédonie.
2. Accepter les conditions de licence CDS et configurer la clé API dans votre environnement local, jamais sur GitHub.
3. Télécharger explicitement les GRIB, en conservant les requêtes, les empreintes SHA-256 et la date.
4. Inspecter et extraire un point de grille/agrégat spatial cohérent pour toutes les années, tous les membres et les observations. **Cette extraction GRIB n'est pas encore automatisée.**
5. Apparier les fichiers mensuels, convertir correctement les unités et calibrer les terciles hors année testée.
6. Exécuter séparément le banc de vérification scientifique hors ligne, sans diffuser le score.

## Sources de référence

- [Tutoriel officiel C3S sur les hindcasts](https://ecmwf-training.github.io/c3s-training/submodules/c3s-training-submodule-seasonal-forecast/sf-verification/)
- [Données mensuelles de prévisions saisonnières](https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels?tab=download)
- [ERA5 mensuel](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels-monthly-means?tab=download)
- [Table officielle de conversion des précipitations](https://confluence.ecmwf.int/pages/viewpage.action?pageId=673332657)
- [Documentation d'accès API CDS](https://cds.climate.copernicus.eu/how-to-api)

La combinaison de départ est ECMWF système 5 (SEAS5), période de référence 1993-2016, tirée de l'exemple officiel. Sa disponibilité, les données de pluie, les conditions de licence et les paramètres de région doivent être confirmés auprès du CDS avant une récupération réelle.

Les téléchargements globaux du tutoriel peuvent nécessiter de gros volumes. Le plan AVANTEMPS réduit l'emprise à un petit domaine de recherche, sans prétendre fournir une prévision communale.

## A — Planifier, sans connexion ni écriture involontaire

~~~sh
python3 -m avantemps.cds_requests --centre ecmwf --system 5 --first-year 1993 --last-year 2016 --init-month 11 --lead-month 1 > var-plan.json
~~~

Pour novembre et les leads 1-3, les mois cibles sont novembre, décembre et janvier de l'année suivante. ERA5 doit couvrir janvier 2017 pour le dernier hindcast de 2016.

La requête ERA5 peut récupérer des mois excédentaires en raison de la sélection par année et mois : ils doivent être filtrés au moment de l'extraction.

## B — Télécharger après consentement explicite

Préparer un compte CDS, accepter les conditions sur les deux jeux de données, installer le package cdsapi et configurer localement les identifiants conformément au portail. Prévoir un dossier vide et de la place sur le disque.

~~~sh
python3 -m avantemps.cds_requests --init-month 11 --lead-month 1 --execute --acknowledge-cds-terms --output-dir var/cds-nc
~~~

Aucun téléchargement n'est lancé dans les tests, le serveur ni GitHub Actions. La commande affiche la progression de cdsapi et produit deux fichiers GRIB et un manifeste avec empreintes SHA-256. Les secrets et fichiers bruts ne vont pas dans Git. Aucun déploiement SILLO n'est envisagé.

## C — Extraction des GRIB : maillon non encore livré

Il faut vérifier les unités réellement déclarées dans les messages, la correspondance de la grille et de la terre, les dimensions année, mois, lead, membre, et vérifier que toutes les saisons attendues sont présentes.

Les exports mensuels doivent contenir **des taux bruts**, avant conversion.

Forecast CSV :

~~~text
year,member,lead_month,tp_m_per_s
1993,0,1,TAUX_REEL_VERIFIE
1993,0,2,TAUX_REEL_VERIFIE
1993,0,3,TAUX_REEL_VERIFIE
...
~~~

Observations ERA5 CSV :

~~~text
year,month,tp_m_per_day
1993,11,TAUX_REEL_VERIFIE
1993,12,TAUX_REEL_VERIFIE
1994,1,TAUX_REEL_VERIFIE
...
~~~

Ces lignes ne sont que des schémas et **ne constituent pas des observations réelles**. L'extraction ne doit pas confondre initialisation du modèle et date de validité, ni changer la définition spatiale entre les deux sources.

## D — Convertir et apparier

~~~sh
python3 -m avantemps.pairing --plan var-plan.json --forecast-monthly var/forecast-monthly.csv --observed-monthly var/observed-monthly.csv --output-dir var/hindcast-nc-paired
~~~

La conversion applique :
- C3S saisonnier mensuel : taux m/s multiplié par 86 400 secondes, par le nombre de jours du mois puis par 1 000 (mm).
- ERA5 mensuel : taux m/jour multiplié par le nombre de jours du mois puis par 1 000 (mm).

Le code traite les années bissextiles et les fenêtres traversant décembre/janvier. Il exige toutes les observations et les membres de l'ensemble et recalcule les probabilités par année en excluant cette dernière du jeu d'entraînement. Il refuse les données manquantes, dupliquées ou non finies.

La sortie contient trois fichiers : pairs.csv, manifest.json, provenance.json. Leur provenance inclut les empreintes SHA-256 des deux CSV sources. Les avertissements indiquent que l'extraction spatiale et ses unités ne sont pas encore auditées, et que le rapport ne doit pas être publié.

## E — Mesurer la performance sans diffusion

~~~sh
python3 -m avantemps.verification --manifest var/hindcast-nc-paired/manifest.json --pairs var/hindcast-nc-paired/pairs.csv
~~~

Ce module calcule un score RPSS rétrospectif exploratoire ; il ne publie aucune prévision. Une relecture scientifique indépendante reste obligatoire.

## Limites

- La résolution C3S de 1 degré ne garantit aucune représentativité communale en Nouvelle-Calédonie, notamment du relief et des îles.
- ERA5 est une réanalyse à grille, pas une mesure pluviométrique de station.
- Un score RPSS positif ne suffit pas à valider un service prédictif.
- Les données réelles et l'extracteur GRIB sont encore à acquérir/développer.
- Aucun calcul de risque local, aucune alerte et aucun accès automatique aux systèmes de production.

## Pré-audit des GRIB (sans extraction automatique)

Avant d'utiliser les fichiers, effectuer un inventaire en lecture seule via ecCodes : `python3 -m avantemps.grib_audit var/cds-nc/forecast.grib --role forecast` puis `python3 -m avantemps.grib_audit var/cds-nc/observations.grib --role observations`. Voir [les limites de ce pré-audit](grib-preflight.md). Le rapport n'autorise aucune extraction ni publication et ne remplace pas le contrôle des unités et de la grille sur fichiers réels.

## Vérifier l'intégrité locale avant le pré-audit GRIB

Ajout du 11 octobre 2026 :

~~~sh
python3 -m avantemps.cds_integrity var/cds-nc
~~~

Cette commande ne se connecte à aucun service et ne modifie aucun fichier. Elle
vérifie le schéma du manifeste, le plan canonique, les deux rôles et leurs jeux
de données, les noms fixes des fichiers, la date UTC déclarée, leur taille et
leur SHA-256 calculé en flux. Les liens symboliques et chemins arbitraires sont
refusés. Les marqueurs GRIB de début/fin sont vérifiés, mais ne prouvent pas que
le fichier est entièrement décodable. Le pré-audit ecCodes reste nécessaire.

`status=matches_local_manifest` signifie seulement que les octets correspondent
au manifeste local. Un manifeste et ses empreintes peuvent être fabriqués
ensemble ; ce contrôle n'authentifie pas le fournisseur, l'acceptation des
licences, les dates de collecte ou la validité scientifique. Les quatre champs
`provider_authenticity_verified`, `scientific_validation_completed`,
`extraction_approved` et `publication_authorized` restent faux.

Les tests utilisent des octets **SYNTHÉTIQUES NON SCIENTIFIQUES** ; ils couvrent
altération à taille constante, troncature, mauvais rôles/jeux, chemins, symlinks,
manifestes invalides et retour CLI. Aucune acquisition réelle pendant ce travail.

Le téléchargement refuse désormais un plan modifié avant de créer un client CDS
ou un répertoire. Les requêtes restent limitées au protocole expérimental défini.
L'accès personnel et l'acceptation manuelle des conditions restent requis selon
la documentation officielle consultée : https://cds.climate.copernicus.eu/how-to-api

Étape suivante inchangée : inspecter les vrais messages puis élaborer et revoir
le protocole d'extraction spatial/temporel. L'intégrité locale ne lève aucun
blocage scientifique, et ne déclenche aucun téléchargement ou déploiement.

## Identité des membres et absence de fuite temporelle

Les identifiants CSV numériques sont normalisés (`00` et `0` désignent le même
membre) avant de vérifier les doublons et la complétude. Un export qui répète un
membre sous plusieurs écritures est refusé afin de ne pas surpondérer ce membre
dans les probabilités. Un export entièrement avec zéros initiaux conserve les
mêmes résultats. Les identifiants numériques non ASCII sont refusés.

Un test de perturbation **SYNTHÉTIQUE** modifie uniquement les prévisions de la
dernière année évaluée : les échantillons de calibration de cette année doivent
rester identiques, tandis que ceux d'une autre année changent. Cela contrôle
l'exclusion de l'année testée dans les terciles modèles ; ce test ne prouve ni
la compétence du modèle ni la représentativité des entrées réelles.

L'appariement réutilise le même validateur de plan canonique que l'acquisition.
Référence méthodologique consultée le 11 octobre 2026 :
https://ecmwf-training.github.io/c3s-training/submodules/c3s-training-submodule-seasonal-forecast/sf-verification/
