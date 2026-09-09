#!/usr/bin/env python3
"""
Sankey diagram: Taxonomy of Visualization Framing Shifts
7 columns: Case | Where(Src) | Who(Src) | How(L1) | How(L2) | Who(Var) | Where(Var)
"""

import plotly.graph_objects as go
from collections import defaultdict, OrderedDict

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CASE DEFINITIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CASES = OrderedDict([
    ("C01", "COVID Deaths"),    ("C02", "Climate Temp."),
    ("C03", "Physicians"),      ("C04", "Deforestation"),
    ("C05", "US Inflation"),    ("C06", "COVID Cases"),
    ("C07", "Unemployment"),    ("C08", "Immigration"),
    ("C09", "Birth Rate"),      ("C10", "Global Climate"),
    ("C11", "CO₂"),             ("C12", "Border"),
    ("C13", "VAERS"),           ("C14", "IQ"),
    ("C15", "Housing"),         ("C16", "Crime"),
    ("C17", "Voter Turnout"),   ("C18", "Recession"),
    ("C19", "Labor Part."),     ("C20", "Unemp. Rate"),
    ("C21", "Fossil Fuel"),     ("C22", "Energy"),
])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NODE INFO: node_id → (role, platform_zh)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NI = {
    "C01-N0": ("bridger",   "政府/官方机构/国际组织"),
    "C01-N1": ("amplifier",  "新闻媒体"),
    "C01-N2": ("amplifier",  "个人网站/博客"),
    "C01-N3": ("extender",   "新闻媒体"),
    "C02-N0": ("bridger",   "政府/官方机构/国际组织"),
    "C02-N1": ("adverser",   "社交媒体"),
    "C02-N2": ("bridger",   "政府/官方机构/国际组织"),
    "C02-N3": ("amplifier",  "新闻媒体"),
    "C03-N0": ("bridger",   "政府/官方机构/国际组织"),
    "C03-N1": ("extender",   "新闻媒体"),
    "C03-N2": ("amplifier",  "社交媒体"),
    "C04-N0": ("bridger",   "政府/官方机构/国际组织"),
    "C04-N1": ("amplifier",  "新闻媒体"),
    "C04-N2": ("adverser",   "新闻媒体"),
    "C04-N3": ("amplifier",  "新闻媒体"),
    "C05-N0": ("bridger",   "第三方数据平台"),
    "C05-N1": ("extender",   "新闻媒体"),
    "C05-N2": ("amplifier",  "新闻媒体"),
    "C05-N3": ("extender",   "机构博客"),
    "C06-N0": ("bridger",   "新闻媒体"),
    "C06-N1": ("amplifier",  "新闻媒体"),
    "C06-N2": ("adverser",   "个人网站/博客"),
    "C07-N0": ("bridger",   "新闻媒体"),
    "C07-N1": ("bridger",   "第三方数据平台"),
    "C07-N2": ("extender",   "新闻媒体"),
    "C08-N0": ("bridger",   "政府/官方机构/国际组织"),
    "C08-N1": ("amplifier",  "社交媒体"),
    "C08-N2": ("amplifier",  "社交媒体"),
    "C08-N3": ("amplifier",  "社交媒体"),
    "C08-N4": ("extender",   "社交媒体"),
    "C08-N5": ("amplifier",  "社交媒体"),
    "C09-N0": ("bridger",   "社交媒体"),
    "C09-N1": ("extender",   "社交媒体"),
    "C09-N2": ("extender",   "社交媒体"),
    "C09-N3": ("bridger",   "社交媒体"),
    "C10-N0": ("bridger",   "第三方数据平台"),
    "C10-N1": ("amplifier",  "新闻媒体"),
    "C10-N2": ("amplifier",  "在线社区/UGC平台"),
    "C11-N0": ("bridger",   "新闻媒体"),
    "C11-N1": ("extender",   "机构博客"),
    "C11-N2": ("amplifier",  "政府/官方机构/国际组织"),
    "C12-N0": ("bridger",   "政府/官方机构/国际组织"),
    "C12-N1": ("amplifier",  "社交媒体"),
    "C12-N2": ("amplifier",  "社交媒体"),
    "C12-N3": ("extender",   "社交媒体"),
    "C13-N0": ("bridger",   "科研机构"),
    "C13-N1": ("amplifier",  "政府/官方机构/国际组织"),
    "C13-N2": ("bridger",   "科研机构"),
    "C13-N3": ("amplifier",  "在线社区/UGC平台"),
    "C13-N4": ("amplifier",  "个人网站/博客"),
    "C14-N0": ("bridger",   "科研机构"),
    "C14-N1": ("amplifier",  "在线社区/UGC平台"),
    "C14-N2": ("amplifier",  "在线社区/UGC平台"),
    "C15-N0": ("bridger",   "个人网站/博客"),
    "C15-N1": ("bridger",   "个人网站/博客"),
    "C15-N2": ("bridger",   "个人网站/博客"),
    "C16-N0": ("bridger",   "个人网站/博客"),
    "C16-N1": ("bridger",   "科研机构"),
    "C16-N2": ("amplifier",  "在线社区/UGC平台"),
    "C16-N3": ("bridger",   "科研机构"),
    "C17-N0": ("bridger",   "科研机构"),
    "C17-N1": ("bridger",   "新闻媒体"),
    "C17-N2": ("bridger",   "第三方数据平台"),
    "C17-N3": ("extender",   "个人网站/博客"),
    "C18-N0": ("bridger",   "政府/官方机构/国际组织"),
    "C18-N1": ("extender",   "新闻媒体"),
    "C18-N2": ("amplifier",  "新闻媒体"),
    "C18-N3": ("extender",   "个人网站/博客"),
    "C18-N4": ("bridger",   "机构博客"),
    "C19-N0": ("bridger",   "政府/官方机构/国际组织"),
    "C19-N1": ("amplifier",  "社交媒体"),
    "C19-N2": ("bridger",   "在线社区/UGC平台"),
    "C19-N3": ("bridger",   "社交媒体"),
    "C19-N4": ("amplifier",  "政府/官方机构/国际组织"),
    "C20-N0": ("bridger",   "政府/官方机构/国际组织"),
    "C20-N1": ("bridger",   "第三方数据平台"),
    "C20-N2": ("amplifier",  "新闻媒体"),
    "C20-N3": ("extender",   "第三方数据平台"),
    "C21-N0": ("bridger",   "第三方数据平台"),
    "C21-N1": ("amplifier",  "新闻媒体"),
    "C22-N0": ("bridger",   "新闻媒体"),
    "C22-N1": ("extender",   "在线社区/UGC平台"),
    "C22-N2": ("bridger",   "科研机构"),
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EDGES: (case_id, source_node, target_node, ops_string)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EDGES = [
    ("C01", "C01-N0", "C01-N1", "change type, simplify axis, change ldg, change title"),
    ("C01", "C01-N0", "C01-N2", "add annotation, simplify axis, change color, change title"),
    ("C01", "C01-N1", "C01-N3", "change title"),
    ("C02", "C02-N0", "C02-N1", "select time range, add annotation, delete source"),
    ("C02", "C02-N0", "C02-N2", "change color, change title"),
    ("C02", "C02-N0", "C02-N3", "add annotation, change title, change color, select time range"),
    ("C03", "C03-N0", "C03-N1", "change color"),
    ("C03", "C03-N0", "C03-N2", "change color, change aspect ratio"),
    ("C04", "C04-N0", "C04-N1", "change color, select time range, change title"),
    ("C04", "C04-N1", "C04-N2", "change color, change title, select time range"),
    ("C04", "C04-N0", "C04-N3", "change color, change title"),
    ("C05", "C05-N0", "C05-N1", "change title, add annotation"),
    ("C05", "C05-N0", "C05-N2", "change color, add annotation"),
    ("C05", "C05-N0", "C05-N3", "change color, change title"),
    ("C06", "C06-N0", "C06-N1", "change annotation, change color"),
    ("C06", "C06-N0", "C06-N2", "change color, add annotation"),
    ("C07", "C07-N0", "C07-N1", "change type, change color, add annotation"),
    ("C07", "C07-N0", "C07-N2", "change color, simplify axis, change title, add data variables"),
    ("C08", "C08-N0", "C08-N1", "select time range, change color, add annotation, delete source, change title"),
    ("C08", "C08-N1", "C08-N2", "change data granularity"),
    ("C08", "C08-N2", "C08-N3", "add annotation"),
    ("C08", "C08-N3", "C08-N4", "add data variables"),
    ("C08", "C08-N4", "C08-N5", "change title, change color, change annotation"),
    ("C09", "C09-N0", "C09-N1", "add data variables"),
    ("C09", "C09-N1", "C09-N2", "add data variables"),
    ("C09", "C09-N0", "C09-N3", "change color"),
    ("C10", "C10-N0", "C10-N1", "add annotation"),
    ("C10", "C10-N0", "C10-N2", "add annotation"),
    ("C11", "C11-N0", "C11-N1", "add annotation"),
    ("C11", "C11-N1", "C11-N2", "add annotation"),
    ("C12", "C12-N0", "C12-N1", "add annotation"),
    ("C12", "C12-N0", "C12-N2", "add annotation"),
    ("C12", "C12-N0", "C12-N3", "select time range"),
    ("C13", "C13-N0", "C13-N1", "change aspect ratio"),
    ("C13", "C13-N0", "C13-N2", "change type"),
    ("C13", "C13-N2", "C13-N3", "change aspect ratio, simplify axis, change axis scale, add annotation, add lgd"),
    ("C13", "C13-N0", "C13-N4", "change aspect ratio, add annotation, simplify axis, change axis scale"),
    ("C14", "C14-N0", "C14-N1", "change color, change title"),
    ("C14", "C14-N1", "C14-N2", "add annotation"),
    ("C15", "C15-N0", "C15-N1", "select data variables"),
    ("C15", "C15-N1", "C15-N2", "add annotation"),
    ("C16", "C16-N0", "C16-N1", "add annotation, change type"),
    ("C16", "C16-N0", "C16-N2", "add annotation, select time range, change title"),
    ("C16", "C16-N0", "C16-N3", "simplify axis, add annotation"),
    ("C17", "C17-N0", "C17-N1", "select time range"),
    ("C17", "C17-N0", "C17-N2", "change color, add lgd"),
    ("C17", "C17-N1", "C17-N3", "add annotation"),
    ("C18", "C18-N0", "C18-N1", "change title, add annotation"),
    ("C18", "C18-N0", "C18-N2", "select time range, change color"),
    ("C18", "C18-N0", "C18-N3", "change color, add data variables"),
    ("C18", "C18-N0", "C18-N4", "change color"),
    ("C19", "C19-N0", "C19-N1", "select time range"),
    ("C19", "C19-N0", "C19-N2", "select time range"),
    ("C19", "C19-N0", "C19-N3", "change title"),
    ("C19", "C19-N0", "C19-N4", "add annotation"),
    ("C20", "C20-N0", "C20-N1", "select time range"),
    ("C20", "C20-N0", "C20-N2", "add annotation, change color"),
    ("C20", "C20-N0", "C20-N3", "add data variables"),
    ("C21", "C21-N0", "C21-N1", "change color, add annotation"),
    ("C22", "C22-N0", "C22-N1", "add annotation, select time range"),
    ("C22", "C22-N0", "C22-N2", "change color"),
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAPPINGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OP_NORM = {
    "change ldg": "change legend", "change lgd": "change legend",
    "add lgd": "add legend", "simplify axis text": "simplify axis"
}

OP_L1 = {
    "select data variables": "Data", "add data variables": "Data",
    "select time range": "Data", "change data granularity": "Data",
    "change type": "Visual", "change color": "Visual",
    "simplify axis": "Visual",
    "change aspect ratio": "Visual", "change axis scale": "Visual",
    "change title": "Text", "add annotation": "Text",
    "change annotation": "Text", "delete source": "Text",
    "change legend": "Text", "add legend": "Text",
}

OP_DISPLAY = {
    "select data variables": "Select Variables",
    "add data variables": "Add Variables",
    "select time range": "Select Time Range",
    "change data granularity": "Change Granularity",
    "change type": "Change Chart Type",
    "change color": "Change Color",
    "simplify axis": "Simplify Axis",
    "change aspect ratio": "Change Aspect Ratio",
    "change axis scale": "Change Axis Scale",
    "change title": "Change Title",
    "add annotation": "Add Annotation",
    "change annotation": "Change Annotation",
    "delete source": "Delete Source",
    "change legend": "Change Legend",
    "add legend": "Add Legend",
}

L2_TO_L1 = {v: OP_L1[k] for k, v in OP_DISPLAY.items()}

PLAT_EN = {
    "政府/官方机构/国际组织": "Gov/IGO",
    "新闻媒体": "News Media",
    "社交媒体": "Social Media",
    "个人网站/博客": "Personal Blog",
    "第三方数据平台": "Data Platform",
    "在线社区/UGC平台": "Online Community",
    "科研机构": "Research Inst.",
    "机构博客": "Inst. Blog",
}

ROLE_NORM = {
    "bridger": "Bridger", "amplifier": "Amplifier",
    "adverser": "Adverser", "extender": "Extender",
}

ROLE_COLOR = {
    "Bridger": "#8A8FCC", "Adverser": "#D08350",
    "Amplifier": "#C44E42", "Extender": "#549E9F",
}

L1_COLOR = {
    "Data": "#EAB84A",
    "Visual": "#C25B8E",
    "Text": "#6AAA3A",
}

PLAT_COLOR = {
    "Gov/IGO": "#8C8C8C",
    "News Media": "#E8B4B8",
    "Social Media": "#B8D4E8",
    "Personal Blog": "#D4C4A8",
    "Data Platform": "#A8C8B8",
    "Online Community": "#E8C89C",
    "Research Inst.": "#9CA8B8",
    "Inst. Blog": "#C8B8D4",
}


def norm_op(op: str) -> str:
    op = op.strip().lower()
    return OP_NORM.get(op, op)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROCESS FLOWS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
flows = []
for case_id, src_node, tgt_node, ops_str in EDGES:
    src_role, src_plat = NI[src_node]
    tgt_role, tgt_plat = NI[tgt_node]
    ops = [norm_op(o) for o in ops_str.split(",")]
    for op in ops:
        l1 = OP_L1.get(op, "Text")
        l2 = OP_DISPLAY.get(op, op)
        flows.append({
            "case": f"{case_id} {CASES[case_id]}",
            "where_src": PLAT_EN[src_plat],
            "who_src": ROLE_NORM[src_role],
            "how_l1": l1,
            "how_l2": l2,
            "who_var": ROLE_NORM[tgt_role],
            "where_var": PLAT_EN[tgt_plat],
        })

print(f"Total flows (edge × operation): {len(flows)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BUILD SANKEY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COLUMNS = ["case", "where_src", "who_src", "how_l1", "how_l2", "who_var", "where_var"]
COL_X = [0.01, 0.15, 0.28, 0.42, 0.58, 0.76, 0.95]

role_order = {"Bridger": 0, "Amplifier": 1, "Extender": 2, "Adverser": 3}
l1_order = {"Data": 0, "Visual": 1, "Text": 2}
plat_order = {
    "Gov/IGO": 0, "Research Inst.": 1, "Data Platform": 2,
    "News Media": 3, "Inst. Blog": 4, "Personal Blog": 5,
    "Social Media": 6, "Online Community": 7,
}

col_labels: dict[str, list[str]] = {c: [] for c in COLUMNS}
for flow in flows:
    for c in COLUMNS:
        if flow[c] not in col_labels[c]:
            col_labels[c].append(flow[c])

col_labels["where_src"].sort(key=lambda p: plat_order.get(p, 99))
col_labels["who_src"].sort(key=lambda r: role_order.get(r, 99))
col_labels["how_l1"].sort(key=lambda l: l1_order.get(l, 99))
col_labels["how_l2"].sort(key=lambda l2: (l1_order.get(L2_TO_L1.get(l2, "Text"), 99), l2))
col_labels["who_var"].sort(key=lambda r: role_order.get(r, 99))
col_labels["where_var"].sort(key=lambda p: plat_order.get(p, 99))

all_labels: list[str] = []
node_idx: dict[tuple[str, str], int] = {}
node_x: list[float] = []
node_color: list[str] = []

for ci, c in enumerate(COLUMNS):
    for label in col_labels[c]:
        idx = len(all_labels)
        node_idx[(c, label)] = idx
        all_labels.append(label)
        node_x.append(COL_X[ci])
        if c in ("who_src", "who_var"):
            node_color.append(ROLE_COLOR.get(label, "#888"))
        elif c == "how_l1":
            node_color.append(L1_COLOR.get(label, "#888"))
        elif c == "how_l2":
            node_color.append(L1_COLOR.get(L2_TO_L1.get(label, "Text"), "#888"))
        elif c in ("where_src", "where_var"):
            node_color.append(PLAT_COLOR.get(label, "#888"))
        else:
            node_color.append("#B0B0B0")

node_flow: dict[int, float] = defaultdict(float)
for flow in flows:
    for c in COLUMNS:
        node_flow[node_idx[(c, flow[c])]] += 1

NODE_PAD_FRAC = 0.012
node_y: list[float] = [0.0] * len(all_labels)

for ci, c in enumerate(COLUMNS):
    labels = col_labels[c]
    n = len(labels)
    fvals = [node_flow[node_idx[(c, l)]] for l in labels]
    total = sum(fvals)
    total_pad = NODE_PAD_FRAC * max(n - 1, 0)
    usable = max(1.0 - total_pad - 0.04, 0.5)
    cum = 0.02
    for i, l in enumerate(labels):
        idx = node_idx[(c, l)]
        h = (fvals[i] / total) * usable if total > 0 else usable / n
        node_y[idx] = min(max(cum + h / 2, 0.001), 0.999)
        cum += h + NODE_PAD_FRAC

link_agg: dict[tuple[int, int, str], float] = defaultdict(float)

for flow in flows:
    l1_cat = flow["how_l1"]
    for i in range(len(COLUMNS) - 1):
        sc = COLUMNS[i]
        tc = COLUMNS[i + 1]
        si = node_idx[(sc, flow[sc])]
        ti = node_idx[(tc, flow[tc])]
        link_agg[(si, ti, l1_cat)] += 1

link_src, link_tgt, link_val, link_clr = [], [], [], []

for (s, t, l1_cat), val in link_agg.items():
    link_src.append(s)
    link_tgt.append(t)
    link_val.append(val)
    base = L1_COLOR.get(l1_cat, "#888888")
    r, g, b = int(base[1:3], 16), int(base[3:5], 16), int(base[5:7], 16)
    link_clr.append(f"rgba({r},{g},{b},0.22)")

print(f"Nodes: {len(all_labels)}, Links: {len(link_src)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CREATE FIGURE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fig = go.Figure(go.Sankey(
    arrangement="snap",
    node=dict(
        pad=12,
        thickness=10,
        line=dict(color="white", width=0.3),
        label=all_labels,
        color=node_color,
        x=node_x,
        y=node_y,
    ),
    link=dict(
        source=link_src,
        target=link_tgt,
        value=link_val,
        color=link_clr,
    ),
))

col_headers = [
    "Case",
    "Where<br>(Source)",
    "Who<br>(Source)",
    "How<br>(L1)",
    "How<br>(L2)",
    "Who<br>(Variants)",
    "Where<br>(Variants)",
]
for header, x in zip(col_headers, COL_X):
    fig.add_annotation(
        x=x, y=1.04,
        text=f"<b>{header}</b>",
        showarrow=False,
        font=dict(size=12, color="#333", family="Arial"),
        xref="paper", yref="paper",
        xanchor="center",
    )

l1_legend_x = 0.35
for l1_name, l1_clr in L1_COLOR.items():
    fig.add_annotation(
        x=l1_legend_x, y=-0.02,
        text=f"<b>■</b> {l1_name}",
        showarrow=False,
        font=dict(size=12, color=l1_clr, family="Arial"),
        xref="paper", yref="paper",
        xanchor="left",
    )
    l1_legend_x += 0.08

fig.update_layout(
    font=dict(size=12, family="Arial"),
    width=2000,
    height=1200,
    margin=dict(l=30, r=30, t=60, b=40),
    paper_bgcolor="white",
    plot_bgcolor="white",
)

out_html = "docs/figures/sankey_taxonomy.html"
fig.write_html(out_html)
print(f"Saved HTML → {out_html}")

try:
    out_png = "docs/figures/sankey_taxonomy.png"
    fig.write_image(out_png, scale=2)
    print(f"Saved PNG → {out_png}")
except Exception as e:
    print(f"PNG export skipped: {e}")
