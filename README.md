# Tableau de bord KPI bagages (Power BI + SQL)

Simulation d'un centre de tri bagages inspiré de Paris-Orly, avec un dashboard de pilotage en deux vues :
**temps réel** et **post-opérationnel**. Projet personnel ; **toutes les données sont synthétiques**.

## Contexte
Ordres de grandeur issus d'une offre publique : 15 km de convoyeurs, ~20 M de bagages/an, pics à ~90 000
bagages/jour. L'échantillon par défaut (500 000 bagages) est à l'échelle ~1/40 ; le rapport pic/moyenne (~1,6)
et les taux de service sont conservés.

## Structure du dépôt
```
generate_data.py          génération des données (SQLite + CSV)
sql/schema.sql            schéma en étoile + vues KPI
sql/validation.sql        valeurs de contrôle pour les mesures DAX
powerbi/power_query.m     chargement et typage des CSV
powerbi/measures.dax      toutes les mesures DAX
powerbi/report_design.md  relations, pages et visuels du rapport
powerbi/theme.json        thème Power BI
docs/KPI_dictionary.md    définition, formule, seuil et utilité de chaque KPI
```

## Modèle de données (schéma en étoile)
`fact_baggage` (un bagage : dépôt, chargement, durée, statut), `fact_incident` (pannes), `dim_date`,
`dim_flight`, `dim_conveyor`. Règle métier : un bagage doit être chargé au plus tard 20 min avant le départ du
vol, sinon `late` ; `mishandled` est prioritaire.

## Démarrage
```bash
pip install -r requirements.txt
python generate_data.py --bags 500000 --seed 42
```
Puis suivre [`powerbi/report_design.md`](powerbi/report_design.md) pour monter le modèle et le rapport.

## Valeurs de référence (seed 42, sans filtre)
| Indicateur | Valeur |
|---|---|
| Bagages | 499 777 (7 147 vols, 365 jours du 2025-10-01 au 2026-09-30) |
| Taux à l'heure | 98,05 % |
| Taux de retard | 1,44 % |
| Mal acheminés pour 1 000 | 5,08 |
| Temps de traitement moyen / médian / P95 | 15,86 / 14,64 / 28,11 min |
| Pic horaire | 359 bagages |
| Incidents / indisponibilité | 45 / 3 841 min |
| Pic journalier / moyenne | 2 132 / 1 369 (x1,56) |

Les cartes Power BI doivent retrouver ces valeurs ; sinon, vérifier relations et types de colonnes.

## Constats (à compléter avec tes captures)
- Les convoyeurs les plus longs (C01, C02) ont les temps de traitement les plus élevés et le plus d'anomalies.
- Les jours de pointe d'été et les vendredis/dimanches concentrent les jours en alerte (taux à l'heure < 97 %).
- Les pannes allongent le temps de traitement sur le convoyeur touché et augmentent le risque de mal acheminés.

## Limites
Données et règles de simulation fictives (seuil de 20 min, pannes aléatoires, congestion selon l'heure). Aucun
chiffre ici ne décrit un aéroport réel. Le N-1 nécessite deux ans de données ; la comparaison à S-1 est utilisée à la place.

## Suite possible
Projet 2 : détection de goulots et prévision des pics en Python, à partir de ces mêmes données.
