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
AIRLINE_WEIGHT_MULTIPLIERS = {
    'KE': 1.0, 'OZ': 1.0, '7C': 4.75884657, 'LJ': 4.387110992, 'TW': 4.413912854,
    'BX': 1.865842867, 'RS': 1.758028702, 'JL': 1.0, 'NH': 1.0, 'ET': 1.0,
    'YP': 5.92588446, 'ZE': 3.783327953, 'WE': 1.0
}

# 📌 Streamlit의 강제 테마 오버라이드를 완전히 제압하는 클래스 기반 CSS 정의
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
    .metric-card { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.03); margin-bottom: 10px; }
    .metric-card-ke { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.03); margin-bottom: 10px; }
    .metric-title { font-size: 12.5px; color: #64748b; margin-bottom: 4px; font-weight: 500; }
    .metric-value { font-size: 22px; color: #1e293b; font-weight: 700; }
    .custom-piv-container, .yoy-table-container { width: 100%; overflow-x: auto; margin-bottom: 20px; border-radius: 8px; border: 1px solid #cbd5e1 !important; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
    .custom-piv-table, .yoy-table { width: 100%; border-collapse: collapse; font-size: 12.5px; background-color: #ffffff; text-align: center !important; table-layout: fixed !important; }
    .custom-piv-table th.header-main, .yoy-table th, .yoy-table th.mkt-header, .yoy-table th.carrier-header { background-color: #cfe2f3 !important; color: #0f172a !important; padding: 8px 6px; border: 1px solid #cbd5e1 !important; font-weight: 600; text-align: center !important; white-space: nowrap; }
    .yoy-table th.ke-header { background-color: #6fa8dc !important; color: #ffffff !important; padding: 8px 6px; border: 1px solid #cbd5e1 !important; font-size: 13px !important; font-weight: 700 !important; text-align: center !important; white-space: nowrap; }
    .custom-piv-table td, .yoy-table td { padding: 6px 10px; border: 1px solid #cbd5e1 !important; text-align: center !important; }
    .yoy-table tr:hover { background-color: #f8fafc !important; }
    
    /* 🔥 여기부터가 색상을 강제로 고정하는 전용 클래스들입니다 🔥 */
    table.custom-piv-table td span.yoy-up, table.yoy-table td span.yoy-up { color: #1d4ed8 !important; font-weight: 700 !important; }
    table.custom-piv-table td span.yoy-down, table.yoy-table td span.yoy-down { color: #dc2626 !important; font-weight: 700 !important; }
    table.custom-piv-table td span.yoy-dash, table.yoy-table td span.yoy-dash { color: #64748b !important; font-weight: 500 !important; }
    table.custom-piv-table td.bg-ke-light, table.yoy-table td.bg-ke-light { background-color: #cfe2f3 !important; }
    table.custom-piv-table td.bg-ke-mid, table.yoy-table td.bg-ke-mid { background-color: #c9daf8 !important; }
    table.custom-piv-table td.bg-ke-dark, table.yoy-table td.bg-ke-dark { background-color: #9fc5e8 !important; }
    table.custom-piv-table td.bg-subtotal, table.yoy-table td.bg-subtotal { background-color: #f1f5f9 !important; }
    table.custom-piv-table td.bg-grandtotal, table.yoy-table td.bg-grandtotal { background-color: #e2e8f0 !important; }
    table.custom-piv-table td span.txt-ke-bold, table.yoy-table td span.txt-ke-bold { color: #0b5394 !important; font-weight: 800 !important; }
</style>
""", unsafe_allow_html=True)

st.sidebar.header("📁 실시간 데이터 업로드")
uploaded_iss = st.sidebar.file_uploader("1. 3/4수송 Parquet/CSV 캐시", type=['parquet', 'csv', 'xlsx'], key="sb_uploader_iss")
uploaded_sup = st.sidebar.file_uploader("2. 공급 데이터", type=['csv', 'xlsx', 'zip', 'parquet'], key="sb_uploader_sup")
uploaded_6th = st.sidebar.file_uploader("3. 6수송 데이터", type=['csv', 'xlsx', 'zip', 'parquet'], key="sb_uploader_6th")

def optimize_df(df_in):
    if df_in is None: return None
    for col in df_in.columns:
        if df_in[col].dtype == 'object':
            if df_in[col].nunique() < len(df_in) * 0.5: df_in[col] = df_in[col].astype('category')
        elif df_in[col].dtype == 'int64': df_in[col] = df_in[col].astype('int32')
        elif df_in[col].dtype == 'float64': df_in[col] = df_in[col].astype('float32')
    return df_in

def clean_transport_column(df):
    if df is None: return df
    b_col = '수송' if '수송' in df.columns else ('Bound' if 'Bound' in df.columns else None)
    if b_col: df['수송'] = df[b_col].astype(str).str.strip()
    return df

@st.cache_data(ttl=3600, show_spinner="3/4수송 데이터를 읽어오는 중...")
def load_fast_parquet_data_file():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(base_dir, 'cache_34_data.parquet')
    if os.path.exists(target_path): return optimize_df(clean_transport_column(pd.read_parquet(target_path)))
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def process_any_uploaded_file(file_obj):
    file_obj.seek(0)
    if file_obj.name.endswith('.parquet'): df = pd.read_parquet(file_obj)
    elif file_obj.name.endswith('.xlsx'): df = pd.read_excel(file_obj)
    else: df = pd.read_csv(file_obj, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    return optimize_df(clean_transport_column(df))

@st.cache_data(ttl=3600, show_spinner=False)
def load_aux_files():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for sp in [os.path.join(base_dir, '공급.csv'), '공급.csv']:
        if os.path.exists(sp):
            try:
                df = pd.read_csv(sp, low_memory=False)
                if df is not None and not df.empty: return optimize_df(df)
            except: pass
    return None

@st.cache_data(ttl=3600, show_spinner="🌐 6수송 집계 데이터를 로드하는 중...")
def load_6th_data_aggregated():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for sp in [os.path.join(base_dir, 'cache_6th_data.parquet'), 'cache_6th_data.parquet']:
        if os.path.exists(sp):
            try: return optimize_df(pd.read_parquet(sp, engine='pyarrow'))
            except: pass
    return None

disk_sup = load_aux_files()
df_iss_merged = process_any_uploaded_file(uploaded_iss) if uploaded_iss else load_fast_parquet_data_file()
df_sup_raw = disk_sup

st.markdown('<div class="main-app-title">✈️ 일본노선 발매/공급 Market Share</div>', unsafe_allow_html=True)
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

# 📌 동적 날짜 범위 표출 헬퍼 함수
def get_dynamic_range_label(opts):
    if not opts: return ""
    valid_opts = [x for x in opts if '-' in x and len(x) == 7]
    if not valid_opts: return ""
    min_opt = min(valid_opts)
    max_opt = max(valid_opts)
    y1, m1 = min_opt[2:4], int(min_opt[5:7])
    y2, m2 = max_opt[2:4], int(max_opt[5:7])
    if y1 == y2:
        return f" ({y1}년 {m1}월~{m2}월)"
    else:
        return f" ({y1}년 {m1}월~{y2}년 {m2}월)"

# 📌 CSS 클래스를 활용한 완벽한 YOY 색상 강제 렌더링 함수
def get_yoy_td_html(val, is_percentage_point=False, bg_class=""):
    unit = "%p" if is_percentage_point else "%"
    class_str = f' class="{bg_class}"' if bg_class else ''
    
    if val > 0: 
        return f'<td{class_str} style="text-align:center !important;"><span class="yoy-up">▲ {val:.1f}{unit}</span></td>'
    elif val < 0: 
        return f'<td{class_str} style="text-align:center !important;"><span class="yoy-down">▼ {abs(val):.1f}{unit}</span></td>'
    else: 
        return f'<td{class_str} style="text-align:center !important;"><span class="yoy-dash">-</span></td>'

def get_dash_td(bg_class=""):
    class_str = f' class="{bg_class}"' if bg_class else ''
    return f'<td{class_str} style="text-align:center !important;"><span class="yoy-dash">-</span></td>'

# ==========================================
# GROUP 1: ✈️ 3/4수송 대시보드
# ==========================================
if selected_group == "✈️ 3/4수송 대시보드":
    m_col_34 = '출발월' if '출발월' in df_iss_merged.columns else ('출발 월' if '출발 월' in df_iss_merged.columns else 'Trip Month')
    w_col_34 = '발매주차_일자' if '발매주차_일자' in df_iss_merged.columns else ('발매 주차' if '발매 주차' in df_iss_merged.columns else 'Purchase Month')
    
    if df_iss_merged is not None and not df_iss_merged.empty:
        dep_str_34 = f"{sorted([str(x).strip() for x in df_iss_merged[m_col_34].dropna().unique() if str(x).strip() != 'nan'])[0]} ~ {sorted([str(x).strip() for x in df_iss_merged[m_col_34].dropna().unique() if str(x).strip() != 'nan'])[-1]}" if m_col_34 in df_iss_merged.columns else dep_range_str
        iss_str_34 = f"{sorted([str(x).strip() for x in df_iss_merged[w_col_34].dropna().unique() if str(x).strip() != 'nan'])[0]} ~ {sorted([str(x).strip() for x in df_iss_merged[w_col_34].dropna().unique() if str(x).strip() != 'nan'])[-1]}" if w_col_34 in df_iss_merged.columns else issue_range_str
    else:
        dep_str_34, iss_str_34 = dep_range_str, issue_range_str

    st.markdown(f'<div class="source-header-box"><b>📌 출처: DDS & OAG 데이터 (3/4수송 대시보드)</b> &nbsp;|&nbsp; <b>🗓️ 발매기간:</b> {iss_str_34} (과거 5주) &nbsp;|&nbsp; <b>✈️ 출발기간:</b> {dep_str_34} (향후 6개월)</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    tab_34_1, tab_34_2, tab_34_3, tab_34_4 = st.tabs(["🎟️ 발매 M/S", "✈️ 공급 M/S", "🏷️ 대리점,RBD별 발매현황", "👥 단체실적"])

    with tab_34_1:
        if df_iss_merged is None: st.warning("❌ 3/4수송 데이터를 찾을 수 없습니다."); st.stop()
        merged_df = df_iss_merged.copy()
        al_col_target = next((c for c in ['Dominant Marketing Airline', 'AL', '항공사', 'Marketing Airline'] if c in merged_df.columns), None)
        merged_df['AL_clean'] = merged_df[al_col_target].astype(str).str.strip().str.upper() if al_col_target else ''
        merged_df['노선_clean'] = merged_df['노선'].astype(str).str.strip()

        region_col = next((c for c in merged_df.columns if str(c).replace(" ", "") in ['일본권역', '권역', 'JapanRegion', 'Region']), None)
        bound_raw_col = next((c for c in merged_df.columns if str(c).replace(" ", "") in ['Bound', 'BOUND', '방향', '바운드']), None)
        week_col = w_col_34
        month_col = m_col_34
        bound_col = '수송' if '수송' in merged_df.columns else ('Bound' if 'Bound' in merged_df.columns else None)

        with st.expander("🔍 **발매 대시보드 피벗 슬라이서 필터 설정** (종속형 순차 필터링)", expanded=True):
            apply_weight_toggle = st.toggle("⚖️ 가중치 적용 M/S 산출", value=True, key="main_wt_toggle_fixed")
            
            temp_df_34 = merged_df.copy()
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            
            opts_rgn = sorted([str(x).strip() for x in temp_df_34[region_col].dropna().unique() if str(x).strip() != 'nan']) if region_col else []
            sel_region_list = render_multiselect_box(f_col1, "1. 일본권역", opts_rgn, "slicer_region_multi")
            if sel_region_list: temp_df_34 = temp_df_34[temp_df_34[region_col].astype(str).str.strip().isin(sel_region_list)]

            opts_route = sorted([str(x).strip() for x in temp_df_34['노선_clean'].dropna().unique() if str(x).strip() != 'nan'])
            sel_route_list = render_multiselect_box(f_col2, "2. KE취항노선", opts_route, "slicer_route_multi")
            if sel_route_list: temp_df_34 = temp_df_34[temp_df_34['노선_clean'].isin(sel_route_list)]

            opts_week = sorted([str(x).strip() for x in temp_df_34[week_col].dropna().unique() if str(x).strip() != 'nan']) if week_col else []
            sel_week_list = render_multiselect_box(f_col3, "3. 발매 주차", opts_week, "slicer_week_multi")
            if sel_week_list: temp_df_34 = temp_df_34[temp_df_34[week_col].astype(str).str.strip().isin(sel_week_list)]

            opts_month = sorted([str(x).strip() for x in temp_df_34[month_col].dropna().unique() if str(x).strip() != 'nan']) if month_col else []
            sel_month_list = render_multiselect_box(f_col4, "4. 출발 월", opts_month, "slicer_month_multi")
            if sel_month_list: temp_df_34 = temp_df_34[temp_df_34[month_col].astype(str).str.strip().isin(sel_month_list)]

            f_col5, f_col6, f_col7, f_col8 = st.columns(4)
            
            opts_bound = sorted([str(x).strip() for x in temp_df_34[bound_col].dropna().unique() if str(x).strip() != 'nan']) if bound_col else []
            sel_bound_list = render_multiselect_box(f_col5, "5. 수송 구분", opts_bound, "slicer_bound_multi")
            if sel_bound_list: temp_df_34 = temp_df_34[temp_df_34[bound_col].astype(str).str.strip().isin(sel_bound_list)]

            opts_bound_raw = sorted([str(x).strip() for x in temp_df_34[bound_raw_col].dropna().unique() if str(x).strip() != 'nan']) if bound_raw_col else []
            sel_bound_raw_list = render_multiselect_box(f_col6, "6. Bound", opts_bound_raw, "slicer_bound_raw_multi")
            if sel_bound_raw_list: temp_df_34 = temp_df_34[temp_df_34[bound_raw_col].astype(str).str.strip().isin(sel_bound_raw_list)]

            opts_tt = sorted([str(x).strip() for x in temp_df_34['Ticket Type'].dropna().unique() if str(x).strip() != 'nan']) if 'Ticket Type' in temp_df_34.columns else []
            sel_tt_list = render_multiselect_box(f_col7, "7. Trip Type", opts_tt, "slicer_tt_multi")
            if sel_tt_list: temp_df_34 = temp_df_34[temp_df_34['Ticket Type'].astype(str).str.strip().isin(sel_tt_list)]

            opts_al = sorted([str(x).strip() for x in temp_df_34['AL_clean'].dropna().unique() if str(x).strip() != 'nan'])
            opts_al = ['KE'] + [x for x in opts_al if x != 'KE'] if 'KE' in opts_al else opts_al
            sel_al_list = render_multiselect_box(f_col8, "8. 항공사", opts_al, "slicer_al_multi")
            if sel_al_list: temp_df_34 = temp_df_34[temp_df_34['AL_clean'].isin(sel_al_list)]

        filtered_df = temp_df_34.copy()

        if not sel_route_list and not sel_region_list:
            filtered_df = filtered_df[filtered_df['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER)]

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

        top_al, top_ms = "-", 0.0
        if not filtered_df.empty and total_pax > 0:
            if apply_weight_toggle:
                top_al, top_ms = str(al_ms_normalized.idxmax()), float(al_ms_normalized.max())
            else:
                al_sum = filtered_df.groupby('AL_clean', observed=False)[val_col].sum()
                top_al, top_ms = str(al_sum.idxmax()), (al_sum.max() / total_pax) * 100

        top_route = str(filtered_df.groupby('노선_clean', observed=False)[val_col].sum().idxmax()) if not filtered_df.empty and total_pax > 0 else "-"
        status_wt_label = " (가중치 보정)" if apply_weight_toggle else " (Raw)"

        tab1, tab2, tab3 = st.tabs(["📈 시각화 분석 차트", "📊 M/S 피벗 테이블", "🔒 Raw Data View (관리자 전용)"])
        with tab1:
            if not filtered_df.empty:
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
                    colors_list = [build_airline_color_map(opts_al).get(al, '#94a3b8') for al in pie_al['AL_clean']]

                    fig1 = go.Figure(data=[go.Pie(labels=labels_list, values=values_for_pie, text=text_labels_pie, textinfo='label+text' if apply_weight_toggle else 'percent+label', hole=0.4, pull=pull_list, marker=dict(colors=colors_list), textposition='inside')])
                    apply_bottom_legend(fig1)
                    st.plotly_chart(fig1, width='stretch')

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
                        top_al_in_week = df_no_week.groupby('AL_clean', observed=False)[val_col].sum().sort_values(ascending=False).index.tolist()
                        top_al_week_display = ['KE'] + [al for al in top_al_in_week if al != 'KE'][:5]
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
                        fig_week_ms.update_layout(yaxis_title="Market Share (%)", xaxis=dict(categoryorder='array', categoryarray=opts_week), yaxis=dict(range=[0, max(week_merged_top['MS_Percent'].max() * 1.25, 15)]), height=450)
                        apply_bottom_legend(fig_week_ms)
                        st.plotly_chart(fig_week_ms, width='stretch')

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
                        top_al_in_dep = df_dep_al.groupby('AL_clean', observed=False)[val_col].sum().sort_values(ascending=False).index.tolist()
                        top_al_display = ['KE'] + [al for al in top_al_in_dep if al != 'KE'][:5]
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
                        fig_ke_dep.update_layout(yaxis_title="Market Share (%)", xaxis=dict(categoryorder='array', categoryarray=opts_month), yaxis=dict(range=[0, max(dep_merged_top['MS_Percent'].max() * 1.25, 15)]), height=420)
                        apply_bottom_legend(fig_ke_dep)
                        st.plotly_chart(fig_ke_dep, width='stretch')

                st.markdown("---")
                
                c3, c4 = st.columns(2)
                ke_only_df = filtered_df[filtered_df['AL_clean'] == 'KE']
                with c3:
                    if bound_col:
                        st.markdown('<div class="unified-sub-header">4. 수송 구분별 점유비 (KE 한정)</div>', unsafe_allow_html=True)
                        bound_pie_df = ke_only_df.groupby(bound_col, observed=False)[val_col].sum().reset_index()
                        fig3 = px.pie(bound_pie_df, values=val_col, names=bound_col, hole=0.4)
                        fig3.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>구분: %{label}</b><br>실적: %{value:,.0f}<br>점유율: %{percent:.1%}<extra></extra>")
                        apply_bottom_legend(fig3)
                        st.plotly_chart(fig3, width='stretch')
                with c4:
                    if 'Ticket Type' in merged_df.columns:
                        st.markdown('<div class="unified-sub-header">5. Trip Type별 점유비 (KE 한정)</div>', unsafe_allow_html=True)
                        tt_pie_df = ke_only_df.groupby('Ticket Type', observed=False)[val_col].sum().reset_index()
                        fig4 = px.pie(tt_pie_df, values=val_col, names='Ticket Type', hole=0.4)
                        fig4.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>Trip Type: %{label}</b><br>실적: %{value:,.0f}<br>점유율: %{percent:.1%}<extra></extra>")
                        apply_bottom_legend(fig4)
                        st.plotly_chart(fig4, width='stretch')

        with tab2:
            st.markdown("##### 📌 주차별 및 노선별 발매 M/S 매트릭스")
            t1, t2 = st.columns([1.1, 1])
            with t1:
                if week_col and week_col in filtered_df.columns:
                    piv_w = filtered_df.pivot_table(index='AL_clean', columns=week_col, values=val_col, aggfunc='sum', fill_value=0, observed=False)
                    piv_w_ms = piv_w.divide(piv_w.sum(axis=0), axis=1) * 100
                    al_sorted = ['KE'] + [x for x in piv_w_ms.index if x != 'KE'] if 'KE' in piv_w_ms.index else piv_w_ms.index
                    piv_w_ms = piv_w_ms.loc[al_sorted].head(100)
                    piv_w_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead><tr><th class="header-main" style="width:100px;">AL_clean</th>'
                    for col_wk in piv_w_ms.columns: piv_w_html += f'<th class="header-main">{col_wk}</th>'
                    piv_w_html += '</tr></thead><tbody>'
                    for al_idx, row_item in piv_w_ms.iterrows():
                        is_ke_r = (str(al_idx).upper() == 'KE')
                        td_class = ' class="bg-ke-light"' if is_ke_r else ''
                        k_span = '<span class="txt-ke-bold">' if is_ke_r else '<span>'
                        piv_w_html += f'<tr><td{td_class}>{k_span}{al_idx}</span></td>'
                        for val_ms in row_item: piv_w_html += f'<td{td_class}>{val_ms:.1f}%</td>'
                        piv_w_html += '</tr>'
                    piv_w_html += '</tbody></table></div>'
                    st.markdown(piv_w_html, unsafe_allow_html=True)
            with t2:
                piv_r = filtered_df.pivot_table(index='노선_clean', columns='AL_clean', values=val_col, aggfunc='sum', fill_value=0, observed=False)
                cols_ke = ['KE'] + [x for x in piv_r.columns if x != 'KE'] if 'KE' in piv_r.columns else piv_r.columns
                piv_r_ms = piv_r[cols_ke].divide(piv_r.sum(axis=1), axis=0) * 100
                piv_r_ms = piv_r_ms.head(100)
                piv_r_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead><tr><th class="header-main" style="width:100px;">노선_clean</th>'
                for col_al in piv_r_ms.columns:
                    is_ke_c = (str(col_al).upper() == 'KE')
                    th_class = ' class="bg-ke-light"' if is_ke_c else ''
                    k_span = '<span class="txt-ke-bold">' if is_ke_c else '<span>'
                    piv_r_html += f'<th{th_class}>{k_span}{col_al}</span></th>'
                piv_r_html += '</tr></thead><tbody>'
                for route_idx, row_item in piv_r_ms.iterrows():
                    piv_r_html += f'<tr><td style="font-weight:700;">{route_idx}</td>'
                    for al_col_name, val_ms in row_item.items():
                        is_ke_c = (str(al_col_name).upper() == 'KE')
                        td_class = ' class="bg-ke-light"' if is_ke_c else ''
                        k_span = '<span class="txt-ke-bold">' if is_ke_c else '<span>'
                        piv_r_html += f'<td{td_class}>{k_span}{val_ms:.1f}%</span></td>'
                    piv_r_html += '</tr>'
                piv_r_html += '</tbody></table></div>'
                st.markdown(piv_r_html, unsafe_allow_html=True)

        with tab3:
            st.subheader("🔒 관리자 전용 Raw Data 조회 및 다운로드")
            admin_pw = st.text_input("🔑 관리자 비밀번호를 입력하세요:", type="password", key="admin_pw_fixed")
            if admin_pw == "1234":
                csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 필터링된 발매 Raw Data (CSV) 전체 다운로드", data=csv_data, file_name=f"Ticketing_Raw_Data_{datetime.date.today().strftime('%Y%m%d')}.csv", mime="text/csv")
                st.dataframe(filtered_df.head(100), width='stretch')
            else: st.info("ℹ️ 관리자 비밀번호 입력 시 이용할 수 있습니다.")

    # ------------------------------------------
    # 2. ✈️ 공급 M/S 탭
    # ------------------------------------------
    with tab_34_2:
        df_sup = df_sup_raw.copy() if df_sup_raw is not None else None
        if df_sup is not None:
            df_sup.columns = [str(c).strip() for c in df_sup.columns]
            al_col = next((c for c in ['Op Airline Code', 'Mkt Al', 'Airline', 'Op Airline', 'CARRIER', '항공사'] if c in df_sup.columns), None)
            df_sup['Airline'] = df_sup[al_col] if al_col else 'Unknown'
            if '노선' in df_sup.columns: df_sup['노선_clean'] = df_sup['노선'].astype(str).str.strip()
            df_sup['KE_취항여부'] = np.where(df_sup['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER), '취항', '미취항')
            df_sup['출발공항'] = df_sup['노선_clean'].apply(lambda x: KOREA_APO_MAP.get(str(x).split('/')[0].strip().upper(), '기타') if '/' in str(x) else '기타')
            df_sup['도착공항'] = df_sup['노선_clean'].apply(lambda x: str(x).split('/')[1].strip().upper() if '/' in str(x) else str(x).strip().upper())
            df_sup['Seats_num'] = pd.to_numeric(df_sup['Seats'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if 'Seats' in df_sup.columns else 0
            df_sup['Flights_num'] = pd.to_numeric(df_sup['Flights'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if 'Flights' in df_sup.columns else 1
            sup_month_col = next((c for c in ['출발월', '출발 월', 'Travel Month'] if c in df_sup.columns), None)

            temp_sup = df_sup.copy()
            st.markdown('<div class="unified-sub-header">🔍 공급 대시보드 필터 설정 (종속형 순차 필터링)</div>', unsafe_allow_html=True)
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

            # 📌 공급 월 필터에서 1900년 찌꺼기 원천 삭제
            opts_sup_m = sorted([str(x) for x in temp_sup[sup_month_col].dropna().unique() if '1900' not in str(x) and str(x).strip() != 'nan']) if sup_month_col else []
            sel_sup_month_list = render_multiselect_box(sf_col4, "4. 출발 월", opts_sup_m, "slicer_month_sup_multi")
            if sel_sup_month_list: temp_sup = temp_sup[temp_sup[sup_month_col].isin(sel_sup_month_list)]

            opts_sup_al = sorted([str(x) for x in temp_sup['Airline'].dropna().unique()])
            opts_sup_al = ['KE'] + [x for x in opts_sup_al if x != 'KE'] if 'KE' in opts_sup_al else opts_sup_al
            sel_sup_al_list = render_multiselect_box(sf_col5, "5. 항공사", opts_sup_al, "slicer_al_sup_multi")
            if sel_sup_al_list: temp_sup = temp_sup[temp_sup['Airline'].isin(sel_sup_al_list)]

            filtered_sup = temp_sup

            st.markdown("---")
            
            st.markdown('<div class="unified-sub-header">3. 노선별 운항 스케줄 타임라인 (경쟁사 포함 - 산점도)</div>', unsafe_allow_html=True)
            
            ke_operated_routes = df_sup[df_sup['Airline'] == 'KE']['노선_clean'].dropna().unique().tolist()
            sup_avail_routes = [r for r in filtered_sup['노선_clean'].dropna().unique() if r in ke_operated_routes]
            
            if not sup_avail_routes:
                st.info("💡 선택하신 조건에 해당하는 스케줄 데이터가 없습니다.")
            else:
                tl_col1, tl_col2 = st.columns(2)
                with tl_col1:
                    selected_single_route = st.selectbox("📌 스케줄 타임라인 노선 선택:", options=sup_avail_routes, key="sb_timeline_route_sel")
                
                df_schedule_route = filtered_sup[filtered_sup['노선_clean'] == selected_single_route].copy() if '노선_clean' in filtered_sup.columns else filtered_sup[filtered_sup['노선'] == selected_single_route].copy()
                
                with tl_col2:
                    if sup_month_col and not df_schedule_route.empty:
                        avail_tl_months = sorted([str(x) for x in df_schedule_route[sup_month_col].dropna().unique() if '1900' not in str(x)])
                        sel_tl_months = st.multiselect("🗓️ 출발 월 필터 (미선택 시 전체):", options=avail_tl_months, default=[])
                        if sel_tl_months:
                            df_schedule = df_schedule_route[df_schedule_route[sup_month_col].astype(str).isin(sel_tl_months)].copy()
                        else:
                            df_schedule = df_schedule_route.copy()
                    else:
                        df_schedule = df_schedule_route.copy()

                if not df_schedule.empty and 'Dep Time' in df_schedule.columns:
                    def parse_time_to_minutes(val):
                        val_str = str(val).strip()
                        if not val_str or val_str.lower() in ['nan', 'none', 'nat']: return 9*60
                        if ':' in val_str:
                            parts = val_str.split(':')
                            hh, mm = int(parts[0]), int(parts[1])
                        else:
                            if val_str.endswith('.0'): val_str = val_str[:-2]
                            val_str = val_str.zfill(4)
                            hh, mm = int(val_str[:2]), int(val_str[2:4])
                        hh = min(hh, 23)
                        mm = min(mm, 59)
                        return hh * 60 + mm

                    df_schedule['Dep_Time_Mins'] = df_schedule['Dep Time'].apply(parse_time_to_minutes)
                    df_schedule['Dep_Time_Str'] = df_schedule['Dep_Time_Mins'].apply(lambda x: f"{x//60:02d}:{x%60:02d}")
                    
                    timeline_color_map = build_airline_color_map(df_schedule['Airline'].unique())
                    
                    # 📌 KE 다이아몬드 + 크기 차별화 심볼 매핑
                    symbol_map = {al: 'diamond' if al == 'KE' else 'circle' for al in df_schedule['Airline'].unique()}

                    fig_timeline = px.scatter(
                        df_schedule, x="Dep_Time_Mins", y="Airline", color="Airline", 
                        symbol="Airline", symbol_map=symbol_map,
                        title=f"[{selected_single_route}] 하루 출발 시간대별 운항 스케줄 분포 (산점도)", 
                        color_discrete_map=timeline_color_map,
                        custom_data=["Seats_num", "Dep_Time_Str"]
                    )
                    
                    # 마커 크기 및 테두리 세부 조정 (KE는 더 크게)
                    for trace in fig_timeline.data:
                        if trace.name == 'KE': trace.marker.size = 18
                        else: trace.marker.size = 14
                        trace.marker.line.width = 2
                        trace.marker.line.color = 'white'
                        trace.opacity = 0.95

                    min_mins = max(0, df_schedule['Dep_Time_Mins'].min() - 30)
                    max_mins = df_schedule['Dep_Time_Mins'].max() + 30
                    tick_vals = list(range(0, 25*60, 60))
                    tick_texts = [f"{h:02d}:00" for h in range(25)]

                    # 📌 Y축 KE 텍스트 Bold 강조
                    unique_al_sorted = df_schedule['Airline'].drop_duplicates().tolist()
                    tick_vals_y = unique_al_sorted
                    tick_text_y = ["<b>KE</b>" if al == "KE" else al for al in unique_al_sorted]

                    fig_timeline.update_yaxes(autorange="reversed", title="항공사", tickvals=tick_vals_y, ticktext=tick_text_y)
                    fig_timeline.update_xaxes(title="출발 시간대", tickvals=tick_vals, ticktext=tick_texts, range=[min_mins, max_mins])
                    
                    fig_timeline.update_traces(
                        hovertemplate="<b>항공사: %{y}</b><br>출발시각: %{customdata[1]}<br>공급석: %{customdata[0]:,.0f}석<extra></extra>"
                    )
                    fig_timeline.update_layout(height=350, showlegend=False)
                    st.plotly_chart(fig_timeline, width='stretch')
                else:
                    st.info("선택한 조건에 해당하는 스케줄 데이터가 없습니다.")

    # 📌 3. 🏷️ 대리점, RBD별 발매현황 탭
    with tab_34_3:
        # 에러 방지를 위한 탭 내부 지역 변수 재선언
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
            week_col_a = '발매주차_일자' if '발매주차_일자' in df_agency.columns else ('발매 주차' if '발매 주차' in df_agency.columns else '발매주차')
            month_col_a = '출발월' if '출발월' in df_agency.columns else ('출발 월' if '출발 월' in df_agency.columns else None)
            bound_col_a = '수송' if '수송' in df_agency.columns else ('Bound' if 'Bound' in df_agency.columns else None)
            df_agency['노선_clean'] = df_agency['노선'].astype(str).str.strip()

            temp_ag = df_agency.copy()
            with st.expander("🔍 **대리점 & RBD 분석 피벗 슬라이서 필터 설정** (종속형 순차 필터링)", expanded=True):
                ac1, ac2, ac3 = st.columns(3)
                opts_r_ag = sorted([str(x) for x in temp_ag['노선_clean'].dropna().unique()])
                sel_route_ag_list = render_multiselect_box(ac1, "1. 노선", opts_r_ag, "slicer_route_ag_multi")
                if sel_route_ag_list: temp_ag = temp_ag[temp_ag['노선_clean'].isin(sel_route_ag_list)]

                opts_m_ag = sorted([str(x) for x in temp_ag[month_col_a].dropna().unique()]) if month_col_a else []
                sel_month_ag_list = render_multiselect_box(ac2, "2. 출발 월 (향후 6개월)", opts_m_ag, "slicer_month_ag_multi")
                if sel_month_ag_list: temp_ag = temp_ag[temp_ag[month_col_a].astype(str).isin(sel_month_ag_list)]

                opts_b_ag = sorted([str(x) for x in temp_ag[bound_col_a].dropna().unique()]) if bound_col_a else []
                sel_bound_ag_list = render_multiselect_box(ac3, "3. 수송 구분", opts_b_ag, "slicer_bound_ag_multi")
                if sel_bound_ag_list: temp_ag = temp_ag[temp_ag[bound_col_a].astype(str).isin(sel_bound_ag_list)]

                ac4, ac5 = st.columns(2)
                opts_tt_ag = sorted([str(x) for x in temp_ag['Ticket Type'].dropna().unique()]) if 'Ticket Type' in temp_ag.columns else []
                sel_tt_ag_list = render_multiselect_box(ac4, "4. TRIP TYPE", opts_tt_ag, "slicer_tt_ag_multi")
                if sel_tt_ag_list: temp_ag = temp_ag[temp_ag['Ticket Type'].astype(str).isin(sel_tt_ag_list)]

                opts_al_ag = sorted([str(x) for x in temp_ag['Dominant Marketing Airline'].dropna().unique()])
                opts_al_ag = ['KE'] + [x for x in opts_al_ag if x != 'KE'] if 'KE' in opts_al_ag else opts_al_ag
                sel_al_ag_list = render_multiselect_box(ac5, "5. 항공사", opts_al_ag, "slicer_al_ag_multi")
                if sel_al_ag_list: temp_ag = temp_ag[temp_ag['Dominant Marketing Airline'].astype(str).isin(sel_al_ag_list)]

            df_ag_filtered = temp_ag
            open_attr = "open" if st.toggle("📂 전체 항목 펼쳐보기 (열기/닫기)", value=True, key="expand_toggle_all_key_fixed") else ""

            sub_tab_rbd, sub_tab_agency = st.tabs(["📊 RBD별 판매현황", "🏢 대리점별 판매현황 (상위 20개 대리점)"])

            with sub_tab_rbd:
                if not df_ag_filtered.empty and 'O&D RBKD' in df_ag_filtered.columns and week_col_a:
                    week_list = sorted([str(x) for x in df_ag_filtered[week_col_a].dropna().unique()], reverse=True)
                    ag_al_sum = df_ag_filtered.groupby('Dominant Marketing Airline', observed=False)['Value'].sum().sort_values(ascending=False)
                    ag_al_list = ['KE'] + [str(x) for x in ag_al_sum.index if x != 'KE' and ag_al_sum[x] > 0]
                    sub_col_w = 80.0 / (len(week_list) + 1)

                    rbd_html = '<div class="custom-piv-container"><table class="custom-piv-table" style="table-layout:fixed; width:100%;"><thead><tr><th class="header-main" style="width:20%;">항공사 / RBD 클래스</th>'
                    for wk in week_list: rbd_html += f'<th class="header-main" style="width:{sub_col_w:.2f}%;">{wk}</th>'
                    rbd_html += f'<th class="header-main" style="width:{sub_col_w:.2f}%;">총합계</th></tr></thead><tbody>'

                    for al_code in ag_al_list:
                        al_sub = df_ag_filtered[df_ag_filtered['Dominant Marketing Airline'] == al_code]
                        al_tot_pax = al_sub['Value'].sum()
                        if al_tot_pax > 0:
                            piv_rbd = al_sub.pivot_table(index='O&D RBKD', columns=week_col_a, values='Value', aggfunc='sum', fill_value=0, observed=False)
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
                if not df_ag_filtered.empty and 'Travel Agency Name' in df_ag_filtered.columns and week_col_a:
                    week_list_ag = sorted([str(x) for x in df_ag_filtered[week_col_a].dropna().unique()], reverse=True)
                    agency_totals = df_ag_filtered.groupby('Travel Agency Name', observed=False)['Value'].sum().sort_values(ascending=False)
                    top_20_agencies = [ag for ag in agency_totals.index if agency_totals[ag] > 0][:20]
                    sub_col_w_ag = 80.0 / (len(week_list_ag) + 1)

                    ag_html = '<div class="custom-piv-container"><table class="custom-piv-table" style="table-layout:fixed; width:100%;"><thead><tr><th class="header-main" style="width:20%;">대리점 / 항공사</th>'
                    for wk in week_list_ag: ag_html += f'<th class="header-main" style="width:{sub_col_w_ag:.2f}%;">{wk}</th>'
                    ag_html += f'<th class="header-main" style="width:{sub_col_w_ag:.2f}%;">총 판매량</th></tr></thead><tbody>'

                    for ag_name in top_20_agencies:
                        ag_sub = df_ag_filtered[df_ag_filtered['Travel Agency Name'] == ag_name]
                        ag_tot_val = ag_sub['Value'].sum()
                        if ag_tot_val > 0:
                            ag_al_totals = ag_sub.groupby('Dominant Marketing Airline', observed=False)['Value'].sum().sort_values(ascending=False)
                            piv_ag_sub = ag_sub.pivot_table(index='Dominant Marketing Airline', columns=week_col_a, values='Value', aggfunc='sum', fill_value=0, observed=False)
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

    # 4. 👥 단체실적 탭
    with tab_34_4:
        st.subheader("👥 발매 - 항공사별/대리점별 단체 발매 현황")
        if df_iss_merged is not None:
            df_grp_raw = df_iss_merged.copy()
            df_grp_raw['노선_clean'] = df_grp_raw['노선'].astype(str).str.strip()
            g_m_col = next((c for c in ['출발월', '출발 월'] if c in df_grp_raw.columns), None)
            g_b_col = next((c for c in ['수송', 'Bound'] if c in df_grp_raw.columns), None)

            temp_grp = df_grp_raw.copy()
            with st.expander("🔍 **단체 실적 분석 피벗 슬라이서 필터 설정** (종속형 순차 필터링)", expanded=True):
                gc1, gc2, gc3 = st.columns(3)
                opts_g_route = sorted([str(x) for x in temp_grp['노선_clean'].dropna().unique()])
                sel_g_route_list = render_multiselect_box(gc1, "1. 노선", opts_g_route, "slicer_g_route_multi")
                if sel_g_route_list: temp_grp = temp_grp[temp_grp['노선_clean'].isin(sel_g_route_list)]

                opts_g_m = sorted([str(x) for x in temp_grp[g_m_col].dropna().unique()]) if g_m_col else []
                sel_g_month_list = render_multiselect_box(gc2, "2. 출발 월 (향후 6개월)", opts_g_m, "slicer_g_month_multi")
                if sel_g_month_list: temp_grp = temp_grp[temp_grp[g_m_col].astype(str).isin(sel_g_month_list)]

                opts_g_b = sorted([str(x) for x in temp_grp[g_b_col].dropna().unique()]) if g_b_col else []
                sel_g_bound_list = render_multiselect_box(gc3, "3. 수송 구분", opts_g_b, "slicer_g_bound_multi")
                if sel_g_bound_list: temp_grp = temp_grp[temp_grp[g_b_col].astype(str).isin(sel_g_bound_list)]

                gc4, gc5 = st.columns(2)
                opts_g_tt = sorted([str(x) for x in temp_grp['Ticket Type'].dropna().unique()]) if 'Ticket Type' in temp_grp.columns else []
                sel_g_tt_list = render_multiselect_box(gc4, "4. TRIP TYPE", opts_g_tt, "slicer_g_tt_multi")
                if sel_g_tt_list: temp_grp = temp_grp[temp_grp['Ticket Type'].astype(str).isin(sel_g_tt_list)]

                opts_g_al = sorted([str(x) for x in temp_grp['Dominant Marketing Airline'].dropna().unique()]) if 'Dominant Marketing Airline' in temp_grp.columns else []
                opts_g_al = ['KE'] + [x for x in opts_g_al if x != 'KE'] if 'KE' in opts_g_al else opts_g_al
                sel_g_al_list = render_multiselect_box(gc5, "5. 항공사", opts_g_al, "slicer_g_al_multi")
                if sel_g_al_list: temp_grp = temp_grp[temp_grp['Dominant Marketing Airline'].astype(str).isin(sel_g_al_list)]

            is_grp_cond = (((temp_grp['Dominant Marketing Airline'] == '7C') & (temp_grp['O&D RBKD'] == 'V')) | ((temp_grp['Dominant Marketing Airline'] != '7C') & (temp_grp['O&D RBKD'] == 'G')))
            df_grp_filtered = temp_grp[is_grp_cond].copy()

            if not df_grp_filtered.empty and 'Travel Agency Name' in df_grp_filtered.columns:
                ag_sum_df = df_grp_filtered.groupby(['Dominant Marketing Airline', 'Travel Agency Name'], observed=False)['Value'].sum().reset_index()
                al_totals = ag_sum_df.groupby('Dominant Marketing Airline', observed=False)['Value'].sum().sort_values(ascending=False)
                al_sorted_list = ['KE'] + [str(x) for x in al_totals.index if x != 'KE' and al_totals[x] > 0]

                for al_code in al_sorted_list:
                    al_sub = ag_sum_df[ag_sum_df['Dominant Marketing Airline'] == al_code]
                    al_tot_val = al_sub['Value'].sum()
                    if al_tot_val > 0:
                        top_ag_sub = al_sub[al_sub['Value'] > 0].sort_values(by='Value', ascending=False).head(100).reset_index(drop=True)
                        if not top_ag_sub.empty:
                            top_ag_sub.index = range(1, len(top_ag_sub) + 1)
                            with st.expander(f"✈️ 항공사: **{al_code}**  |  총 단체 실적: **{al_tot_val:,.0f}**건", expanded=(al_code == 'KE')):
                                g_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead><tr><th class="header-main" style="width:80px;">순위</th><th class="header-main">여행사(대리점)명</th><th class="header-main" style="width:200px;">단체 예약 실적 (석)</th></tr></thead><tbody>'
                                g_html += f'<tr class="row-group-header-custom"><td style="text-align:center;">-</td><td style="text-align:center; font-weight:800;">★ {al_code} 전체 총합계</td><td style="text-align:center;"><b>{al_tot_val:,.0f}</b></td></tr>'
                                for r_idx, ag_row in top_ag_sub.iterrows():
                                    g_html += f'<tr><td style="text-align:center;">{r_idx}위</td><td style="text-align:center; font-weight:600;">{ag_row["Travel Agency Name"]}</td><td style="text-align:center; font-weight:700;">{ag_row["Value"]:,.0f}</td></tr>'
                                g_html += '</tbody></table></div>'
                                st.markdown(g_html, unsafe_allow_html=True)

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

    col_pur_m_disp = get_actual_col("Ticket Purchase month") or "Ticket Purchase month"
    col_trip_m_disp = get_actual_col("Trip Month") or "Trip Month"
    col_rgn = get_actual_col("4.OD RGN") or "4.OD RGN"
    col_dir = get_actual_col("DIRECTION") or "DIRECTION"
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

    df_6['Val_num'] = pd.to_numeric(df_6[col_val_6].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if col_val_6 in df_6.columns else 0.0

    if col_year_type in df_6.columns:
        df_6['Val_CY_num'] = np.where(df_6[col_year_type].astype(str).str.contains('금년|CY', na=False), df_6['Val_num'], 0.0)
        df_6['Val_PY_num'] = np.where(df_6[col_year_type].astype(str).str.contains('전년|PY', na=False), df_6['Val_num'], 0.0)
    else:
        df_6['Val_CY_num'] = df_6['Val_num']
        df_6['Val_PY_num'] = 0.0

    tab6_1, tab6_2 = st.tabs(["📊 O&D별 종합 M/S 분석 및 Carrier별 상세 비교", "📋 6수송 Raw Data View"])

    with tab6_1:
        st.markdown('<div class="unified-sub-header">✈️ 6수송 발매 M/S 현황 (종속형 순차 필터링 적용)</div>', unsafe_allow_html=True)
        
        temp_df = df_6.copy()

        # ------------------- Row 1 (6개 슬라이서) -------------------
        f6_col1, f6_col2, f6_col3, f6_col4, f6_col5, f6_col6 = st.columns(6)
        
        # 📌 2026년 필터 및 동적 날짜 표출 로직 적용
        opts_pur_m_all = sorted([str(x).strip() for x in temp_df[col_pur_m_disp].dropna().unique() if str(x).strip() != 'nan' and str(x).strip() != ''], reverse=True) if col_pur_m_disp in temp_df.columns else []
        opts_pur_m_2026 = [x for x in opts_pur_m_all if x.startswith('2026')]
        pur_label = "1. 금년 발매월" + get_dynamic_range_label(opts_pur_m_2026)
        
        sel_pur_m_disp = render_multiselect_box(f6_col1, pur_label, opts_pur_m_2026, "slicer6_pur_m_disp")
        if sel_pur_m_disp: 
            sel_months = [x.split('-')[1] for x in sel_pur_m_disp if '-' in x]
            target_pur_m = [f"2026-{m}" for m in sel_months] + [f"2025-{m}" for m in sel_months]
            temp_df = temp_df[temp_df[col_pur_m_disp].astype(str).isin(target_pur_m)]

        opts_trip_m_all = sorted([str(x).strip() for x in temp_df[col_trip_m_disp].dropna().unique() if str(x).strip() != 'nan' and str(x).strip() != ''], reverse=False) if col_trip_m_disp in temp_df.columns else []
        opts_trip_m_2026 = [x for x in opts_trip_m_all if x.startswith('2026')]
        trip_label = "2. 금년 출발월" + get_dynamic_range_label(opts_trip_m_2026)
        
        sel_trip_m_disp = render_multiselect_box(f6_col2, trip_label, opts_trip_m_2026, "slicer6_trip_m_disp")
        if sel_trip_m_disp: 
            sel_months = [x.split('-')[1] for x in sel_trip_m_disp if '-' in x]
            target_trip_m = [f"2026-{m}" for m in sel_months] + [f"2025-{m}" for m in sel_months]
            temp_df = temp_df[temp_df[col_trip_m_disp].astype(str).isin(target_trip_m)]

        opts_rgn = sorted([str(x).strip() for x in temp_df[col_rgn].dropna().unique() if str(x).strip() != 'nan']) if col_rgn in temp_df.columns else []
        sel_rgn = render_multiselect_box(f6_col3, "3. OD Region", opts_rgn, "slicer6_rgn")
        if sel_rgn: temp_df = temp_df[temp_df[col_rgn].astype(str).isin(sel_rgn)]

        if col_al_6 in temp_df.columns:
            al_val_series = temp_df[temp_df['Val_CY_num'] > 0].groupby(col_al_6, observed=False)['Val_CY_num'].sum().sort_values(ascending=False)
            al_sorted = [str(x).strip() for x in al_val_series.index if str(x).strip() != 'nan']
            opts_al = ['KE'] + [x for x in al_sorted if x != 'KE'] if 'KE' in al_sorted else al_sorted
        else:
            opts_al = []
        sel_al_list = render_multiselect_box(f6_col4, "4. 항공사", opts_al, "slicer6_al_multi")
        if sel_al_list: temp_df = temp_df[temp_df[col_al_6].astype(str).isin(sel_al_list)]

        opts_vv = sorted([str(x).strip() for x in temp_df[col_od_mkt].dropna().unique() if str(x).strip() != 'nan']) if col_od_mkt in temp_df.columns else []
        sel_vv = render_multiselect_box(f6_col5, "5. Trip O&D V.V.", opts_vv, "slicer6_vv")
        if sel_vv: temp_df = temp_df[temp_df[col_od_mkt].astype(str).isin(sel_vv)]

        opts_dir = sorted([str(x).strip() for x in temp_df[col_dir].dropna().unique() if str(x).strip() != 'nan']) if col_dir in temp_df.columns else []
        sel_dir = render_multiselect_box(f6_col6, "6. 일본발/일본행", opts_dir, "slicer6_dir")
        if sel_dir: temp_df = temp_df[temp_df[col_dir].astype(str).isin(sel_dir)]

        # ------------------- Row 2 (6개 슬라이서) -------------------
        f6_col7, f6_col8, f6_col9, f6_col10, f6_col11, f6_col12 = st.columns(6)

        opts_direct = sorted([str(x).strip() for x in temp_df[col_direct_transit].dropna().unique() if str(x).strip() != 'nan']) if col_direct_transit in temp_df.columns else []
        sel_direct = render_multiselect_box(f6_col7, "7. 직항/경유", opts_direct, "slicer6_direct")
        if sel_direct: temp_df = temp_df[temp_df[col_direct_transit].astype(str).isin(sel_direct)]

        opts_od = sorted([str(x).strip() for x in temp_df[col_od_simple].dropna().unique() if str(x).strip() != 'nan']) if col_od_simple in temp_df.columns else []
        sel_od_simple = render_multiselect_box(f6_col8, "8. Trip O&D", opts_od, "slicer6_od_simple")
        if sel_od_simple: temp_df = temp_df[temp_df[col_od_simple].astype(str).isin(sel_od_simple)]

        opts_orig_c = sorted([str(x).strip() for x in temp_df[col_orig_c].dropna().unique() if str(x).strip() != 'nan']) if col_orig_c in temp_df.columns else []
        sel_orig_c = render_multiselect_box(f6_col9, "9. 출발국가", opts_orig_c, "slicer6_orig_c")
        if sel_orig_c: temp_df = temp_df[temp_df[col_orig_c].astype(str).isin(sel_orig_c)]

        opts_dest_c = sorted([str(x).strip() for x in temp_df[col_dest_c].dropna().unique() if str(x).strip() != 'nan']) if col_dest_c in temp_df.columns else []
        sel_dest_c = render_multiselect_box(f6_col10, "10. 도착국가", opts_dest_c, "slicer6_dest_c")
        if sel_dest_c: temp_df = temp_df[temp_df[col_dest_c].astype(str).isin(sel_dest_c)]

        opts_jp_apo = sorted([str(x).strip() for x in temp_df[col_jp_apo].dropna().unique() if str(x).strip() != 'nan']) if col_jp_apo in temp_df.columns else []
        sel_jp_apo = render_multiselect_box(f6_col11, "11. 일본공항", opts_jp_apo, "slicer6_jp_apo")
        if sel_jp_apo: temp_df = temp_df[temp_df[col_jp_apo].astype(str).isin(sel_jp_apo)]

        opts_ov_apo = sorted([str(x).strip() for x in temp_df[col_ov_apo].dropna().unique() if str(x).strip() != 'nan']) if col_ov_apo in temp_df.columns else []
        sel_ov_apo = render_multiselect_box(f6_col12, "12. 해외공항", opts_ov_apo, "slicer6_ov_apo")
        if sel_ov_apo: temp_df = temp_df[temp_df[col_ov_apo].astype(str).isin(sel_ov_apo)]

        filtered_6th = temp_df

        if not filtered_6th.empty and col_al_6 in filtered_6th.columns:
            al_agg = filtered_6th.groupby(col_al_6, observed=False)[['Val_CY_num', 'Val_PY_num']].sum().reset_index()
            non_ke_agg = al_agg[al_agg[col_al_6] != 'KE'].sort_values(by='Val_CY_num', ascending=False)
            ke_agg = al_agg[al_agg[col_al_6] == 'KE']
            al_agg_sorted = pd.concat([ke_agg, non_ke_agg]).reset_index(drop=True)

            full_al_ranking = [str(x) for x in al_agg.sort_values(by='Val_CY_num', ascending=False)[col_al_6].tolist()]
            ke_rank = (full_al_ranking.index('KE') + 1) if 'KE' in full_al_ranking else "-"
            airline_rank_list = [str(x) for x in al_agg_sorted[col_al_6].tolist()[:11]]

            html_table = '<div class="yoy-table-container"><table class="yoy-table"><thead><tr><th class="mkt-header" style="width:110px;">월별 M/S</th><th class="mkt-header" style="width:110px;">총합계</th>'
            for al_code in airline_rank_list:
                if al_code == 'KE': html_table += f'<th class="ke-header" style="width:130px; background-color:#6fa8dc !important; color:#ffffff !important;">★ KE ({ke_rank}위)</th>'
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

            html_table += f'<tr><td style="color:#64748b; font-weight:600;">YOY</td>{(get_yoy_td_html(t_yoy_pct) if t_prev>0 else get_dash_td())}'
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                p_val = al_agg[al_agg[col_al_6] == al_code]['Val_PY_num'].sum()
                indiv_yoy = ((c_val - p_val) / p_val * 100) if p_val > 0 else 0
                html_table += (get_yoy_td_html(indiv_yoy) if p_val>0 else get_dash_td())
            html_table += '</tr>'

            html_table += '<tr class="row-title"><td>전체 M/S</td><td><b>100%</b></td>'
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                ms_val = (c_val / t_curr * 100) if t_curr > 0 else 0
                html_table += f'<td><b>{ms_val:.1f}%</b></td>'
            html_table += '</tr>'

            diff_total_ms = 0
            html_table += f'<tr class="row-ms-yoy"><td style="color:#64748b; font-weight:600;">YOY</td>{(get_yoy_td_html(diff_total_ms, True) if t_prev>0 else get_dash_td())}'
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[col_al_6] == al_code]['Val_CY_num'].sum()
                p_val = al_agg[al_agg[col_al_6] == al_code]['Val_PY_num'].sum()
                ms_c = (c_val / t_curr * 100) if t_curr > 0 else 0
                ms_p = (p_val / t_prev * 100) if t_prev > 0 else 0
                diff_p = ms_c - ms_p
                html_table += (get_yoy_td_html(diff_p, True) if t_prev>0 and p_val>0 else get_dash_td())
            html_table += '</tr></tbody></table></div>'
            st.markdown(html_table, unsafe_allow_html=True)

        st.markdown("---")

        # ------------------------------------------
        # 📌 Carrier별 M/S (오직 Trip O&D 단방향 기준 TOP 20 정렬)
        # ------------------------------------------
        st.markdown('<div class="unified-sub-header">🏆 Carrier별 M/S (TOP 20 Trip O&D 및 전체 총계)</div>', unsafe_allow_html=True)
        
        if not filtered_6th.empty and col_od_simple in filtered_6th.columns:
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

            od_totals = filtered_6th.groupby(col_od_simple, observed=False)['Val_CY_num'].sum().sort_values(ascending=False)
            top20_ods = [x for x in od_totals.index if od_totals[x] > 0][:20]

            if top20_ods:
                matrix_rows = []
                for rank_i, od_simple_code in enumerate(top20_ods, 1):
                    df_od = filtered_6th[filtered_6th[col_od_simple] == od_simple_code]

                    mkt_cy = df_od['Val_CY_num'].sum()
                    mkt_py = df_od['Val_PY_num'].sum()
                    mkt_yoy = ((mkt_cy - mkt_py) / mkt_py * 100) if mkt_py > 0 else 0

                    df_sel = df_od[df_od[col_al_6].isin(sel_carriers)] if sel_carriers else df_od
                    sel_cy = df_sel['Val_CY_num'].sum()
                    sel_py = df_sel['Val_PY_num'].sum()
                    sel_yoy = ((sel_cy - sel_py) / sel_py * 100) if sel_py > 0 else 0
                    sel_ms_cy = (sel_cy / mkt_cy * 100) if mkt_cy > 0 else 0
                    sel_ms_py = (sel_py / mkt_py * 100) if mkt_py > 0 else 0
                    sel_ms_yoy = sel_ms_cy - sel_ms_py

                    df_ke = df_od[df_od[col_al_6] == 'KE']
                    ke_cy = df_ke['Val_CY_num'].sum()
                    ke_py = df_ke['Val_PY_num'].sum()
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

                od_matrix_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead>'
                od_matrix_html += '<tr><th rowspan="2" class="header-main" style="width:40px;">순위</th>'
                od_matrix_html += '<th rowspan="2" class="header-main" style="width:120px;">Trip O&D</th>'
                od_matrix_html += '<th colspan="2" class="header-main" style="background-color:#215b88 !important; color:#ffffff !important;">시장 전체</th>'
                od_matrix_html += f'<th colspan="2" class="header-main" style="background-color:#1e4e79 !important; color:#ffffff !important;">선택 항공사 발매량{sel_al_title_suffix}</th>'
                od_matrix_html += '<th colspan="2" class="header-main" style="background-color:#1b3d5a !important; color:#ffffff !important;">선택 항공사 M/S</th>'
                od_matrix_html += '<th colspan="4" class="header-main" style="background-color:#6fa8dc !important; color:#ffffff !important;">KE 발매량 & M/S (대한항공)</th></tr>'
                od_matrix_html += '<tr><th class="header-main" style="background-color:#3172ac !important; color:#ffffff !important;">금년</th>'
                od_matrix_html += '<th class="header-main" style="background-color:#3172ac !important; color:#ffffff !important;">YOY</th>'
                od_matrix_html += '<th class="header-main" style="background-color:#28629b !important; color:#ffffff !important;">금년</th>'
                od_matrix_html += '<th class="header-main" style="background-color:#28629b !important; color:#ffffff !important;">YOY</th>'
                od_matrix_html += '<th class="header-main" style="background-color:#204f77 !important; color:#ffffff !important;">금년 M/S</th>'
                od_matrix_html += '<th class="header-main" style="background-color:#204f77 !important; color:#ffffff !important;">YOY</th>'
                od_matrix_html += '<th class="header-main" style="background-color:#6fa8dc !important; color:#ffffff !important;">금년 발매량</th>'
                od_matrix_html += '<th class="header-main" style="background-color:#6fa8dc !important; color:#ffffff !important;">YOY</th>'
                od_matrix_html += '<th class="header-main" style="background-color:#6fa8dc !important; color:#ffffff !important;">KE M/S</th>'
                od_matrix_html += '<th class="header-main" style="background-color:#6fa8dc !important; color:#ffffff !important;">YOY</th></tr></thead><tbody>'

                for r in matrix_rows:
                    od_matrix_html += f'<tr><td style="font-weight:700;">{r["rank"]}</td>'
                    od_matrix_html += f'<td style="font-weight:700;">{r["od_simple"]}</td>'
                    od_matrix_html += f'<td>{r["mkt_cy"]:,.0f}</td>'
                    od_matrix_html += get_yoy_td_html(r["mkt_yoy"])
                    od_matrix_html += f'<td style="font-weight:700;">{r["sel_cy"]:,.0f}</td>'
                    od_matrix_html += get_yoy_td_html(r["sel_yoy"])
                    od_matrix_html += f'<td style="font-weight:700;">{r["sel_ms_cy"]:.1f}%</td>'
                    od_matrix_html += get_yoy_td_html(r["sel_ms_yoy"], True)
                    
                    # 📌 전용 CSS 클래스 바인딩으로 KE 색상 강제 유지
                    od_matrix_html += f'<td class="bg-ke-light" style="text-align:center !important;"><span class="txt-ke-bold">{r["ke_cy"]:,.0f}</span></td>'
                    od_matrix_html += get_yoy_td_html(r["ke_yoy"], bg_class="bg-ke-light")
                    od_matrix_html += f'<td class="bg-ke-light" style="text-align:center !important;"><span class="txt-ke-bold">{r["ke_ms_cy"]:.1f}%</span></td>'
                    od_matrix_html += get_yoy_td_html(r["ke_ms_yoy"], True, bg_class="bg-ke-light")
                    od_matrix_html += '</tr>'

                # 📌 소계 행 (전용 bg-subtotal 클래스 적용)
                od_matrix_html += f'<tr class="row-title bg-subtotal" style="border-top:2px solid #94a3b8 !important;"><td colspan="2" style="font-weight:800 !important; text-align:center;">[TOP 20 소계]</td>'
                od_matrix_html += f'<td style="font-weight:800 !important;">{tot_mkt_cy:,.0f}</td>'
                od_matrix_html += get_yoy_td_html(tot_mkt_yoy, bg_class="bg-subtotal")
                od_matrix_html += f'<td style="font-weight:800 !important;">{tot_sel_cy:,.0f}</td>'
                od_matrix_html += get_yoy_td_html(tot_sel_yoy, bg_class="bg-subtotal")
                od_matrix_html += f'<td style="font-weight:800 !important;">{tot_sel_ms_cy:.1f}%</td>'
                od_matrix_html += get_yoy_td_html(tot_sel_ms_yoy, True, bg_class="bg-subtotal")
                od_matrix_html += f'<td class="bg-ke-mid" style="text-align:center !important;"><span class="txt-ke-bold">{tot_ke_cy:,.0f}</span></td>'
                od_matrix_html += get_yoy_td_html(tot_ke_yoy, bg_class="bg-ke-mid")
                od_matrix_html += f'<td class="bg-ke-mid" style="text-align:center !important;"><span class="txt-ke-bold">{tot_ke_ms_cy:.1f}%</span></td>'
                od_matrix_html += get_yoy_td_html(tot_ke_ms_yoy, True, bg_class="bg-ke-mid")
                od_matrix_html += '</tr>'

                # 📌 총계 행 (전용 bg-grandtotal 클래스 적용)
                od_matrix_html += f'<tr class="row-title bg-grandtotal" style="border-top:2px solid #64748b !important;"><td colspan="2" style="font-weight:800 !important; text-align:center; color:#0f172a !important;">[선택 필터 전체 총계]</td>'
                od_matrix_html += f'<td style="font-weight:800 !important; color:#0f172a !important;">{grand_mkt_cy:,.0f}</td>'
                od_matrix_html += get_yoy_td_html(grand_mkt_yoy, bg_class="bg-grandtotal")
                od_matrix_html += f'<td style="font-weight:800 !important; color:#0f172a !important;">{grand_sel_cy:,.0f}</td>'
                od_matrix_html += get_yoy_td_html(grand_sel_yoy, bg_class="bg-grandtotal")
                od_matrix_html += f'<td style="font-weight:800 !important; color:#0f172a !important;">{grand_sel_ms_cy:.1f}%</td>'
                od_matrix_html += get_yoy_td_html(grand_sel_ms_yoy, True, bg_class="bg-grandtotal")
                od_matrix_html += f'<td class="bg-ke-dark" style="text-align:center !important;"><span class="txt-ke-bold" style="color:#ffffff !important;">{grand_ke_cy:,.0f}</span></td>'
                od_matrix_html += get_yoy_td_html(grand_ke_yoy, bg_class="bg-ke-dark")
                od_matrix_html += f'<td class="bg-ke-dark" style="text-align:center !important;"><span class="txt-ke-bold" style="color:#ffffff !important;">{grand_ke_ms_cy:.1f}%</span></td>'
                od_matrix_html += get_yoy_td_html(grand_ke_ms_yoy, True, bg_class="bg-ke-dark")
                od_matrix_html += '</tr>'

                od_matrix_html += '</tbody></table></div>'
                st.markdown(od_matrix_html, unsafe_allow_html=True)
            else:
                st.info("💡 실적이 존재하는 O&D Market이 없습니다.")

    with tab6_2:
        st.subheader("📋 6수송 사전 집계 Data 조회 및 다운로드")
        if not filtered_6th.empty:
            csv_6th_bytes = filtered_6th.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 필터링된 6수송 Data (CSV) 다운로드", data=csv_6th_bytes, file_name=f"6th_Freedom_Data_{datetime.date.today().strftime('%Y%m%d')}.csv", mime="text/csv")
            st.dataframe(filtered_6th.head(100), width="stretch")

else:
    st.markdown('<div class="unified-sub-header">🔗 대한항공 W26 연결 네트워크 외부 연동 시스템</div>', unsafe_allow_html=True)
    st.link_button("🔗 W26 연결 네트워크 바로가기 (새 탭에서 열기)", EXT_WEB_APP_URL, use_container_width=True)