GLOBAL_CSS = """
<style>
/* ── 背景：淺藍灰，與首頁 navy 同色系 ── */
.stApp {
    background: linear-gradient(160deg, #eef2fa 0%, #e8eef8 55%, #edf1f9 100%) !important;
}

/* ── 主文字 ── */
html, body, [class*="css"], .stMarkdown, .stText, p, li, label,
h1, h2, h3, h4, h5, h6,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    color: #1a2340 !important;
}

/* ── 標題 ── */
h1, h2, h3 { color: #1a2a4a !important; }

/* ── 側邊欄 ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #dce6f5 0%, #d0dcf0 100%) !important;
}
[data-testid="stSidebar"] * { color: #1a2a4a !important; }
[data-testid="stSidebar"] label { color: #2a3a60 !important; font-weight: 500 !important; }

/* ── Selectbox trigger ── */
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] {
    background-color: #dce6f5 !important;
    border: 1px solid #b0c4e0 !important;
    color: #1a2340 !important;
}
[data-baseweb="select"] * { color: #1a2340 !important; }
[data-baseweb="select"] svg { fill: #1a2340 !important; }

/* ── Dropdown popover（body portal，手機和桌機通用） ── */
[data-baseweb="popover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] > div > div {
    background-color: #dce6f5 !important;
    border: 1px solid #b0c4e0 !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 16px rgba(30,50,100,0.10) !important;
}
[data-baseweb="menu"] {
    background-color: #dce6f5 !important;
}
[data-baseweb="menu"] ul,
[data-baseweb="menu"] li {
    background-color: #dce6f5 !important;
    color: #1a2340 !important;
}
/* role="listbox" 是實際選項容器 */
[role="listbox"] {
    background-color: #dce6f5 !important;
    color: #1a2340 !important;
}
[role="option"] {
    background-color: #dce6f5 !important;
    color: #1a2340 !important;
}
[role="option"] * {
    background-color: transparent !important;
    color: #1a2340 !important;
}
[role="option"]:hover {
    background-color: #c4d4ec !important;
}
[role="option"][aria-selected="true"] {
    background-color: #dce6f5 !important;
    color: #1a2340 !important;
    font-weight: 600 !important;
}

/* ── 原生 <select>（Android WebView fallback） ── */
select {
    background-color: #ffffff !important;
    color: #1a2340 !important;
    border: 1px solid #b0c4e0 !important;
    border-radius: 6px !important;
}
select option {
    background-color: #ffffff !important;
    color: #1a2340 !important;
}

/* ── 手機版 sidebar overlay 容器 ── */
section[data-testid="stSidebar"] > div,
[data-testid="stSidebarNav"] {
    background: linear-gradient(180deg, #dce6f5 0%, #d0dcf0 100%) !important;
}

/* ── Text input / textarea ── */
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
    background-color: #ffffff !important;
    border: 1px solid #b0c4e0 !important;
    color: #1a2340 !important;
    border-radius: 6px !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder { color: #8098b8 !important; }

/* ── Buttons ── */
.stButton > button {
    background-color: #dce8f8 !important;
    color: #1a3060 !important;
    border: 1px solid #a0b8d8 !important;
    border-radius: 8px !important;
}
.stButton > button:hover {
    background-color: #c8d8f0 !important;
    border-color: #7a9cc8 !important;
}
/* Primary button — 用 data-testid 確保手機/桌機都生效 */
[data-testid="baseButton-primary"],
.stButton > button[kind="primary"] {
    background-color: #2563a8 !important;
    border-color: #2563a8 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
}
[data-testid="baseButton-primary"] p,
[data-testid="baseButton-primary"] span,
.stButton > button[kind="primary"] p,
.stButton > button[kind="primary"] span {
    color: #ffffff !important;
}
[data-testid="baseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover {
    background-color: #1e50a0 !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background-color: transparent !important;
    border-bottom: 1px solid #b0c4e0 !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    color: #4a6a9a !important;
    background-color: transparent !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #1a3060 !important;
    border-bottom: 2px solid #2563a8 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background-color: rgba(255, 255, 255, 0.75) !important;
    border: 1px solid #b0c4e0 !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: #1a2a4a !important;
}

/* ── Metric boxes ── */
[data-testid="stMetric"] {
    background-color: rgba(255, 255, 255, 0.8) !important;
    border: 1px solid #b0c4e0 !important;
    border-radius: 8px !important;
    padding: 0.8rem 1rem !important;
}
[data-testid="stMetricValue"] { color: #1a3060 !important; }
[data-testid="stMetricLabel"] { color: #4a6a9a !important; }

/* ── Info / Warning / Error / Success banners ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background-color: rgba(255, 255, 255, 0.7) !important;
    border: 1px dashed #90b0d8 !important;
    border-radius: 8px !important;
}

/* ── Dataframe / table ── */
[data-testid="stDataFrame"] { background-color: rgba(255, 255, 255, 0.8) !important; }

/* ── Radio / Checkbox ── */
.stRadio label, .stCheckbox label { color: #1a2a4a !important; }

/* ── Divider ── */
hr { border-color: #b0c4e0 !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #dce6f5; }
::-webkit-scrollbar-thumb { background: #90b0d8; border-radius: 3px; }
</style>
"""
