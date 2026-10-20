# Dictionnaire des KPI

Chaque indicateur est défini une seule fois ici ; les mesures DAX correspondantes sont dans
[`powerbi/measures.dax`](../powerbi/measures.dax). Les seuils sont des **hypothèses de travail** pour
des données synthétiques, à ajuster avec les exploitants dans un contexte réel.

Statuts d'un bagage : `on_time` (chargé au plus tard 20 min avant le départ du vol), `late` (chargé après
cette limite), `mishandled` (mal acheminé, prioritaire sur `late`).

## Qualité de service

| KPI | Définition | Formule | Mesure DAX | Seuils (OK / Alerte / Critique) | Utilité |
|---|---|---|---|---|---|
| Taux de bagages à l'heure | Part des bagages chargés dans les temps | bagages `on_time` / bagages | `On-Time Rate` | ≥ 97 % / 95-97 % / < 95 % | Indicateur principal de service ; pilotage quotidien |
| Taux de retard | Part des bagages chargés trop tard | bagages `late` / bagages | `Late Rate` | ≤ 2 % / 2-4 % / > 4 % | Distingue un problème de flux d'un problème de manutention |
| Mal acheminés pour 1 000 | Bagages `mishandled` pour 1 000 traités | bagages `mishandled` / bagages x 1 000 | `Mishandled per 1000` | ≤ 6 / 6-8 / > 8 | Standard du secteur ; comparable entre sites |
| Taux d'anomalie | Retards + mal acheminés | (`late` + `mishandled`) / bagages | `Issue Rate` | suivi de tendance | Vue unique pour comparer convoyeurs et créneaux |

## Performance du flux

| KPI | Définition | Formule | Mesure DAX | Seuils | Utilité |
|---|---|---|---|---|---|
| Temps de traitement moyen | Durée dépôt → chargement | moyenne de `processing_min` | `Avg Processing Min` | suivi de tendance | Santé générale du flux |
| Temps de traitement médian | Durée typique, insensible aux extrêmes | médiane de `processing_min` | `Median Processing Min` | suivi de tendance | Référence « jour normal » |
| Temps de traitement P95 | 95 % des bagages sont traités en moins de | percentile 95 de `processing_min` | `P95 Processing Min` | ≤ 30 min / 30-35 / > 35 | Révèle la queue de distribution, là où se jouent les retards |
| Pic horaire | Plus grand nombre de dépôts sur une heure | max sur les heures de [Bagages] | `Peak Hour Bags` | comparer à la capacité | Dimensionnement des équipes et du système |
| Bagages par km de convoyeur | Charge rapportée à la longueur de convoyeur | bagages / (longueur en km) | `Bags per Conveyor km` | comparaison entre convoyeurs | Détecte un convoyeur sous- ou sur-utilisé |

## Volumes et tendances

| KPI | Définition | Mesure DAX | Utilité |
|---|---|---|---|
| Bagages | Nombre de bagages traités | `Bags` | Base de tous les ratios |
| Glissant 7 jours | Volume ou taux sur les 7 derniers jours | `Bags Rolling 7d`, `On-Time Rate Rolling 7d` | Lisse les effets de jour de semaine |
| Variation vs semaine précédente | Écart au même jour S-1 | `Bags vs LW %`, `On-Time vs LW (pts)` | Lecture rapide « mieux ou pire qu'habituellement » |
| Variation vs N-1 | Écart à la même période un an avant | `Bags vs PY %` | Nécessite 2 ans de données (non disponible dans l'échantillon d'un an) |

## Fiabilité des équipements

| KPI | Définition | Mesure DAX | Utilité |
|---|---|---|---|
| Incidents | Nombre de pannes de convoyeur | `Incidents` | Fréquence des pannes |
| Indisponibilité | Minutes cumulées de panne | `Downtime Min` | Impact potentiel sur le service |
| Durée moyenne d'incident | Indisponibilité / incidents | `Avg Incident Duration` | Réactivité de la maintenance |

## Vue « temps réel » (simulée)

Les données étant historiques, le « temps réel » est simulé : l'heure de référence est le dernier dépôt du jour
sélectionné (`Reference Time`). `Bags Last 3h` et `On-Time Rate Last 3h` portent sur les 3 heures qui précèdent.
Dans un système réel, cette référence serait l'horloge du système d'exploitation, alimentée par un flux
(DirectQuery ou jeu de données en streaming).

## Limites connues
- Données synthétiques : les résultats reflètent les hypothèses de simulation, pas la réalité d'un aéroport.
- Le seuil de 20 minutes avant départ est fixe et identique pour tous les vols.
- Le statut `mishandled` est tiré aléatoirement (probabilité accrue en cas de congestion ou de panne) ; il n'est pas lié à une cause précise.
