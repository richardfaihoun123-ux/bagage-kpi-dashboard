// =====================================================================
// Power Query (M) - chargement des CSV générés par generate_data.py
// 1) Accueil > Transformer les données > Nouveau paramètre :
//      Nom = DataFolder, Type = Texte, valeur ex. C:\projets\bagage-kpi-dashboard\data\csv\
// 2) Créer une requête vide par bloc ci-dessous (Éditeur avancé) et la nommer comme indiqué.
// =====================================================================

// ---------- dim_date ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "dim_date.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"date_key", Int64.Type}, {"full_date", type date}, {"year", Int64.Type},
                 {"month", Int64.Type}, {"day_of_week", Int64.Type}, {"is_weekend", Int64.Type},
                 {"is_school_holiday", Int64.Type}, {"season", type text}}, "en-US"),
    MonthLbl = Table.AddColumn(Typed, "month_label", each Date.ToText([full_date], "yyyy-MM"), type text),
    DayName  = Table.AddColumn(MonthLbl, "day_name", each Date.ToText([full_date], "ddd", "fr-FR"), type text)
in
    DayName

// ---------- dim_conveyor ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "dim_conveyor.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {{"conveyor_id", type text}, {"terminal", type text}, {"length_m", Int64.Type}}, "en-US")
in
    Typed

// ---------- dim_flight ----------
// Les colonnes date_key et conveyor_id sont masquées dans le modèle (pas de relation, évite les chemins ambigus).
let
    Source   = Csv.Document(File.Contents(DataFolder & "dim_flight.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"flight_id", Int64.Type}, {"flight_number", type text}, {"airline", type text},
                 {"destination", type text}, {"terminal", type text}, {"scheduled_dep", type datetime},
                 {"date_key", Int64.Type}, {"conveyor_id", type text}}, "en-US")
in
    Typed

// ---------- fact_baggage ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "fact_baggage.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"bag_id", Int64.Type}, {"flight_id", Int64.Type}, {"conveyor_id", type text},
                 {"date_key", Int64.Type}, {"checkin_ts", type datetime}, {"loaded_ts", type datetime},
                 {"processing_min", type number}, {"status", type text}}, "en-US"),
    HourTs   = Table.AddColumn(Typed, "checkin_hour_ts",
                 each DateTime.From(Date.From([checkin_ts])) + #duration(0, Time.Hour([checkin_ts]), 0, 0), type datetime),
    HourNum  = Table.AddColumn(HourTs, "checkin_hour", each Time.Hour([checkin_ts]), Int64.Type)
in
    HourNum

// ---------- fact_incident ----------
let
    Source   = Csv.Document(File.Contents(DataFolder & "fact_incident.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed    = Table.TransformColumnTypes(Promoted, {
                 {"incident_id", Int64.Type}, {"conveyor_id", type text},
                 {"start_ts", type datetime}, {"duration_min", Int64.Type}}, "en-US"),
    DateKey  = Table.AddColumn(Typed, "date_key", each Number.From(Date.ToText(Date.From([start_ts]), "yyyyMMdd")), Int64.Type)
in
    DateKey
