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
