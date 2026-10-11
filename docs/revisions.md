# Journal des révisions : contrat scientifique et API

Version expérimentale du 11 octobre 2026.

## La distinction centrale

1. **Évolution temporelle** : RONI change entre deux trimestres glissants consécutifs ; cela traduit une variation des observations du climat.
2. **Révision de données** : la NOAA republie une valeur modifiée pour *la même saison* ; cela traduit une correction de l'archive, pas une nouvelle catastrophe.
3. **Ajout de saison** : une saison supplémentaire est disponible ; il s'agit d'une nouvelle observation, pas d'une révision de l'ancienne.
4. **Suppression** : une saison disparaît d'une version ; cela doit être signalé, jamais interprété comme une absence de danger.

Une comparaison est identifiée par **deux empreintes SHA-256 des fichiers d'origine**, les dates de première collecte et une liste de changements.

## Contrat HTTP local

- GET /api/roni/changes retourne un statut insufficient_versions et une comparaison null s'il n'y a qu'une version ; si zéro archive, retourne une erreur 503.
- Lorsque deux versions sont disponibles, status=ok et comparison expose :
  - from, to : identifiants SHA et date de première collecte ;
  - counts : added, removed, revised ;
  - changes : série ordonnée de valeurs et les valeurs concernées en degrés Celsius ;
  - explanation : pourquoi il ne s'agit pas d'une alerte.
- GET /api/roni/changes?before=SHA256&after=SHA256 compare explicitement deux versions. Identifiants invalides : 400 ; archives inconnues : 404.
- Le serveur ne réécrit pas l'historique. Chaque fichier brut est vérifié par son empreinte avant lecture et confronté aux valeurs JSON enregistrées.

## Cas limites

- Deux fichiers différents au niveau des espaces peuvent produire **zéro** changement de mesure.
- La même version peut être revérifiée à plusieurs dates. La date de dernière vérification avance, mais la première date d'archivage est conservée.
- En cas de panne ou de contenu NOAA tronqué : aucune nouvelle version n'est publiée, et la dernière collecte réussie n'est pas modifiée.
- Si un ancien fichier réapparaît après une version plus récente : le pointeur courant est corrigé ; la comparaison automatique utilise une autre version disponible, pas un scénario scientifique fictif.
- La comparaison automatique reste un raccourci pratique, pas un journal exhaustif d'événements d'ingestion. L'audit complet des séquences de re-publication est un chantier ultérieur.

**Aucune donnée synthétique de tests ne doit être présentée comme une observation NOAA.**
