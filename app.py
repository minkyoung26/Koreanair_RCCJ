# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import datetime
import os
import gc
import glob

# 1. Page Config
st.set_page_config(
    page_title="일본노선 발매/공급 Market Share",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

EXT_WEB_APP_URL = "https://script.google.com/a/macros/koreanair.com/s/AKfycbxt3IfN0gB4n344U4gL1kt5i4RVjn7_uuG5PtKY-pPgNejpDCsjp2PEbopEexw5NLUjDQ/exec"

today = datetime.date.today()
current_monday = today - datetime.timedelta(days=today.weekday())
issue_start_date = current_monday - datetime.timedelta(weeks=5)
issue_end_date = current_monday - datetime.timedelta(days=1)
dep_start_m = today.replace(day=1)
dep_months = []
for i in range(5):
    m = (dep_start_m.month - 1 + i) % 12 + 1
    y = dep_start_m.year + (dep_start_m.month - 1 + i) // 12
    dep_months.append(f"{y}.{m:02d}월")
dep_range_str = f"{dep_months[0]} ~ {dep_months[-1]}"
issue_range_str = f"{issue_start_date.strftime('%Y.%m.%d')} ~ {issue_end_date.strftime('%Y.%m.%d')}"

EXCEL_KE_ROUTES_MASTER = [
    "G/HND", "I/NRT", "I/HND", "P/NRT", "C/NRT", "I/KIX", "G/KIX", "I/UKB",
    "I/OKJ", "I/HIJ", "I/FUK", "I/KOJ", "I/NGS", "I/KMJ", "I/OIT", "I/NGO",
    "P/NGO", "I/KIJ", "I/KMQ", "I/OKA", "I/CTS", "I/AOJ"
]
KOREA_APO_MAP = {'I': 'ICN', 'G': 'GMP', 'P': 'PUS', 'C': 'CJU', 'T': 'TAE', 'W': 'MWX', 'Y': 'YNY', 'K': 'CJJ'}

MONTH_MAP = {
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
}

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"], .stApp { font-family: 'Noto Sans KR', sans-serif !important; color: #0f172a; }
    :root { --primary-color: #0ea5e9 !important; --primaryColor: #0ea5e9 !important; }
    .main-app-title { font-size: 28px !important; font-weight: 700 !important; color: #0f172a; margin-bottom: 12px; }
    .unified-sub-header { font-size: 18px !important; font-weight: 600 !important; color: #0f172a; margin-top: 10px; margin-bottom: 10px; }
    .group-section-header { font-size: 18px !important; font-weight: 600 !important; color: #0f172a; padding-bottom: 8px; border-bottom: 2px solid #cbd5e1; margin-top: 10px; margin-bottom: 12px; }
    p, span, label, div, select, button, input { font-size: 13.5px !important; font-weight: 400; }
    div[data-baseweb="tab-highlight"] { display: none !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px !important; background-color: #f1f5f9 !important; padding: 6px !important; border-radius: 8px !important; border: 1px solid #cbd5e1 !important; margin-bottom: 15px !important; }
    div[role="tab"], button[role="tab"], button[data-baseweb="tab"], div[data-baseweb="tab"] { background-color: #cbd5e1 !important; border: 1px solid #94a3b8 !important; border-radius: 6px !important; padding: 8px 18px !important; color: #1e293b !important; font-weight: 700 !important; }
    div[role="tab"][aria-selected="true"], button[role="tab"][aria-selected="true"], button[data-baseweb="tab"][aria-selected="true"], div[data-baseweb="tab"][aria-selected="true"] { background-color: #0284c7 !important; color: #ffffff !important; border-color: #0284c7 !important; box-shadow: 0 2px 4px rgba(0,0,0,0.15) !important; }
    summary::-webkit-details-marker { display: none !important; }
    summary { list-style: none !important; list-style-type: none !important; cursor: pointer; }
    details > summary { list-style: none !important; list-style-type: none !important; }
    div[data-baseweb="popover"] div[role="listbox"] { max-height: 400px !important; overflow-y: auto !important; }
    .source-header-box { background-color: #f0f9ff; border-left: 5px solid #0284c7; padding: 12px 18px; border-radius: 6px; margin-bottom: 15px; font-size: 13.5px; color: #0f172a; font-weight: 500; }
    .filter-label-title { font-size: 13px !important; font-weight: 700 !important; color: #334155; margin-bottom: 4px; margin-top: 8px; border-left: 3px solid #0ea5e9; padding-left: 6px; }
    .metric-card { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.03); margin-bottom: 10px; }
    .metric-card-ke { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.03); margin-bottom: 10px; }
    .metric-title { font-size: 12.5px; color: #64748b; margin-bottom: 4px; font-weight: 500; }
    .metric-value { font-size: 22px; color: #1e293b; font-weight: 700; }
    .custom-piv-container, .yoy-table-container { width: 100%; overflow-x: auto; margin-bottom: 20px; border-radius: 8px; border: 1px solid #cbd5e1 !important; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
    .custom-piv-table, .yoy-table { width: 100%; border-collapse: collapse; font-size: 12.5px; background-color: #ffffff; text-align: center !important; table-layout: fixed !important; }
    .custom-piv-table th.header-main, .yoy-table th, .yoy-table th.mkt-header, .yoy-table th.carrier-header { background-color: #cfe2f3 !important; color: #0f172a !important; padding: 8px 6px; border: 1px solid #cbd5e1 !important; font-weight: 600; text-align: center !important; white-space: nowrap; }
    .yoy-table th.ke-header { background-color: #9fc5e8 !important; color: #0f172a !important; padding: 8px 6px; border: 1px solid #cbd5e1 !important; font-size: 13px !important; font-weight: 700 !important; text-align: center !important; white-space: nowrap; }
    .custom-piv-table td, .yoy-table td { padding: 6px 10px; border: 1px solid #cbd5e1 !important; text-align: center !important; }
    .yoy-table tr:hover { background-color: #f8fafc !important; }
    table.custom-piv-table td span.yoy-up, table.yoy-table td span.yoy-up { color: #1d4ed8 !important; font-weight: 700 !important; }
    table.custom-piv-table td span.yoy-down, table.yoy-table td span.yoy-down { color: #dc2626 !important; font-weight: 700 !important; }
    table.custom-piv-table td span.yoy-dash, table.yoy-table td span.yoy-dash { color: #64748b !important; font-weight: 500 !important; }
    table.custom-piv-table td span.txt-ke-bold, table.yoy-table td span.txt-ke-bold { color: #0b5394 !important; font-weight: 800 !important; }
    tr.total-row-blue td { background-color: #0284c7 !important; color: #ffffff !important; border-bottom: 3px solid #ef4444 !important; font-weight: 800 !important; }
    tr.total-row-blue td span.yoy-up { color: #a5f3fc !important; font-weight: 900 !important; }
    tr.total-row-blue td span.yoy-down { color: #fecaca !important; font-weight: 900 !important; }
    tr.total-row-blue td span.yoy-dash { color: #f1f5f9 !important; }
    tr.total-row-blue td span.txt-ke-bold { color: #ffffff !important; font-weight: 900 !important;}
</style>
""", unsafe_allow_html=True)

st.sidebar.header("📁 실시간 데이터 업로드")
uploaded_iss = st.sidebar.file_uploader("1. 3/4수송 Parquet/CSV 캐시", type=['parquet', 'csv', 'xlsx'], key="sb_uploader_iss")
uploaded_sup = st.sidebar.file_uploader("2. 공급 데이터", type=['csv', 'xlsx', 'zip', 'parquet'], key="sb_uploader_sup")
uploaded_6th = st.sidebar.file_uploader("3. 6수송 데이터", type=['csv', 'xlsx', 'zip', 'parquet'], key="sb_uploader_6th")

def find_column_by_candidates(columns, candidates):
    for cand in candidates:
        for c in columns:
            cleaned_col = str(c).lower().replace(" ", "").replace("_", "").replace(".", "")
            if cand == cleaned_col or cand in cleaned_col:
                return c
    return None

def clean_transport_column(df):
    if df is None: return df
    b_col = find_column_by_candidates(df.columns, ['수송', 'bound'])
    if b_col: df['수송'] = df[b_col].astype(str).str.strip()
    return df

def load_fast_parquet_data_file():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, 'cache_34_data.parquet'),
        'cache_34_data.parquet',
        os.path.join(os.getcwd(), 'cache_34_data.parquet')
    ]
    for target_path in candidates:
        if os.path.exists(target_path):
            try:
                df = pd.read_parquet(target_path, engine='pyarrow')
                if df is not None and not df.empty:
                    return clean_transport_column(df)
            except Exception: pass
    return None
# 함수 위에 데코레이터를 추가하여 읽어온 데이터를 메모리에 캐싱합니다.
@st.cache_data
def process_any_uploaded_file(file_obj):
    file_obj.seek(0)
    if file_obj.name.endswith(".parquet"):
        df = pd.read_parquet(file_obj)
    elif file_obj.name.endswith(".xlsx"):
        df = pd.read_excel(file_obj)
    else:
        df = pd.read_csv(file_obj, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    return clean_transport_column(df)
def process_any_uploaded_file(file_obj):
    file_obj.seek(0)
    if file_obj.name.endswith('.parquet'): df = pd.read_parquet(file_obj)
    elif file_obj.name.endswith('.xlsx'): df = pd.read_excel(file_obj)
    else: df = pd.read_csv(file_obj, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    return clean_transport_column(df)

def load_aux_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for sp in [os.path.join(base_dir, '공급.csv'), '공급.csv', os.path.join(os.getcwd(), '공급.csv')]:
        if os.path.exists(sp):
            try:
                df = pd.read_csv(sp, low_memory=False)
                if df is not None and not df.empty: return df
            except: pass
    return None
# 🟢 @st.cache_data 대신 @st.cache_resource 사용 (메모리 복사본 생성 완전 차단)
@st.cache_resource
def load_6th_data_aggregated():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, 'cache_6th_data.parquet'),
        'cache_6th_data.parquet'
    ]
    for target_path in candidates:
        if os.path.exists(target_path):
            try:
                # pyarrow 메모리 맵(memory_map=True)으로 자원 최소 점유
                return pd.read_parquet(target_path, engine='pyarrow', memory_map=True)
            except Exception: pass
    return None
def load_6th_data_aggregated():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, 'cache_6th_data.parquet'),
        'cache_6th_data.parquet',
        os.path.join(os.getcwd(), 'cache_6th_data.parquet')
    ]
    for target_path in candidates:
        if os.path.exists(target_path):
            try:
                df = pd.read_parquet(target_path, engine='pyarrow')
                if df is not None and not df.empty:
                    return df
            except Exception: pass
    return None

def get_34_last_updated_date():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(base_dir, 'cache_34_data.parquet')
    if os.path.exists(target_path):
        mtime = os.path.getmtime(target_path)
        return datetime.datetime.fromtimestamp(mtime).strftime('%Y.%m.%d %H:%M')
    return "날짜 정보 없음"

def get_6th_last_updated_date():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(base_dir, 'cache_6th_data.parquet')
    if os.path.exists(target_path):
        mtime = os.path.getmtime(target_path)
        return datetime.datetime.fromtimestamp(mtime).strftime('%Y.%m.%d %H:%M')
    return "날짜 정보 없음"

def extract_pure_month(val):
    if pd.isna(val): return ""
    s_raw = str(val).strip().lower()
    for m_abbr, m_num in MONTH_MAP.items():
        if m_abbr in s_raw:
            return m_num
    s = s_raw.replace('-', '').replace('.', '').replace('/', '').replace('월', '').strip()
    if len(s) >= 6 and s.isdigit(): return s[4:6].zfill(2)
    elif len(s) == 4 and s.isdigit(): return s[2:4].zfill(2)
    elif len(s) <= 2 and s.isdigit(): return s.zfill(2)
    return s

def sort_month_options(opts, reverse=True):
    def date_key(x):
        s = str(x).strip()
        if not s or s.lower() in ['nan', 'none']:
            return pd.Timestamp('1900-01-01')
        formats_to_try = ['%y-%b', '%b-%y', '%Y-%m', '%Y.%m', '%Y%m', '%y-%B', '%B-%y', '%d-%b-%y', '%Y-%m-%d']
        for fmt in formats_to_try:
            try:
                dt = pd.to_datetime(s, format=fmt)
                if pd.notna(dt): return dt
            except Exception: continue
        try:
            dt = pd.to_datetime(s, errors='coerce')
            return dt if pd.notna(dt) else pd.Timestamp('1900-01-01')
        except Exception:
            return pd.Timestamp('1900-01-01')
    return sorted(opts, key=date_key, reverse=reverse)

def get_dynamic_range_label_6th(opts):
    if not opts: return ""
    clean_opts = [str(x).strip() for x in opts if str(x).strip() not in ['', 'nan', 'none']]
    if not clean_opts: return ""
    return f" ({clean_opts[-1]} ~ {clean_opts[0]})"

disk_sup = load_aux_files()
df_iss_merged = process_any_uploaded_file(uploaded_iss) if uploaded_iss else load_fast_parquet_data_file()
df_sup_raw = disk_sup

st.markdown('<div class="main-app-title">✈ 일본노선 발매/공급 Market Share</div>', unsafe_allow_html=True)
st.markdown('<div class="group-section-header">🗂️ 메인 대시보드 선택</div>', unsafe_allow_html=True)

selected_group = st.radio("분석할 수송 영역을 선택하세요:", options=["✈️ 3/4수송 대시보드", "🌐 6수송 대시보드", "🔗 W26 연결 네트워크"], index=0, horizontal=True)

def build_airline_color_map(airlines_list):
    cmap = {'KE': '#16a34a'}
    palette = px.colors.qualitative.Plotly + px.colors.qualitative.Bold + px.colors.qualitative.Pastel
    color_idx = 0
    for al in airlines_list:
        if str(al).upper() != 'KE':
            while True:
                candidate = palette[color_idx % len(palette)]
                color_idx += 1
                if candidate.upper() not in [c.upper() for c in ['#16a34a', '#16A34A', '#00cc96', '#00CC96', '#2ca02c', '#636EFA', '#0ea5e9']]:
                    cmap[al] = candidate
                    break
    return cmap

def apply_bottom_legend(fig):
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5, title=dict(text="")), margin=dict(b=80))
    return fig

def render_multiselect_box(container, label, full_list, key_name, default_vals=None):
    container.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
    opts = [str(x).strip() for x in full_list if str(x).strip() != 'nan']
    default_vals = [] if default_vals is None else [x for x in default_vals if x in opts]
    return container.multiselect(label, options=opts, default=default_vals, key=key_name, label_visibility="collapsed")

def render_panel_multiselect(container, label, full_list, key_name, default_vals=None):
    container.markdown(f'<div class="filter-label-title">{label}</div>', unsafe_allow_html=True)
    opts = [str(x).strip() for x in full_list if str(x).strip() != 'nan']
    default_vals = [] if default_vals is None else [x for x in default_vals if x in opts]
    return container.multiselect(label, options=opts, default=default_vals, key=key_name, label_visibility="collapsed")

def get_yoy_td_html(val, is_percentage_point=False, bg_color="", bg_class=""):
    unit = "%p" if is_percentage_point else "%"
    class_str = f' class="{bg_class}"' if bg_class else ''
    style_str = f' style="background-color:{bg_color} !important; text-align:center !important; white-space:nowrap !important; padding:6px 4px !important;"' if bg_color and not bg_class else ' style="text-align:center !important; white-space:nowrap !important; padding:6px 4px !important;"'
    base_td = f'<td{class_str}{style_str}>'
    if val > 0: return f'{base_td}<span class="yoy-up">▲ {val:.1f}{unit}</span></td>'
    elif val < 0: return f'{base_td}<span class="yoy-down">▼ {abs(val):.1f}{unit}</span></td>'
    else: return f'<td{class_str}{style_str}><span class="yoy-dash">-</span></td>'

def get_dash_td(bg_color="", bg_class=""):
    class_str = f' class="{bg_class}"' if bg_class else ''
    style_str = f' style="background-color:{bg_color} !important; text-align:center !important;"' if bg_color and not bg_class else ' style="text-align:center !important;"'
    return f'<td{class_str}{style_str}><span class="yoy-dash">-</span></td>'

def get_dynamic_date_ranges_34(df_iss):
    if df_iss is None or df_iss.empty: return issue_range_str, dep_range_str
    m_col = find_column_by_candidates(df_iss.columns, ['출발월', 'tripmonth', 'travelmonth'])
    dep_str = f"{sorted([str(x).strip() for x in df_iss[m_col].dropna().unique() if str(x).strip() != 'nan'])[0]} ~ {sorted([str(x).strip() for x in df_iss[m_col].dropna().unique() if str(x).strip() != 'nan'])[-1]}" if m_col else dep_range_str
    w_col = find_column_by_candidates(df_iss.columns, ['발매주차', 'issueweek', 'purchaseweek'])
    iss_str = f"{sorted([str(x).strip() for x in df_iss[w_col].dropna().unique() if str(x).strip() != 'nan'])[0]} ~ {sorted([str(x).strip() for x in df_iss[w_col].dropna().unique() if str(x).strip() != 'nan'])[-1]}" if w_col else issue_range_str
    return iss_str, dep_str

# ==========================================
# GROUP 1: ✈ 3/4수송 대시보드
# ==========================================
if "3/4수송" in selected_group:
    dynamic_iss_str_34, dynamic_dep_str_34 = get_dynamic_date_ranges_34(df_iss_merged)
    last_updated_str_34 = get_34_last_updated_date()
    
    st.markdown(
        f'<div class="source-header-box">'
        f'<b>📌 출처: DDS & OAG 데이터 (3/4수송 대시보드)</b> &nbsp;|&nbsp; '
        f'<b>🗓 발매기간:</b> {dynamic_iss_str_34} (과거 5주) &nbsp;|&nbsp; '
        f'<b>✈ 출발기간:</b> {dynamic_dep_str_34} (향후 6개월) &nbsp;|&nbsp; '
        f'<b>🕒 데이터 최근 업데이트:</b> {last_updated_str_34}'
        f'</div>', 
        unsafe_allow_html=True
    )
    st.markdown("---")
    
    tab_34_1, tab_34_2, tab_34_3, tab_34_4 = st.tabs(["🎟️ 발매 M/S", "✈ 공급 M/S", "🏷 대리점,RBD별 발매현황", "👥 단체실적"])

    with tab_34_1:
        if df_iss_merged is None: 
            st.warning("❌ 3/4수송 데이터(cache_34_data.parquet)를 찾을 수 없습니다.")
            st.stop()
            
        merged_df = df_iss_merged.copy()
        
        route_col_target = find_column_by_candidates(merged_df.columns, ['노선', 'route'])
        if route_col_target and '노선_clean' not in merged_df.columns:
            merged_df['노선_clean'] = merged_df[route_col_target].astype(str).str.strip().str.upper()

        if '노선_clean' in merged_df.columns:
            merged_df = merged_df[merged_df['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER)]
        
        al_col_target = find_column_by_candidates(merged_df.columns, ['dominant', 'dominantmarketingairline', 'mktal', 'marketing', 'carrier', 'segmentoperator'])
        merged_df['AL_clean'] = merged_df[al_col_target].astype(str).str.strip().str.upper() if al_col_target and al_col_target in merged_df.columns else 'OTHER'

        region_col = find_column_by_candidates(merged_df.columns, ['일본권역', '권역', 'japanregion', 'region'])
        bound_raw_col = find_column_by_candidates(merged_df.columns, ['bound', '방향', '바운드'])
        week_col = find_column_by_candidates(merged_df.columns, ['발매주차', 'issueweek', 'purchaseweek'])
        month_col = find_column_by_candidates(merged_df.columns, ['출발월', 'tripmonth', 'travelmonth'])
        bound_col = find_column_by_candidates(merged_df.columns, ['수송', 'bound'])

        with st.expander("🔍 **발매 대시보드 피벗 슬라이서 필터 설정**", expanded=True):
            apply_weight_toggle = st.toggle("⚖️ 가중치 적용 M/S 산출", value=True, key="main_wt_toggle_fixed")
            
            temp_df_34 = merged_df.copy()
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            
            opts_rgn = sorted([str(x).strip() for x in temp_df_34[region_col].dropna().unique() if str(x).strip() != 'nan']) if region_col and region_col in temp_df_34.columns else []
            sel_region_list = render_multiselect_box(f_col1, "1. 일본권역", opts_rgn, "slicer_region_multi")
            if sel_region_list and region_col: temp_df_34 = temp_df_34[temp_df_34[region_col].astype(str).str.strip().isin(sel_region_list)]

            opts_route = sorted([str(x).strip() for x in temp_df_34['노선_clean'].dropna().unique() if str(x).strip() != 'nan'])
            sel_route_list = render_multiselect_box(f_col2, "2. KE취항노선", opts_route, "slicer_route_multi")
            if sel_route_list: temp_df_34 = temp_df_34[temp_df_34['노선_clean'].isin(sel_route_list)]

            opts_week = sorted([str(x).strip() for x in temp_df_34[week_col].dropna().unique() if str(x).strip() != 'nan']) if week_col and week_col in temp_df_34.columns else []
            sel_week_list = render_multiselect_box(f_col3, "3. 발매 주차", opts_week, "slicer_week_multi")
            if sel_week_list and week_col: temp_df_34 = temp_df_34[temp_df_34[week_col].astype(str).str.strip().isin(sel_week_list)]

            raw_month_34 = [str(x).strip() for x in temp_df_34[month_col].dropna().unique() if str(x).strip() != 'nan'] if month_col and month_col in temp_df_34.columns else []
            opts_month = sort_month_options(raw_month_34, reverse=True)
            sel_month_list = render_multiselect_box(f_col4, "4. 출발 월", opts_month, "slicer_month_multi")
            if sel_month_list and month_col: temp_df_34 = temp_df_34[temp_df_34[month_col].astype(str).str.strip().isin(sel_month_list)]

            f_col5, f_col6, f_col7, f_col8 = st.columns(4)
            
            opts_bound = sorted([str(x).strip() for x in temp_df_34[bound_col].dropna().unique() if str(x).strip() != 'nan']) if bound_col and bound_col in temp_df_34.columns else []
            sel_bound_list = render_multiselect_box(f_col5, "5. 수송 구분", opts_bound, "slicer_bound_multi")
            if sel_bound_list and bound_col: temp_df_34 = temp_df_34[temp_df_34[bound_col].astype(str).str.strip().isin(sel_bound_list)]

            opts_bound_raw = sorted([str(x).strip() for x in temp_df_34[bound_raw_col].dropna().unique() if str(x).strip() != 'nan']) if bound_raw_col and bound_raw_col in temp_df_34.columns else []
            sel_bound_raw_list = render_multiselect_box(f_col6, "6. Bound", opts_bound_raw, "slicer_bound_raw_multi")
            if sel_bound_raw_list and bound_raw_col: temp_df_34 = temp_df_34[temp_df_34[bound_raw_col].astype(str).str.strip().isin(sel_bound_raw_list)]

            tt_col = find_column_by_candidates(temp_df_34.columns, ['tickettype', 'triptype'])
            opts_tt = sorted([str(x).strip() for x in temp_df_34[tt_col].dropna().unique() if str(x).strip() != 'nan']) if tt_col and tt_col in temp_df_34.columns else []
            sel_tt_list = render_multiselect_box(f_col7, "7. Trip Type", opts_tt, "slicer_tt_multi")
            if sel_tt_list and tt_col: temp_df_34 = temp_df_34[temp_df_34[tt_col].astype(str).str.strip().isin(sel_tt_list)]

            opts_al = sorted([str(x).strip() for x in temp_df_34['AL_clean'].dropna().unique() if str(x).strip() != 'nan'])
            opts_al = ['KE'] + [x for x in opts_al if x != 'KE'] if 'KE' in opts_al else opts_al
            sel_al_list = render_multiselect_box(f_col8, "8. 항공사", opts_al, "slicer_al_multi")
            if sel_al_list: temp_df_34 = temp_df_34[temp_df_34['AL_clean'].isin(sel_al_list)]

        filtered_df = temp_df_34.copy()

        if apply_weight_toggle and 'Calc_Weighted_Value' in filtered_df.columns:
            val_col = 'Calc_Weighted_Value'
        else:
            val_col = 'Value'

        al_wt_sum = filtered_df.groupby('AL_clean', observed=False)[val_col].sum()
        total_pax = al_wt_sum.sum()
        ke_pax = al_wt_sum.get('KE', 0)
        ke_ms = (ke_pax / total_pax * 100) if total_pax > 0 else 0
        al_ms_normalized = (al_wt_sum / total_pax * 100) if total_pax > 0 else pd.Series(0.0, index=al_wt_sum.index)

        top_al, top_ms = "-", 0.0
        if not filtered_df.empty and total_pax > 0:
            top_al, top_ms = str(al_ms_normalized.idxmax()), float(al_ms_normalized.max())

        top_route = str(filtered_df.groupby('노선_clean', observed=False)[val_col].sum().idxmax()) if not filtered_df.empty and total_pax > 0 else "-"
        status_wt_label = " (가중치 보정)" if apply_weight_toggle else " (Raw)"

        tab1, tab2, tab3 = st.tabs(["📈 시각화 분석 차트", "📊 M/S 피벗 테이블", "🔒 Raw Data View"])
        with tab1:
            if not filtered_df.empty:
                st.markdown('<div class="unified-sub-header">1. 항공사별 M/S 점유비</div>', unsafe_allow_html=True)
                c1, c2 = st.columns([1.6, 1])
                with c1:
                    pie_al = al_ms_normalized.reset_index()
                    pie_al.columns = ['AL_clean', 'Display_MS']
                    values_for_pie = pie_al['Display_MS']
                    text_labels_pie = [f"<b>{v:.1f}%</b>" for v in pie_al['Display_MS']]
                    
                    labels_list = [f"<b>{x}</b>" if str(x) == 'KE' else str(x) for x in pie_al['AL_clean']]
                    pull_list = [0.08 if str(x) == 'KE' else 0 for x in pie_al['AL_clean']]
                    colors_list = [build_airline_color_map(opts_al).get(al, '#94a3b8') for al in pie_al['AL_clean']]

                    fig1 = go.Figure(data=[go.Pie(labels=labels_list, values=values_for_pie, text=text_labels_pie, textinfo='label+text', hole=0.4, pull=pull_list, marker=dict(colors=colors_list), textposition='inside')])
                    apply_bottom_legend(fig1)
                    st.plotly_chart(fig1, width="stretch")

                with c2:
                    st.markdown("##### 📌 발매 실적 핵심 요약 (Summary)")
                    st.markdown(f'<div class="metric-card"><div class="metric-title">총 발매 실적{status_wt_label}</div><div class="metric-value">{total_pax:,.0f}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-card-ke"><div class="metric-title" style="color:#16a34a; font-weight:bold;">✈️ <span class="ke-highlight">KE (대한항공) M/S</span></div><div class="metric-value" style="color:#16a34a;"><b>{ke_pax:,.0f} ({ke_ms:.1f}%)</b></div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-card"><div class="metric-title">1위 항공사 (M/S)</div><div class="metric-value" style="color:#1d4ed8;"><b>{top_al}</b> ({top_ms:.1f}%)</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-card"><div class="metric-title">최대 실적 노선</div><div class="metric-value" style="color:#047857;">{top_route}</div></div>', unsafe_allow_html=True)

                st.markdown("---")

                if week_col and week_col in merged_df.columns:
                    st.markdown('<div class="unified-sub-header">2. 발매 주차별 주요 항공사 M/S 점유비 추이 (%)</div>', unsafe_allow_html=True)
                    df_no_week = filtered_df
                    if not df_no_week.empty:
                        week_al_grp = df_no_week.groupby([week_col, 'AL_clean'], observed=False)[val_col].sum().reset_index()
                        week_tot = df_no_week.groupby(week_col, observed=False)[val_col].sum().reset_index()
                        week_merged = pd.merge(week_al_grp, week_tot, on=week_col, suffixes=('', '_Mkt'))
                        week_merged['MS_Percent'] = np.where(week_merged[f'{val_col}_Mkt'] > 0, (week_merged[val_col] / week_merged[f'{val_col}_Mkt']) * 100, 0)
                        
                        al_totals_wk = df_no_week.groupby('AL_clean', observed=False)[val_col].sum()
                        top_al_in_week = al_totals_wk[al_totals_wk > 0].sort_values(ascending=False).index.tolist()
                        
                        top_al_week_display = []
                        if 'KE' in top_al_in_week: top_al_week_display.append('KE')
                        top_al_week_display += [al for al in top_al_in_week if al != 'KE'][:5]
                        
                        week_merged_top = week_merged[week_merged['AL_clean'].isin(top_al_week_display)].copy()

                        fig_week_ms = go.Figure()
                        color_map_al = build_airline_color_map(opts_al)

                        for al_code in top_al_week_display:
                            al_data = week_merged_top[week_merged_top['AL_clean'] == al_code]
                            if al_data.empty: continue
                            is_ke = (al_code == 'KE')
                            line_style = dict(color='#16a34a', width=4) if is_ke else dict(color=color_map_al.get(al_code, '#94a3b8'), dash='dot', width=1.5)
                            marker_style = dict(size=9, symbol='circle') if is_ke else dict(size=5)
                            mode_setting = 'lines+markers+text' if is_ke else 'lines+markers'
                            text_labels = [f"<b>{v:.1f}%</b>" for v in al_data['MS_Percent']] if is_ke else None

                            fig_week_ms.add_trace(go.Scatter(
                                x=al_data[week_col], y=al_data['MS_Percent'], mode=mode_setting,
                                name=f"★ KE (대한항공)" if is_ke else al_code, line=line_style, marker=marker_style, text=text_labels,
                                textposition="top center", hovertemplate=f"<b>항공사: {al_code}</b><br>발매주차: %{{x}}<br>M/S 점유율: %{{y:.1f}}%<extra></extra>"
                            ))
                        if not week_merged_top.empty:
                            fig_week_ms.update_layout(yaxis_title="Market Share (%)", xaxis=dict(categoryorder='array', categoryarray=opts_week), yaxis=dict(range=[0, max(week_merged_top['MS_Percent'].max() * 1.25, 15)]), height=450)
                        apply_bottom_legend(fig_week_ms)
                        st.plotly_chart(fig_week_ms, width="stretch")

                st.markdown("---")

                if month_col and month_col in merged_df.columns:
                    st.markdown('<div class="unified-sub-header">3. 출발기간별 주요 항공사 M/S 점유비 추이</div>', unsafe_allow_html=True)
                    df_dep_al = filtered_df
                    if not df_dep_al.empty:
                        dep_al_grp = df_dep_al.groupby([month_col, 'AL_clean'], observed=False)[val_col].sum().reset_index()
                        dep_mkt_tot = df_dep_al.groupby(month_col, observed=False)[val_col].sum().reset_index()
                        dep_al_grp[month_col] = dep_al_grp[month_col].astype(str)
                        dep_mkt_tot[month_col] = dep_mkt_tot[month_col].astype(str)
                        dep_merged = pd.merge(dep_al_grp, dep_mkt_tot, on=month_col, suffixes=('', '_Mkt'))
                        dep_merged[val_col] = dep_merged[val_col].fillna(0)
                        dep_merged['MS_Percent'] = np.where(dep_merged[f'{val_col}_Mkt'] > 0, (dep_merged[val_col] / dep_merged[f'{val_col}_Mkt']) * 100, 0)
                        
                        al_totals_mo = df_dep_al.groupby('AL_clean', observed=False)[val_col].sum()
                        top_al_in_dep = al_totals_mo[al_totals_mo > 0].sort_values(ascending=False).index.tolist()
                        
                        top_al_display = []
                        if 'KE' in top_al_in_dep: top_al_display.append('KE')
                        top_al_display += [al for al in top_al_in_dep if al != 'KE'][:5]
                        
                        dep_merged_top = dep_merged[dep_merged['AL_clean'].isin(top_al_display)].copy()

                        fig_ke_dep = go.Figure()
                        for al_code in top_al_display:
                            al_data = dep_merged_top[dep_merged_top['AL_clean'] == al_code]
                            if al_data.empty: continue
                            is_ke = (al_code == 'KE')
                            line_style = dict(color='#16a34a', width=3.5) if is_ke else dict(color=build_airline_color_map(opts_al).get(al_code, '#94a3b8'), dash='dot', width=1.5)
                            marker_style = dict(size=8, symbol='circle') if is_ke else dict(size=4)
                            mode_setting = 'lines+markers+text' if is_ke else 'lines+markers'
                            text_labels = [f"<b>{v:.1f}%</b>" for v in al_data['MS_Percent']] if is_ke else None
                            fig_ke_dep.add_trace(go.Scatter(
                                x=al_data[month_col], y=al_data['MS_Percent'], mode=mode_setting,
                                name=f"★ KE (대한항공)" if is_ke else al_code, line=line_style, marker=marker_style, text=text_labels,
                                textposition="top center", hovertemplate=f"<b>항공사: {al_code}</b><br>출발월: %{{x}}<br>점유율: %{{y:.1f}}%<extra></extra>"
                            ))
                        if not dep_merged_top.empty:
                            fig_ke_dep.update_layout(yaxis_title="Market Share (%)", xaxis=dict(categoryorder='array', categoryarray=opts_month), yaxis=dict(range=[0, max(dep_merged_top['MS_Percent'].max() * 1.25, 15)]), height=420)
                        apply_bottom_legend(fig_ke_dep)
                        st.plotly_chart(fig_ke_dep, width="stretch")

                st.markdown("---")
                
                c3, c4 = st.columns(2)
                ke_only_df = filtered_df[filtered_df['AL_clean'] == 'KE']
                with c3:
                    if bound_col and bound_col in ke_only_df.columns:
                        st.markdown('<div class="unified-sub-header">4. 수송 구분별 점유비 (KE 한정)</div>', unsafe_allow_html=True)
                        bound_pie_df = ke_only_df.groupby(bound_col, observed=False)[val_col].sum().reset_index()
                        fig3 = px.pie(bound_pie_df, values=val_col, names=bound_col, hole=0.4)
                        fig3.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>구분: %{label}</b><br>실적: %{value:,.0f}<br>점유율: %{percent:.1%}<extra></extra>")
                        apply_bottom_legend(fig3)
                        st.plotly_chart(fig3, width="stretch")
                with c4:
                    tt_col = find_column_by_candidates(merged_df.columns, ['tickettype', 'triptype'])
                    if tt_col and tt_col in ke_only_df.columns:
                        st.markdown('<div class="unified-sub-header">5. Trip Type별 점유비 (KE 한정)</div>', unsafe_allow_html=True)
                        tt_pie_df = ke_only_df.groupby(tt_col, observed=False)[val_col].sum().reset_index()
                        fig4 = px.pie(tt_pie_df, values=val_col, names=tt_col, hole=0.4)
                        fig4.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>Trip Type: %{label}</b><br>실적: %{value:,.0f}<br>점유율: %{percent:.1%}<extra></extra>")
                        apply_bottom_legend(fig4)
                        st.plotly_chart(fig4, width="stretch")

        with tab2:
            st.markdown("##### 📌 주차별 및 노선별 발매 M/S 매트릭스")
            t1, t2 = st.columns([1.1, 1])
            with t1:
                if week_col and week_col in filtered_df.columns:
                    piv_w = filtered_df.pivot_table(index='AL_clean', columns=week_col, values=val_col, aggfunc='sum', fill_value=0, observed=False)
                    piv_w = piv_w[piv_w.sum(axis=1) > 0] 
                    piv_w_ms = piv_w.divide(piv_w.sum(axis=0), axis=1) * 100
                    al_sorted = ['KE'] + [x for x in piv_w_ms.index if x != 'KE'] if 'KE' in piv_w_ms.index else piv_w_ms.index
                    piv_w_ms = piv_w_ms.loc[al_sorted].head(100)
                    piv_w_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead><tr><th class="header-main" style="width:100px;">AL_clean</th>'
                    for col_wk in piv_w_ms.columns: piv_w_html += f'<th class="header-main">{col_wk}</th>'
                    piv_w_html += '</tr></thead><tbody>'
                    for al_idx, row_item in piv_w_ms.iterrows():
                        is_ke_r = (str(al_idx).upper() == 'KE')
                        td_style = ' style="background-color: #ffffff !important;"'
                        k_span = '<span class="txt-ke-bold">' if is_ke_r else '<span>'
                        piv_w_html += f'<tr><td{td_style}>{k_span}{al_idx}</span></td>'
                        for val_ms in row_item: piv_w_html += f'<td{td_style}>{k_span}{val_ms:.1f}%</span></td>'
                        piv_w_html += '</tr>'
                    piv_w_html += '</tbody></table></div>'
                    st.markdown(piv_w_html, unsafe_allow_html=True)
            
            with t2:
                piv_r = filtered_df.pivot_table(index='노선_clean', columns='AL_clean', values=val_col, aggfunc='sum', fill_value=0, observed=False)
                piv_r = piv_r[piv_r.sum(axis=1) > 0] 
                piv_r = piv_r.loc[:, piv_r.sum(axis=0) > 0] 
                
                if not piv_r.empty:
                    cols_ke = ['KE'] + [x for x in piv_r.columns if x != 'KE'] if 'KE' in piv_r.columns else piv_r.columns
                    piv_r_ms = piv_r[cols_ke].divide(piv_r.sum(axis=1), axis=0) * 100
                    piv_r_ms = piv_r_ms.head(100)
                    
                    piv_r_html = '<div class="custom-piv-container" style="overflow-x: auto;"><table class="custom-piv-table" style="width: auto; min-width: 100%;"><thead><tr><th class="header-main" style="min-width: 100px; white-space: nowrap;">노선</th>'
                    for col_al in piv_r_ms.columns:
                        is_ke_c = (str(col_al).upper() == 'KE')
                        th_style = ' style="background-color: #9fc5e8 !important; color: #0f172a !important; min-width: 70px; white-space: nowrap;"' if is_ke_c else ' style="min-width: 70px; white-space: nowrap;"'
                        k_span = '<span style="color:#0f172a !important; font-weight:bold;">' if is_ke_c else '<span>'
                        piv_r_html += f'<th class="header-main"{th_style}>{k_span}{col_al}</span></th>'
                    piv_r_html += '</tr></thead><tbody>'
                    
                    for route_idx, row_item in piv_r_ms.iterrows():
                        piv_r_html += f'<tr><td style="font-weight:700; white-space: nowrap;">{route_idx}</td>'
                        for al_col_name, val_ms in row_item.items():
                            is_ke_c = (str(al_col_name).upper() == 'KE')
                            td_style = ' style="background-color: #ffffff !important; white-space: nowrap; padding: 8px 12px;"'
                            k_span = '<span class="txt-ke-bold">' if is_ke_c else '<span>'
                            piv_r_html += f'<td{td_style}>{k_span}{val_ms:.1f}%</span></td>'
                        piv_r_html += '</tr>'
                    piv_r_html += '</tbody></table></div>'
                    st.markdown(piv_r_html, unsafe_allow_html=True)
                else:
                    st.info("💡 선택 조건에 해당하는 실적 데이터가 없습니다.")

        with tab3:
            st.subheader("🔒 관리자 전용 Raw Data 조회 및 다운로드")
            admin_pw = st.text_input("🔑 관리자 비밀번호를 입력하세요:", type="password", key="admin_pw_fixed")
            if admin_pw == "1234":
                csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 필터링된 발매 Raw Data (CSV) 전체 다운로드", data=csv_data, file_name=f"Ticketing_Raw_Data_{datetime.date.today().strftime('%Y%m%d')}.csv", mime="text/csv")
                st.dataframe(filtered_df.head(100), width="stretch")
            else: st.info("ℹ️️ 관리자 비밀번호 입력 시 이용할 수 있습니다.")

    # 공급 M/S 탭
    with tab_34_2:
        df_sup = df_sup_raw.copy() if df_sup_raw is not None else None
        if df_sup is not None:
            df_sup.columns = [str(c).strip() for c in df_sup.columns]
            al_col = find_column_by_candidates(df_sup.columns, ['opairline', 'mktal', 'airline', 'carrier', '항공사'])
            df_sup['Airline'] = df_sup[al_col] if al_col else 'Unknown'
            
            sup_route_col = find_column_by_candidates(df_sup.columns, ['노선', 'route'])
            df_sup['노선_clean'] = df_sup[sup_route_col].astype(str).str.strip() if sup_route_col else ""

            df_sup['KE_취항여부'] = np.where(df_sup['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER), '취항', '미취항')
            df_sup['출발공항'] = df_sup['노선_clean'].apply(lambda x: KOREA_APO_MAP.get(str(x).split('/')[0].strip().upper(), '기타') if '/' in str(x) else '기타')
            df_sup['도착공항'] = df_sup['노선_clean'].apply(lambda x: str(x).split('/')[1].strip().upper() if '/' in str(x) else str(x).strip().upper())
            df_sup['Seats_num'] = pd.to_numeric(df_sup['Seats'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if 'Seats' in df_sup.columns else 0
            df_sup['Flights_num'] = pd.to_numeric(df_sup['Flights'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if 'Flights' in df_sup.columns else 1
            sup_month_col = find_column_by_candidates(df_sup.columns, ['출발월', 'travelmonth', 'depmonth'])

            temp_sup = df_sup.copy()
            st.markdown('<div class="unified-sub-header">🔍 공급 대시보드 필터 설정</div>', unsafe_allow_html=True)
            metric_mode = st.radio("📊 분석 공급 지표 선택:", options=["공급석 (Seats)", "운항 편수 (Flight Frequencies)"], horizontal=True)
            sf_col1, sf_col2, sf_col3, sf_col4, sf_col5 = st.columns(5)
            
            opts_ke_serv = sorted([str(x) for x in temp_sup['KE_취항여부'].dropna().unique()])
            sel_sup_ke_serv_list = render_multiselect_box(sf_col1, "1. KE 취항여부", opts_ke_serv, "slicer_sup_ke_serv_multi")
            if sel_sup_ke_serv_list: temp_sup = temp_sup[temp_sup['KE_취항여부'].isin(sel_sup_ke_serv_list)]

            opts_ori = sorted([str(x) for x in temp_sup['출발공항'].dropna().unique()])
            sel_sup_origin_list = render_multiselect_box(sf_col2, "2. 출발 공항", opts_ori, "slicer_sup_origin_multi")
            if sel_sup_origin_list: temp_sup = temp_sup[temp_sup['출발공항'].isin(sel_sup_origin_list)]

            opts_dest = sorted([str(x) for x in temp_sup['도착공항'].dropna().unique()])
            sel_sup_dest_list = render_multiselect_box(sf_col3, "3. 도착 공항", opts_dest, "slicer_sup_dest_multi")
            if sel_sup_dest_list: temp_sup = temp_sup[temp_sup['도착공항'].isin(sel_sup_dest_list)]

            raw_sup_m = [str(x) for x in temp_sup[sup_month_col].dropna().unique() if '1900' not in str(x) and str(x).strip() != 'nan'] if sup_month_col and sup_month_col in temp_sup.columns else []
            opts_sup_m = sort_month_options(raw_sup_m, reverse=True)
            sel_sup_month_list = render_multiselect_box(sf_col4, "4. 출발 월", opts_sup_m, "slicer_month_sup_multi")
            if sel_sup_month_list and sup_month_col: temp_sup = temp_sup[temp_sup[sup_month_col].isin(sel_sup_month_list)]

            opts_sup_al = sorted([str(x) for x in temp_sup['Airline'].dropna().unique()])
            opts_sup_al = ['KE'] + [x for x in opts_sup_al if x != 'KE'] if 'KE' in opts_sup_al else opts_sup_al
            sel_sup_al_list = render_multiselect_box(sf_col5, "5. 항공사", opts_sup_al, "slicer_al_sup_multi")
            if sel_sup_al_list: temp_sup = temp_sup[temp_sup['Airline'].isin(sel_sup_al_list)]

            filtered_sup = temp_sup
            st.markdown("---")
            val_col_sup = 'Seats_num' if 'Seats' in metric_mode else 'Flights_num'
            
            if not filtered_sup.empty and sup_month_col and sup_month_col in filtered_sup.columns:
                st.markdown('<div class="unified-sub-header">1. 출발기간별 주요 항공사 공급 M/S 점유비 추이</div>', unsafe_allow_html=True)
                sup_al_grp = filtered_sup.groupby([sup_month_col, 'Airline'], observed=False)[val_col_sup].sum().reset_index()
                sup_mkt_tot = filtered_sup.groupby(sup_month_col, observed=False)[val_col_sup].sum().reset_index()
                
                sup_merged = pd.merge(sup_al_grp, sup_mkt_tot, on=sup_month_col, suffixes=('', '_Mkt'))
                sup_merged['MS_Percent'] = np.where(sup_merged[f'{val_col_sup}_Mkt'] > 0, (sup_merged[val_col_sup] / sup_merged[f'{val_col_sup}_Mkt']) * 100, 0)
                
                al_sup_totals = filtered_sup.groupby('Airline', observed=False)[val_col_sup].sum()
                valid_al_sup = al_sup_totals[al_sup_totals > 0].sort_values(ascending=False).index.tolist()
                
                top_sup_display = []
                if 'KE' in valid_al_sup: top_sup_display.append('KE')
                top_sup_display += [al for al in valid_al_sup if al != 'KE'][:5]
                
                sup_merged_top = sup_merged[sup_merged['Airline'].isin(top_sup_display)].copy()

                fig_sup_line = go.Figure()
                color_map_sup = build_airline_color_map(opts_sup_al)

                for al_code in top_sup_display:
                    al_data = sup_merged_top[sup_merged_top['Airline'] == al_code]
                    if al_data.empty: continue
                    is_ke = (al_code == 'KE')
                    line_style = dict(color='#16a34a', width=3.5) if is_ke else dict(color=color_map_sup.get(al_code, '#94a3b8'), dash='dot', width=1.5)
                    marker_style = dict(size=8, symbol='circle') if is_ke else dict(size=4)
                    mode_setting = 'lines+markers+text' if is_ke else 'lines+markers'
                    text_labels = [f"<b>{v:.1f}%</b>" for v in al_data['MS_Percent']] if is_ke else None
                    
                    fig_sup_line.add_trace(go.Scatter(
                        x=al_data[sup_month_col], y=al_data['MS_Percent'], mode=mode_setting,
                        name=f"★ KE (대한항공)" if is_ke else al_code, line=line_style, marker=marker_style, text=text_labels,
                        textposition="top center", hovertemplate=f"<b>항공사: {al_code}</b><br>출발월: %{{x}}<br>공급 M/S: %{{y:.1f}}%<extra></extra>"
                    ))
                if not sup_merged_top.empty:
                    fig_sup_line.update_layout(yaxis_title="Supply Market Share (%)", xaxis=dict(categoryorder='array', categoryarray=opts_sup_m), yaxis=dict(range=[0, max(sup_merged_top['MS_Percent'].max() * 1.25, 15)]), height=420)
                apply_bottom_legend(fig_sup_line)
                st.plotly_chart(fig_sup_line, width="stretch")
                
                st.markdown("---")
                st.markdown('<div class="unified-sub-header">2. 출발기간별 주요 항공사 공급 M/S 피벗 테이블</div>', unsafe_allow_html=True)
                
                piv_sup = filtered_sup.pivot_table(index='Airline', columns=sup_month_col, values=val_col_sup, aggfunc='sum', fill_value=0, observed=False)
                piv_sup['총합계'] = piv_sup.sum(axis=1)
                piv_sup = piv_sup[piv_sup['총합계'] > 0] 
                
                piv_sup_ms = piv_sup.divide(piv_sup.sum(axis=0).replace(0, 1), axis=1) * 100
                al_sup_sorted = ['KE'] + [x for x in piv_sup_ms.index if x != 'KE'] if 'KE' in piv_sup_ms.index else piv_sup_ms.index
                piv_sup_ms = piv_sup_ms.loc[al_sup_sorted].head(100)
                
                sup_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead><tr><th class="header-main" style="width:100px;">항공사</th>'
                for col_m in piv_sup_ms.columns: sup_html += f'<th class="header-main">{col_m}</th>'
                sup_html += '</tr></thead><tbody>'
                for al_idx, row_item in piv_sup_ms.iterrows():
                    is_ke_r = (str(al_idx).upper() == 'KE')
                    td_style = ' style="background-color: #ffffff !important;"'
                    k_span = '<span class="txt-ke-bold">' if is_ke_r else '<span>'
                    sup_html += f'<tr><td{td_style}>{k_span}{al_idx}</span></td>'
                    for val_ms in row_item: sup_html += f'<td{td_style}>{k_span}{val_ms:.1f}%</span></td>'
                    sup_html += '</tr>'
                sup_html += '</tbody></table></div>'
                st.markdown(sup_html, unsafe_allow_html=True)

    # 대리점/RBD 탭
    with tab_34_3:
        RBD_HIERARCHY_LOCAL = {
            'KE': list('YBMSHEKLUQTX'), 'OZ': list('YBMHEQKSVWTLX'),
            '7C': list('YBKNQMTWORXSZLHEFVGPJ'), 'LJ': list('YWDEHKLQBNMXPSVZARIOT'),
            'TW': list('YWZVSPONMLKHDBAJQET'), 'BX': list('YBRMKEUDOIVJHXGWQN'),
            'RS': list('YBMHEQKSOLWTRUIXAVGNDPFJC'), 'JL': list('WREYBHKMLVSOGQNPZ'),
            'NH': list('ENYBMUHQVWSLK'), 'YP': list('PRZYBMHELQNSAFKVOGWX'),
            'ZE': list('PFAJCIROYBMSHEKLQNTVWGX'), 'WE': list('ADIZOYBMHEUQNTVW')
        }
        
        if df_iss_merged is not None:
            df_agency = df_iss_merged.copy()
            agency_route_col = find_column_by_candidates(df_agency.columns, ['노선', 'route'])
            df_agency['노선_clean'] = df_agency[agency_route_col].astype(str).str.strip() if agency_route_col else ""
            df_agency = df_agency[df_agency['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER)]

            week_col_a = find_column_by_candidates(df_agency.columns, ['발매주차', 'issueweek', 'purchaseweek'])
            month_col_a = find_column_by_candidates(df_agency.columns, ['출발월', 'tripmonth', 'travelmonth'])
            bound_col_a = find_column_by_candidates(df_agency.columns, ['수송', 'bound'])

            temp_ag = df_agency.copy()
            with st.expander("🔍 **대리점 & RBD 분석 피벗 슬라이서 필터 설정**", expanded=True):
                ac1, ac2, ac3 = st.columns(3)
                opts_r_ag = sorted([str(x) for x in temp_ag['노선_clean'].dropna().unique()])
                sel_route_ag_list = render_multiselect_box(ac1, "1. 노선", opts_r_ag, "slicer_route_ag_multi")
                if sel_route_ag_list: temp_ag = temp_ag[temp_ag['노선_clean'].isin(sel_route_ag_list)]

                raw_m_ag = [str(x) for x in temp_ag[month_col_a].dropna().unique()] if month_col_a and month_col_a in temp_ag.columns else []
                opts_m_ag = sort_month_options(raw_m_ag, reverse=True)
                sel_month_ag_list = render_multiselect_box(ac2, "2. 출발 월", opts_m_ag, "slicer_month_ag_multi")
                if sel_month_ag_list and month_col_a: temp_ag = temp_ag[temp_ag[month_col_a].astype(str).isin(sel_month_ag_list)]

                opts_b_ag = sorted([str(x) for x in temp_ag[bound_col_a].dropna().unique()]) if bound_col_a and bound_col_a in temp_ag.columns else []
                sel_bound_ag_list = render_multiselect_box(ac3, "3. 수송 구분", opts_b_ag, "slicer_bound_ag_multi")
                if sel_bound_ag_list and bound_col_a: temp_ag = temp_ag[temp_ag[bound_col_a].astype(str).isin(sel_bound_ag_list)]

                ac4, ac5 = st.columns(2)
                tt_col_ag = find_column_by_candidates(temp_ag.columns, ['tickettype', 'triptype'])
                opts_tt_ag = sorted([str(x) for x in temp_ag[tt_col_ag].dropna().unique()]) if tt_col_ag and tt_col_ag in temp_ag.columns else []
                sel_tt_ag_list = render_multiselect_box(ac4, "4. TRIP TYPE", opts_tt_ag, "slicer_tt_ag_multi")
                if sel_tt_ag_list and tt_col_ag: temp_ag = temp_ag[temp_ag[tt_col_ag].astype(str).isin(sel_tt_ag_list)]

                al_col_ag = find_column_by_candidates(temp_ag.columns, ['dominant', 'dominantmarketingairline', 'mktal', 'marketing', 'carrier', 'segmentoperator'])
                opts_al_ag = sorted([str(x) for x in temp_ag[al_col_ag].dropna().unique()]) if al_col_ag and al_col_ag in temp_ag.columns else []
                opts_al_ag = ['KE'] + [x for x in opts_al_ag if x != 'KE'] if 'KE' in opts_al_ag else opts_al_ag
                sel_al_ag_list = render_multiselect_box(ac5, "5. 항공사", opts_al_ag, "slicer_al_ag_multi")
                if sel_al_ag_list and al_col_ag: temp_ag = temp_ag[temp_ag[al_col_ag].astype(str).isin(sel_al_ag_list)]

            df_ag_filtered = temp_ag
            open_attr = "open" if st.toggle("📂 전체 항목 펼쳐보기", value=True, key="expand_toggle_all_key_fixed") else ""

            sub_tab_rbd, sub_tab_agency = st.tabs(["📊 RBD별 판매현황", "🏢 대리점별 판매현황 (상위 20개 대리점)"])

            with sub_tab_rbd:
                rbd_col_ag = find_column_by_candidates(df_ag_filtered.columns, ['rbkd', 'rbd', 'bookingclass'])
                val_col_ag = 'Value'
                df_ag_filtered['Value'] = pd.to_numeric(df_ag_filtered[val_col_ag].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if val_col_ag in df_ag_filtered.columns else 0.0

                if not df_ag_filtered.empty and rbd_col_ag and week_col_a and al_col_ag:
                    week_list = sorted([str(x) for x in df_ag_filtered[week_col_a].dropna().unique()], reverse=True)
                    ag_al_sum = df_ag_filtered.groupby(al_col_ag, observed=False)['Value'].sum().sort_values(ascending=False)
                    ag_al_list = ['KE'] + [str(x) for x in ag_al_sum.index if x != 'KE' and ag_al_sum[x] > 0]
                    sub_col_w = 80.0 / (len(week_list) + 1)

                    rbd_html = '<div class="custom-piv-container"><table class="custom-piv-table" style="table-layout:fixed; width:100%;"><thead><tr><th class="header-main" style="width:20%;">항공사 / RBD 클래스</th>'
                    for wk in week_list: rbd_html += f'<th class="header-main" style="width:{sub_col_w:.2f}%;">{wk}</th>'
                    rbd_html += f'<th class="header-main" style="width:{sub_col_w:.2f}%;">총합계</th></tr></thead><tbody>'

                    for al_code in ag_al_list:
                        al_sub = df_ag_filtered[df_ag_filtered[al_col_ag] == al_code]
                        al_tot_pax = al_sub['Value'].sum()
                        if al_tot_pax > 0:
                            piv_rbd = al_sub.pivot_table(index=rbd_col_ag, columns=week_col_a, values='Value', aggfunc='sum', fill_value=0, observed=False)
                            piv_rbd['총합계'] = piv_rbd.sum(axis=1)
                            piv_rbd = piv_rbd[piv_rbd['총합계'] > 0]

                            if not piv_rbd.empty:
                                if al_code in RBD_HIERARCHY_LOCAL:
                                    h_ord = RBD_HIERARCHY_LOCAL[al_code]
                                    e_rbds = piv_rbd.index.tolist()
                                    piv_rbd = piv_rbd.loc[[r for r in h_ord if r in e_rbds] + [r for r in e_rbds if r not in h_ord]]

                                rbd_html += f'<tr><td colspan="{len(week_list)+2}" style="padding:0; border:none;"><details class="rbd-details-group" {open_attr}><summary style="list-style:none !important; list-style-type:none !important;"><table style="width:100%; table-layout:fixed; border-collapse:collapse;"><tr class="row-summary-top-dark"><td style="width:20%; text-align:center; font-weight:800;">★ {al_code} 총계</td>'
                                for wk in week_list: rbd_html += f'<td style="width:{sub_col_w:.2f}%; text-align:center;">{al_sub[al_sub[week_col_a] == wk]["Value"].sum():,.0f}</td>'
                                rbd_html += f'<td style="width:{sub_col_w:.2f}%; text-align:center;">{al_tot_pax:,.0f}</td></tr></table></summary><table style="width:100%; table-layout:fixed; border-collapse:collapse;">'

                                for rbd_code, rbd_row in piv_rbd.iterrows():
                                    rbd_html += f'<tr class="rbd-child-row"><td style="width:20%; text-align:center; font-weight:700;">{rbd_code}</td>'
                                    for wk in week_list: rbd_html += f'<td style="width:{sub_col_w:.2f}%; text-align:center;">{rbd_row.get(wk, 0):,.0f}</td>'
                                    rbd_html += f'<td style="width:{sub_col_w:.2f}%; text-align:center; font-weight:700;">{rbd_row.get("총합계", 0):,.0f}</td></tr>'
                                rbd_html += '</table></details></td></tr>'
                    rbd_html += '</tbody></table></div>'
                    st.markdown(rbd_html, unsafe_allow_html=True)

            with sub_tab_agency:
                agency_col_target = find_column_by_candidates(df_ag_filtered.columns, ['agency', '대리점', '여행사'])
                if not df_ag_filtered.empty and agency_col_target and week_col_a and al_col_ag:
                    week_list_ag = sorted([str(x) for x in df_ag_filtered[week_col_a].dropna().unique()], reverse=True)
                    agency_totals = df_ag_filtered.groupby(agency_col_target, observed=False)['Value'].sum().sort_values(ascending=False)
                    top_20_agencies = [ag for ag in agency_totals.index if agency_totals[ag] > 0][:20]
                    sub_col_w_ag = 80.0 / (len(week_list_ag) + 1)

                    ag_html = '<div class="custom-piv-container"><table class="custom-piv-table" style="table-layout:fixed; width:100%;"><thead><tr><th class="header-main" style="width:20%;">대리점 / 항공사</th>'
                    for wk in week_list_ag: ag_html += f'<th class="header-main" style="width:{sub_col_w_ag:.2f}%;">{wk}</th>'
                    ag_html += f'<th class="header-main" style="width:{sub_col_w_ag:.2f}%;">총 판매량</th></tr></thead><tbody>'

                    for ag_name in top_20_agencies:
                        ag_sub = df_ag_filtered[df_ag_filtered[agency_col_target] == ag_name]
                        ag_tot_val = ag_sub['Value'].sum()
                        if ag_tot_val > 0:
                            ag_al_totals = ag_sub.groupby(al_col_ag, observed=False)['Value'].sum().sort_values(ascending=False)
                            piv_ag_sub = ag_sub.pivot_table(index=al_col_ag, columns=week_col_a, values='Value', aggfunc='sum', fill_value=0, observed=False)
                            piv_ag_sub['총합계'] = piv_ag_sub.sum(axis=1)
                            piv_ag_sub = piv_ag_sub.reindex([al for al in ag_al_totals.index if ag_al_totals[al] > 0]).dropna(how='all')

                            if not piv_ag_sub.empty:
                                ag_html += f'<tr><td colspan="{len(week_list_ag)+2}" style="padding:0; border:none;"><details class="rbd-details-group" {open_attr}><summary style="list-style:none !important; list-style-type:none !important;"><table style="width:100%; table-layout:fixed; border-collapse:collapse;"><tr class="row-summary-top-dark"><td style="width:20%; text-align:center; font-weight:800;">★ {ag_name} 총계</td>'
                                for wk in week_list_ag: ag_html += f'<td style="width:{sub_col_w_ag:.2f}%; text-align:center;">{ag_sub[ag_sub[week_col_a] == wk]["Value"].sum():,.0f}</td>'
                                ag_html += f'<td style="width:{sub_col_w_ag:.2f}%; text-align:center;">{ag_tot_val:,.0f}</td></tr></table></summary><table style="width:100%; table-layout:fixed; border-collapse:collapse;">'

                                for al_code, al_row in piv_ag_sub.iterrows():
                                    is_ke = (al_code == 'KE')
                                    cell_style = 'font-weight:700; color:#16a34a;' if is_ke else 'color:#475569;'
                                    ag_html += f'<tr class="rbd-child-row"><td style="width:20%; text-align:center; {cell_style}">{"★ KE" if is_ke else al_code}</td>'
                                    for wk in week_list_ag: ag_html += f'<td style="width:{sub_col_w_ag:.2f}%; text-align:center; {cell_style}">{al_row.get(wk, 0):,.0f}</td>'
                                    ag_html += f'<td style="width:{sub_col_w_ag:.2f}%; text-align:center; font-weight:700; {cell_style}">{al_row.get("총합계", 0):,.0f}</td></tr>'
                                ag_html += '</table></details></td></tr>'
                    ag_html += '</tbody></table></div>'
                    st.markdown(ag_html, unsafe_allow_html=True)

    # 단체실적 탭
    with tab_34_4:
        st.subheader("👥 발매 - 항공사별/대리점별 단체 발매 현황")
        if df_iss_merged is not None:
            df_grp_raw = df_iss_merged.copy()
            grp_route_col = find_column_by_candidates(df_grp_raw.columns, ['노선', 'route'])
            df_grp_raw['노선_clean'] = df_grp_raw[grp_route_col].astype(str).str.strip() if grp_route_col else ""
            df_grp_raw = df_grp_raw[df_grp_raw['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER)]

            g_m_col = find_column_by_candidates(df_grp_raw.columns, ['출발월', 'tripmonth', 'travelmonth'])
            g_b_col = find_column_by_candidates(df_grp_raw.columns, ['수송', 'bound'])

            temp_grp = df_grp_raw.copy()
            with st.expander("🔍 **단체 실적 분석 피벗 슬라이서 필터 설정**", expanded=True):
                gc1, gc2, gc3 = st.columns(3)
                opts_g_route = sorted([str(x) for x in temp_grp['노선_clean'].dropna().unique()])
                sel_g_route_list = render_multiselect_box(gc1, "1. 노선", opts_g_route, "slicer_g_route_multi")
                if sel_g_route_list: temp_grp = temp_grp[temp_grp['노선_clean'].isin(sel_g_route_list)]

                raw_g_m = [str(x) for x in temp_grp[g_m_col].dropna().unique()] if g_m_col and g_m_col in temp_grp.columns else []
                opts_g_m = sort_month_options(raw_g_m, reverse=True)
                sel_g_month_list = render_multiselect_box(gc2, "2. 출발 월", opts_g_m, "slicer_g_month_multi")
                if sel_g_month_list and g_m_col: temp_grp = temp_grp[temp_grp[g_m_col].astype(str).isin(sel_g_month_list)]

                opts_g_b = sorted([str(x) for x in temp_grp[g_b_col].dropna().unique()]) if g_b_col and g_b_col in temp_grp.columns else []
                sel_g_bound_list = render_multiselect_box(gc3, "3. 수송 구분", opts_g_b, "slicer_g_bound_multi")
                if sel_g_bound_list and g_b_col: temp_grp = temp_grp[temp_grp[g_b_col].astype(str).isin(sel_g_bound_list)]

                gc4, gc5 = st.columns(2)
                tt_g_col = find_column_by_candidates(temp_grp.columns, ['tickettype', 'triptype'])
                opts_g_tt = sorted([str(x) for x in temp_grp[tt_g_col].dropna().unique()]) if tt_g_col and tt_g_col in temp_grp.columns else []
                sel_g_tt_list = render_multiselect_box(gc4, "4. TRIP TYPE", opts_g_tt, "slicer_g_tt_multi")
                if sel_g_tt_list and tt_g_col: temp_grp = temp_grp[temp_grp[tt_g_col].astype(str).isin(sel_g_tt_list)]

                al_g_col = find_column_by_candidates(temp_grp.columns, ['dominant', 'dominantmarketingairline', 'mktal', 'marketing', 'carrier', 'segmentoperator'])
                opts_g_al = sorted([str(x) for x in temp_grp[al_g_col].dropna().unique()]) if al_g_col and al_g_col in temp_grp.columns else []
                opts_g_al = ['KE'] + [x for x in opts_g_al if x != 'KE'] if 'KE' in opts_g_al else opts_g_al
                sel_g_al_list = render_multiselect_box(gc5, "5. 항공사", opts_g_al, "slicer_g_al_multi")
                if sel_g_al_list and al_g_col: temp_grp = temp_grp[temp_grp[al_g_col].astype(str).isin(sel_g_al_list)]

            rbd_g_col = find_column_by_candidates(temp_grp.columns, ['rbkd', 'rbd', 'bookingclass'])
            ag_g_col = find_column_by_candidates(temp_grp.columns, ['agency', '대리점', '여행사'])

            if rbd_g_col and al_g_col and ag_g_col:
                is_grp_cond = (((temp_grp[al_g_col] == '7C') & (temp_grp[rbd_g_col] == 'V')) | ((temp_grp[al_g_col] != '7C') & (temp_grp[rbd_g_col] == 'G')))
                df_grp_filtered = temp_grp[is_grp_cond].copy()

                if not df_grp_filtered.empty:
                    val_g_col = 'Value'
                    df_grp_filtered['Value'] = pd.to_numeric(df_grp_filtered[val_g_col].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if val_g_col in df_grp_filtered.columns else 0.0

                    ag_sum_df = df_grp_filtered.groupby([al_g_col, ag_g_col], observed=False)['Value'].sum().reset_index()
                    al_totals = ag_sum_df.groupby(al_g_col, observed=False)['Value'].sum().sort_values(ascending=False)
                    al_sorted_list = ['KE'] + [str(x) for x in al_totals.index if x != 'KE' and al_totals[x] > 0]

                    for al_code in al_sorted_list:
                        al_sub = ag_sum_df[ag_sum_df[al_g_col] == al_code]
                        al_tot_val = al_sub['Value'].sum()
                        if al_tot_val > 0:
                            top_ag_sub = al_sub[al_sub['Value'] > 0].sort_values(by='Value', ascending=False).head(100).reset_index(drop=True)
                            if not top_ag_sub.empty:
                                top_ag_sub.index = range(1, len(top_ag_sub) + 1)
                                with st.expander(f"✈ 항공사: **{al_code}**  |  총 단체 실적: **{al_tot_val:,.0f}**건", expanded=(al_code == 'KE')):
                                    g_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead><tr><th class="header-main" style="width:80px;">순위</th><th class="header-main">여행사(대리점)명</th><th class="header-main" style="width:200px;">단체 예약 실적 (석)</th></tr></thead><tbody>'
                                    g_html += f'<tr class="row-group-header-custom"><td style="text-align:center;">-</td><td style="text-align:center; font-weight:800;">★ {al_code} 전체 총합계</td><td style="text-align:center;"><b>{al_tot_val:,.0f}</b></td></tr>'
                                    for r_idx, ag_row in top_ag_sub.iterrows():
                                        g_html += f'<tr><td style="text-align:center;">{r_idx}위</td><td style="text-align:center; font-weight:600;">{ag_row[ag_g_col]}</td><td style="text-align:center; font-weight:700;">{ag_row["Value"]:,.0f}</td></tr>'
                                    g_html += '</tbody></table></div>'
                                    st.markdown(g_html, unsafe_allow_html=True)

# ==========================================
# GROUP 2: 🌐 6수송 대시보드 (데이터 타입/필터 완벽 동기화판)
# ==========================================
elif "6수송" in selected_group:
    df_6th_raw = load_6th_data_aggregated()

    if df_6th_raw is None or df_6th_raw.empty:
        st.error("❌ 6수송 캐시 파켓 파일(`cache_6th_data.parquet`)이 없거나 비어 있습니다.")
        st.stop()

    df_6 = df_6th_raw.copy()
    df_6.columns = [str(c).strip() for c in df_6.columns]
    lower_col_map = {c.lower().replace(" ", "").replace("_", "").replace(".", ""): c for c in df_6.columns}

    def get_actual_col(target_str):
        cleaned = target_str.lower().replace(" ", "").replace("_", "").replace(".", "")
        return lower_col_map.get(cleaned, None)

    col_pur_m_disp = get_actual_col("Ticket Purchase month") or "Ticket Purchase month"
    col_trip_m_disp = get_actual_col("Trip Month") or "Trip Month"
    col_rgn = get_actual_col("4.OD RGN") or get_actual_col("OD Region") or "4.OD RGN"
    col_dir = get_actual_col("DIRECTION") or get_actual_col("Direction") or "DIRECTION"
    col_direct_transit = get_actual_col("직항/경유") or "직항/경유"
    col_orig_c = get_actual_col("Trip Origin Country Code") or "Trip Origin Country Code"
    col_dest_c = get_actual_col("Trip Destination Country Code") or "Trip Destination Country Code"
    col_jp_apo = get_actual_col("일본 APO") or "일본 APO"
    col_ov_apo = get_actual_col("해외 APO") or "해외 APO"
    col_od_simple = get_actual_col("Trip O&D") or "Trip O&D"
    col_od_mkt = get_actual_col("Trip O&D Market") or "Trip O&D Market"
    col_al_6 = get_actual_col("Dominant Marketing Airline") or "Dominant Marketing Airline"
    col_val_6 = get_actual_col("Value") or "Value"
    col_year_type = get_actual_col("금년/전년") or "금년/전년"
    col_pur_year_type = get_actual_col("발매_연도구분") or "발매_연도구분"
    col_trip_year_type = get_actual_col("출발_연도구분") or "출발_연도구분"

    # 값 정제
    if col_val_6 in df_6.columns:
        df_6['Val_num'] = pd.to_numeric(df_6[col_val_6].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    else:
        df_6['Val_num'] = 0.0

    if col_year_type in df_6.columns:
        df_6['Val_CY_num'] = np.where(df_6[col_year_type].astype(str).str.contains('금년|CY', na=False), df_6['Val_num'], 0.0)
        df_6['Val_PY_num'] = np.where(df_6[col_year_type].astype(str).str.contains('전년|PY', na=False), df_6['Val_num'], 0.0)
    else:
        df_6['Val_CY_num'] = df_6['Val_num']
        df_6['Val_PY_num'] = 0.0

    # 월 추출 (문자열 규격 통일)
    df_6['Pur_M_Norm'] = df_6[col_pur_m_disp].astype(str).apply(extract_pure_month) if col_pur_m_disp in df_6.columns else ""
    df_6['Trip_M_Norm'] = df_6[col_trip_m_disp].astype(str).apply(extract_pure_month) if col_trip_m_disp in df_6.columns else ""

    last_updated_str = get_6th_last_updated_date()

    st.markdown('<div class="unified-sub-header">✈ 6수송 발매 M/S 현황</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="source-header-box">'
        f'<b>📌 출처:</b> DDS, Bi-Directional, 일본-중국/동남아/미주/구주/기타 &nbsp;|&nbsp; '
        f'<b>🕒 데이터 최근 업데이트:</b> {last_updated_str}'
        f'</div>', 
        unsafe_allow_html=True
    )
    st.markdown("---")
    
    col_left_filter, col_right_data = st.columns([1, 3.5])
    
    with col_left_filter:
        st.markdown('<div style="font-size:15px; font-weight:800; color:#0f172a; border-bottom:2px solid #cbd5e1; padding-bottom:8px; margin-bottom:15px;">🔍 대시보드 슬라이서</div>', unsafe_allow_html=True)

        # 🟢 1. 전년 데이터를 제외한 '금년(CY)' 데이터만 선별
        df_cy_only = df_6[df_6[col_pur_year_type].astype(str).str.contains('금년|CY', na=False)] if col_pur_year_type in df_6.columns else df_6
        if df_cy_only.empty: 
            df_cy_only = df_6

        # 🟢 2. 금년 데이터에서만 옵션을 추출하는 전용 함수
        def get_clean_opts_cy(col_name):
            if col_name in df_cy_only.columns:
                return sorted([str(x).strip() for x in df_cy_only[col_name].dropna().unique() if str(x).strip() not in ['', 'nan', 'none', 'null']])
            return []

     # 🟢 발매월/출발월 및 전체 슬라이서 옵션을 금년(CY) 데이터 기준으로만 추출
        df_cy_pur = df_6[df_6[col_pur_year_type].astype(str).str.contains('금년|CY', na=False)] if col_pur_year_type in df_6.columns else df_6
        if df_cy_pur.empty: df_cy_pur = df_6

        df_cy_trip = df_6[df_6[col_trip_year_type].astype(str).str.contains('금년|CY', na=False)] if col_trip_year_type in df_6.columns else df_6
        if df_cy_trip.empty: df_cy_trip = df_6

        def get_clean_opts_from_df(target_df, col_name):
            if col_name in target_df.columns:
                return sorted([str(x).strip() for x in target_df[col_name].dropna().unique() if str(x).strip() not in ['', 'nan', 'none', 'null']])
            return []

        opts_pur_m = sort_month_options(get_clean_opts_from_df(df_cy_pur, col_pur_m_disp), reverse=True)
        opts_trip_m = sort_month_options(get_clean_opts_from_df(df_cy_trip, col_trip_m_disp), reverse=True)
        
        opts_rgn = get_clean_opts_from_df(df_cy_pur, col_rgn)
        opts_dir = get_clean_opts_from_df(df_cy_pur, col_dir)
        opts_direct = get_clean_opts_from_df(df_cy_pur, col_direct_transit)
        opts_al = get_clean_opts_from_df(df_cy_pur, col_al_6)
        if 'KE' in opts_al: opts_al = ['KE'] + [x for x in opts_al if x != 'KE']
        
        opts_od = get_clean_opts_from_df(df_cy_pur, col_od_simple)
        opts_orig_c = get_clean_opts_from_df(df_cy_pur, col_orig_c)
        opts_dest_c = get_clean_opts_from_df(df_cy_pur, col_dest_c)
        opts_jp_apo = get_clean_opts_from_df(df_cy_pur, col_jp_apo)
        opts_ov_apo = get_clean_opts_from_df(df_cy_pur, col_ov_apo)
        sel_pur_m_disp = st.multiselect(f"발매월{get_dynamic_range_label_6th(opts_pur_m)}", options=opts_pur_m, key="m_pur_6th_v2")
        sel_trip_m_disp = st.multiselect(f"출발월{get_dynamic_range_label_6th(opts_trip_m)}", options=opts_trip_m, key="m_trip_6th_v2")
        sel_rgn = st.multiselect("OD Region", options=opts_rgn, key="m_rgn_6th_v2")
        sel_dir = st.multiselect("Direction (일본발/행)", options=opts_dir, key="m_dir_6th_v2")
        sel_direct = st.multiselect("직항/경유", options=opts_direct, key="m_direct_6th_v2")
        sel_al_list = st.multiselect("항공사 (Carrier)", options=opts_al, key="m_al_6th_v2")
        sel_od_simple = st.multiselect("Trip O&D", options=opts_od, key="m_od_6th_v2")
        sel_orig_c = st.multiselect("출발 국가 (Origin)", options=opts_orig_c, key="m_orig_6th_v2")
        sel_dest_c = st.multiselect("도착 국가 (Destination)", options=opts_dest_c, key="m_dest_6th_v2")
        sel_jp_apo = st.multiselect("일본 APO", options=opts_jp_apo, key="m_jp_6th_v2")
        sel_ov_apo = st.multiselect("해외 APO", options=opts_ov_apo, key="m_ov_6th_v2")

        # 💡 [핵심] 문자열 변환 및 스페이스 정제 후 필터링
        mask = np.ones(len(df_6), dtype=bool)

        if sel_pur_m_disp:
            sel_norm_months = [extract_pure_month(x) for x in sel_pur_m_disp]
            mask &= df_6['Pur_M_Norm'].isin(sel_norm_months)

        if sel_trip_m_disp:
            sel_norm_trip_months = [extract_pure_month(x) for x in sel_trip_m_disp]
            mask &= df_6['Trip_M_Norm'].isin(sel_norm_trip_months)

        if sel_rgn and col_rgn in df_6.columns:
            mask &= df_6[col_rgn].astype(str).str.strip().isin(sel_rgn)

        if sel_dir and col_dir in df_6.columns:
            mask &= df_6[col_dir].astype(str).str.strip().isin(sel_dir)

        if sel_direct and col_direct_transit in df_6.columns:
            mask &= df_6[col_direct_transit].astype(str).str.strip().isin(sel_direct)

        if sel_al_list and col_al_6 in df_6.columns:
            mask &= df_6[col_al_6].astype(str).str.strip().isin(sel_al_list)

        if sel_od_simple and col_od_simple in df_6.columns:
            mask &= df_6[col_od_simple].astype(str).str.strip().isin(sel_od_simple)

        if sel_orig_c and col_orig_c in df_6.columns:
            mask &= df_6[col_orig_c].astype(str).str.strip().isin(sel_orig_c)

        if sel_dest_c and col_dest_c in df_6.columns:
            mask &= df_6[col_dest_c].astype(str).str.strip().isin(sel_dest_c)

        if sel_jp_apo and col_jp_apo in df_6.columns:
            mask &= df_6[col_jp_apo].astype(str).str.strip().isin(sel_jp_apo)

        if sel_ov_apo and col_ov_apo in df_6.columns:
            mask &= df_6[col_ov_apo].astype(str).str.strip().isin(sel_ov_apo)

        filtered_6th = df_6[mask]
        # 🟢 [추가] 필터링 후 메모리에 남은 임시 변수들 즉시 강제 수거
        gc.collect()

    with col_right_data:
        if filtered_6th.empty:
            st.warning("⚠️️ 선택하신 필터 조합에 해당하는 6수송 실적 데이터가 없습니다. 필터 조건을 변경해 주세요.")
        else:
            tabs = st.tabs(["📊 종합 M/S 분석 및 Carrier 상세 비교", "📋 6수송 Raw Data View"])

            with tabs[0]:
                # 1. Carrier별 순위 M/S 요약 표
                try:
                    if col_al_6 in filtered_6th.columns:
                        al_agg = filtered_6th.groupby(col_al_6, observed=True)[['Val_CY_num', 'Val_PY_num']].sum().reset_index()

                        non_ke_agg = al_agg[al_agg[col_al_6] != 'KE'].sort_values(by='Val_CY_num', ascending=False)
                        ke_agg = al_agg[al_agg[col_al_6] == 'KE']
                        al_agg_sorted = pd.concat([ke_agg, non_ke_agg]).reset_index(drop=True)

                        full_al_ranking = [str(x) for x in al_agg.sort_values(by='Val_CY_num', ascending=False)[col_al_6].tolist()]
                        ke_rank = (full_al_ranking.index('KE') + 1) if 'KE' in full_al_ranking else "-"
                        airline_rank_list = [str(x) for x in al_agg_sorted[col_al_6].tolist()[:13]]

                        html_table = '<div class="yoy-table-container"><table class="yoy-table"><thead><tr><th class="mkt-header" style="width:110px;">월별 M/S</th><th class="mkt-header" style="width:110px;">총합계</th>'
                        for al_code in airline_rank_list:
                            if al_code == 'KE': html_table += f'<th class="ke-header" style="width:130px; background-color:#9fc5e8 !important; color:#0f172a !important;">★ KE ({ke_rank}위)</th>'
                            else:
                                rank_num = full_al_ranking.index(al_code) + 1 if al_code in full_al_ranking else "-"
                                html_table += f'<th class="carrier-header" style="width:110px;"><div style="font-size:10px; opacity:0.85;">{rank_num}위</div>{al_code}</th>'
                        html_table += '</tr></thead><tbody>'

                        t_curr = al_agg['Val_CY_num'].sum()
                        t_prev = al_agg['Val_PY_num'].sum()
                        t_yoy_pct = ((t_curr - t_prev) / t_prev * 100) if t_prev > 0 else 0

                        html_table += f'<tr class="row-title"><td style="background-color:#f1f5f9 !important;">전체 발매</td><td style="background-color:#ffffff !important;"><b>{t_curr:,.0f}</b></td>'
                        for al_code in airline_rank_list:
                            row_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                            html_table += f'<td style="background-color:#ffffff !important;"><b>{row_val:,.0f}</b></td>'
                        html_table += '</tr>'

                        html_table += f'<tr><td style="color:#64748b; font-weight:600; background-color:#f1f5f9 !important;">YOY</td>{(get_yoy_td_html(t_yoy_pct, bg_color="#ffffff") if t_prev>0 else get_dash_td(bg_color="#ffffff"))}'
                        for al_code in airline_rank_list:
                            c_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                            p_val = al_agg[al_agg[col_al_6] == al_code]['Val_PY_num'].sum()
                            indiv_yoy = ((c_val - p_val) / p_val * 100) if p_val > 0 else 0
                            html_table += (get_yoy_td_html(indiv_yoy, bg_color="#ffffff") if p_val>0 else get_dash_td(bg_color="#ffffff"))
                        html_table += '</tr>'

                        html_table += '<tr class="row-title"><td style="background-color:#f1f5f9 !important;">전체 M/S</td><td style="background-color:#ffffff !important;"><b>100%</b></td>'
                        for al_code in airline_rank_list:
                            c_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                            ms_val = (c_val / t_curr * 100) if t_curr > 0 else 0
                            html_table += f'<td style="background-color:#ffffff !important;"><b>{ms_val:.1f}%</b></td>'
                        html_table += '</tr>'

                        diff_total_ms = 0
                        html_table += f'<tr class="row-ms-yoy"><td style="color:#64748b; font-weight:600; background-color:#f1f5f9 !important;">YOY</td>{(get_yoy_td_html(diff_total_ms, True, bg_color="#ffffff") if t_prev>0 else get_dash_td(bg_color="#ffffff"))}'
                        for al_code in airline_rank_list:
                            c_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                            p_val = al_agg[al_agg[col_al_6] == al_code]['Val_PY_num'].sum()
                            ms_c = (c_val / t_curr * 100) if t_curr > 0 else 0
                            ms_p = (p_val / t_prev * 100) if t_prev > 0 else 0
                            diff_p = ms_c - ms_p
                            html_table += (get_yoy_td_html(diff_p, True, bg_color="#ffffff") if t_prev>0 and p_val>0 else get_dash_td(bg_color="#ffffff"))
                        html_table += '</tr></tbody></table></div>'
                        st.markdown(html_table, unsafe_allow_html=True)
                except Exception as e:
                    st.info("💡 M/S 요약 테이블 연산 방어 모드가 실행되었습니다.")

                st.markdown("---")
                
                # 2. OD Region별 발매 및 M/S 현황
                try:
                    if col_rgn in filtered_6th.columns and not filtered_6th.empty:
                        st.markdown('<div class="unified-sub-header">🌍 OD Region별 발매 및 M/S 현황</div>', unsafe_allow_html=True)
                        g_mkt_cy = filtered_6th['Val_CY_num'].sum()
                        g_mkt_py = filtered_6th['Val_PY_num'].sum()
                        
                        rgn_agg = []
                        for rgn_name, df_rgn in filtered_6th.groupby(col_rgn, observed=True):
                            m_cy = df_rgn['Val_CY_num'].sum()
                            m_py = df_rgn['Val_PY_num'].sum()
                            
                            df_ke = df_rgn[df_rgn[col_al_6] == 'KE']
                            k_cy = df_ke['Val_CY_num'].sum()
                            k_py = df_ke['Val_PY_num'].sum()
                            
                            rgn_agg.append({
                                'Region': rgn_name,
                                'm_cy': m_cy, 'm_py': m_py,
                                'k_cy': k_cy, 'k_py': k_py
                            })
                            
                        rgn_agg = sorted(rgn_agg, key=lambda x: x['m_cy'], reverse=True)
                        
                        rgn_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead>'
                        rgn_html += '<tr><th rowspan="2" class="header-main" style="width:150px;">OD Region</th>'
                        rgn_html += '<th colspan="4" class="header-main" style="background-color:#215b88 !important; color:#ffffff !important;">시장 전체</th>'
                        rgn_html += '<th colspan="4" class="header-main" style="background-color:#9fc5e8 !important; color:#0f172a !important;">KE 발매량 & M/S (대한항공)</th></tr>'
                        rgn_html += '<tr>'
                        rgn_html += '<th class="header-main" style="background-color:#3172ac !important; color:#ffffff !important;">금년 발매량</th>'
                        rgn_html += '<th class="header-main" style="background-color:#3172ac !important; color:#ffffff !important;">YOY</th>'
                        rgn_html += '<th class="header-main" style="background-color:#28629b !important; color:#ffffff !important;">비중(M/S)</th>'
                        rgn_html += '<th class="header-main" style="background-color:#28629b !important; color:#ffffff !important;">YOY</th>'
                        rgn_html += '<th class="header-main" style="background-color:#9fc5e8 !important; color:#0f172a !important;">금년 발매량</th>'
                        rgn_html += '<th class="header-main" style="background-color:#9fc5e8 !important; color:#0f172a !important;">YOY</th>'
                        rgn_html += '<th class="header-main" style="background-color:#9fc5e8 !important; color:#0f172a !important;">KE M/S</th>'
                        rgn_html += '<th class="header-main" style="background-color:#9fc5e8 !important; color:#0f172a !important;">YOY</th>'
                        rgn_html += '</tr></thead><tbody>'

                        for r in rgn_agg:
                            m_yoy = ((r['m_cy'] - r['m_py']) / r['m_py'] * 100) if r['m_py'] > 0 else 0
                            m_ms_cy = (r['m_cy'] / g_mkt_cy * 100) if g_mkt_cy > 0 else 0
                            m_ms_py = (r['m_py'] / g_mkt_py * 100) if g_mkt_py > 0 else 0
                            m_ms_yoy = m_ms_cy - m_ms_py
                            
                            k_yoy = ((r['k_cy'] - r['k_py']) / r['k_py'] * 100) if r['k_py'] > 0 else 0
                            k_ms_cy = (r['k_cy'] / r['m_cy'] * 100) if r['m_cy'] > 0 else 0
                            k_ms_py = (r['k_py'] / r['m_py'] * 100) if r['m_py'] > 0 else 0
                            k_ms_yoy = k_ms_cy - k_ms_py
                            
                            rgn_html += f'<tr><td style="font-weight:700; background-color:#ffffff !important;">{r["Region"]}</td>'
                            rgn_html += f'<td style="background-color:#ffffff !important;">{r["m_cy"]:,.0f}</td>'
                            rgn_html += get_yoy_td_html(m_yoy, bg_color="#ffffff")
                            rgn_html += f'<td style="background-color:#ffffff !important;">{m_ms_cy:.1f}%</td>'
                            rgn_html += get_yoy_td_html(m_ms_yoy, True, bg_color="#ffffff")
                            
                            rgn_html += f'<td style="background-color:#ffffff !important; text-align:center !important;"><span class="txt-ke-bold">{r["k_cy"]:,.0f}</span></td>'
                            rgn_html += get_yoy_td_html(k_yoy, bg_color="#ffffff")
                            rgn_html += f'<td style="background-color:#ffffff !important; text-align:center !important;"><span class="txt-ke-bold">{k_ms_cy:.1f}%</span></td>'
                            rgn_html += get_yoy_td_html(k_ms_yoy, True, bg_color="#ffffff")
                            rgn_html += '</tr>'
                            
                        g_m_yoy = ((g_mkt_cy - g_mkt_py) / g_mkt_py * 100) if g_mkt_py > 0 else 0
                        g_m_ms_cy = 100.0 if g_mkt_cy > 0 else 0
                        g_m_ms_py = 100.0 if g_mkt_py > 0 else 0
                        g_m_ms_yoy = g_m_ms_cy - g_m_ms_py
                        
                        df_ke_tot = filtered_6th[filtered_6th[col_al_6] == 'KE']
                        g_k_cy = df_ke_tot['Val_CY_num'].sum()
                        g_k_py = df_ke_tot['Val_PY_num'].sum()
                        g_k_yoy = ((g_k_cy - g_k_py) / g_k_py * 100) if g_k_py > 0 else 0
                        g_k_ms_cy = (g_k_cy / g_mkt_cy * 100) if g_mkt_cy > 0 else 0
                        g_k_ms_py = (g_k_py / g_mkt_py * 100) if g_mkt_py > 0 else 0
                        g_k_ms_yoy = g_k_ms_cy - g_k_ms_py

                        rgn_html += '<tr class="total-row-blue">'
                        rgn_html += '<td style="text-align:center;">총계</td>'
                        rgn_html += f'<td>{g_mkt_cy:,.0f}</td>'
                        rgn_html += get_yoy_td_html(g_m_yoy)
                        rgn_html += f'<td>{g_m_ms_cy:.1f}%</td>'
                        rgn_html += get_yoy_td_html(g_m_ms_yoy, True)
                        
                        rgn_html += f'<td><span class="txt-ke-bold">{g_k_cy:,.0f}</span></td>'
                        rgn_html += get_yoy_td_html(g_k_yoy)
                        rgn_html += f'<td><span class="txt-ke-bold">{g_k_ms_cy:.1f}%</span></td>'
                        rgn_html += get_yoy_td_html(g_k_ms_yoy, True)
                        rgn_html += '</tr>'
                        
                        rgn_html += '</tbody></table></div>'
                        st.markdown(rgn_html, unsafe_allow_html=True)
                except Exception as e:
                    st.info("💡 OD Region 분석 연산 중 방어 모드가 실행되었습니다.")

                st.markdown("---")

                # 3. Carrier별 M/S (TOP 20 Trip O&D 및 전체 총계)
                try:
                    if col_od_simple in filtered_6th.columns and not filtered_6th.empty:
                        st.markdown('<div class="unified-sub-header">🏆 Carrier별 M/S (TOP 20 Trip O&D 및 전체 총계)</div>', unsafe_allow_html=True)
                        
                        grand_mkt_cy = filtered_6th['Val_CY_num'].sum()
                        grand_mkt_py = filtered_6th['Val_PY_num'].sum()
                        grand_mkt_yoy = ((grand_mkt_cy - grand_mkt_py) / grand_mkt_py * 100) if grand_mkt_py > 0 else 0

                        sel_carriers = [al for al in sel_al_list if al in filtered_6th[col_al_6].unique()] if sel_al_list else []
                        sel_al_title_suffix = f" ({', '.join(sel_carriers)})" if sel_carriers else " 전체"

                        df_grand_sel = filtered_6th[filtered_6th[col_al_6].isin(sel_carriers)] if sel_carriers else filtered_6th
                        grand_sel_cy = df_grand_sel['Val_CY_num'].sum()
                        grand_sel_py = df_grand_sel['Val_PY_num'].sum()
                        grand_sel_yoy = ((grand_sel_cy - grand_sel_py) / grand_sel_py * 100) if grand_sel_py > 0 else 0
                        grand_sel_ms_cy = (grand_sel_cy / grand_mkt_cy * 100) if grand_mkt_cy > 0 else 0
                        grand_sel_ms_py = (grand_sel_py / grand_mkt_py * 100) if grand_mkt_py > 0 else 0
                        grand_sel_ms_yoy = grand_sel_ms_cy - grand_sel_ms_py

                        df_grand_ke = filtered_6th[filtered_6th[col_al_6] == 'KE']
                        grand_ke_cy = df_grand_ke['Val_CY_num'].sum()
                        grand_ke_py = df_grand_ke['Val_PY_num'].sum()
                        grand_ke_yoy = ((grand_ke_cy - grand_ke_py) / grand_ke_py * 100) if grand_ke_py > 0 else 0
                        grand_ke_ms_cy = (grand_ke_cy / grand_mkt_cy * 100) if grand_mkt_cy > 0 else 0
                        grand_ke_ms_py = (grand_ke_py / grand_mkt_py * 100) if grand_mkt_py > 0 else 0
                        grand_ke_ms_yoy = grand_ke_ms_cy - grand_ke_ms_py

                        od_totals = filtered_6th.groupby(col_od_simple, observed=True)['Val_CY_num'].sum().sort_values(ascending=False)
                        top20_ods = [
                            x for x in od_totals.index 
                            if str(x).strip().lower() not in ['nan', 'none', 'null', '', 'nat'] and od_totals[x] > 0
                        ][:20]

                        if top20_ods:
                            df_top20 = filtered_6th[filtered_6th[col_od_simple].isin(top20_ods)]
                            
                            od_mkt_piv = df_top20.groupby([col_od_simple], observed=True)[['Val_CY_num', 'Val_PY_num']].sum()
                            od_al_piv = df_top20.groupby([col_od_simple, col_al_6], observed=True)[['Val_CY_num', 'Val_PY_num']].sum()

                            matrix_rows = []
                            for rank_i, od_simple_code in enumerate(top20_ods, 1):
                                mkt_cy = od_mkt_piv.loc[od_simple_code, 'Val_CY_num'] if od_simple_code in od_mkt_piv.index else 0
                                mkt_py = od_mkt_piv.loc[od_simple_code, 'Val_PY_num'] if od_simple_code in od_mkt_piv.index else 0
                                mkt_yoy = ((mkt_cy - mkt_py) / mkt_py * 100) if mkt_py > 0 else 0

                                if od_simple_code in od_al_piv.index:
                                    sub_al = od_al_piv.loc[od_simple_code]
                                    if sel_carriers:
                                        sub_sel = sub_al[sub_al.index.isin(sel_carriers)]
                                        sel_cy, sel_py = sub_sel['Val_CY_num'].sum(), sub_sel['Val_PY_num'].sum()
                                    else:
                                        sel_cy, sel_py = mkt_cy, mkt_py

                                    if 'KE' in sub_al.index:
                                        ke_cy = sub_al.loc['KE', 'Val_CY_num']
                                        ke_py = sub_al.loc['KE', 'Val_PY_num']
                                    else:
                                        ke_cy, ke_py = 0, 0
                                else:
                                    sel_cy, sel_py = 0, 0
                                    ke_cy, ke_py = 0, 0

                                sel_yoy = ((sel_cy - sel_py) / sel_py * 100) if sel_py > 0 else 0
                                sel_ms_cy = (sel_cy / mkt_cy * 100) if mkt_cy > 0 else 0
                                sel_ms_py = (sel_py / mkt_py * 100) if mkt_py > 0 else 0
                                sel_ms_yoy = sel_ms_cy - sel_ms_py

                                ke_yoy = ((ke_cy - ke_py) / ke_py * 100) if ke_py > 0 else 0
                                ke_ms_cy = (ke_cy / mkt_cy * 100) if mkt_cy > 0 else 0
                                ke_ms_py = (ke_py / mkt_py * 100) if mkt_py > 0 else 0
                                ke_ms_yoy = ke_ms_cy - ke_ms_py

                                matrix_rows.append({
                                    'rank': rank_i, 'od_simple': od_simple_code,
                                    'mkt_cy': mkt_cy, 'mkt_yoy': mkt_yoy,
                                    'sel_cy': sel_cy, 'sel_yoy': sel_yoy,
                                    'sel_ms_cy': sel_ms_cy, 'sel_ms_yoy': sel_ms_yoy,
                                    'ke_cy': ke_cy, 'ke_yoy': ke_yoy,
                                    'ke_ms_cy': ke_ms_cy, 'ke_ms_yoy': ke_ms_yoy
                                })

                            tot_mkt_cy = sum(r['mkt_cy'] for r in matrix_rows)
                            tot_mkt_py = filtered_6th[filtered_6th[col_od_simple].isin(top20_ods)]['Val_PY_num'].sum()
                            tot_mkt_yoy = ((tot_mkt_cy - tot_mkt_py) / tot_mkt_py * 100) if tot_mkt_py > 0 else 0

                            tot_sel_cy = sum(r['sel_cy'] for r in matrix_rows)
                            df_top20_all = filtered_6th[filtered_6th[col_od_simple].isin(top20_ods)]
                            df_top20_sel = df_top20_all[df_top20_all[col_al_6].isin(sel_carriers)] if sel_carriers else df_top20_all
                            tot_sel_py = df_top20_sel['Val_PY_num'].sum()
                            tot_sel_yoy = ((tot_sel_cy - tot_sel_py) / tot_sel_py * 100) if tot_sel_py > 0 else 0
                            tot_sel_ms_cy = (tot_sel_cy / tot_mkt_cy * 100) if tot_mkt_cy > 0 else 0
                            tot_sel_ms_py = (tot_sel_py / tot_mkt_py * 100) if tot_mkt_py > 0 else 0
                            tot_sel_ms_yoy = tot_sel_ms_cy - tot_sel_ms_py

                            tot_ke_cy = sum(r['ke_cy'] for r in matrix_rows)
                            tot_ke_py = df_top20_all[df_top20_all[col_al_6] == 'KE']['Val_PY_num'].sum()
                            tot_ke_yoy = ((tot_ke_cy - tot_ke_py) / tot_ke_py * 100) if tot_ke_py > 0 else 0
                            tot_ke_ms_cy = (tot_ke_cy / tot_mkt_cy * 100) if tot_mkt_cy > 0 else 0
                            tot_ke_ms_py = (tot_ke_py / tot_mkt_py * 100) if tot_mkt_py > 0 else 0
                            tot_ke_ms_yoy = tot_ke_ms_cy - tot_ke_ms_py

                            od_matrix_html = '<div class="custom-piv-container" style="overflow-x:auto;"><table class="custom-piv-table" style="width:100%; min-width:1150px; border-collapse:collapse;"><thead>'
                            od_matrix_html += '<tr>'
                            od_matrix_html += '<th rowspan="2" class="header-main" style="width:4%; padding:6px 2px; white-space:nowrap;">순위</th>'
                            od_matrix_html += '<th rowspan="2" class="header-main" style="width:8%; padding:6px 2px; white-space:nowrap;">Trip O&D</th>'
                            od_matrix_html += '<th colspan="2" class="header-main" style="width:17.6%; background-color:#215b88 !important; color:#ffffff !important; white-space:nowrap;">시장 전체</th>'
                            od_matrix_html += f'<th colspan="2" class="header-main" style="width:17.6%; background-color:#1e4e79 !important; color:#ffffff !important; white-space:nowrap;">선택 항공사 발매량{sel_al_title_suffix}</th>'
                            od_matrix_html += '<th colspan="2" class="header-main" style="width:17.6%; background-color:#1b3d5a !important; color:#ffffff !important; white-space:nowrap;">선택 항공사 M/S</th>'
                            od_matrix_html += '<th colspan="4" class="header-main" style="width:35.2%; background-color:#9fc5e8 !important; color:#0f172a !important; white-space:nowrap;">KE 발매량 & M/S (대한항공)</th>'
                            od_matrix_html += '</tr>'
                            
                            th_col_style_dark = 'style="width:8.8%; background-color:#3172ac !important; color:#ffffff !important; padding:6px 2px; white-space:nowrap;"'
                            th_col_style_mid  = 'style="width:8.8%; background-color:#28629b !important; color:#ffffff !important; padding:6px 2px; white-space:nowrap;"'
                            th_col_style_navy = 'style="width:8.8%; background-color:#204f77 !important; color:#ffffff !important; padding:6px 2px; white-space:nowrap;"'
                            th_col_style_ke   = 'style="width:8.8%; background-color:#9fc5e8 !important; color:#0f172a !important; padding:6px 2px; white-space:nowrap;"'
                            
                            od_matrix_html += '<tr>'
                            od_matrix_html += f'<th class="header-main" {th_col_style_dark}>금년</th>'
                            od_matrix_html += f'<th class="header-main" {th_col_style_dark}>YOY</th>'
                            od_matrix_html += f'<th class="header-main" {th_col_style_mid}>금년</th>'
                            od_matrix_html += f'<th class="header-main" {th_col_style_mid}>YOY</th>'
                            od_matrix_html += f'<th class="header-main" {th_col_style_navy}>금년 M/S</th>'
                            od_matrix_html += f'<th class="header-main" {th_col_style_navy}>YOY</th>'
                            od_matrix_html += f'<th class="header-main" {th_col_style_ke}>금년 발매량</th>'
                            od_matrix_html += f'<th class="header-main" {th_col_style_ke}>YOY</th>'
                            od_matrix_html += f'<th class="header-main" {th_col_style_ke}>KE M/S</th>'
                            od_matrix_html += f'<th class="header-main" {th_col_style_ke}>YOY</th>'
                            od_matrix_html += '</tr></thead><tbody>'

                            for r in matrix_rows:
                                od_matrix_html += '<tr>'
                                od_matrix_html += f'<td style="font-weight:700; background-color:#ffffff !important; padding:6px 2px; white-space:nowrap;">{r["rank"]}</td>'
                                od_matrix_html += f'<td style="font-weight:700; background-color:#ffffff !important; padding:6px 2px; white-space:nowrap;">{r["od_simple"]}</td>'
                                od_matrix_html += f'<td style="background-color:#ffffff !important; padding:6px 2px; white-space:nowrap;">{r["mkt_cy"]:,.0f}</td>'
                                od_matrix_html += get_yoy_td_html(r["mkt_yoy"], bg_color="#ffffff")
                                od_matrix_html += f'<td style="font-weight:700; background-color:#ffffff !important; padding:6px 2px; white-space:nowrap;">{r["sel_cy"]:,.0f}</td>'
                                od_matrix_html += get_yoy_td_html(r["sel_yoy"], bg_color="#ffffff")
                                od_matrix_html += f'<td style="font-weight:700; background-color:#ffffff !important; padding:6px 2px; white-space:nowrap;">{r["sel_ms_cy"]:.1f}%</td>'
                                od_matrix_html += get_yoy_td_html(r["sel_ms_yoy"], True, bg_color="#ffffff")
                                
                                od_matrix_html += f'<td style="background-color:#ffffff !important; text-align:center !important; padding:6px 2px; white-space:nowrap;"><span class="txt-ke-bold">{r["ke_cy"]:,.0f}</span></td>'
                                od_matrix_html += get_yoy_td_html(r["ke_yoy"], bg_color="#ffffff")
                                od_matrix_html += f'<td style="background-color:#ffffff !important; text-align:center !important; padding:6px 2px; white-space:nowrap;"><span class="txt-ke-bold">{r["ke_ms_cy"]:.1f}%</span></td>'
                                od_matrix_html += get_yoy_td_html(r["ke_ms_yoy"], True, bg_color="#ffffff")
                                od_matrix_html += '</tr>'

                            bg_sub = "#e2e8f0"
                            od_matrix_html += f'<tr style="border-top:2px solid #94a3b8 !important;">'
                            od_matrix_html += f'<td colspan="2" style="font-weight:800 !important; text-align:center; background-color:{bg_sub} !important;">TOP 20 소계</td>'
                            od_matrix_html += f'<td style="font-weight:800 !important; background-color:{bg_sub} !important;">{tot_mkt_cy:,.0f}</td>'
                            od_matrix_html += get_yoy_td_html(tot_mkt_yoy, bg_color=bg_sub)
                            od_matrix_html += f'<td style="font-weight:800 !important; background-color:{bg_sub} !important;">{tot_sel_cy:,.0f}</td>'
                            od_matrix_html += get_yoy_td_html(tot_sel_yoy, bg_color=bg_sub)
                            od_matrix_html += f'<td style="font-weight:800 !important; background-color:{bg_sub} !important;">{tot_sel_ms_cy:.1f}%</td>'
                            od_matrix_html += get_yoy_td_html(tot_sel_ms_yoy, True, bg_color=bg_sub)
                            od_matrix_html += f'<td style="text-align:center !important; background-color:{bg_sub} !important;"><span class="txt-ke-bold">{tot_ke_cy:,.0f}</span></td>'
                            od_matrix_html += get_yoy_td_html(tot_ke_yoy, bg_color=bg_sub)
                            od_matrix_html += f'<td style="text-align:center !important; background-color:{bg_sub} !important;"><span class="txt-ke-bold">{tot_ke_ms_cy:.1f}%</span></td>'
                            od_matrix_html += get_yoy_td_html(tot_ke_ms_yoy, True, bg_color=bg_sub)
                            od_matrix_html += '</tr>'

                            od_matrix_html += '<tr class="total-row-blue">'
                            od_matrix_html += '<td colspan="2" style="text-align:center;">선택 필터 전체 총계</td>'
                            od_matrix_html += f'<td>{grand_mkt_cy:,.0f}</td>'
                            od_matrix_html += get_yoy_td_html(grand_mkt_yoy)
                            od_matrix_html += f'<td>{grand_sel_cy:,.0f}</td>'
                            od_matrix_html += get_yoy_td_html(grand_sel_yoy)
                            od_matrix_html += f'<td>{grand_sel_ms_cy:.1f}%</td>'
                            od_matrix_html += get_yoy_td_html(grand_sel_ms_yoy, True)
                            od_matrix_html += f'<td><span class="txt-ke-bold">{grand_ke_cy:,.0f}</span></td>'
                            od_matrix_html += get_yoy_td_html(grand_ke_yoy)
                            od_matrix_html += f'<td><span class="txt-ke-bold">{grand_ke_ms_cy:.1f}%</span></td>'
                            od_matrix_html += get_yoy_td_html(grand_ke_ms_yoy, True)
                            od_matrix_html += '</tr>'

                            od_matrix_html += '</tbody></table></div>'
                            st.markdown(od_matrix_html, unsafe_allow_html=True)
                except Exception as e:
                    st.info("💡 TOP 20 O&D 분석 연산 중 방어 모드가 실행되었습니다.")

            with tabs[1]:
                st.markdown('<div class="unified-sub-header">📋 6수송 사전 집계 Data 조회 및 다운로드</div>', unsafe_allow_html=True)
                if df_6th_raw is not None and not df_6th_raw.empty:
                    show_df = filtered_6th if not filtered_6th.empty else df_6th_raw
                    csv_6th_bytes = show_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button("📥 필터링된 6수송 Data (CSV) 다운로드", data=csv_6th_bytes, file_name=f"6th_Freedom_Data_{datetime.date.today().strftime('%Y%m%d')}.csv", mime="text/csv")
                    st.dataframe(show_df.head(100), use_container_width=True)
                    
# ==========================================
# GROUP 3: 🔗 W26 연결 네트워크
# ==========================================
else:
    st.markdown('<div class="unified-sub-header">🔗 대한항공 W26 연결 네트워크 외부 연동 시스템</div>', unsafe_allow_html=True)
    st.link_button("🔗 W26 연결 네트워크 바로가기 (새 탭에서 열기)", EXT_WEB_APP_URL, width="stretch")