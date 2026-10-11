# Pré-audit GRIB en lecture seule (prototype)

AVANTEMPS peut maintenant **inventorier les messages GRIB** via ecCodes avant la préparation de séries climatiques. Ce module est volontairement un **pré-audit bloquant**, pas un extracteur scientifique.

## Préparer localement

- Utiliser les GRIB réellement téléchargés via CDS après acceptation des licences.
- Installer Python et la bibliothèque ecCodes dans un environnement isolé sur le Mac Pro ; vérifier la documentation officielle https://github.com/ecmwf/eccodes-python et https://confluence.ecmwf.int/display/ECC/ecCodes+documentation.
- Ne pas installer ces dépendances sur SILLO : l'API AVANTEMPS reste légère.

Depuis la racine du dépôt :

~~~sh
python3 -m avantemps.grib_audit var/cds-nc/forecast.grib --role forecast
python3 -m avantemps.grib_audit var/cds-nc/observations.grib --role observations
~~~

Chaque commande produit un rapport JSON avec taille, SHA-256, nombre de messages, paramètres, unités déclarées, grilles et présence de membres/leads pour les prévisions. Aucune modification du GRIB, aucune connexion réseau et aucune publication dans l'API.

## Important : ne PAS prendre le rapport pour une validation

- La présence d'un en-tête GRIB ne prouve pas que les messages correspondent bien au produit CDS annoncé.
- La syntaxe exacte des unités doit être vérifiée pour chaque message ; elles restent marquées comme non confirmées.
- Les coordonnées et résolutions doivent être comparées au domaine demandé et à la configuration effective du produit.
- Les dimensions d'ensemble, dates de validité, type de moyenne temporelle et masques de terrain doivent faire l'objet d'une validation scientifique ; ce module ne les certifie pas.
- Les rapports mentionnent systématiquement "extraction_approved=false" et "publication_authorized=false".
- Le code d'appariement CSV existant ne doit pas recevoir des GRIB décodés sans protocole d'extraction revu.

La prochaine étape est de tester le pré-audit sur de **vrais fichiers CDS** et d'adapter les clés, unités et messages observés avant toute extraction automatique. Aucune donnée réelle n'a été traitée pendant cette livraison.

## Contrôle optionnel des valeurs brutes — 11 octobre 2026

`python3 -m avantemps.grib_audit fichier.grib --role forecast --inspect-values`

Cette option décode un message à la fois (limite : un million de points par
message). Le bitmap GRIB identifie les points manquants ; une comparaison avec
la sentinelle numérique serait ambiguë. Les nombres non finis et les valeurs
négatives sont signalés, jamais corrigés ou remplacés. Les extrema restent en
unités brutes déclarées dans le GRIB. Un rapport sans anomalie numérique ne
valide ni les unités, ni le produit, ni la couverture temporelle, ni la compétence.
Les indicateurs `extraction_approved` et `publication_authorized` restent faux.
La signature de grille inclut désormais résolution et ordre de balayage.

Références officielles consultées le 11 octobre 2026 :
- https://confluence.ecmwf.int/display/ECC/GRIB+examples (iterator bitmap)
- https://confluence.ecmwf.int/display/ECC/grib_get_data
- https://confluence.ecmwf.int/spaces/CKB/pages/165320495/Guidelines+to+decode+monthly+C3S+seasonal+forecast+data
- https://cds.climate.copernicus.eu/datasets/seasonal-monthly-single-levels

Attention : pour les systèmes à initialisations décalées, `dataDate` peut être
la date réelle plutôt que nominale ; `indexingDate`, `indexingTime` et la
 définition locale sont maintenant inventoriés. Leur présence ne suffit pas à
reconstruire automatiquement les dates. Aucun élargissement aux autres systèmes.

### Résultats et limites

Les tests couvrent bitmap, valeurs manquantes, nombres non finis, pluie négative,
absence de modification et aller-retour d'un GRIB **SYNTHÉTIQUE** encodé avec
ecCodes. Ce fichier ne représente aucune observation ni sortie Copernicus.
Aucun fichier réel CDS n'a été acquis ou validé pendant ce travail. Aucun score.

L'extraction GRIB vers les séries CSV reste bloquée par l'absence de fichiers
réels inspectés. Il faut un accès personnel CDS et les licences acceptées, puis
contrôler système/version, unités, dates nominales/valides, membres, échéances,
complétude et grille. L'agrégat spatial doit être revu indépendamment avant la
comparaison ; ERA5 est une réanalyse, pas une station pluviométrique locale.
L'étendue marine et la topographie rendent une moyenne du rectangle NC impropre
à représenter automatiquement la pluie sur les terres. Publication verrouillée.

## Contrôler la couverture des hindcasts contre un plan CDS

~~~sh
python3 -m avantemps.grib_audit var/cds-nc/forecast.grib --role forecast --plan var-plan.json --inspect-values
~~~

Le contrôle optionnel `--plan` est limité aux hindcasts ECMWF burst des systèmes
5/51 déjà documentés. Il lit les clés explicites `system`, `centre`, `dataDate`,
`dataTime`, `number` et `forecastMonth` : aucun lead n'est déduit d'une date de
validité, aucune date d'initialisation décalée n'est remappée silencieusement.
Les couples de dates réelle/nominale différents requièrent une inspection.

La documentation officielle donne 25 membres de hindcast ECMWF. Les identifiants
sont inventoriés dans le fichier, sans présumer `0..24` ou `1..25`. Le contrôle
vérifie le nombre documenté, le produit cartésien initialisation/membre/échéance,
les messages dupliqués et les clés hors plan. Un membre absent sur toute la
période n'est pas inventé dans la liste des identifiants manquants : le nombre de
membres incorrect est signalé séparément. Exemples de diagnostics limités à dix.

`header_coverage_matches_plan` ne signifie que couverture des en-têtes conforme.
Cela ne prouve ni authenticité, unités, périodes de moyenne, emprise, valeurs,
représentativité, ni compétence. L'extraction et la publication restent interdites.
`review_required` indique un écart ; le CLI fournit un inventaire JSON et n'est
pas un garde automatique d'extraction. Lire le statut et ses problèmes explicites.
Le contrôle ne valide pas ERA5 et refuse `--plan` avec le rôle observations.

Sources consultées le 11 octobre 2026 :
- https://confluence.ecmwf.int/spaces/CKB/pages/77213502/Description+of+the+C3S+seasonal+multi-system
- https://confluence.ecmwf.int/spaces/CKB/pages/165320495/Guidelines+to+decode+monthly+C3S+seasonal+forecast+data

Tests : métadonnées SYNTHÉTIQUES complètes/incomplètes, membre totalement absent,
doublon masquant une absence, version/centre/dates/leads incorrects, alias de
membre, fenêtre glissante et GRIB synthétique non saisonnier refusé comme couvert.
Aucun fichier CDS réel validé ; les clés et le protocole restent à éprouver lors
de la première acquisition légitime. L'extracteur GRIB->CSV n'est pas livré.
