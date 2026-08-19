# Chocolate Sales — Power BI project (PBIP)

A Power BI Project built as plain text: TMDL for the semantic model, PBIR JSON for the
report. Everything here is diffable and editable outside Power BI Desktop.

## Open it

Double-click `ChocolateSales.pbip`, or in Power BI Desktop use **File → Open → Browse**
and pick that file.

On first open the tables are empty — the project stores definitions, not cached data.
Hit **Home → Refresh** to load the CSV. Desktop may ask you to approve access to a local
file; allow it.

## Layout

```
ChocolateSales.pbip                    entry point
ChocolateSales.SemanticModel/
  definition/
    database.tmdl                      compatibility level
    model.tmdl                         culture, table refs, auto date/time off
    relationships.tmdl                 Sales[Date] -> Calendar[Date]
    tables/Sales.tmdl                  fact table + measures + M query
    tables/Calendar.tmdl               date dimension + M query
ChocolateSales.Report/
  definition.pbir                      points at the semantic model, byPath
  definition/
    version.json                       REQUIRED - PBIR definition version
    report.json                        REQUIRED - theme, layout options
    pages/pages.json                   optional - page order, active page
    pages/<id>/page.json               REQUIRED - canvas 1280x720, "Overview"
    pages/<id>/visuals/<id>/visual.json   one file per visual
```

Per the [PBIR docs](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report),
`version.json`, `report.json`, `pages/` and each `page.json` are required inside
`definition/`; `pages.json`, `bookmarks/` and `reportExtensions.json` are optional.
`version.json` must carry `"version": "2.0.0"` — the value Power BI Desktop and Fabric
emit today, matching `version.json` in microsoft/BCApps, microsoft/semantic-link-labs and
microsoft/fabric-toolbox. Omitting the file fails the open with
`Cannot find file 'version.json'.`

## Model

**Sales** — loaded from `Chocolate SaleS.csv` (3,282 rows). Two transformations matter:

- `Amount` arrives as a quoted currency string (`"$5,320.00"`). The M query strips `$`,
  `,` and spaces, then converts to a number.
- `Date` is day-first (`27/04/2022`). Parsed with culture `en-GB`, not the default
  locale — without this, rows like `04/01/2022` silently become 4 January vs 1 April.

**Calendar** — a date dimension generated in Power Query, not DAX. It derives its range
from the fact table (`Date.StartOfYear(List.Min(Sales[Date]))` to `Date.EndOfYear(...)`),
so it extends automatically when new data arrives. Expected: 1,096 rows,
2022-01-01 → 2024-12-31.

Marked as a date table (`dataCategory: Time`, `Date` column is the key). `Month Name`,
`Month Year` and `Day of Week` each sort by a numeric companion column, so charts order
chronologically instead of alphabetically. Power BI's auto date/time is disabled
(`__PBI_TimeIntelligenceEnabled = 0`) since this table replaces it.

### Measures

| Measure | Definition |
| --- | --- |
| Total Sales | `SUM(Sales[Amount])` |
| Total Boxes | `SUM(Sales[Boxes Shipped])` |
| Orders | `COUNTROWS(Sales)` |
| Avg Order Value | `DIVIDE([Total Sales], [Orders])` |
| Sales per Box | `DIVIDE([Total Sales], [Total Boxes])` |
| Sales PY | `CALCULATE([Total Sales], SAMEPERIODLASTYEAR('Calendar'[Date]))` |
| Sales YoY % | `DIVIDE([Total Sales] - [Sales PY], [Sales PY])` |
| Sales YTD | `TOTALYTD([Total Sales], 'Calendar'[Date])` |

## Verify the load

These come straight from the CSV. If the dashboard disagrees, the import is wrong.

| | Expected |
| --- | --- |
| Total Sales | $19,791,572 |
| Total Boxes | 540,437 |
| Orders | 3,282 |
| Avg Order Value | $6,030 |
| Sales per Box | $36.62 |
| 2022 / 2023 / 2024 | $6,183,625 / $6,643,378 / $6,964,569 |
| Top country | Australia, $3,646,444 |
| Top product | Smooth Sliky Salty, $1,120,201 |
| Top salesperson | Ches Bonnell, $1,022,600 |

The date parse is the thing most likely to break quietly. If `Date` were read
month-first, ~1,900 rows would land in the wrong month and the monthly trend line would
look scrambled while the annual total stayed correct — so check the monthly shape, not
just the grand total.

## Known caveats

**The data ends 31 Aug 2024.** Each year holds exactly 1,094 rows, so 2024 packs a full
year of orders into eight months. Two consequences:

- `Sales YoY %` on the card with no date filter is not meaningful — at the grand total,
  `SAMEPERIODLASTYEAR` shifts the entire three-year window back a year and compares
  overlapping ranges. The measure is correct per year or per month; select a year in the
  slicer before reading it.
- Full-year 2024 vs 2023 is not like-for-like regardless of the measure used.

**Hardcoded CSV path.** `Sales.tmdl` points at
`D:\CLAUDE_FOLDER\POWER BI\Chocolate SaleS.csv`. Move the folder and the refresh breaks;
edit that one line, or promote it to a parameter.

**Default formatting only.** Visuals carry fields and positions but no custom titles,
colors, data labels, or conditional formatting. That was deliberate for the first pass —
fewer hand-written properties, less to go wrong on first open.

**The Year slicer** renders as a numeric range slider because `Year` is a whole number.
Switch it to List in the Format pane if you prefer checkboxes.

## Rebuilding and checking

`generate_pbip.py` regenerates the whole project from scratch, overwriting the
`.SemanticModel` and `.Report` folders. It does not touch the CSV.

```bash
py "D:\CLAUDE_FOLDER\POWER BI\generate_pbip.py"
```

`validate_pbip.py` checks every JSON file against the constraints published in the Fabric
schemas — required properties, allowed properties, `$schema` URL patterns, enum values —
plus a couple of sanity checks the schemas don't cover (visuals fitting inside the page,
folder names matching the `name` inside each file).

```bash
py "D:\CLAUDE_FOLDER\POWER BI\validate_pbip.py"
```

It runs offline. Every one of these schemas sets `additionalProperties: false`, so an
unexpected property is just as fatal as a missing one — which is worth knowing before
Desktop tells you the hard way.

Things that cost a failed open while building this, all worth checking first:

- The `.pbip` uses `fabric/pbip/pbipProperties/...`. Every other file uses
  `fabric/item/<type>/...`. It is the one exception.
- `$schema` is a *required* property in `.pbip`, `definition.pbir`, `definition.pbism`,
  `version.json`, `report.json`, `page.json` and `visual.json`. Leaving it out is fatal.
- `definition/version.json` is required and easy to miss — nothing references it.
- `definition.pbir` needs `"version": "4.0"` or higher, or Desktop expects the report in
  legacy `report.json` form and ignores the `definition/` folder entirely.

Visual role names are not in the schemas — the schema only says `queryState` maps role
names to projections, not which roles a given `visualType` accepts. The ones used here
were verified against real PBIR reports: `card` and `slicer` and `tableEx` take `Values`;
`lineChart` and `clusteredBarChart` take `Category` and `Y` (plus optional `Series`).
`queryRef` is `Entity.Property`.

Regenerating assigns fresh `lineageTag` GUIDs. That is fine for a local file, but if this
model is ever published and you regenerate, downstream references keyed on lineage tags
will not match. Once you start editing in Desktop, edit in Desktop (or edit the TMDL by
hand) rather than re-running the generator.
