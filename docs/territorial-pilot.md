# Pilote territorial — Nouvelle-Calédonie

**Version documentaire : 11 octobre 2026.** Relecture scientifique externe : **non effectuée**. Les dossiers sont statiques et jamais présentés comme un suivi en direct.

## Pourquoi ce territoire ?

Météo-France Nouvelle-Calédonie documente une influence forte d'ENSO sur les pluies, variable selon la saison et la localisation. Elle indique un contraste particulier pour le nord de la Grande Terre et les îles Loyauté en saison chaude.

Source : « Le climat en Nouvelle-Calédonie » (9 décembre 2025).
https://meteo.nc/fr/node/569750

## Quatre informations à ne jamais confondre

| Nature | Information publiée par la source | Interprétation permise | Interprétation interdite |
|---|---|---|---|
| Association climatologique | Durant El Niño, les précipitations d'octobre à mars sont en moyenne environ 20 % inférieures à une phase neutre (Météo-France, 29 septembre 2026). | **Moyenne historique** liée à ENSO dans ce territoire. | Prévoir -20 % en 2026 ou dans une commune. |
| Association climatologique | Le lien ENSO/pluies varie dans l'espace ; sécheresse et feux plus fréquents lors d'El Niño (Météo-France, 9 décembre 2025). | Contexte scientifique et facteurs de vigilance à étudier. | Annoncer une sécheresse ou un départ de feu local. |
| Bulletin saisonnier daté | Le bulletin publié le 17 septembre 2026 et visant octobre–décembre indique un El Niño en phase croissante en septembre. | Compte rendu de ce que le service officiel disait **à cette date**. | Le transformer en bulletin « actuellement à jour » ou en prévision locale chiffrée. |
| Observation mesurée | Le bulletin du 6 octobre 2026 décrit **20 mm** de pluie et un déficit de **64 %** sur le territoire en septembre 2026. | Mesure mensuelle passée documentée. | Affirmer qu'El Niño a causé seul le déficit ou que les mois suivants seront aussi secs. |

Sources :

- ENSO et Nouvelle-Calédonie, Météo-France, 29/09/2026 : https://meteo.nc/en/node/569807
- Bulletins saisonniers, Météo-France NC, 17/09/2026 : https://meteo.nc/en/node/569805
- Bulletin pluviométrique septembre 2026, Météo-France NC, 06/10/2026 : https://meteo.nc/fr/publications/bulletin-de-suivi-pluviometrique-septembre-2026
- Article explicatif Météo-France NC, 19/06/2026, indique expressément que l'intensité d'El Niño ne détermine pas automatiquement l'ampleur locale des impacts : https://meteo.nc/en/node/569792

## Comment l'application sépare ces catégories

- L'API `GET /api/territories` liste des dossiers **sans aucun score de risque**.
- L'API `GET /api/territories/nouvelle-caledonie` fournit des entrées typées `documented_association`, `dated_official_bulletin` et `dated_observation`, chacune avec les sources primaires datées.
- Les valeurs NOAA globales sont consultées via des routes **séparées** ; aucune fonction ne transforme RONI en niveau de risque pour la Nouvelle-Calédonie.
- L'interface affiche une catégorie et une attribution **pour chaque fait**, et précise que ces textes ne sont pas actualisés en direct.
- Nantes et Guyane ont le statut `not_assessed` : l'absence d'analyse est explicite plutôt que comblée par un nombre fictif.

## Travail nécessaire avant des prévisions régionales

1. Acquérir des séries locales datées (précipitations, température, sécheresse), leur climatologie et leurs restrictions de redistribution.
2. Définir les horizons de prévision, cibles géographiques et modèles de référence, sans choisir des paramètres après coup.
3. Tester la compétence prédictive avec des *hindcasts* hors échantillon et l'incertitude associée, séparément par variable, saison et région.
4. Faire relire la méthodologie par un météorologue ou climatologue connaissant le Pacifique sud-ouest.
5. Étudier la compréhension des habitants et des acteurs de prévention, notamment le risque de confondre moyennes climatiques et alertes.
6. **Droit d'abstention** : si le lien n'est pas établi ou le modèle insuffisant, afficher « impossible de conclure ».

Le modèle initial **ne prétend pas** mesurer l'habileté des prévisions, ni disposer d'un partenariat Météo-France. Aucune procédure de vigilance officielle n'est substituée.
