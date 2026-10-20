# Guide de construction du rapport Power BI

Fichier à produire : `powerbi/bagage_kpi.pbix` (à enregistrer dans le dépôt). Thème : `powerbi/theme.json`
(Affichage > Thèmes > Parcourir les thèmes).

## 1. Préparation du modèle
1. Générer les données : `python generate_data.py`.
2. Créer le paramètre `DataFolder` et les 5 requêtes de [`power_query.m`](power_query.m).
3. Fermer et appliquer, puis créer les relations (vue Modèle), toutes en un-à-plusieurs, filtre unidirectionnel :

| De (un) | Vers (plusieurs) |
|---|---|
| `dim_date[date_key]` | `fact_baggage[date_key]` |
| `dim_date[date_key]` | `fact_incident[date_key]` |
| `dim_conveyor[conveyor_id]` | `fact_baggage[conveyor_id]` |
| `dim_conveyor[conveyor_id]` | `fact_incident[conveyor_id]` |
| `dim_flight[flight_id]` | `fact_baggage[flight_id]` |

   Ne **pas** relier `dim_flight[date_key]` ni `dim_flight[conveyor_id]` (chemins ambigus) : les masquer.
4. Marquer `dim_date` comme table de dates (clic droit > Marquer comme table de dates > `full_date`).
5. Trier `day_name` par `day_of_week`, et `month_label` croissant.
6. Créer une table `_Mesures` et y coller [`measures.dax`](measures.dax). Masquer les colonnes techniques (`bag_id`, `date_key`, `*_ts` inutiles).
7. Contrôler les cartes sans filtre avec [`sql/validation.sql`](../sql/validation.sql) (valeurs de référence dans le README).

## 2. Page 1 : Temps réel
Objectif : « où en est-on maintenant, faut-il intervenir ? »

| Zone | Visuel | Champs |
|---|---|---|
| Haut gauche | Segment (date unique) + segment terminal | `dim_date[full_date]`, `dim_conveyor[terminal]` |
| Bandeau | 4 cartes : Heure de référence, Bagages dernières 3 h, Taux à l'heure 3 h, Mal acheminés /1 000 | `Reference Time`, `Bags Last 3h`, `On-Time Rate Last 3h`, `Mishandled per 1000` |
| Centre | Courbe par heure (axe `checkin_hour`) : bagages et taux d'anomalie | `Bags`, `Issue Rate` |
| Droite | Matrice convoyeur x heure, mise en forme conditionnelle (carte thermique) | `dim_conveyor[conveyor_id]`, `checkin_hour`, `Issue Rate` |
| Bas | Table des convoyeurs avec statut | `conveyor_id`, `Bags`, `P95 Processing Min`, `On-Time Status` |

Mise en forme conditionnelle : couleur de police des cartes via « Valeur du champ » = `On-Time Color` / `Mishandling Color`.

## 3. Page 2 : Post-opérationnel
Objectif : analyser, comparer, expliquer.

| Zone | Visuel | Champs |
|---|---|---|
| Haut | Segments période (`month_label`), terminal, jour de semaine | |
| Cartes | Bagages, Taux à l'heure (+ `On-Time vs LW (pts)`), Mal acheminés /1 000, P95 | mesures correspondantes |
| Gauche | Courbe quotidienne + glissant 7 jours | `full_date`, `Bags`, `Bags Rolling 7d` |
| Centre | Colonnes par mois avec ligne du taux à l'heure | `month_label`, `Bags`, `On-Time Rate` |
| Droite | Pareto des convoyeurs (colonnes + % cumulé) | `conveyor_id`, `Bags In Issue`, `Issue Share of Total` |
| Bas | Infobulle de page : détail du jour (taux, P95, incidents) | `Incidents`, `Downtime Min` |

## 4. Page 3 (bonus) : Goulots et incidents
- Nuage de points : longueur de convoyeur (`dim_conveyor[length_m]`) vs `Avg Processing Min`, taille = `Bags`.
- Colonnes : `Downtime Min` par convoyeur ; table des incidents (`start_ts`, `duration_min`).
- Texte de conclusion rédigé à la main : 3 constats et 3 leviers (ex. rééquilibrer la charge des convoyeurs longs aux heures de pointe).

## 5. Finition
- Titres explicites en français, unités affichées (min, ‰, %), pas de couleur sans signification.
- Signets : « Vue exploitation » et « Vue direction » ; info-bulle de page pour le détail.
- Exporter 3 captures d'écran dans `docs/img/` et les intégrer au README.
