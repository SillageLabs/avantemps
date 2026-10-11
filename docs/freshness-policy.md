# Affichage des archives anciennes

Politique interne `avantemps.noaa-freshness.v1`, définie le 11 octobre 2026
pour le prototype local (tickets #6 et #4). Aucun téléchargement automatique,
aucune suppression d'archives et aucune alerte météorologique.

La NOAA indique une mise à jour mensuelle, au plus tard le 5 du mois, et des
révisions possibles pendant deux mois :
https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/
(documentation officielle consultée le 11 octobre 2026). Le tableau précise
les mois des saisons et leur année centrale : NDJ 2026 se termine en janvier
2027, DJF 2026 en février 2026.

Deux horloges indépendantes sont évaluées à chaque lecture de `/api/roni/latest` :

| Contrôle | Limite interne | Sens |
| --- | --- | --- |
| Temps depuis `last_checked_at_utc` | Plus de 45 jours | Source non vérifiée récemment |
| Temps depuis la fin du dernier mois de la dernière saison | Plus de 90 jours calendaires | Observation ancienne, même après une nouvelle collecte |

Ces limites prudentes sont des **choix du prototype**, pas des seuils NOAA,
une garantie de disponibilité ou une validation scientifique. À exactement
45 ou 90 jours, la limite n'est pas dépassée. Une date absente, invalide,
sans fuseau ou future donne un statut `unknown`. La première collecte ne
remplace jamais une vérification manquante. Les fuseaux sont ramenés à UTC.

L'API ajoute `freshness` avec le statut, les motifs, la date du contrôle et
les limites. L'interface affiche le message près de la valeur. Une archive
`stale` reste consultable comme historique, avec ses dates et sa provenance.
`within_internal_limits` ne signifie pas que le fournisseur a effectivement
publié sa dernière version. Le bouton d'actualisation relit l'archive locale
sans rafraîchir sa date de vérification ni télécharger NOAA.

Les dossiers territoriaux restent figés et explicitement datés. Cette règle
ne certifie pas leur actualité, ne s'applique pas aux hindcasts historiques
Copernicus et ne permet aucune publication de score ou prévision. Il reste
à valider la politique avant une éventuelle diffusion et à organiser une
revue humaine des sources locales. Aucun calendrier de mise à jour n'est
activé par cette modification.
