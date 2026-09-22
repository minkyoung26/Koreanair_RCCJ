# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import datetime
import os

# 1. Page Config
st.set_page_config(
    page_title="일본노선 발매/공급 Market Share",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 외부 구글 앱스 스크립트 웹앱 URL
EXT_WEB_APP_URL = "https://script.google.com/a/macros/koreanair.com/s/AKfycbxt3IfN0gB4n344U4gL1kt5i4RVjn7_uuG5PtKY-pPgNejpDCsjp2PEbopEexw5NLUjDQ/exec"

# 2. Dynamic Date Logic (2026년 기준)
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

AIRLINE_WEIGHT_MULTIPLIERS = {
    'KE': 1.0, 'OZ': 1.0, '7C': 4.75884657, 'LJ': 4.387110992, 'TW': 4.413912854,
    'BX': 1.865842867, 'RS': 1.758028702, 'JL': 1.0, 'NH': 1.0, 'ET': 1.0,
    'YP': 5.92588446, 'ZE': 3.783327953, 'WE': 1.0
}

RBD_HIERARCHY = {
    'KE': list('YBMSHEKLUQTX'), 'OZ': list('YBMHEQKSVWTLX'),
    '7C': list('YBKNQMTWORXSZLHEFVGPJ'), 'LJ': list('YWDEHKLQBNMXPSVZARIOT'),
    'TW': list('YWZVSPONMLKHDBAJQET'), 'BX': list('YBRMKEUDOIVJHXGWQN'),
    'RS': list('YBMHEQKSOLWTRUIXAVGNDPFJC'), 'JL': list('WREYBHKMLVSOGQNPZ'),
    'NH': list('ENYBMUHQVWSLK'), 'YP': list('PRZYBMHELQNSAFKVOGWX'),
    'ZE': list('PFAJCIROYBMSHEKLQNTVWGX'), 'WE': list('ADIZOYBMHEUQNTVW')
}

# CSS
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
    .source-header-box { background-color: #f0f9ff; border-left: 5px solid #0284c7; padding: 12px 18px; border-radius: 6px; margin-bottom: 15px; font-size: 13.5px; color: #0f172a; font-weight: 500; }
    .metric-card { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.03); margin-bottom: 10px; }
    .metric-card-ke { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.03); margin-bottom: 10px; }
    .metric-title { font-size: 12.5px; color: #64748b; margin-bottom: 4px; font-weight: 500; }
    .metric-value { font-size: 22px; color: #1e293b; font-weight: 700; }
    .custom-piv-container, .yoy-table-container { width: 100%; overflow-x: auto; margin-bottom: 20px; border-radius: 8px; border: 1px solid #cbd5e1 !important; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
    .custom-piv-table, .yoy-table { width: 100%; border-collapse: collapse; font-size: 12.5px; background-color: #ffffff; text-align: center !important; table-layout: fixed !important; }
    .custom-piv-table th.header-main, .yoy-table th, .yoy-table th.mkt-header, .yoy-table th.carrier-header { background-color: #cfe2f3 !important; color: #0f172a !important; padding: 8px 6px; border: 1px solid #cbd5e1 !important; font-weight: 600; text-align: center !important; white-space: nowrap; }
    .yoy-table th.ke-header { background-color: #6fa8dc !important; color: #ffffff !important; padding: 8px 6px; border: 1px solid #cbd5e1 !important; font-size: 13px !important; font-weight: 700 !important; text-align: center !important; white-space: nowrap; }
    .custom-piv-table td, .yoy-table td, .yoy-table tr.ke-row td.ke-cell { padding: 6px 10px; border: 1px solid #cbd5e1 !important; background-color: #ffffff !important; text-align: center !important; }
    .yoy-table tr:hover { background-color: #f8fafc !important; }
    .yoy-table tr.row-title { background-color: #f8fafc !important; font-weight: 600; color: #0f172a; }
</style>
""", unsafe_allow_html=True)

# 5. Sidebar Uploader
st.sidebar.header("📁 실시간 데이터 업로드")
uploaded_iss = st.sidebar.file_uploader("1. 3/4수송 Parquet/CSV 캐시", type=['parquet', 'csv', 'xlsx'], key="sb_uploader_iss")
uploaded_sup = st.sidebar.file_uploader("2. 공급 데이터", type=['csv', 'xlsx', 'zip', 'parquet'], key="sb_uploader_sup")
uploaded_6th = st.sidebar.file_uploader("3. 6수송 데이터", type=['csv', 'xlsx', 'zip', 'parquet'], key="sb_uploader_6th")

def optimize_df(df_in):
    if df_in is None: return None
    for col in df_in.columns:
        if df_in[col].dtype == 'object':
            if df_in[col].nunique() < len(df_in) * 0.5:
                df_in[col] = df_in[col].astype('category')
        elif df_in[col].dtype == 'int64': df_in[col] = df_in[col].astype('int32')
        elif df_in[col].dtype == 'float64': df_in[col] = df_in[col].astype('float32')
    return df_in

def clean_transport_column(df):
    if df is None: return df
    b_col = '수송' if '수송' in df.columns else ('Bound' if 'Bound' in df.columns else None)
    if b_col:
        df['수송'] = df[b_col].astype(str).str.strip()
    return df

@st.cache_data(ttl=3600, show_spinner="3/4수송 데이터를 읽어오는 중...")
def load_fast_parquet_data_file():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(base_dir, 'cache_34_data.parquet')
    if os.path.exists(target_path):
        df_p = pd.read_parquet(target_path)
        return optimize_df(clean_transport_column(df_p))
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def process_any_uploaded_file(file_obj):
    file_obj.seek(0)
    if file_obj.name.endswith('.parquet'):
        df = pd.read_parquet(file_obj)
    elif file_obj.name.endswith('.xlsx'):
        df = pd.read_excel(file_obj)
    else:
        df = pd.read_csv(file_obj, low_memory=False)

    df.columns = [str(c).strip() for c in df.columns]
    return optimize_df(clean_transport_column(df))

@st.cache_data(ttl=3600, show_spinner=False)
def load_aux_files():
    df_sup = None
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sup_paths = [os.path.join(base_dir, '공급.csv'), '공급.csv']
    for sp in sup_paths:
        if os.path.exists(sp):
            try:
                df_sup = pd.read_csv(sp, low_memory=False)
                if df_sup is not None and not df_sup.empty: break
            except: pass
    return optimize_df(df_sup)

@st.cache_data(ttl=3600, show_spinner="🌐 6수송 집계 데이터를 로드하는 중입니다...")
def load_6th_data_aggregated():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    six_paths = [os.path.join(base_dir, 'cache_6th_data.parquet'), 'cache_6th_data.parquet']
    for sp in six_paths:
        if os.path.exists(sp):
            try:
                df = pd.read_parquet(sp, engine='pyarrow')
                return optimize_df(df)
            except: pass
    return None

disk_sup = load_aux_files()

if uploaded_iss is not None:
    df_iss_merged = process_any_uploaded_file(uploaded_iss)
else:
    df_iss_merged = load_fast_parquet_data_file()

df_sup_raw = disk_sup

st.markdown('<div class="main-app-title">✈️ 일본노선 발매/공급 Market Share</div>', unsafe_allow_html=True)
st.markdown('<div class="group-section-header">🗂️ 메인 대시보드 선택</div>', unsafe_allow_html=True)

selected_group = st.radio(
    "분석할 수송 영역을 선택하세요:",
    options=["✈️ 3/4수송 대시보드", "🌐 6수송 대시보드", "🔗 W26 연결 네트워크"],
    index=0,
    horizontal=True
)

ALL_OPTION = "전체 (All)"

def build_airline_color_map(airlines_list):
    KE_COLOR = '#16a34a'
    palette = px.colors.qualitative.Plotly + px.colors.qualitative.Bold + px.colors.qualitative.Pastel + px.colors.qualitative.Dark24
    FORBIDDEN_COLORS = ['#16a34a', '#16A34A', '#00cc96', '#00CC96', '#2ca02c', '#2CA02C', '#636EFA', '#0ea5e9']
    
    cmap = {'KE': KE_COLOR}
    color_idx = 0
    
    for al in airlines_list:
        if str(al).upper() != 'KE':
            while True:
                candidate_color = palette[color_idx % len(palette)]
                color_idx += 1
                if candidate_color.upper() not in [c.upper() for c in FORBIDDEN_COLORS]:
                    cmap[al] = candidate_color
                    break
    return cmap

def apply_bottom_legend(fig):
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5, title=dict(text="")), margin=dict(b=80))
    return fig

def format_dep_time(dep_val):
    try:
        val_str = str(int(dep_val)).zfill(4)
        hh, mm = int(val_str[:2]), int(val_str[2:])
        if hh >= 24: hh = 23
        if mm >= 60: mm = 59
        return f"2026-08-01 {hh:02d}:{mm:02d}:00", f"2026-08-01 {(hh+2)%24:02d}:{mm:02d}:00"
    except: return "2026-08-01 09:00:00", "2026-08-01 11:00:00"

def render_multiselect_box(container, label, full_list, key_name, default_vals=None):
    container.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
    opts = [str(x).strip() for x in full_list if str(x).strip() != 'nan']
    if default_vals is None:
        default_vals = []
    else:
        default_vals = [x for x in default_vals if x in opts]
    return container.multiselect(label, options=opts, default=default_vals, key=key_name, label_visibility="collapsed")

def get_dynamic_date_ranges_34(df_iss):
    if df_iss is None or df_iss.empty: return issue_range_str, dep_range_str
    m_col = '출발월' if '출발월' in df_iss.columns else ('출발 월' if '출발 월' in df_iss.columns else 'Trip Month')
    dep_str = f"{sorted([str(x).strip() for x in df_iss[m_col].dropna().unique() if str(x).strip() != 'nan'])[0]} ~ {sorted([str(x).strip() for x in df_iss[m_col].dropna().unique() if str(x).strip() != 'nan'])[-1]}" if m_col in df_iss.columns else dep_range_str
    w_col = '발매주차_일자' if '발매주차_일자' in df_iss.columns else ('발매 주차' if '발매 주차' in df_iss.columns else 'Purchase Month')
    iss_str = f"{sorted([str(x).strip() for x in df_iss[w_col].dropna().unique() if str(x).strip() != 'nan'])[0]} ~ {sorted([str(x).strip() for x in df_iss[w_col].dropna().unique() if str(x).strip() != 'nan'])[-1]}" if w_col in df_iss.columns else issue_range_str
    return iss_str, dep_str

def get_yoy_td_html(val, is_percentage_point=False):
    unit = "%p" if is_percentage_point else "%"
    if val > 0:
        return f'<td style="color: #1d4ed8 !important; font-size: 10px !important; font-weight: 600 !important; text-align: center !important;">▲ {val:.0f}{unit}</td>'
    elif val < 0:
        return f'<td style="color: #dc2626 !important; font-size: 10px !important; font-weight: 600 !important; text-align: center !important;">▼ {abs(val):.0f}{unit}</td>'
    else:
        return f'<td style="color: #475569 !important; font-size: 10px !important; font-weight: 500 !important; text-align: center !important;">▲ 0{unit}</td>'

# ==========================================
# GROUP 1: ✈️ 3/4수송 대시보드
# ==========================================
if selected_group == "✈️ 3/4수송 대시보드":
    dynamic_iss_str_34, dynamic_dep_str_34 = get_dynamic_date_ranges_34(df_iss_merged)
    st.markdown(f"""
    <div class="source-header-box">
        <b>📌 출처: DDS & OAG 데이터 (3/4수송 대시보드)</b> &nbsp;|&nbsp; 
        <b>🗓️ 발매기간 (Purchase Month):</b> {dynamic_iss_str_34} (과거 5주) &nbsp;|&nbsp; 
        <b>✈️ 출발기간 (Trip Month):</b> {dynamic_dep_str_34} (향후 6개월)
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    
    tab_34_1, tab_34_2, tab_34_3, tab_34_4 = st.tabs([
        "🎟️ 발매 M/S", "✈️ 공급 M/S", "🏷️ 대리점,RBD별 발매현황", "👥 단체실적"
    ])

    with tab_34_1:
        if df_iss_merged is None:
            st.warning("❌ 3/4수송 데이터를 찾을 수 없습니다.")
            st.stop()

        merged_df = df_iss_merged.copy()

        al_col_target = None
        for col_cand in ['Dominant Marketing Airline', 'AL', '항공사', 'Marketing Airline']:
            if col_cand in merged_df.columns:
                al_col_target = col_cand
                break
        
        merged_df['AL_clean'] = merged_df[al_col_target].astype(str).str.strip().str.upper() if al_col_target else ''
        merged_df['노선_clean'] = merged_df['노선'].astype(str).str.strip()

        region_col = next((c for c in merged_df.columns if str(c).replace(" ", "") in ['일본권역', '권역', 'JapanRegion', 'Region']), None)
        bound_raw_col = next((c for c in merged_df.columns if str(c).replace(" ", "") in ['Bound', 'BOUND', '방향', '바운드']), None)

        week_col = '발매주차_일자' if '발매주차_일자' in merged_df.columns else ('발매 주차' if '발매 주차' in merged_df.columns else '발매주차')
        all_issue_weeks = sorted([str(x).strip() for x in merged_df[week_col].dropna().unique()]) if week_col else []

        month_col = '출발월' if '출발월' in merged_df.columns else ('출발 월' if '출발 월' in merged_df.columns else None)
        all_dep_months = sorted([str(x).strip() for x in merged_df[month_col].dropna().unique()]) if month_col else []
        
        bound_col = '수송' if '수송' in merged_df.columns else ('Bound' if 'Bound' in merged_df.columns else None)
        all_bounds = sorted([str(x).strip() for x in merged_df[bound_col].dropna().unique()]) if bound_col else []

        all_regions = sorted([str(x).strip() for x in merged_df[region_col].dropna().unique() if str(x).strip() != 'nan' and str(x).strip() != '']) if region_col else []
        all_bound_raws = sorted([str(x).strip() for x in merged_df[bound_raw_col].dropna().unique() if str(x).strip() != 'nan']) if bound_raw_col else ["IN", "OUT"]
        all_ticket_types = sorted([str(x).strip() for x in merged_df['Ticket Type'].dropna().unique()]) if 'Ticket Type' in merged_df.columns else []

        raw_airlines = sorted([str(x).strip() for x in merged_df['AL_clean'].dropna().unique()])
        all_airlines = ['KE'] + [x for x in raw_airlines if x != 'KE'] if 'KE' in raw_airlines else raw_airlines

        with st.expander("🔍 **발매 대시보드 피벗 슬라이서 필터 설정** (다중 선택 가능)", expanded=True):
            apply_weight_toggle = st.toggle("⚖️ 가중치 적용 M/S 산출", value=True, key="main_wt_toggle_fixed")
            
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            sel_region_list = render_multiselect_box(f_col1, "1. 일본권역", all_regions, "slicer_region_multi")

            if region_col and region_col in merged_df.columns and sel_region_list:
                df_region_sub = merged_df[merged_df[region_col].astype(str).str.strip().isin(sel_region_list)]
                df_has_value_sub = df_region_sub[(df_region_sub['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER)) & (df_region_sub['Value'] > 0)]
                route_sum_sub = df_has_value_sub.groupby('노선_clean', observed=False)['Value'].sum().sort_values(ascending=False)
                dynamic_route_list = [str(x).strip() for x in route_sum_sub.index.tolist() if str(x) != 'nan']
            else:
                df_has_value = merged_df[(merged_df['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER)) & (merged_df['Value'] > 0)]
                full_route_sum = df_has_value.groupby('노선_clean', observed=False)['Value'].sum().sort_values(ascending=False)
                dynamic_route_list = [str(x).strip() for x in full_route_sum.index.tolist() if str(x) != 'nan']

            valid_ke_routes = dynamic_route_list

            sel_route_list = render_multiselect_box(f_col2, "2. KE취항노선", dynamic_route_list, "slicer_route_multi")
            sel_week_list = render_multiselect_box(f_col3, "3. 발매 주차 (과거 5주)", all_issue_weeks, "slicer_week_multi")
            sel_month_list = render_multiselect_box(f_col4, "4. 출발 월 (향후 6개월)", all_dep_months, "slicer_month_multi")

            f_col5, f_col6, f_col7, f_col8 = st.columns(4)
            sel_bound_list = render_multiselect_box(f_col5, "5. 수송 구분", all_bounds, "slicer_bound_multi")
            sel_bound_raw_list = render_multiselect_box(f_col6, "6. Bound", all_bound_raws, "slicer_bound_raw_multi")
            sel_tt_list = render_multiselect_box(f_col7, "7. Trip Type", all_ticket_types, "slicer_tt_multi")
            sel_al_list = render_multiselect_box(f_col8, "8. 항공사", all_airlines, "slicer_al_multi")

        filter_mask = pd.Series(True, index=merged_df.index)

        if region_col and region_col in merged_df.columns and sel_region_list:
            filter_mask &= (merged_df[region_col].astype(str).str.strip().isin(sel_region_list))
        if sel_route_list: filter_mask &= (merged_df['노선_clean'].isin(sel_route_list))
        elif valid_ke_routes: filter_mask &= (merged_df['노선_clean'].isin(valid_ke_routes))
        else: filter_mask &= (merged_df['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER))

        if sel_week_list and week_col: filter_mask &= (merged_df[week_col].astype(str).str.strip().isin(sel_week_list))
        if sel_month_list and month_col: filter_mask &= (merged_df[month_col].astype(str).str.strip().isin(sel_month_list))
        if sel_bound_list and bound_col: filter_mask &= (merged_df[bound_col].astype(str).str.strip().isin(sel_bound_list))
        if bound_raw_col and bound_raw_col in merged_df.columns and sel_bound_raw_list: filter_mask &= (merged_df[bound_raw_col].astype(str).str.strip().isin(sel_bound_raw_list))
        if sel_tt_list and 'Ticket Type' in merged_df.columns: filter_mask &= (merged_df['Ticket Type'].astype(str).str.strip().isin(sel_tt_list))
        if sel_al_list: filter_mask &= (merged_df['AL_clean'].isin(sel_al_list))

        filtered_df = merged_df[filter_mask].copy()

        if apply_weight_toggle:
            filtered_df['Mult_map'] = filtered_df['AL_clean'].map(AIRLINE_WEIGHT_MULTIPLIERS).fillna(1.0)
            filtered_df['Calc_Weighted_Value'] = filtered_df['Value'] * filtered_df['Mult_map']
            val_col = 'Calc_Weighted_Value'

            al_wt_sum = filtered_df.groupby('AL_clean', observed=False)[val_col].sum()
            total_pax = al_wt_sum.sum()
            ke_pax = al_wt_sum.get('KE', 0)
            ke_ms = (ke_pax / total_pax * 100) if total_pax > 0 else 0
            al_ms_normalized = (al_wt_sum / total_pax * 100) if total_pax > 0 else pd.Series(0.0, index=al_wt_sum.index)
        else:
            val_col = 'Value'
            total_pax = filtered_df[val_col].sum()
            ke_pax = filtered_df[filtered_df['AL_clean'] == 'KE'][val_col].sum() if not filtered_df.empty else 0
            ke_ms = (ke_pax / total_pax * 100) if total_pax > 0 else 0

        top_al = "-"
        top_ms = 0.0
        if not filtered_df.empty and total_pax > 0:
            if apply_weight_toggle:
                top_al = str(al_ms_normalized.idxmax())
                top_ms = float(al_ms_normalized.max())
            else:
                al_sum = filtered_df.groupby('AL_clean', observed=False)[val_col].sum()
                top_al = str(al_sum.idxmax())
                top_ms = (al_sum.max() / total_pax) * 100

        top_route = str(filtered_df.groupby('노선_clean', observed=False)[val_col].sum().idxmax()) if not filtered_df.empty and total_pax > 0 else "-"
        status_wt_label = " (가중치 보정)" if apply_weight_toggle else " (Raw)"

        tab1, tab2, tab3 = st.tabs(["📈 시각화 분석 차트", "📊 M/S 피벗 테이블", "🔒 Raw Data View (관리자 전용)"])
        with tab1:
            if not filtered_df.empty:
                al_order = [al for al in all_airlines if al in filtered_df['AL_clean'].unique()]
                
                st.markdown('<div class="unified-sub-header">1. 항공사별 M/S 점유비</div>', unsafe_allow_html=True)
                c1, c2 = st.columns([1.6, 1])
                with c1:
                    if apply_weight_toggle:
                        pie_al = al_ms_normalized.reset_index()
                        pie_al.columns = ['AL_clean', 'Display_MS']
                        values_for_pie = pie_al['Display_MS']
                        text_labels_pie = [f"<b>{v:.1f}%</b>" for v in pie_al['Display_MS']]
                    else:
                        pie_al = filtered_df.groupby('AL_clean', observed=False)[val_col].sum().reset_index()
                        values_for_pie = pie_al[val_col]
                        text_labels_pie = None
                    
                    labels_list = [f"<b>{x}</b>" if str(x) == 'KE' else str(x) for x in pie_al['AL_clean']]
                    pull_list = [0.08 if str(x) == 'KE' else 0 for x in pie_al['AL_clean']]
                    colors_list = [build_airline_color_map(all_airlines).get(al, '#94a3b8') for al in pie_al['AL_clean']]

                    fig1 = go.Figure(data=[go.Pie(
                        labels=labels_list,
                        values=values_for_pie,
                        text=text_labels_pie,
                        textinfo='label+text' if apply_weight_toggle else 'percent+label',
                        hole=0.4,
                        pull=pull_list,
                        marker=dict(colors=colors_list),
                        textposition='inside'
                    )])

                    apply_bottom_legend(fig1)
                    st.plotly_chart(fig1, width='stretch')

                with c2:
                    st.markdown("##### 📌 발매 실적 핵심 요약 (Summary)")
                    st.markdown(f'<div class="metric-card"><div class="metric-title">총 발매 실적{status_wt_label}</div><div class="metric-value">{total_pax:,.0f}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-card-ke"><div class="metric-title" style="color:#16a34a; font-weight:bold;">✈️ <span class="ke-highlight">KE (대한항공) M/S</span></div><div class="metric-value" style="color:#16a34a;"><b>{ke_pax:,.0f} ({ke_ms:.1f}%)</b></div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-card"><div class="metric-title">1위 항공사 (M/S)</div><div class="metric-value" style="color:#1d4ed8;"><b>{top_al}</b> ({top_ms:.1f}%)</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-card"><div class="metric-title">최대 실적 노선</div><div class="metric-value" style="color:#047857;">{top_route}</div></div>', unsafe_allow_html=True)

        with tab2:
            st.markdown("##### 📌 주차별 및 노선별 발매 M/S 매트릭스")

        with tab3:
            admin_pw = st.text_input("🔑 관리자 비밀번호를 입력하세요:", type="password", key="admin_pw_fixed")

    with tab_34_2: pass
    with tab_34_3: pass
    with tab_34_4: pass

# ==========================================
# GROUP 2: 🌐 6수송 대시보드
# ==========================================
elif selected_group == "🌐 6수송 대시보드":
    df_6th_raw = load_6th_data_aggregated()

    if df_6th_raw is None:
        st.warning("👈 6수송 캐시 파켓 파일(`cache_6th_data.parquet`)이 없거나 읽을 수 없습니다.")
        st.stop()

    df_6 = df_6th_raw.copy()
    df_6.columns = [str(c).strip() for c in df_6.columns]

    lower_col_map = {c.lower().replace(" ", "").replace("_", "").replace(".", ""): c for c in df_6.columns}

    def get_actual_col(target_str):
        cleaned = target_str.lower().replace(" ", "").replace("_", "").replace(".", "")
        return lower_col_map.get(cleaned, None)

    col_pur_m = get_actual_col("Ticket Purchase month") or "Ticket Purchase month"
    col_trip_m = get_actual_col("Trip Month") or "Trip Month"
    col_rgn = get_actual_col("4.OD RGN") or get_actual_col("OD Region") or "4.OD RGN"
    col_dir = get_actual_col("DIRECTION") or "DIRECTION"
    col_orig_c = get_actual_col("Trip Origin Country Code") or "Trip Origin Country Code"
    col_dest_c = get_actual_col("Trip Destination Country Code") or "Trip Destination Country Code"
    col_jp_apo = get_actual_col("일본 APO") or "일본 APO"
    col_ov_apo = get_actual_col("해외 APO") or "해외 APO"
    col_od_mkt = get_actual_col("Trip O&D Market") or "Trip O&D Market"
    col_al_6 = get_actual_col("Dominant Marketing Airline") or "Dominant Marketing Airline"
    col_val_6 = get_actual_col("Value") or "Value"
    col_year_type = get_actual_col("금년/전년") or "금년/전년"

    df_6['Val_num'] = pd.to_numeric(df_6[col_val_6].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if col_val_6 in df_6.columns else 0.0

    # 📌 금년 / 전년 연동 분리
    if col_year_type in df_6.columns:
        df_6['Val_CY_num'] = np.where(df_6[col_year_type].astype(str).str.contains('금년|CY', na=False), df_6['Val_num'], 0.0)
        df_6['Val_PY_num'] = np.where(df_6[col_year_type].astype(str).str.contains('전년|PY', na=False), df_6['Val_num'], 0.0)
    else:
        df_6['Val_CY_num'] = df_6['Val_num']
        df_6['Val_PY_num'] = 0.0

    # 📌 슬라이서 옵션 정밀 추출
    if col_pur_m in df_6.columns:
        all_pur_m = sorted([str(x).strip() for x in df_6[col_pur_m].dropna().unique() if str(x).strip() != 'nan'])
        default_pur_m = all_pur_m[-6:] if len(all_pur_m) >= 6 else all_pur_m
    else:
        all_pur_m, default_pur_m = [], []

    if col_trip_m in df_6.columns:
        all_trip_m = sorted([str(x).strip() for x in df_6[col_trip_m].dropna().unique() if str(x).strip() != 'nan'])
    else:
        all_trip_m = []

    all_rgn = sorted([str(x).strip() for x in df_6[col_rgn].dropna().unique() if str(x).strip() != 'nan']) if col_rgn in df_6.columns else []
    default_rgn = ["JPN-AME"] if "JPN-AME" in all_rgn else []

    all_dir = sorted([str(x).strip() for x in df_6[col_dir].dropna().unique() if str(x).strip() != 'nan']) if col_dir in df_6.columns else []
    all_orig_c = sorted([str(x).strip() for x in df_6[col_orig_c].dropna().unique() if str(x).strip() != 'nan']) if col_orig_c in df_6.columns else []
    all_dest_c = sorted([str(x).strip() for x in df_6[col_dest_c].dropna().unique() if str(x).strip() != 'nan']) if col_dest_c in df_6.columns else []
    all_jp_apo = sorted([str(x).strip() for x in df_6[col_jp_apo].dropna().unique() if str(x).strip() != 'nan']) if col_jp_apo in df_6.columns else []
    all_ov_apo = sorted([str(x).strip() for x in df_6[col_ov_apo].dropna().unique() if str(x).strip() != 'nan']) if col_ov_apo in df_6.columns else []
    all_od_mkt = sorted([str(x).strip() for x in df_6[col_od_mkt].dropna().unique() if str(x).strip() != 'nan']) if col_od_mkt in df_6.columns else []

    tab6_1, tab6_2 = st.tabs(["📊 O&D별 종합 M/S 분석 및 Carrier별 상세 비교", "📋 6수송 Raw Data View"])

    # ------------------------------------------
    # 6수송 1번 탭: 종합 M/S 분석 & Carrier별 TOP 20 O&D 매트릭스
    # ------------------------------------------
    with tab6_1:
        st.markdown('<div class="unified-sub-header">✈️ 6수송 발매 M/S 현황 (요청 9개 필터 세트)</div>', unsafe_allow_html=True)
        
        # 📌 9개 필터 박스 배치
        f6_col1, f6_col2, f6_col3, f6_col4, f6_col5 = st.columns(5)
        sel_pur_m = render_multiselect_box(f6_col1, "1. 발매 기간", all_pur_m, "slicer6_pur_m", default_pur_m)
        sel_trip_m = render_multiselect_box(f6_col2, "2. 출발 기간 (9개월)", all_trip_m, "slicer6_trip_m")
        sel_rgn = render_multiselect_box(f6_col3, "3. OD Region", all_rgn, "slicer6_rgn", default_rgn)
        sel_dir = render_multiselect_box(f6_col4, "4. 일본발/일본행", all_dir, "slicer6_dir")
        sel_orig_c = render_multiselect_box(f6_col5, "5. 출발 국가", all_orig_c, "slicer6_orig_c")

        f6_col6, f6_col7, f6_col8, f6_col9, f6_blank = st.columns(5)
        sel_dest_c = render_multiselect_box(f6_col6, "6. 도착 국가", all_dest_c, "slicer6_dest_c")
        sel_jp_apo = render_multiselect_box(f6_col7, "7. 일본 APO", all_jp_apo, "slicer6_jp_apo")
        sel_ov_apo = render_multiselect_box(f6_col8, "8. 해외 APO", all_ov_apo, "slicer6_ov_apo")
        sel_od_mkt = render_multiselect_box(f6_col9, "9. Trip O&D", all_od_mkt, "slicer6_od_mkt")

        # 필터링 마스크
        mask_6th = pd.Series(True, index=df_6.index)
        if col_pur_m in df_6.columns and sel_pur_m: mask_6th &= (df_6[col_pur_m].astype(str).isin(sel_pur_m))
        if col_trip_m in df_6.columns and sel_trip_m: mask_6th &= (df_6[col_trip_m].astype(str).isin(sel_trip_m))
        if col_rgn in df_6.columns and sel_rgn: mask_6th &= (df_6[col_rgn].astype(str).isin(sel_rgn))
        if col_dir in df_6.columns and sel_dir: mask_6th &= (df_6[col_dir].astype(str).isin(sel_dir))
        if col_orig_c in df_6.columns and sel_orig_c: mask_6th &= (df_6[col_orig_c].astype(str).isin(sel_orig_c))
        if col_dest_c in df_6.columns and sel_dest_c: mask_6th &= (df_6[col_dest_c].astype(str).isin(sel_dest_c))
        if col_jp_apo in df_6.columns and sel_jp_apo: mask_6th &= (df_6[col_jp_apo].astype(str).isin(sel_jp_apo))
        if col_ov_apo in df_6.columns and sel_ov_apo: mask_6th &= (df_6[col_ov_apo].astype(str).isin(sel_ov_apo))
        if col_od_mkt in df_6.columns and sel_od_mkt: mask_6th &= (df_6[col_od_mkt].astype(str).isin(sel_od_mkt))

        filtered_6th = df_6[mask_6th]

        # ------------------------------------------
        # 1-1) 1번째 표: 항공사별 M/S 비교표 (YOY)
        # ------------------------------------------
        if not filtered_6th.empty and col_al_6 in filtered_6th.columns:
            al_agg = filtered_6th.groupby(col_al_6, observed=False)[['Val_CY_num', 'Val_PY_num']].sum().reset_index()
            al_agg = al_agg.sort_values(by='Val_CY_num', ascending=False).reset_index(drop=True)
            
            full_al_ranking = [str(x) for x in al_agg[col_al_6].tolist()]
            ke_rank = (full_al_ranking.index('KE') + 1) if 'KE' in full_al_ranking else "-"

            top_10_no_ke = [x for x in full_al_ranking if x != 'KE'][:10]
            airline_rank_list = ['KE'] + top_10_no_ke

            html_table = '<div class="yoy-table-container"><table class="yoy-table"><thead><tr><th class="mkt-header" style="width:110px;">월별 M/S</th><th class="mkt-header" style="width:110px;">총합계</th>'
            for al_code in airline_rank_list:
                if al_code == 'KE':
                    html_table += f'<th class="ke-header" style="width:130px; background-color:#6fa8dc !important; color:#ffffff !important;">KE ({ke_rank}위)</th>'
                else:
                    rank_num = full_al_ranking.index(al_code) + 1 if al_code in full_al_ranking else "-"
                    html_table += f'<th class="carrier-header" style="width:110px;"><div style="font-size:10px; opacity:0.85;">{rank_num}위</div>{al_code}</th>'
            html_table += '</tr></thead><tbody>'

            t_curr = al_agg['Val_CY_num'].sum()
            t_prev = al_agg['Val_PY_num'].sum()
            t_yoy_pct = ((t_curr - t_prev) / t_prev * 100) if t_prev > 0 else 0

            html_table += f'<tr class="row-title"><td>전체 발매</td><td><b>{t_curr:,.0f}</b></td>'
            for al_code in airline_rank_list:
                row_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                html_table += f'<td><b>{row_val:,.0f}</b></td>'
            html_table += '</tr>'

            html_table += f'<tr><td style="color:#64748b; font-weight:600;">YOY</td>{(get_yoy_td_html(t_yoy_pct) if t_prev>0 else "<td>-</td>")}'
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                p_val = al_agg[al_agg[col_al_6] == al_code]['Val_PY_num'].sum()
                indiv_yoy = ((c_val - p_val) / p_val * 100) if p_val > 0 else 0
                html_table += (get_yoy_td_html(indiv_yoy) if p_val>0 else "<td>-</td>")
            html_table += '</tr>'

            html_table += '<tr class="row-title"><td>전체 M/S</td><td><b>100%</b></td>'
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                ms_val = (c_val / t_curr * 100) if t_curr > 0 else 0
                html_table += f'<td><b>{ms_val:.0f}%</b></td>'
            html_table += '</tr>'

            diff_total_ms = 0
            html_table += f'<tr class="row-ms-yoy"><td style="color:#64748b; font-weight:600;">YOY</td>{(get_yoy_td_html(diff_total_ms, True) if t_prev>0 else "<td>-</td>")}'
            
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                p_val = al_agg[al_agg[col_al_6] == al_code]['Val_PY_num'].sum()
                ms_c = (c_val / t_curr * 100) if t_curr > 0 else 0
                ms_p = (p_val / t_prev * 100) if t_prev > 0 else 0
                diff_p = ms_c - ms_p
                html_table += (get_yoy_td_html(diff_p, True) if t_prev>0 and p_val>0 else "<td>-</td>")
            html_table += '</tr></tbody></table></div>'
            st.markdown(html_table, unsafe_allow_html=True)

        st.markdown("---")

        # ------------------------------------------
        # 📌 1-2) 2번째 표: Carrier별 M/S (TOP 20 O&D) 종합 비교 표 복구
        # ------------------------------------------
        st.markdown('<div class="unified-sub-header">🏆 Carrier별 M/S (TOP 20 O&D)</div>', unsafe_allow_html=True)
        
        if not filtered_6th.empty and col_od_mkt in filtered_6th.columns:
            od_totals = filtered_6th.groupby(col_od_mkt, observed=False)['Val_CY_num'].sum().sort_values(ascending=False)
            top20_ods = [x for x in od_totals.index if od_totals[x] > 0][:20]

            if top20_ods:
                matrix_rows = []
                sel_carriers = [al for al in sel_al_list if al in filtered_6th[col_al_6].unique()] if 'sel_al_list' in locals() and sel_al_list else []

                for rank_i, od_code in enumerate(top20_ods, 1):
                    df_od = filtered_6th[filtered_6th[col_od_mkt] == od_code]
                    
                    # 시장 전체
                    mkt_cy = df_od['Val_CY_num'].sum()
                    mkt_py = df_od['Val_PY_num'].sum()
                    mkt_yoy = ((mkt_cy - mkt_py) / mkt_py * 100) if mkt_py > 0 else 0

                    # 선택 항공사
                    df_sel = df_od[df_od[col_al_6].isin(sel_carriers)] if sel_carriers else df_od
                    sel_cy = df_sel['Val_CY_num'].sum()
                    sel_py = df_sel['Val_PY_num'].sum()
                    sel_yoy = ((sel_cy - sel_py) / sel_py * 100) if sel_py > 0 else 0
                    sel_ms_cy = (sel_cy / mkt_cy * 100) if mkt_cy > 0 else 0
                    sel_ms_py = (sel_py / mkt_py * 100) if mkt_py > 0 else 0
                    sel_ms_yoy = sel_ms_cy - sel_ms_py

                    # KE
                    df_ke = df_od[df_od[col_al_6] == 'KE']
                    ke_cy = df_ke['Val_CY_num'].sum()
                    ke_py = df_ke['Val_PY_num'].sum()
                    ke_yoy = ((ke_cy - ke_py) / ke_py * 100) if ke_py > 0 else 0
                    ke_ms_cy = (ke_cy / mkt_cy * 100) if mkt_cy > 0 else 0

                    matrix_rows.append({
                        'rank': rank_i, 'od': od_code,
                        'mkt_cy': mkt_cy, 'mkt_py': mkt_py, 'mkt_yoy': mkt_yoy,
                        'sel_cy': sel_cy, 'sel_py': sel_py, 'sel_yoy': sel_yoy,
                        'sel_ms_cy': sel_ms_cy, 'sel_ms_py': sel_ms_py, 'sel_ms_yoy': sel_ms_yoy,
                        'ke_cy': ke_cy, 'ke_py': ke_py, 'ke_yoy': ke_yoy, 'ke_ms_cy': ke_ms_cy
                    })

                tot_mkt_cy = sum(r['mkt_cy'] for r in matrix_rows)
                tot_mkt_py = sum(r['mkt_py'] for r in matrix_rows)
                tot_mkt_yoy = ((tot_mkt_cy - tot_mkt_py) / tot_mkt_py * 100) if tot_mkt_py > 0 else 0

                tot_sel_cy = sum(r['sel_cy'] for r in matrix_rows)
                tot_sel_py = sum(r['sel_py'] for r in matrix_rows)
                tot_sel_yoy = ((tot_sel_cy - tot_sel_py) / tot_sel_py * 100) if tot_sel_py > 0 else 0
                tot_sel_ms_cy = (tot_sel_cy / tot_mkt_cy * 100) if tot_mkt_cy > 0 else 0
                tot_sel_ms_py = (tot_sel_py / tot_mkt_py * 100) if tot_mkt_py > 0 else 0
                tot_sel_ms_yoy = tot_sel_ms_cy - tot_sel_ms_py

                tot_ke_cy = sum(r['ke_cy'] for r in matrix_rows)
                tot_ke_py = sum(r['ke_py'] for r in matrix_rows)
                tot_ke_yoy = ((tot_ke_cy - tot_ke_py) / tot_ke_py * 100) if tot_ke_py > 0 else 0
                tot_ke_ms_cy = (tot_ke_cy / tot_mkt_cy * 100) if tot_mkt_cy > 0 else 0

                od_matrix_html = '''
                <div class="custom-piv-container">
                <table class="custom-piv-table">
                <thead>
                    <tr>
                        <th rowspan="2" class="header-main" style="width:40px;">순위</th>
                        <th rowspan="2" class="header-main" style="width:110px;">TOP O&D</th>
                        <th colspan="3" class="header-main" style="background-color:#215b88 !important; color:#ffffff !important;">시장 전체</th>
                        <th colspan="3" class="header-main" style="background-color:#1e4e79 !important; color:#ffffff !important;">선택 항공사 발매량</th>
                        <th colspan="3" class="header-main" style="background-color:#1b3d5a !important; color:#ffffff !important;">선택 항공사 M/S</th>
                        <th colspan="4" class="header-main" style="background-color:#16a34a !important; color:#ffffff !important;">KE 발매량</th>
                    </tr>
                    <tr>
                        <th class="header-main" style="background-color:#3172ac !important; color:#ffffff !important;">금년</th>
                        <th class="header-main" style="background-color:#3172ac !important; color:#ffffff !important;">전년</th>
                        <th class="header-main" style="background-color:#3172ac !important; color:#ffffff !important;">YOY</th>
                        <th class="header-main" style="background-color:#28629b !important; color:#ffffff !important;">금년</th>
                        <th class="header-main" style="background-color:#28629b !important; color:#ffffff !important;">전년</th>
                        <th class="header-main" style="background-color:#28629b !important; color:#ffffff !important;">YOY</th>
                        <th class="header-main" style="background-color:#204f77 !important; color:#ffffff !important;">M/S</th>
                        <th class="header-main" style="background-color:#204f77 !important; color:#ffffff !important;">전년</th>
                        <th class="header-main" style="background-color:#204f77 !important; color:#ffffff !important;">YOY</th>
                        <th class="header-main" style="background-color:#22c55e !important; color:#ffffff !important;">금년</th>
                        <th class="header-main" style="background-color:#22c55e !important; color:#ffffff !important;">전년</th>
                        <th class="header-main" style="background-color:#22c55e !important; color:#ffffff !important;">YOY</th>
                        <th class="header-main" style="background-color:#22c55e !important; color:#ffffff !important;">M/S</th>
                    </tr>
                </thead>
                <tbody>
                '''

                for r in matrix_rows:
                    od_matrix_html += f'''
                    <tr>
                        <td style="font-weight:700;">{r['rank']}</td>
                        <td style="font-weight:700;">{r['od']}</td>
                        <td>{r['mkt_cy']:,.0f}</td>
                        <td style="color:#64748b;">{r['mkt_py']:,.0f}</td>
                        {get_yoy_td_html(r['mkt_yoy'])}
                        <td style="font-weight:700;">{r['sel_cy']:,.0f}</td>
                        <td style="color:#64748b;">{r['sel_py']:,.0f}</td>
                        {get_yoy_td_html(r['sel_yoy'])}
                        <td style="font-weight:700;">{r['sel_ms_cy']:.0f}%</td>
                        <td style="color:#64748b;">{r['sel_ms_py']:.0f}%</td>
                        {get_yoy_td_html(r['sel_ms_yoy'], True)}
                        <td style="font-weight:700; color:#16a34a;">{r['ke_cy']:,.0f}</td>
                        <td style="color:#64748b;">{r['ke_py']:,.0f}</td>
                        {get_yoy_td_html(r['ke_yoy'])}
                        <td style="font-weight:700; color:#16a34a;">{r['ke_ms_cy']:.1f}%</td>
                    </tr>
                    '''

                od_matrix_html += f'''
                <tr class="row-title" style="background-color:#f1f5f9 !important; font-weight:800;">
                    <td colspan="2">금년 요약</td>
                    <td><b>{tot_mkt_cy:,.0f}</b></td>
                    <td style="color:#64748b;"><b>{tot_mkt_py:,.0f}</b></td>
                    {get_yoy_td_html(tot_mkt_yoy)}
                    <td><b>{tot_sel_cy:,.0f}</b></td>
                    <td style="color:#64748b;"><b>{tot_sel_py:,.0f}</b></td>
                    {get_yoy_td_html(tot_sel_yoy)}
                    <td><b>{tot_sel_ms_cy:.0f}%</b></td>
                    <td style="color:#64748b;"><b>{tot_sel_ms_py:.0f}%</b></td>
                    {get_yoy_td_html(tot_sel_ms_yoy, True)}
                    <td style="color:#16a34a;"><b>{tot_ke_cy:,.0f}</b></td>
                    <td style="color:#64748b;"><b>{tot_ke_py:,.0f}</b></td>
                    {get_yoy_td_html(tot_ke_yoy)}
                    <td style="color:#16a34a;"><b>{tot_ke_ms_cy:.0f}%</b></td>
                </tr>
                </tbody></table></div>
                '''
                st.markdown(od_matrix_html, unsafe_allow_html=True)
            else:
                st.info("💡 실적이 존재하는 O&D Market이 없습니다.")

    # ------------------------------------------
    # 6수송 2번 탭: Raw Data View 및 다운로드
    # ------------------------------------------
    with tab6_2:
        st.subheader("📋 6수송 사전 집계 Data 조회 및 다운로드")
        if not filtered_6th.empty:
            csv_6th_bytes = filtered_6th.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 필터링된 6수송 Data (CSV) 다운로드",
                data=csv_6th_bytes,
                file_name=f"6th_Freedom_Data_{datetime.date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            st.markdown("*(속도 최적화를 위해 상위 100건 샘플만 표출합니다)*")
            st.dataframe(filtered_6th.head(100), width="stretch")
        else:
            st.info("💡 선택하신 슬라이서 조건에 해당하는 6수송 데이터가 없습니다.")

# ==========================================
# GROUP 3: 🔗 W26 연결 네트워크
# ==========================================
else:
    st.markdown('<div class="unified-sub-header">🔗 대한항공 W26 연결 네트워크 외부 연동 시스템</div>', unsafe_allow_html=True)
    st.link_button("🔗 W26 연결 네트워크 바로가기 (새 탭에서 열기)", EXT_WEB_APP_URL, use_container_width=True)