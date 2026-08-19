# Chocolate Sales dashboard — overview

A Power BI dashboard built entirely as text files, no binary `.pbix`. The semantic model
is TMDL, the report is PBIR JSON. Power BI Desktop opens it directly; git diffs it cleanly.

## Files

| Path | What it is |
| --- | --- |
| `ChocolateSales.pbip` | Entry point — double-click to open |
| `ChocolateSales.SemanticModel/` | Model as TMDL: tables, measures, relationship |
| `ChocolateSales.Report/` | Report as PBIR JSON: one file per page and per visual |
| `Chocolate SaleS.csv` | Source data, 3,282 rows |
| `generate_pbip.py` | Rebuilds the whole project from scratch |
| `validate_pbip.py` | Checks every JSON file against the Fabric schemas, offline |
| `README.md` | Full detail — schema gotchas, rebuild notes |

## Model

**Sales** — the fact table, loaded from the CSV. Two cleanups happen on import: `Amount`
arrives as a quoted currency string (`"$5,320.00"`) and is converted to a number, and
`Date` is day-first (`27/04/2022`) so it's parsed with culture `en-GB`. On a default
locale `04/01/2022` would silently become 4 January instead of 1 April.

**Calendar** — a date dimension generated in Power Query. Its range comes from the fact
table's own min/max dates, so it extends itself as data grows. Marked as a date table, so
DAX time intelligence works and Power BI's auto date/time is switched off. `Month Name`,
`Month Year` and `Day of Week` sort by numeric companion columns so charts run
chronologically instead of alphabetically.

Related `Sales[Date]` → `Calendar[Date]`, many-to-one.

**Measures:** Total Sales, Total Boxes, Orders, Avg Order Value, Sales per Box, Sales PY,
Sales YoY %, Sales YTD.

## Report

One page, *Overview*, 1280×720:

- Year slicer and four KPI cards — Total Sales, Total Boxes, Avg Order Value, Sales YoY %
- Monthly sales trend (line)
- Sales by country (bar)
- Sales by product (bar)
- Salesperson table — sales, boxes, average order value

Fields and layout only; no custom colors, titles or data labels yet.

## Opening it

Double-click `ChocolateSales.pbip`, then **Home → Refresh** to load the CSV — the project
stores definitions, not cached data, so tables start empty.

Sanity check after refresh:

| | Expected |
| --- | --- |
| Total Sales | $19,791,572 |
| Total Boxes | 540,437 |
| Orders | 3,282 |
| Calendar rows | 1,096 |

Check the shape of the monthly trend too, not just the total — a date-parsing error
leaves annual totals correct while scrambling the months.

## Two caveats

**Data ends 31 Aug 2024**, but each year holds the same 1,094 rows, so 2024 packs a full
year of orders into eight months. `Sales YoY %` is only meaningful with a year or month
selected — at the grand total it compares overlapping ranges.

**The CSV path is hardcoded** in `Sales.tmdl`. Move this folder and refresh breaks; edit
that one line.
