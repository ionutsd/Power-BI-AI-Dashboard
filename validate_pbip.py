"""Offline structural check for the PBIP files.

Encodes the constraints from the published Fabric schemas (fetched and read on
2026-08-18) so the project can be checked without network access. Every schema
below sets additionalProperties:false, so an unexpected property is as fatal as
a missing required one.
"""
import json, os, re, glob, sys

ROOT = r"D:\CLAUDE_FOLDER\POWER BI"

errors = []
checked = 0


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check(cond, path, msg):
    if not cond:
        errors.append("%s: %s" % (os.path.relpath(path, ROOT), msg))


def props(obj, required, allowed, path, where=""):
    label = (where + " ") if where else ""
    for r in required:
        check(r in obj, path, "%smissing required property '%s'" % (label, r))
    for k in obj:
        check(k in allowed, path, "%sproperty '%s' not allowed" % (label, k))


def schema_matches(obj, pattern, path):
    got = obj.get("$schema", "")
    check(re.match(pattern, got) is not None, path,
          "$schema %r does not match %s" % (got, pattern))


# ---------------------------------------------------------------- .pbip
p = os.path.join(ROOT, "ChocolateSales.pbip")
d = load(p); checked += 1
props(d, ["$schema", "version", "artifacts"],
      ["$schema", "version", "artifacts", "settings"], p)
schema_matches(d, r"^https://developer\.microsoft\.com/json-schemas/fabric/pbip/"
                  r"pbipProperties/1\.[0-9]+\.[0-9]+/schema\.json$", p)
for art in d.get("artifacts", []):
    props(art, ["report"], ["report"], p, "artifacts[]")
    props(art.get("report", {}), ["path"], ["path"], p, "artifacts[].report")

# --------------------------------------------------------------- .pbism
p = os.path.join(ROOT, "ChocolateSales.SemanticModel", "definition.pbism")
d = load(p); checked += 1
props(d, ["$schema", "version"], ["$schema", "version", "settings"], p)
schema_matches(d, r"^https://developer\.microsoft\.com/json-schemas/fabric/item/"
                  r"semanticModel/definitionProperties/1\.[0-9]+\.[0-9]+/schema\.json$", p)

# ---------------------------------------------------------------- .pbir
p = os.path.join(ROOT, "ChocolateSales.Report", "definition.pbir")
d = load(p); checked += 1
props(d, ["$schema", "version", "datasetReference"],
      ["$schema", "version", "datasetReference"], p)
schema_matches(d, r"^https://developer\.microsoft\.com/json-schemas/fabric/item/"
                  r"report/definitionProperties/[12]\.[0-9]+\.[0-9]+/schema\.json$", p)
check(d.get("version", "").split(".")[0].isdigit()
      and int(d.get("version", "0").split(".")[0]) >= 4, p,
      "version %r must be 4.0 or higher for the \\definition (PBIR) folder to be used"
      % d.get("version"))
dr = d.get("datasetReference", {})
check(("byPath" in dr) != ("byConnection" in dr), p,
      "datasetReference needs exactly one of byPath / byConnection")
if "byPath" in dr:
    props(dr["byPath"], ["path"], ["path"], p, "datasetReference.byPath")

# ------------------------------------------------------------- .platform
for sub in ("ChocolateSales.SemanticModel", "ChocolateSales.Report"):
    p = os.path.join(ROOT, sub, ".platform")
    d = load(p); checked += 1
    props(d, ["$schema", "metadata", "config"], ["$schema", "metadata", "config"], p)
    props(d.get("metadata", {}), ["type", "displayName"],
          ["type", "displayName", "description"], p, "metadata")
    props(d.get("config", {}), ["version", "logicalId"], ["version", "logicalId"], p, "config")

# ---------------------------------------------------------- version.json
# Required by the PBIR loader; its absence is what produced
# "Cannot find file 'version.json'." on open.
p = os.path.join(ROOT, "ChocolateSales.Report", "definition", "version.json")
check(os.path.isfile(p), p, "REQUIRED file is missing")
if os.path.isfile(p):
    d = load(p); checked += 1
    props(d, ["$schema", "version"], ["$schema", "version"], p)
    check(d.get("$schema") == "https://developer.microsoft.com/json-schemas/fabric/item/"
                              "report/definition/versionMetadata/1.0.0/schema.json", p,
          "$schema must be exactly the versionMetadata/1.0.0 URL (schema uses const)")
    check(re.match(r"^[1-9][0-9]*\.(0|[1-9][0-9]*)\.0$", d.get("version", "")) is not None,
          p, "version %r must be major>=1, minor>=0, patch always 0" % d.get("version"))

# ----------------------------------------------------------- report.json
p = os.path.join(ROOT, "ChocolateSales.Report", "definition", "report.json")
d = load(p); checked += 1
props(d, ["$schema", "layoutOptimization", "themeCollection"],
      ["$schema", "themeCollection", "layoutOptimization", "filterConfig", "objects",
       "reportSource", "publicCustomVisuals", "resourcePackages",
       "organizationCustomVisuals", "annotations", "dataSourceVariables", "settings",
       "slowDataSourceSettings"], p)
for key in ("baseTheme", "customTheme"):
    if key in d.get("themeCollection", {}):
        props(d["themeCollection"][key], ["name", "reportVersionAtImport", "type"],
              ["name", "reportVersionAtImport", "type"], p, "themeCollection." + key)
        check(d["themeCollection"][key]["type"] in ("RegisteredResources", "SharedResources"),
              p, "themeCollection.%s.type must be RegisteredResources or SharedResources" % key)

# ------------------------------------------------------------ pages.json
PAGES = os.path.join(ROOT, "ChocolateSales.Report", "definition", "pages")
p = os.path.join(PAGES, "pages.json")
d = load(p); checked += 1
props(d, ["$schema"], ["$schema", "pageOrder", "activePageName"], p)
page_order = d.get("pageOrder", [])

# ------------------------------------------------------------- page.json
DISPLAY_OPTIONS = {"DeprecatedDynamic", "FitToPage", "FitToWidth", "ActualSize",
                   "ActualSizeTopLeft"}
page_dirs = [x for x in glob.glob(os.path.join(PAGES, "*")) if os.path.isdir(x)]
for pd in page_dirs:
    p = os.path.join(pd, "page.json")
    d = load(p); checked += 1
    props(d, ["$schema", "displayName", "displayOption", "name"],
          ["$schema", "name", "displayName", "displayOption", "height", "width",
           "filterConfig", "pageBinding", "objects", "visibility", "visualInteractions",
           "autoPageGenerationConfig", "annotations", "howCreated"], p)
    check(d.get("displayOption") in DISPLAY_OPTIONS, p,
          "displayOption %r not in %s" % (d.get("displayOption"), sorted(DISPLAY_OPTIONS)))
    check(d.get("name") == os.path.basename(pd), p,
          "page name %r does not match folder %r" % (d.get("name"), os.path.basename(pd)))
    check(d.get("name") in page_order, p, "page not listed in pages.json pageOrder")

    # ---------------------------------------------------- visual.json
    for vp in glob.glob(os.path.join(pd, "visuals", "*", "visual.json")):
        vd = load(vp); checked += 1
        props(vd, ["$schema", "name", "position"],
              ["$schema", "name", "position", "visual", "visualGroup", "parentGroupName",
               "filterConfig", "isHidden", "annotations", "howCreated"], vp)
        check(vd.get("name") == os.path.basename(os.path.dirname(vp)), vp,
              "visual name does not match its folder")
        props(vd.get("position", {}), ["x", "y", "height", "width"],
              ["x", "y", "z", "height", "width", "tabOrder", "angle"], vp, "position")
        pos = vd.get("position", {})
        if all(k in pos for k in ("x", "width")):
            check(pos["x"] + pos["width"] <= d.get("width", 1280), vp,
                  "visual extends past page width (%s + %s > %s)"
                  % (pos["x"], pos["width"], d.get("width")))
        if all(k in pos for k in ("y", "height")):
            check(pos["y"] + pos["height"] <= d.get("height", 720), vp,
                  "visual extends past page height (%s + %s > %s)"
                  % (pos["y"], pos["height"], d.get("height")))
        v = vd.get("visual", {})
        props(v, ["visualType"],
              ["visualType", "autoSelectVisualType", "query", "expansionStates", "objects",
               "visualContainerObjects", "syncGroup", "drillFilterOtherVisuals"], vp, "visual")
        q = v.get("query", {})
        props(q, [], ["sortDefinition", "options", "queryState", "isDrillDisabled"],
              vp, "visual.query")
        for role, state in q.get("queryState", {}).items():
            props(state, [], ["showAll", "projections", "fieldParameters"], vp,
                  "queryState.%s" % role)
            for pr in state.get("projections", []):
                props(pr, ["field", "queryRef"],
                      ["field", "queryRef", "nativeQueryRef", "displayName", "format",
                       "active", "hidden"], vp, "queryState.%s projection" % role)
                fld = pr.get("field", {})
                check(len(fld) == 1 and next(iter(fld)) in
                      ("Column", "Measure", "Aggregation", "HierarchyLevel"), vp,
                      "projection field has unexpected shape: %s" % list(fld))

print("checked %d json files" % checked)
if errors:
    print("\n%d PROBLEM(S):" % len(errors))
    for e in errors:
        print("  -", e)
    sys.exit(1)
print("all structural checks passed")
