# Confusion SAST: Interactive Notebook Environment

An interactive Jupyter environment for developing confusion vulnerability detection rules, exploring parsed code graphs, and testing detection strategies across a corpus of intentionally vulnerable Flask applications.

## Setup

From a fresh machine with Python 3.11+ available:

```bash
cd sast/

# Create virtualenv and install everything
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,notebook]"
```

This installs the `confusion-sast` package (editable) along with JupyterLab, ipywidgets, ipycytoscape (graph visualization), ipydatagrid (interactive tables), anywidget (custom code viewer widget), and Pygments (full-file syntax highlighting).

Verify the Jupyter extensions loaded correctly:

```bash
jupyter labextension list
```

You should see `jupyter-cytoscape`, `ipydatagrid`, and `anywidget` listed as enabled.

## Starting Jupyter

```bash
cd sast/
source .venv/bin/activate
jupyter lab
```

Open any notebook from this directory. The `01_quickstart.ipynb` notebook walks through the basics.

For quick terminal exploration without a browser:

```bash
.venv/bin/ipython -i notebooks/exploration.py
```

## First Cell

Every notebook starts the same way:

```python
%load_ext autoreload
%autoreload 2

from confusion_sast.notebook import *
```

The autoreload magic means any source code changes you make to the `confusion_sast` package are picked up immediately, without restarting the kernel. The star import brings in everything you need for interactive work.

## Selecting Targets

The `targets()` function discovers exercises in the `webapp/` directory:

```python
t = targets()
t                    # renders a browsable table in Jupyter
```

Navigate with attribute access:

```python
t.r01                # Section: input source confusion (9 exercises)
t.r01.e01            # Exercise: dual parameter confusion
t.r04.e03            # Exercise: duplicate coupons
```

Exercise objects work anywhere a path is expected. You can pass them directly to `load()`, `scan()`, `extract()`, or even `Path()`.

For batch helpers:

```python
batch_load(t.r01)   # one section
batch_load(t)       # entire corpus
```

## Loading and Scanning

**Load a graph** (parse source code into a queryable structure):

```python
g = load(t.r01.e01)        # cached -- instant on repeat calls
g = load(t.r01.e01, force=True)  # force re-parse
```

The result is an `AnalysisGraph` containing routes, input accesses, call edges, and more. Just type `g` in a cell to open the interactive Explorer directly.

**Scan for vulnerabilities** (load graph + run detection rules):

```python
r = scan(t.r01.e01)                     # all rules
r = scan(t.r01.e01, rules=["CONF-002"]) # specific rules only
r                                        # renders findings + endpoint table
```

**Load many exercises at once:**

```python
graphs = batch_load(t.r01)                      # all of r01
graphs = batch_load([t.r01.e01, t.r04.e03])    # cherry-pick
```

Returns a dict like `{"r01/e01": AnalysisGraph, "r01/e02": AnalysisGraph, ...}`.

## Writing and Testing Rules

This is the primary workflow. You write a rule in a notebook cell, run it, see the results, refine, and repeat.

### Define a rule

```python
@detect("MY-001", severity="high")
def multi_source_check(g):
    for handler, route, accs in g.by_endpoint():
        sources = {a.source for a in accs}
        if len(sources) > 1:
            yield finding(
                f"Multiple sources: {sorted(s.value for s in sources)}",
                evidence=accs,
                endpoint=route,
            )
```

### Test on one exercise

```python
results = run_fn(multi_source_check, g)
show(results)
```

### Test across many exercises

```python
graphs = batch_load(t.r01)
batch_results = batch_run(multi_source_check, graphs)
batch_results   # summary table showing which exercises trigger the rule
```

### Drill into specific results

```python
batch_results.hits                  # only exercises with findings
batch_results["r01/e03"]           # findings for a specific exercise
batch_results.total                 # total finding count across all exercises
```

### Iterate

Edit the rule cell, re-run it, re-run `batch_run()`. The graph cache means you never wait for re-parsing.

## Exploring the Graph

The `AnalysisGraph` provides several ways to inspect what the parser found:

```python
g.stats()                           # summary: nodes, edges, routes, accesses
g.by_endpoint()                     # [(handler, route, accesses), ...]
g.by_key()                          # {parameter_name: [accesses]}
g.accesses_reachable_from(handler)  # all accesses in handler + its callees
g.call_path("routes.handler", "utils.helper")  # shortest call path
g.endpoint_summaries()              # endpoint-oriented summaries for notebook UIs
g.function_summary("utils.helper")  # direct facts and graph metadata for one node
g.call_edges_between("a", "b")      # preserved call-site locations for an edge
```

For filtered queries:

```python
accesses(g, source="form")          # all form accesses
accesses(g, key="item")            # all accesses to 'item'
endpoint_detail("create_order", g)  # deep dive into one endpoint
diff_keys(g)                        # keys accessed with divergent patterns
```

### Raw NetworkX access

The underlying graph is a standard `nx.DiGraph`:

```python
g.g.number_of_nodes()
g.g.number_of_edges()
list(g.g.nodes(data=True))[:5]     # node attributes include 'kind'
```

## Interactive Widgets

### Explorer Panel

The composite `Explorer` is now a full analysis workbench:

- findings browser
- endpoint browser
- focused graph navigator
- evidence table
- details panel
- stacked full-file code-path browser

```python
explorer = Explorer(g, r.findings, target_path=t.r01.e01.path)
explorer
```

You can usually omit `target_path`; it is inferred from the graph or scan result:

```python
Explorer(g)
Explorer(r)
Explorer(g, r.findings)
```

Typical workflow:

- click a finding to focus the graph on only the functions relevant to that match
- inspect individual evidence rows to jump to the exact call path behind that evidence
- click a graph node to browse its direct accesses, callers/callees, and full source file
- switch to the endpoint tab for open-ended graph exploration even before you have findings

### Individual widgets

**Code Viewer** for full-file source context with syntax highlighting, line annotations, auto-scroll, and native resize handles:

```python
viewer = CodeViewer()
viewer.show_finding(r.findings[0])
viewer
```

**Code Path View** to materialize several code contexts for a route-to-evidence path:

```python
cp = CodePathView(target_path=t.r01.e01.path)
cp.show_finding(g, r.findings[0])
cp.widget
```

**Graph View** for focused graph navigation:

```python
gv = GraphView(g)
gv.focus_finding(r.findings[0])
gv.widget
```

The graph view supports:

- full graph vs endpoint-only vs focused subgraph scopes
- text search across functions, route rules, sources, and keys
- preserved edge metadata for call-site inspection
- coordinated node/edge highlighting for findings and evidence paths

**Findings Table** with filtering and richer rule-development context:

```python
ft = FindingsTable(r.findings, target_path=t.r01.e01.path)
ft.on_select(lambda f: viewer.show_finding(f))
ft.widget
```

**Endpoint Table** for backend/IR exploration:

```python
et = EndpointTable(g)
et.widget
```

**Evidence Table** for drilling into the exact facts backing a finding or function:

```python
ev = EvidenceTable(target_path=t.r01.e01.path)
ev.update(r.findings[0].evidence, title="Selected finding evidence")
ev.widget
```

## Backend Comparison

Compare how different parsers see the same code:

```python
comp = compare(t.r01.e01, backends=["ast", "joern", "codeql"])
comp.print_summary()
```

Note: `joern` requires a running Joern server, and `codeql` requires the CodeQL CLI. The `ast` backend has no external dependencies.

## Types Reference

When writing rules, you'll pattern-match against these:

| Type | Values |
|------|--------|
| `InputSource` | `ARGS`, `FORM`, `VALUES`, `JSON`, `DATA`, `HEADERS`, `COOKIES`, `FILES` |
| `AccessorKind` | `GET`, `GETLIST`, `INDEX`, `ATTR`, `DIRECT` |
| `Severity` | `INFO`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |

Access them as `InputSource.FORM`, `AccessorKind.GETLIST`, etc.

## Existing Detection Rules

| Rule | What it detects |
|------|----------------|
| CONF-001 | Same key read from different sources in one endpoint |
| CONF-002 | Singular/plural parameter name pairs (e.g. `item` vs `items`) |
| CONF-003 | Same key accessed with both `get()` and `getlist()` |
| CONF-004 | `request.values` used alongside `request.args` or `request.form` |
| CONF-005 | Dict merge where user data can overwrite computed values |
| CONF-006 | Middleware and handler reading the same key from different sources |
| CONF-007 | Conditional source selection based on Content-Type |

## Notebooks

| File | Purpose |
|------|---------|
| `01_quickstart.ipynb` | End-to-end walkthrough centered on the synchronized Explorer workbench |
| `02_graph_exploration.ipynb` | Endpoint-first graph exploration, focused subgraphs, and source-grounded navigation |
| `03_rule_development.ipynb` | Writing rules, batch testing, and inspecting matches through the workbench |
| `exploration.py` | IPython startup script (for terminal-based exploration) |
