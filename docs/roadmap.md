# Feuille de route — objectifs mesurables

## P0 : preuve de données (première PR)

- [x] Définir RONI officiel et ses limites.
- [x] Analyseur indépendant du réseau avec validations.
- [x] Archivage par empreinte SHA-256 avec conservation de la source brute.
- [x] API locale en lecture seule et visualisation mobile.
- [x] Tests unitaires et pipeline CI.
- [ ] Vérifier le téléchargement réel sur plusieurs cycles NOAA.
- [ ] Obtenir un avis de scientifique indépendant.
- [ ] Vérifier en détail les obligations de redistribution et l'usage du nom.

## P1 : traçabilité et compréhension

- [x] Différences entre deux versions d'une même saison, dates de première collecte et historique local (issue #3).
- [x] Comparaison consultable via API et panneau mobile.
- [ ] Export complet documenté et visualisation du parcours des révisions sur plus de deux versions.
- [ ] Glossaire ENSO et évaluation de compréhension avec utilisateurs.
- [ ] Diagnostic ENSO officiel distinct des valeurs de l'indice.

## P2 : territoire pilote

- [x] Première revue de quatre sources primaires Météo-France pour la Nouvelle-Calédonie (version documentaire, non validée par expert externe).
- [x] Fiche territoriale sourcée et catégorisée (climatologie, bulletin daté, observation historique).
- [x] Affichage d'abstention explicite pour Nantes et Guyane.
- [ ] Étendre la revue scientifique à des articles évalués et aux séries locales exploitables.
- [x] Outillage hors ligne de vérification probabiliste expérimentale (RPS/RPSS), avec absence systématique de publication de scores.
- [x] Générateur de requêtes C3S / ERA5 bornées et téléchargement optionnel documenté (sans clé dans Git).
- [x] Outil d'appariement de taux de pluie mensuels préparés vers pairs.csv, calibration leave-one-year-out, conversion des unités et gestion des calendriers.
- [x] Premier pré-audit GRIB en lecture seule avec ecCodes : inventaire des messages, grilles et unités, sans publication.
- [ ] Exécuter ce pré-audit sur des vrais GRIB CDS et inspecter les clés effectives.
- [ ] Extraction reproductible GRIB -> tableaux mensuels, audit de la grille et des membres d'ensemble.
- [ ] Acquisition de vrais hindcasts C3S + observations adaptées ; **aucune mesure réelle de performance territoriale effectuée**.
- [ ] Audit de la méthodologie hors échantillon et des performances par variable et échéance.
- [x] Droit d'abstention dans l'API et l'interface pour les territoires non étudiés.
- [ ] Tester la même abstention pour les prévisions régionales insuffisamment fiables.
- [ ] Retour utilisateur local avant extension.

## P3 : alertes et continuité (seulement après validation)

- [ ] Inventaire juridique, licences, latences et couverture des flux officiels.
- [ ] Relais explicite des alertes officielles avec lien vers la source.
- [ ] Audit de sécurité, accessibilité, gestion des pannes, méthodes de distribution.
- [ ] Application installable si la PWA présente une limite d'usage réelle.

Aucune échéance de livraison opérationnelle n'est promise avant les revues externes.
