# Audit documentaire des services existants

Revue du **11 octobre 2026**, ticket #5. Sources officielles publiques uniquement.
Les fonctions ci-dessous sont décrites par leurs éditeurs : elles ne prouvent
ni leur performance, ni leur disponibilité dans chaque territoire. Aucun compte
créé, application installée, notification déclenchée ou entretien réalisé.
L'absence d'une fonction dans ces pages ne prouve pas son absence du produit.

## Comparaison datée

| Service | Fonction documentée et horizon | Public / accès décrit | Limite de notre vérification | Implication pour AVANTEMPS (analyse interne) |
| --- | --- | --- | --- | --- |
| Météo-France [M1] | Vigilance des dangers pour aujourd'hui et demain jusqu'à minuit dans l'Hexagone ; cartes actualisées au moins à 6 h et 16 h, conseils associés | Citoyens, autorités et médias ; sites et applications | Dispositifs outre-mer spécifiques ; ne pas transposer ces règles à la Nouvelle-Calédonie. Pas de test des notifications | Orienter vers l'autorité locale ; une carte et des conseils ne constituent pas une différence démontrée |
| myPredict, Predict Services [P1] | Avertissement géolocalisé de risques et conseils de sauvegarde ; jusqu'à cinq adresses selon la page de présentation | Application annoncée gratuite pour particuliers ; France et international annoncés | Extrait indexé du site officiel seulement : lecture directe refusée (403). Aucun test mobile, de délai ou de couverture NC | Ne pas développer des notifications sur cette seule hypothèse ; l'utilité d'un historique scientifique reste à comparer |
| DisasterAWARE / PDC [D1] | Plateforme multirisque d'alerte précoce ; Disaster Alert web/mobile pour le public | DisasterAWARE Pro annoncé gratuit pour professionnels ; Disaster Alert gratuit pour le public | Aucune session professionnelle ni carte locale testée ; ne pas confondre l'offre PDC avec une offre commerciale homonyme | La surveillance multirisque existe déjà ; vérifier les explications et historiques avant toute revendication d'originalité |
| Google Flood Hub [G1, G2] | Débit et zones inondées pour les crues fluviales, jusqu'à sept jours ; modèle de crues soudaines urbaines jusqu'à 24 h | Cartes et prévisions publiques gratuites selon Google ; mise à jour quotidienne annoncée | Horizons maximaux annoncés, sans garantie locale ; couverture Nantes, Guyane et NC non vérifiée dans l'interface | Ne pas prétendre que Flood Hub ignore les crues soudaines ; une prévision de pluie saisonnière ne fournit pas cette information |
| ThinkHazard! [T1] | Niveaux d'aléa et recommandations, maximum dans une unité administrative ; horizon de long terme | Outil documentaire territorial, disponible en français selon sa FAQ | FAQ excluant événements temps réel et base historique d'événements ; niveau non fourni à l'adresse précise. Dossiers locaux non testés | Distinguer aléa de long terme, événement et prévision ; liens vers analyses locales détaillées indispensables |
| GDACS [A1] | Information sur catastrophes soudaines, notifications et coordination des premières phases de réponse | Informations publiques ; Virtual OSOCC restreint pour la coordination | Pages de présentation consultées, sans abonnement, flux intégré ou vérification d'événement ; chiffres d'utilisateurs non repris | Complément institutionnel potentiel ; ne pas reconstruire une plateforme de coordination |
| Copernicus C3S [C1, C2] | Cartes et séries saisonnières jusqu'à six mois, systèmes individuels et combinaisons, actualisation mensuelle ; données CDS et documentation de compétence | Produits graphiques publics ; acquisition CDS distincte, soumise aux conditions documentées dans le dépôt | Aucune acquisition réelle ni compétence de pluie NC mesurée. Qualité variable selon variable, lieu, saison et échéance | La vérification des prévisions existe déjà chez C3S : tester la valeur pédagogique et la traçabilité du dossier, sans revendiquer l'invention des scores |

## Sources et niveau d'accès

Toutes les adresses ont été recherchées ou consultées le 11 octobre 2026.
La date de consultation n'est ni une date de publication, ni un engagement
de l'éditeur. Les pages et les offres peuvent évoluer.

- **M1 — Météo-France**, « Qu'est-ce que la Vigilance météorologique ? », page lue : https://meteofrance.com/vigilance-et-securite/quest-ce-que-la-vigilance-meteorologique
- **P1 — Predict Services**, particuliers, extrait indexé officiel consulté ; ouverture directe 403 : https://www.predictservices.com/particuliers/
- **D1 — Pacific Disaster Center**, « About PDC », page lue : https://disasteraware.org/about/
- **G1 — Google**, aide « What are the Different Models? », page lue : https://support.google.com/flood-hub/answer/15638002?hl=en
- **G2 — Google Research**, « Flood Forecasting », description officielle consultée : https://sites.research.google/gr/floodforecasting/
- **T1 — ThinkHazard!**, FAQ, page lue : https://www.thinkhazard.org/en/faq
- **A1 — GDACS**, présentation, page lue : https://www.gdacs.org/About/overview.aspx
- **C1 — Copernicus**, produits saisonniers, page lue : https://climate.copernicus.eu/seasonal-forecasts
- **C2 — CDS**, assurance qualité des données saisonnières, description officielle consultée : https://cds.climate.copernicus.eu/datasets/seasonal-original-single-levels?tab=quality_assurance_tab

## Hypothèses à mettre à l'épreuve

Les cas suivants sont des **scénarios de test**, pas des besoins déjà confirmés
ni des lacunes constatées chez les autres services :

1. Une association NC reçoit un bulletin trimestriel : peut-elle distinguer
   probabilité de pluie, historique ENSO et vigilance immédiate, avec les
   services qu'elle utilise déjà ?
2. Une collectivité veut retrouver ce qui a changé dans une série climatique :
   peut-elle identifier la version, la date et le sens de la correction ?
3. Un citoyen cherche la fiabilité d'une prévision pour son territoire :
   retrouve-t-il la variable, l'échéance, la période de validation et une
   abstention explicite lorsque la preuve manque ?

Pour chaque scénario, observer d'abord le parcours dans le service existant
approprié, puis dans AVANTEMPS. Consigner les URL, tâches effectivement
réalisées, blocages et temps observés. Une annonce commerciale ou une page
non accessible ne suffit pas à conclure à une lacune.

## Décision provisoire

**Poursuivre uniquement l'étude et le prototype documentaire.** Les sources
montrent un recouvrement important sur cartes, alertes et conseils. Aucune
fonctionnalité distinctive n'a encore son go : journal scientifique et dossier
explicable restent des hypothèses. Aucune exclusivité ni supériorité mesurée
n'est revendiquée.

Le go/no-go final nécessite au moins cinq entretiens réels et des parcours
comparés, suivant [le protocole](user-validation.md). Aucun entretien ou contact
n'a été inventé ou envoyé. Les résultats négatifs doivent être conservés.
La publication de prévisions requiert en plus l'acquisition réelle et la revue
scientifique des tickets #10 et #4 ; les retours utilisateurs n'y substituent
pas une validation scientifique. Le ticket #5 demeure ouvert.
