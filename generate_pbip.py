import json, os, uuid, shutil

ROOT = r"D:\CLAUDE_FOLDER\POWER BI"
NAME = "ChocolateSales"
SM = os.path.join(ROOT, NAME + ".SemanticModel")
RPT = os.path.join(ROOT, NAME + ".Report")
CSV = r"D:\CLAUDE_FOLDER\POWER BI\Chocolate SaleS.csv"
FENCE = "`" * 3

def g():
    return str(uuid.uuid4())

def vid():
    return uuid.uuid4().hex[:20]

def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(text)

def wj(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")

for d in (SM, RPT):
    if os.path.isdir(d):
        shutil.rmtree(d)

T = "\t"

# ------------------------------------------------------------------ .pbip
wj(os.path.join(ROOT, NAME + ".pbip"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
    "version": "1.0",
    "artifacts": [{"report": {"path": NAME + ".Report"}}],
    "settings": {"enableAutoRecovery": True},
})

# --------------------------------------------------------- semantic model
wj(os.path.join(SM, ".platform"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "SemanticModel", "displayName": NAME},
    "config": {"version": "2.0", "logicalId": g()},
})
wj(os.path.join(SM, "definition.pbism"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
    "version": "4.2",
    "settings": {},
})

w(os.path.join(SM, "definition", "database.tmdl"),
  "database\n" + T + "compatibilityLevel: 1567\n")

w(os.path.join(SM, "definition", "model.tmdl"), "\n".join([
    "model Model",
    T + "culture: en-US",
    T + "defaultPowerBIDataSourceVersion: powerBI_V3",
    T + "discourageImplicitMeasures",
    T + "sourceQueryCulture: en-US",
    T + "dataAccessOptions",
    T + T + "legacyRedirects",
    T + T + "returnErrorValuesAsNull",
    "",
    'annotation PBI_QueryOrder = ["Sales","Calendar"]',
    "",
    "annotation __PBI_TimeIntelligenceEnabled = 0",
    "",
    "ref table Sales",
    "ref table Calendar",
    "",
]))

def col(name, dtype, summarize, source, fmt=None, extra_ann=None, flags=(), sort_by=None):
    q = "'%s'" % name if " " in name else name
    out = [T + "column " + q, T * 2 + "dataType: " + dtype]
    for fl in flags:
        out.append(T * 2 + fl)
    if fmt:
        out.append(T * 2 + "formatString: " + fmt)
    out += [T * 2 + "lineageTag: " + g(),
            T * 2 + "summarizeBy: " + summarize,
            T * 2 + "sourceColumn: " + source]
    if sort_by:
        out.append(T * 2 + "sortByColumn: '%s'" % sort_by)
    out.append("")
    out.append(T * 2 + "annotation SummarizationSetBy = Automatic")
    for a in (extra_ann or []):
        out.append(T * 2 + "annotation " + a)
    out.append("")
    return out

def measure(name, expr, fmt, desc=None):
    out = []
    if desc:
        out.append(T + "/// " + desc)
    out.append(T + "measure '%s' = %s" % (name, expr))
    out.append(T * 2 + "formatString: " + fmt)
    out.append(T * 2 + "lineageTag: " + g())
    out.append("")
    return out

def partition(table, lines):
    out = [T + "partition %s = m" % table, T * 2 + "mode: import", T * 2 + "source = " + FENCE]
    out += [T * 4 + ln for ln in lines]
    out += [T * 4 + FENCE, "", T + "annotation PBI_ResultType = Table", ""]
    return out

# ---- Sales
sales_m = [
    "let",
    '    Source = Csv.Document(File.Contents("%s"),[Delimiter=",", Columns=6, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),' % CSV,
    "    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
    '    CleanAmount = Table.TransformColumns(Headers, {{"Amount", each Number.FromText(Text.Remove(Text.From(_), {"$", ",", " "})), type number}}),',
    '    TypedText = Table.TransformColumnTypes(CleanAmount, {{"Sales Person", type text}, {"Country", type text}, {"Product", type text}, {"Boxes Shipped", Int64.Type}}),',
    '    TypedDate = Table.TransformColumnTypes(TypedText, {{"Date", type date}}, "en-GB")',
    "in",
    "    TypedDate",
]

sales = ["table Sales", T + "lineageTag: " + g(), ""]
sales += measure("Total Sales", "SUM(Sales[Amount])", "\\$#,0", "Total sales value.")
sales += measure("Total Boxes", "SUM(Sales[Boxes Shipped])", "#,0", "Total boxes shipped.")
sales += measure("Orders", "COUNTROWS(Sales)", "#,0", "Number of sales transactions.")
sales += measure("Avg Order Value", "DIVIDE([Total Sales], [Orders])", "\\$#,0", "Total Sales divided by Orders.")
sales += measure("Sales per Box", "DIVIDE([Total Sales], [Total Boxes])", "\\$#,0.00", "Revenue per box shipped.")
sales += measure("Sales PY", "CALCULATE([Total Sales], SAMEPERIODLASTYEAR('Calendar'[Date]))", "\\$#,0", "Total Sales for the same period one year earlier.")
sales += measure("Sales YoY %", "DIVIDE([Total Sales] - [Sales PY], [Sales PY])", "0.0%;-0.0%;0.0%", "Year-over-year growth. Data ends 31 Aug 2024, so full-year 2024 vs 2023 is not like-for-like.")
sales += measure("Sales YTD", "TOTALYTD([Total Sales], 'Calendar'[Date])", "\\$#,0", "Year-to-date total sales.")
sales += col("Sales Person", "string", "none", "Sales Person")
sales += col("Country", "string", "none", "Country", extra_ann=['PBI_DataCategory = "Country"'])
sales += col("Product", "string", "none", "Product")
sales += col("Date", "dateTime", "none", "Date", fmt="Long Date",
             extra_ann=["UnderlyingDateTimeDataType = Date"])
sales += col("Amount", "double", "sum", "Amount", fmt="\\$#,0.00")
sales += col("Boxes Shipped", "int64", "sum", "Boxes Shipped", fmt="#,0")
sales += partition("Sales", sales_m)
w(os.path.join(SM, "definition", "tables", "Sales.tmdl"), "\n".join(sales))

# ---- Calendar
cal_m = [
    "let",
    "    First = Date.StartOfYear(List.Min(Sales[Date])),",
    "    Last = Date.EndOfYear(List.Max(Sales[Date])),",
    "    DayCount = Duration.Days(Last - First) + 1,",
    "    Dates = List.Dates(First, DayCount, #duration(1, 0, 0, 0)),",
    '    ToTable = Table.FromList(Dates, Splitter.SplitByNothing(), {"Date"}),',
    '    Typed = Table.TransformColumnTypes(ToTable, {{"Date", type date}}),',
    '    Yr = Table.AddColumn(Typed, "Year", each Date.Year([Date]), Int64.Type),',
    '    QNum = Table.AddColumn(Yr, "Quarter Number", each Date.QuarterOfYear([Date]), Int64.Type),',
    '    Qtr = Table.AddColumn(QNum, "Quarter", each "Q" & Text.From([Quarter Number]), type text),',
    '    MNum = Table.AddColumn(Qtr, "Month Number", each Date.Month([Date]), Int64.Type),',
    '    MName = Table.AddColumn(MNum, "Month Name", each Date.ToText([Date], [Format="MMM", Culture="en-US"]), type text),',
    '    MYear = Table.AddColumn(MName, "Month Year", each Date.ToText([Date], [Format="MMM yyyy", Culture="en-US"]), type text),',
    '    MYSort = Table.AddColumn(MYear, "Month Year Sort", each [Year] * 100 + [Month Number], Int64.Type),',
    '    DowNum = Table.AddColumn(MYSort, "Day of Week Number", each Date.DayOfWeek([Date], Day.Monday) + 1, Int64.Type),',
    '    DowName = Table.AddColumn(DowNum, "Day of Week", each Date.ToText([Date], [Format="ddd", Culture="en-US"]), type text)',
    "in",
    "    DowName",
]

cal = ["table Calendar", T + "lineageTag: " + g(), T + "dataCategory: Time", ""]
cal += col("Date", "dateTime", "none", "Date", fmt="yyyy-mm-dd",
           extra_ann=["UnderlyingDateTimeDataType = Date"], flags=("isKey",))
cal += col("Year", "int64", "none", "Year", fmt="0")
cal += col("Quarter Number", "int64", "none", "Quarter Number", fmt="0")
cal += col("Quarter", "string", "none", "Quarter")
cal += col("Month Number", "int64", "none", "Month Number", fmt="0")
cal += col("Month Name", "string", "none", "Month Name", sort_by="Month Number")
cal += col("Month Year", "string", "none", "Month Year", sort_by="Month Year Sort")
cal += col("Month Year Sort", "int64", "none", "Month Year Sort", fmt="0")
cal += col("Day of Week Number", "int64", "none", "Day of Week Number", fmt="0")
cal += col("Day of Week", "string", "none", "Day of Week", sort_by="Day of Week Number")
cal += partition("Calendar", cal_m)
w(os.path.join(SM, "definition", "tables", "Calendar.tmdl"), "\n".join(cal))

w(os.path.join(SM, "definition", "relationships.tmdl"), "\n".join([
    "relationship " + g(),
    T + "fromColumn: Sales.Date",
    T + "toColumn: Calendar.Date",
    "",
]))

# ------------------------------------------------------------------ report
wj(os.path.join(RPT, ".platform"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
    "metadata": {"type": "Report", "displayName": NAME},
    "config": {"version": "2.0", "logicalId": g()},
})
wj(os.path.join(RPT, "definition.pbir"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0",
    "datasetReference": {"byPath": {"path": "../" + NAME + ".SemanticModel"}},
})

# Required by the PBIR loader. "2.0.0" is the report definition version emitted by
# Power BI Desktop and Fabric today - confirmed against version.json in
# microsoft/BCApps, microsoft/semantic-link-labs and microsoft/fabric-toolbox.
wj(os.path.join(RPT, "definition", "version.json"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
    "version": "2.0.0",
})
wj(os.path.join(RPT, "definition", "report.json"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/1.0.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": "5.55", "type": "SharedResources"}},
    "layoutOptimization": "None",
    "settings": {"useStylableVisualContainerHeader": True, "defaultFilterActionIsDataFilter": True},
})

PAGE = "b1a2c3d4e5f60718293a"
wj(os.path.join(RPT, "definition", "pages", "pages.json"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
    "pageOrder": [PAGE],
    "activePageName": PAGE,
})
wj(os.path.join(RPT, "definition", "pages", PAGE, "page.json"), {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/1.0.0/schema.json",
    "name": PAGE,
    "displayName": "Overview",
    "displayOption": "FitToPage",
    "height": 720,
    "width": 1280,
})

def m_field(prop, ent="Sales"):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}}

def c_field(prop, ent):
    return {"Column": {"Expression": {"SourceRef": {"Entity": ent}}, "Property": prop}}

def proj(field, ent, prop):
    return {"field": field, "queryRef": "%s.%s" % (ent, prop), "nativeQueryRef": prop}

def visual(vtype, x, y, wd, ht, tab, roles):
    name = vid()
    qs = {}
    for role, items in roles.items():
        qs[role] = {"projections": [proj(f, e, p) for (f, e, p) in items]}
    obj = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/1.4.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": tab, "width": wd, "height": ht, "tabOrder": tab},
        "visual": {
            "visualType": vtype,
            "query": {"queryState": qs},
            "drillFilterOtherVisuals": True,
        },
    }
    wj(os.path.join(RPT, "definition", "pages", PAGE, "visuals", name, "visual.json"), obj)
    return name

# row 1 - slicer + KPI cards
visual("slicer", 16, 16, 236, 92, 0,
       {"Values": [(c_field("Year", "Calendar"), "Calendar", "Year")]})
for i, mname in enumerate(["Total Sales", "Total Boxes", "Avg Order Value", "Sales YoY %"]):
    visual("card", 268 + i * 252, 16, 236, 92, i + 1,
           {"Values": [(m_field(mname), "Sales", mname)]})

# row 2 - trend + country
visual("lineChart", 16, 124, 760, 286, 5, {
    "Category": [(c_field("Month Year", "Calendar"), "Calendar", "Month Year")],
    "Y": [(m_field("Total Sales"), "Sales", "Total Sales")],
})
visual("clusteredBarChart", 792, 124, 472, 286, 6, {
    "Category": [(c_field("Country", "Sales"), "Sales", "Country")],
    "Y": [(m_field("Total Sales"), "Sales", "Total Sales")],
})

# row 3 - products + people
visual("clusteredBarChart", 16, 426, 616, 278, 7, {
    "Category": [(c_field("Product", "Sales"), "Sales", "Product")],
    "Y": [(m_field("Total Sales"), "Sales", "Total Sales")],
})
visual("tableEx", 648, 426, 616, 278, 8, {
    "Values": [
        (c_field("Sales Person", "Sales"), "Sales", "Sales Person"),
        (m_field("Total Sales"), "Sales", "Total Sales"),
        (m_field("Total Boxes"), "Sales", "Total Boxes"),
        (m_field("Avg Order Value"), "Sales", "Avg Order Value"),
    ],
})

print("generated OK")
