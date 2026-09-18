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

issue_end_6th = current_monday - datetime.timedelta(days=1)
issue_start_6th = current_monday - datetime.timedelta(weeks=13)
issue_range_str_6th = f"{issue_start_6th.strftime('%Y.%m.%d')} ~ {issue_end_6th.strftime('%Y.%m.%d')}"

# 📌 엑셀 수식 기준 지정 22개 대한항공 정규 취항 노선 마스터 리스트
EXCEL_KE_ROUTES_MASTER = [
    "G/HND", "I/NRT", "I/HND", "P/NRT", "C/NRT", "I/KIX", "G/KIX", "I/UKB",
    "I/OKJ", "I/HIJ", "I/FUK", "I/KOJ", "I/NGS", "I/KMJ", "I/OIT", "I/NGO",
    "P/NGO", "I/KIJ", "I/KMQ", "I/OKA", "I/CTS", "I/AOJ"
]

# 3. 항공사별 RBD 계층 정의
RBD_HIERARCHY = {
    'KE': list('YBMSHEKLUQTX'),
    'OZ': list('YBMHEQKSVWTLX'),
    '7C': list('YBKNQMTWORXSZLHEFVGPJ'),
    'LJ': list('YWDEHKLQBNMXPSVZARIOT'),
    'TW': list('YWZVSPONMLKHDBAJQET'),
    'BX': list('YBRMKEUDOIVJHXGWQN'),
    'RS': list('YBMHEQKSOLWTRUIXAVGNDPFJC'),
    'JL': list('WREYBHKMLVSOGQNPZ'),
    'NH': list('ENYBMUHQVWSLK'),
    'YP': list('PRZYBMHELQNSAFKVOGWX'),
    'ZE': list('PFAJCIROYBMSHEKLQNTVWGX'),
    'WE': list('ADIZOYBMHEUQNTVW')
}

# 4. Custom CSS
st.markdown("""
<style>
    :root { --primary-color: #0ea5e9 !important; --primaryColor: #0ea5e9 !important; }
    .main-app-title { font-size: 26px !important; font-weight: 800 !important; color: #0f172a; margin-bottom: 12px; }
    .unified-sub-header { font-size: 16px !important; font-weight: 700 !important; color: #0f172a; margin-top: 10px; margin-bottom: 10px; }
    div[role="radiogroup"] label div[role="radio"][aria-checked="true"] { background-color: #0ea5e9 !important; border-color: #0ea5e9 !important; }
    button[data-baseweb="tab"][aria-selected="true"] { color: #0ea5e9 !important; border-bottom-color: #0ea5e9 !important; }
    div[data-testid="stToggle"] input:checked + div { background-color: #0ea5e9 !important; }
    .source-header-box { background-color: #f0f9ff; border-left: 5px solid #0284c7; padding: 12px 18px; border-radius: 6px; margin-bottom: 15px; font-size: 14px; color: #0f172a; font-weight: 500; }
    .group-section-header { font-size: 17px !important; font-weight: 700 !important; color: #0f172a; padding-bottom: 8px; border-bottom: 2px solid #cbd5e1; margin-top: 10px; margin-bottom: 12px; }
    .metric-card { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.03); margin-bottom: 10px; }
    .metric-card-ke { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 14px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.03); margin-bottom: 10px; }
    .metric-title { font-size: 13px; color: #64748b; margin-bottom: 4px; font-weight: 600; }
    .metric-value { font-size: 22px; color: #1e293b; font-weight: 700; }
    .custom-piv-container, .yoy-table-container { width: 100%; overflow-x: auto; margin-bottom: 20px; border-radius: 8px; border: 1px solid #cbd5e1 !important; box-shadow: 0 2px 6px rgba(0,0,0,0.04); }
    .custom-piv-table, .yoy-table { width: 100%; border-collapse: collapse; font-size: 12.5px; background-color: #ffffff; text-align: center !important; }
    .custom-piv-table th.header-main, .yoy-table th, .yoy-table th.mkt-header, .yoy-table th.carrier-header { background-color: #cfe2f3 !important; color: #0f172a !important; padding: 8px 6px; border: 1px solid #cbd5e1 !important; font-weight: 700; text-align: center !important; white-space: nowrap; }
    .yoy-table th.ke-header { background-color: #dcfce7 !important; color: #15803d !important; padding: 8px 6px; border: 1px solid #cbd5e1 !important; font-size: 13px !important; font-weight: 800 !important; text-align: center !important; white-space: nowrap; }
    .custom-piv-table td, .yoy-table td, .yoy-table td.ke-cell, .yoy-table tr.ke-row td.ke-cell { padding: 6px 10px; border: 1px solid #cbd5e1 !important; color: #334155 !important; background-color: #ffffff !important; text-align: center !important; }
    .yoy-table tr:hover { background-color: #f8fafc !important; }
    .yoy-table tr.row-title { background-color: #f8fafc !important; font-weight: bold; color: #0f172a; }
    
    /* 6수송 Carrier별 M/S 엑셀 커스텀 테이블 전용 CSS */
    .carrier-excel-container { width: 100%; overflow-x: auto; margin-top: 15px; margin-bottom: 25px; border: 1px solid #cbd5e1; border-radius: 6px; }
    .carrier-excel-table { width: 100%; border-collapse: collapse; font-size: 12px; font-family: 'Segoe UI', Malgun Gothic, sans-serif; }
    .carrier-excel-table th { padding: 8px 6px; border: 1px solid #cbd5e1; text-align: center; font-weight: 700; }
    .carrier-excel-table td { padding: 6px 8px; border: 1px solid #cbd5e1; text-align: center; }
    
    .th-dark-blue { background-color: #cfe2f3; color: #0f172a; }
    .th-mkt-blue { background-color: #cfe2f3; color: #0f172a; }
    .th-sel-blue { background-color: #9fc5e8; color: #0f172a; }
    .th-sel-light { background-color: #9fc5e8; color: #0f172a; }
    .th-ke-green { background-color: #6fa8dc; color: #ffffff; }
    .th-ke-light { background-color: #6fa8dc; color: #ffffff; }
    
    .tr-summary-footer { background-color: #efefef; color: #0f172a; font-weight: 800; }
    .tr-summary-footer td { border-top: 2px solid #94a3b8 !important; background-color: #efefef; color: #0f172a; font-weight: 800; }
    
    details.rbd-details-group { width: 100%; margin: 0; padding: 0; }
    details.rbd-details-group summary { list-style: none; cursor: pointer; outline: none; }
    details.rbd-details-group summary::-webkit-details-marker { display: none; }
    .row-summary-top-dark { background-color: #cccccc !important; color: #0f172a !important; font-weight: 800 !important; }
    .row-summary-top-dark td { background-color: #cccccc !important; color: #0f172a !important; font-weight: 800 !important; border: 1px solid #cbd5e1 !important; }
    .rbd-child-row td { background-color: #ffffff !important; font-size: 12px; }
    .custom-piv-table tr.row-group-header, .yoy-table tr.row-summary, .yoy-table tr.row-summary td { background-color: #efefef !important; font-weight: bold; color: #0f172a; }
    .row-group-header-custom, .row-group-header-custom td { background-color: #cccccc !important; color: #0f172a !important; font-weight: 800 !important; }
    .yoy-up { color: #1d4ed8 !important; font-weight: 700; }
    .yoy-down { color: #dc2626 !important; font-weight: 700; }
    .ke-timeline-box { background-color: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 12px 18px; margin-bottom: 15px; color: #0369a1; font-weight: 600; font-size: 14px; }
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

def load_fast_parquet_data_file():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(base_dir, 'cache_34_data.parquet')
    if os.path.exists(target_path):
        df_p = pd.read_parquet(target_path)
        return optimize_df(clean_transport_column(df_p))
    return None

def process_any_uploaded_file(file_obj):
    file_obj.seek(0)
    if file_obj.name.endswith('.parquet'):
        df = pd.read_parquet(file_obj)
    elif file_obj.name.endswith('.xlsx'):
        df = pd.read_excel(file_obj)
    else:
        df = pd.read_csv(file_obj, low_memory=False)

    df.columns = [str(c).strip() for c in df.columns]
    if 'Weighted_Value' not in df.columns:
        df['Weighted_Value'] = pd.to_numeric(df['Value'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    return optimize_df(clean_transport_column(df))

def load_aux_files():
    df_sup, df_6th = None, None
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    sup_paths = [os.path.join(base_dir, '공급.csv'), '공급.csv']
    for sp in sup_paths:
        if os.path.exists(sp):
            try:
                df_sup = pd.read_csv(sp, low_memory=False)
                if df_sup is not None and not df_sup.empty: break
            except: pass

    six_paths = [os.path.join(base_dir, 'cache_6th_data.parquet'), 'cache_6th_data.parquet']
    for sp in six_paths:
        if os.path.exists(sp):
            try:
                df_6th = pd.read_parquet(sp)
                if df_6th is not None and not df_6th.empty: break
            except: pass

    return optimize_df(df_sup), optimize_df(df_6th)

disk_sup, disk_6th = load_aux_files()

if uploaded_iss is not None:
    df_iss_merged = process_any_uploaded_file(uploaded_iss)
else:
    df_iss_merged = load_fast_parquet_data_file()

df_sup_raw = disk_sup
df_6th_raw = disk_6th

st.markdown('<div class="main-app-title">✈️ 일본노선 발매/공급 Market Share</div>', unsafe_allow_html=True)
st.markdown('<div class="group-section-header">🗂️ 메인 대시보드 선택</div>', unsafe_allow_html=True)

selected_group = st.radio(
    "분석할 수송 영역을 선택하세요:",
    options=["✈️ 3/4수송 대시보드", "🌐 6수송 대시보드", "🔗 W26 연결 네트워크"],
    horizontal=True
)

ALL_OPTION = "전체 (All)"

def build_airline_color_map(airlines_list):
    palette = px.colors.qualitative.Plotly + px.colors.qualitative.Bold + px.colors.qualitative.Pastel
    cmap = {'KE': '#16a34a'}
    idx = 0
    for al in airlines_list:
        if al != 'KE':
            color = palette[idx % len(palette)]
            if color in ['#636EFA', '#16a34a', '#0ea5e9']:
                idx += 1
                color = palette[idx % len(palette)]
            cmap[al] = color
            idx += 1
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

def render_slicer_box(container, label, full_list, key_name):
    opts = [ALL_OPTION] + [str(x).strip() for x in full_list if str(x).strip() != ALL_OPTION]
    container.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
    return container.selectbox(label, options=opts, index=0, key=key_name, label_visibility="collapsed")

def get_dynamic_date_ranges_34(df_iss):
    if df_iss is None or df_iss.empty: return issue_range_str, dep_range_str
    m_col = '출발월' if '출발월' in df_iss.columns else ('출발 월' if '출발 월' in df_iss.columns else 'Trip Month')
    dep_str = f"{sorted([str(x).strip() for x in df_iss[m_col].dropna().unique() if str(x).strip() != 'nan'])[0]} ~ {sorted([str(x).strip() for x in df_iss[m_col].dropna().unique() if str(x).strip() != 'nan'])[-1]}" if m_col in df_iss.columns else dep_range_str
    w_col = '발매주차_일자' if '발매주차_일자' in df_iss.columns else ('발매 주차' if '발매 주차' in df_iss.columns else 'Purchase Month')
    iss_str = f"{sorted([str(x).strip() for x in df_iss[w_col].dropna().unique() if str(x).strip() != 'nan'])[0]} ~ {sorted([str(x).strip() for x in df_iss[w_col].dropna().unique() if str(x).strip() != 'nan'])[-1]}" if w_col in df_iss.columns else issue_range_str
    return iss_str, dep_str

def format_yoy_html(val, is_percentage_point=False):
    unit = "%p" if is_percentage_point else "%"
    if val > 0:
        return f'<span class="yoy-up">▲ {val:.0f}{unit}</span>'
    elif val < 0:
        return f'<span class="yoy-down">▼ {abs(val):.0f}{unit}</span>'
    else:
        return f'▲ 0{unit}'

# ==========================================
# GROUP 1: ✈️ 3/4수송 대시보드
# ==========================================
if selected_group == "✈️ 3/4수송 대시보드":
    dynamic_iss_str_34, dynamic_dep_str_34 = get_dynamic_date_ranges_34(df_iss_merged)
    st.markdown(f"""
    <div class="source-header-box">
        <b>📌 출처: DDS & OAG 데이터 (3/4수송 대시보드)</b> &nbsp;|&nbsp; 
        <b>🗓️ 발매기간 (Purchase Month):</b> {dynamic_iss_str_34} &nbsp;|&nbsp; 
        <b>✈️ 출발기간 (Trip Month):</b> {dynamic_dep_str_34}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    
    tab_34_1, tab_34_2, tab_34_3, tab_34_4 = st.tabs([
        "🎟️ 발매 M/S", 
        "✈️ 공급 M/S", 
        "🏷️ 대리점,RBD별 발매현황", 
        "👥 단체실적"
    ])

    with tab_34_1:
        if df_iss_merged is None:
            st.warning("❌ 3/4수송 데이터를 찾을 수 없습니다. 좌측 사이드바 1번에서 파일을 업로드해 주세요.")
            st.stop()

        merged_df = df_iss_merged.copy()

        al_col_target = None
        for col_cand in ['Dominant Marketing Airline', 'AL', '항공사', 'Marketing Airline']:
            if col_cand in merged_df.columns:
                al_col_target = col_cand
                break
        
        if al_col_target:
            merged_df['AL_clean'] = merged_df[al_col_target].astype(str).str.strip().str.upper()
        else:
            merged_df['AL_clean'] = ''

        merged_df['노선_clean'] = merged_df['노선'].astype(str).str.strip()

        week_col = '발매주차_일자' if '발매주차_일자' in merged_df.columns else ('발매 주차' if '발매 주차' in merged_df.columns else '발매주차')
        all_issue_weeks = sorted([str(x).strip() for x in merged_df[week_col].dropna().unique()]) if week_col else []

        month_col = '출발월' if '출발월' in merged_df.columns else ('출발 월' if '출발 월' in merged_df.columns else None)
        all_dep_months = sorted([str(x).strip() for x in merged_df[month_col].dropna().unique()]) if month_col else []
        
        bound_col = '수송' if '수송' in merged_df.columns else ('Bound' if 'Bound' in merged_df.columns else None)
        all_bounds = sorted([str(x).strip() for x in merged_df[bound_col].dropna().unique()]) if bound_col else []

        all_ticket_types = sorted([str(x).strip() for x in merged_df['Ticket Type'].dropna().unique()]) if 'Ticket Type' in merged_df.columns else []

        raw_airlines = sorted([str(x).strip() for x in merged_df['AL_clean'].dropna().unique()])
        all_airlines = ['KE'] + [x for x in raw_airlines if x != 'KE'] if 'KE' in raw_airlines else raw_airlines

        with st.expander("🔍 **발매 대시보드 피벗 슬라이서 필터 설정** (KE 취항노선 전용)", expanded=True):
            apply_weight_toggle = st.toggle("⚖️ 가중치 적용 M/S 산출", value=True, key="main_wt_toggle_fixed")
            val_col = 'Weighted_Value' if (apply_weight_toggle and 'Weighted_Value' in merged_df.columns) else 'Value'

            # 💡 22개 마스터 노선 중 실적(Value > 0)이 실제 존재하는 KE 취항 노선만 드롭다운에 노출
            df_has_value = merged_df[(merged_df['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER)) & (merged_df['Value'] > 0)]
            full_route_sum = df_has_value.groupby('노선_clean', observed=False)[val_col].sum().sort_values(ascending=False)
            route_order_list = [str(x).strip() for x in full_route_sum.index.tolist() if str(x) != 'nan']
            
            valid_ke_routes = route_order_list
            GLOBAL_VALID_KE_ROUTES = valid_ke_routes

            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            sel_route_str = render_slicer_box(f_col1, "1. 노선 (KE취항/발매량순)", route_order_list, "slicer_route_fixed")
            sel_week_str = render_slicer_box(f_col2, "2. 발매 주차 및 일자", all_issue_weeks, "slicer_week_fixed") if week_col else ALL_OPTION
            sel_month_str = render_slicer_box(f_col3, "3. 출발 월", all_dep_months, "slicer_month_fixed") if month_col else ALL_OPTION
            sel_bound_str = render_slicer_box(f_col4, "4. 수송 구분 (3TF/4TF/OTHERS)", all_bounds, "slicer_bound_fixed") if bound_col else ALL_OPTION

            f_col5, f_col6, _, _ = st.columns(4)
            sel_tt_str = render_slicer_box(f_col5, "5. Ticket Type (여정)", all_ticket_types, "slicer_tt_fixed")
            sel_al_str = render_slicer_box(f_col6, "6. 항공사", all_airlines, "slicer_al_fixed")

        filter_mask = pd.Series(True, index=merged_df.index)

        if sel_route_str != ALL_OPTION:
            filter_mask &= (merged_df['노선_clean'] == str(sel_route_str).strip())
        elif valid_ke_routes:
            filter_mask &= (merged_df['노선_clean'].isin(valid_ke_routes))

        if sel_al_str != ALL_OPTION:
            filter_mask &= (merged_df['AL_clean'] == str(sel_al_str).strip().upper())
        if month_col and sel_month_str != ALL_OPTION:
            filter_mask &= (merged_df[month_col].astype(str).str.strip() == str(sel_month_str).strip())
        if bound_col and sel_bound_str != ALL_OPTION:
            filter_mask &= (merged_df[bound_col].astype(str).str.strip() == str(sel_bound_str).strip())
        if 'Ticket Type' in merged_df.columns and sel_tt_str != ALL_OPTION:
            filter_mask &= (merged_df['Ticket Type'].astype(str).str.strip() == str(sel_tt_str).strip())
        if week_col and sel_week_str != ALL_OPTION:
            filter_mask &= (merged_df[week_col].astype(str).str.strip() == str(sel_week_str).strip())

        filtered_df = merged_df[filter_mask].copy()

        total_pax = filtered_df[val_col].sum()
        ke_pax = filtered_df[filtered_df['AL_clean'] == 'KE'][val_col].sum() if not filtered_df.empty else 0
        ke_ms = (ke_pax / total_pax * 100) if total_pax > 0 else 0

        top_al = "-"
        top_ms = 0.0
        if not filtered_df.empty and total_pax > 0:
            al_sum = filtered_df.groupby('AL_clean', observed=False)[val_col].sum()
            top_al = str(al_sum.idxmax())
            top_ms = (al_sum.max() / total_pax) * 100

        top_route = str(filtered_df.groupby('노선_clean', observed=False)[val_col].sum().idxmax()) if not filtered_df.empty and total_pax > 0 else "-"
        status_wt_label = " (가중치)" if apply_weight_toggle else " (Raw)"

        tab1, tab2, tab3 = st.tabs(["📈 시각화 분석 차트", "📊 M/S 피벗 테이블", "🔒 Raw Data View (관리자 전용)"])
        with tab1:
            if not filtered_df.empty:
                al_order = [al for al in all_airlines if al in filtered_df['AL_clean'].unique()]
                
                st.markdown('<div class="unified-sub-header">1. 항공사별 M/S 점유비</div>', unsafe_allow_html=True)
                c1, c2 = st.columns([1.6, 1])
                with c1:
                    pie_al = filtered_df.groupby('AL_clean', observed=False)[val_col].sum().reset_index()
                    fig1 = px.pie(
                        pie_al, values=val_col, names='AL_clean',
                        hole=0.4, category_orders={'AL_clean': al_order}
                    )
                    fig1.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>항공사: %{label}</b><br>실적: %{value:,.0f}<br>점유율: %{percent:.1%}<extra></extra>")
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
                    st.markdown('<div class="unified-sub-header">2. 발매/주차별 항공사 발매량 추이</div>', unsafe_allow_html=True)
                    df_no_week = filtered_df

                    if not df_no_week.empty:
                        week_al_grp = df_no_week.groupby([week_col, 'AL_clean'], observed=False)[val_col].sum().reset_index()
                        week_totals = week_al_grp.groupby(week_col, observed=False)[val_col].sum().reset_index()
                        week_totals_dict = dict(zip(week_totals[week_col].astype(str), week_totals[val_col]))
                        ke_week_grp = week_al_grp[week_al_grp['AL_clean'] == 'KE'].set_index(week_col)[val_col].to_dict()

                        week_al_grp['Week_Total'] = week_al_grp[week_col].map(week_totals_dict)
                        week_tot_num = pd.to_numeric(week_al_grp['Week_Total'], errors='coerce').fillna(0)
                        val_col_num = pd.to_numeric(week_al_grp[val_col], errors='coerce').fillna(0)
                        week_al_grp['MS_Percent'] = np.where(week_tot_num > 0, (val_col_num / week_tot_num) * 100, 0)
                        week_al_grp['Text_Display'] = week_al_grp['MS_Percent'].map(lambda x: f"{x:.1f}%" if x >= 3.0 else "")

                        fig_week = px.bar(
                            week_al_grp, x=week_col, y=val_col, color='AL_clean',
                            barmode='stack', text='Text_Display',
                            category_orders={'AL_clean': al_order, week_col: all_issue_weeks},
                            custom_data=['AL_clean', val_col, 'MS_Percent']
                        )
                        fig_week.update_traces(textposition='inside', hovertemplate="<b>항공사: %{customdata[0]}</b><br>발매 실적: %{customdata[1]:,.0f}<br>점유비: %{customdata[2]:.1f}%<extra></extra>")

                        valid_weeks = [w for w in all_issue_weeks if w in week_totals_dict]
                        top_bar_labels = [f"<b>{week_totals_dict.get(w, 0):,.0f}</b><br><span style='color:#16a34a;'>(★KE {(ke_week_grp.get(w, 0)/week_totals_dict.get(w,0)*100) if week_totals_dict.get(w,0)>0 else 0:.1f}%)</span>" for w in valid_weeks]

                        fig_week.add_trace(go.Scatter(x=valid_weeks, y=[week_totals_dict[w] for w in valid_weeks], mode='text', text=top_bar_labels, textposition='top center', showlegend=False, hoverinfo='skip'))
                        fig_week.update_layout(yaxis_title=f"발매 실적{status_wt_label}")
                        apply_bottom_legend(fig_week)
                        st.plotly_chart(fig_week, width='stretch')

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
                            line_style = dict(color='#16a34a', width=3.5) if is_ke else dict(dash='dot', width=1.5)
                            marker_style = dict(size=8, symbol='circle') if is_ke else dict(size=4)
                            mode_setting = 'lines+markers+text' if is_ke else 'lines+markers'
                            text_labels = [f"<b>{v:.1f}%</b>" for v in al_data['MS_Percent']] if is_ke else None

                            fig_ke_dep.add_trace(go.Scatter(
                                x=al_data[month_col], y=al_data['MS_Percent'], mode=mode_setting,
                                name=f"★ KE (대한항공)" if is_ke else al_code,
                                line=line_style, marker=marker_style, text=text_labels,
                                textposition="top center",
                                hovertemplate=f"<b>항공사: {al_code}</b><br>출발월: %{{x}}<br>점유율: %{{y:.1f}}%<extra></extra>"
                            ))

                        fig_ke_dep.update_layout(
                            yaxis_title="Market Share (%)",
                            xaxis=dict(categoryorder='array', categoryarray=all_dep_months),
                            yaxis=dict(range=[0, max(dep_merged_top['MS_Percent'].max() * 1.25, 15)]),
                            height=420
                        )
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
                    st.dataframe(piv_w_ms.loc[al_sorted].head(100).map(lambda x: f"{x:.1f}%"), width='stretch')
            with t2:
                piv_r = filtered_df.pivot_table(index='노선_clean', columns='AL_clean', values=val_col, aggfunc='sum', fill_value=0, observed=False)
                cols_ke = ['KE'] + [x for x in piv_r.columns if x != 'KE'] if 'KE' in piv_r.columns else piv_r.columns
                piv_r_ms = piv_r[cols_ke].divide(piv_r.sum(axis=1), axis=0) * 100
                st.dataframe(piv_r_ms.head(100).map(lambda x: f"{x:.1f}%"), width='stretch')

        with tab3:
            st.subheader("🔒 관리자 전용 Raw Data 조회 및 다운로드")
            admin_pw = st.text_input("🔑 관리자 비밀번호를 입력하세요:", type="password", key="admin_pw_fixed")
            if admin_pw == "1234":
                st.success("✅ 관리자 인증이 완료되었습니다.")
                csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 필터링된 발매 Raw Data (CSV) 전체 다운로드",
                    data=csv_data,
                    file_name=f"Ticketing_Raw_Data_{datetime.date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                st.dataframe(filtered_df.head(100), width='stretch')
            else:
                if admin_pw: st.error("❌ 비밀번호가 올바르지 않습니다.")
                else: st.info("ℹ️ 관리자 비밀번호 입력 시 이용할 수 있습니다.")

    # 2. ✈️ 공급 M/S 탭
    with tab_34_2:
        df_sup = df_sup_raw.copy() if df_sup_raw is not None else None
        
        if df_sup is None:
            st.warning("⚠️ 공급 데이터(`공급.csv`)를 읽을 수 없습니다. 좌측 사이드바 2번에서 파일을 직접 업로드해 주세요.")
            st.stop()

        df_sup.columns = [str(c).strip() for c in df_sup.columns]

        sup_ke_col = None
        for c in ['KE취항여부', 'KE 취항여부', 'KE취항노선 여부', 'KE취항', 'KE 취항']:
            if c in df_sup.columns:
                sup_ke_col = c
                break
                
        if sup_ke_col:
            df_sup = df_sup[df_sup[sup_ke_col].astype(str).str.strip().str.contains('취항', na=False)]

        al_col = None
        for c in ['Op Airline Code', 'Mkt Al', 'Airline', 'Op Airline', 'CARRIER', '항공사']:
            if c in df_sup.columns:
                al_col = c
                break

        if al_col: df_sup['Airline'] = df_sup[al_col]
        else: df_sup['Airline'] = 'Unknown'

        if '노선' in df_sup.columns:
            df_sup['노선_clean'] = df_sup['노선'].astype(str).str.strip()
            df_sup = df_sup[df_sup['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER)]

        df_sup = df_sup.reset_index(drop=True)

        df_sup['Seats_num'] = pd.to_numeric(df_sup['Seats'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if 'Seats' in df_sup.columns else 0
        df_sup['Flights_num'] = pd.to_numeric(df_sup['Flights'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if 'Flights' in df_sup.columns else 1

        if '노선_clean' in df_sup.columns:
            sup_routes = df_sup.groupby('노선_clean', observed=False)['Seats_num'].sum().sort_values(ascending=False).index.astype(str).tolist()
        else:
            sup_routes = []

        sup_month_col = '출발월' if '출발월' in df_sup.columns else ('출발 월' if '출발 월' in df_sup.columns else ('Travel Month' if 'Travel Month' in df_sup.columns else None))
        sup_months = sorted([str(x) for x in df_sup[sup_month_col].dropna().unique()]) if sup_month_col else []
        sup_time_cats = sorted([str(x) for x in df_sup['출발 시간대'].dropna().unique()]) if '출발 시간대' in df_sup.columns else []

        raw_sup_al = sorted([str(x) for x in df_sup['Airline'].dropna().unique()])
        sup_airlines = ['KE'] + [x for x in raw_sup_al if x != 'KE'] if 'KE' in raw_sup_al else raw_sup_al
        sup_color_map = build_airline_color_map(sup_airlines)

        st.markdown('<div class="unified-sub-header">🔍 공급 대시보드 필터 설정 (KE 취항노선 전용)</div>', unsafe_allow_html=True)
        metric_mode = st.radio("📊 분석 공급 지표 선택:", options=["공급석 (Seats)", "운항 편수 (Flight Frequencies)"], horizontal=True)
        
        sf_col1, sf_col2, sf_col3, sf_col4 = st.columns(4)
        selected_sup_route_str = render_slicer_box(sf_col1, "1. 노선 (KE 취항 한정)", sup_routes, "slicer_route_sup_fixed")
        selected_sup_month_str = render_slicer_box(sf_col2, "2. 출발 월", sup_months, "slicer_month_sup_fixed") if sup_month_col else ALL_OPTION
        selected_sup_time_str = render_slicer_box(sf_col3, "3. 출발 시간대", sup_time_cats, "slicer_time_sup_fixed")
        selected_sup_al_str = render_slicer_box(sf_col4, "4. 항공사", sup_airlines, "slicer_al_sup_fixed")

        target_val = 'Seats_num' if "공급석" in metric_mode else 'Flights_num'

        filter_mask_sup = pd.Series(True, index=df_sup.index)
        if selected_sup_route_str != ALL_OPTION and '노선_clean' in df_sup.columns: filter_mask_sup &= (df_sup['노선_clean'].astype(str) == selected_sup_route_str)
        if selected_sup_al_str != ALL_OPTION: filter_mask_sup &= (df_sup['Airline'].astype(str) == selected_sup_al_str)
        if sup_month_col and selected_sup_month_str != ALL_OPTION: filter_mask_sup &= (df_sup[sup_month_col].astype(str) == selected_sup_month_str)
        if '출발 시간대' in df_sup.columns and selected_sup_time_str != ALL_OPTION: filter_mask_sup &= (df_sup['출발 시간대'].astype(str) == selected_sup_time_str)

        filtered_sup = df_sup[filter_mask_sup]

        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        total_seats = filtered_sup['Seats_num'].sum()
        total_flights = filtered_sup['Flights_num'].sum()
        ke_sup_val = filtered_sup[filtered_sup['Airline'] == 'KE'][target_val].sum() if not filtered_sup.empty else 0
        total_sup_val = filtered_sup[target_val].sum()
        ke_sup_ms = (ke_sup_val / total_sup_val * 100) if total_sup_val > 0 else 0
        top_sup_al = str(filtered_sup.groupby('Airline', observed=False)[target_val].sum().idxmax()) if not filtered_sup.empty else "-"

        with col_s1: st.markdown(f'<div class="metric-card"><div class="metric-title">총 공급 좌석수 (Seats)</div><div class="metric-value">{total_seats:,.0f}석</div></div>', unsafe_allow_html=True)
        with col_s2: st.markdown(f'<div class="metric-card"><div class="metric-title">총 운항 편수 (Flights)</div><div class="metric-value">{total_flights:,.0f}회</div></div>', unsafe_allow_html=True)
        with col_s3: st.markdown(f'<div class="metric-card-ke"><div class="metric-title" style="color:#16a34a; font-weight:bold;">✈️ KE 공급 M/S ({metric_mode.split()[0]})</div><div class="metric-value" style="color:#16a34a;"><b>{ke_sup_val:,.0f} ({ke_sup_ms:.1f}%)</b></div></div>', unsafe_allow_html=True)
        with col_s4: st.markdown(f'<div class="metric-card"><div class="metric-title">공급 M/S 1위 항공사</div><div class="metric-value" style="color:#1d4ed8;"><b>{top_sup_al}</b></div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if not filtered_sup.empty:
            sup_al_order = [al for al in sup_airlines if al in filtered_sup['Airline'].unique()]
            cs1, cs2 = st.columns([1, 1.2])
            with cs1:
                st.markdown(f'<div class="unified-sub-header">1. 항공사별 전체 공급 M/S 점유비 ({metric_mode})</div>', unsafe_allow_html=True)
                pie_sup_al = filtered_sup.groupby('Airline', observed=False)[target_val].sum().reset_index()
                fig_s1 = px.pie(pie_sup_al, values=target_val, names='Airline', hole=0.4, category_orders={'Airline': sup_al_order}, color='Airline', color_discrete_map=sup_color_map)
                fig_s1.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>항공사: %{label}</b><br>공급량: %{value:,.0f}<br>점유율: %{percent:.1%}<extra></extra>")
                apply_bottom_legend(fig_s1)
                st.plotly_chart(fig_s1, width='stretch')

            with cs2:
                st.markdown(f'<div class="unified-sub-header">2. 항공사별 공급 실적 및 M/S 요약</div>', unsafe_allow_html=True)
                pie_sup_al['공급 M/S (%)'] = (pie_sup_al[target_val] / pie_sup_al[target_val].sum()) * 100
                pie_sup_al = pie_sup_al.sort_values(by=target_val, ascending=False).reset_index(drop=True).head(100)
                pie_sup_al.index = range(1, len(pie_sup_al) + 1)
                
                sup_pivot_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead><tr><th class="header-main" style="width:60px;">순위</th><th class="header-main">항공사</th>'
                sup_pivot_html += f'<th class="header-main">공급 실적 ({metric_mode.split()[0]})</th><th class="header-main">공급 M/S (%)</th></tr></thead><tbody>'

                for rank_idx, row in pie_sup_al.iterrows():
                    al_name = str(row['Airline'])
                    s_val = row[target_val]
                    s_ms = row['공급 M/S (%)']
                    is_ke = (al_name == 'KE')
                    row_style = ' class="row-group-header"' if is_ke else ''
                    sup_pivot_html += f'<tr{row_style}><td style="text-align:center;"><b>{rank_idx}위</b></td><td style="text-align:center; font-weight:700;">{"★ KE" if is_ke else al_name}</td><td style="text-align:center;"><b>{s_val:,.0f}</b></td><td style="text-align:center;"><b>{s_ms:.1f}%</b></td></tr>'

                sup_pivot_html += '</tbody></table></div>'
                st.markdown(sup_pivot_html, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown('<div class="unified-sub-header">3. 항공사별 스케줄 타임라인</div>', unsafe_allow_html=True)
            
            ke_sup_sub = filtered_sup[filtered_sup['Airline'] == 'KE']
            ke_seats_total = ke_sup_sub['Seats_num'].sum() if not ke_sup_sub.empty else 0
            ke_flights_total = ke_sup_sub['Flights_num'].sum() if not ke_sup_sub.empty else 0

            st.markdown(f"""
            <div class="ke-timeline-box">
                <b>✈️ [대한항공(KE) 공급 스케줄 요약]</b> &nbsp;|&nbsp; 
                총 공급석: <b>{ke_seats_total:,.0f}석</b> &nbsp;|&nbsp; 
                총 운항편수: <b>{ke_flights_total:,.0f}회</b> (점유비: <b>{ke_sup_ms:.1f}%</b>)
            </div>
            """, unsafe_allow_html=True)

            is_all_selected = (selected_sup_route_str == ALL_OPTION)
            if is_all_selected:
                st.info("💡 **상단 필터에서 특정 노선을 선택하시면 해당 노선의 항공사별 운항 스케줄 타임라인이 표출됩니다.**")
            else:
                selected_single_route = [selected_sup_route_str][0]
                df_schedule = filtered_sup[filtered_sup['노선_clean'] == selected_single_route].copy() if '노선_clean' in filtered_sup.columns else filtered_sup[filtered_sup['노선'] == selected_single_route].copy()
                if not df_schedule.empty and 'Dep Time' in df_schedule.columns:
                    time_tuples = df_schedule['Dep Time'].apply(format_dep_time)
                    df_schedule['Start_Time'] = [t[0] for t in time_tuples]
                    df_schedule['End_Time'] = [t[1] for t in time_tuples]

                    fig_timeline = px.timeline(df_schedule, x_start="Start_Time", x_end="End_Time", y="Airline", color="Airline", text="Airline", title=f"[{selected_single_route}] 노선 하루 출발 시간대별 운항 스케줄 타임라인", color_discrete_map=sup_color_map, category_orders={'Airline': sup_airlines})
                    fig_timeline.update_yaxes(autorange="reversed", title="항공사")
                    fig_timeline.update_xaxes(title="하루 시간대 (00:00 ~ 24:00)", dtick=3600000, tickformat="%H:%M")
                    fig_timeline.update_traces(textposition='inside', hovertemplate="<b>항공사: %{y}</b><br>출발시각: %{x}<br>공급석: %{customdata[0]:,.0f}석<extra></extra>", customdata=df_schedule[['Seats_num']])
                    fig_timeline.update_layout(height=400, showlegend=True)
                    apply_bottom_legend(fig_timeline)
                    st.plotly_chart(fig_timeline, width='stretch')

    # 3. 🏷️ 대리점,RBD별 발매현황 탭 (KE 취항 노선 전용 필터 보정 완수)
    with tab_34_3:
        if df_iss_merged is not None:
            df_agency = df_iss_merged.copy()
            week_col_a = '발매주차_일자' if '발매주차_일자' in df_agency.columns else ('발매 주차' if '발매 주차' in df_agency.columns else '발매주차')
            month_col_a = '출발월' if '출발월' in df_agency.columns else ('출발 월' if '출발 월' in df_agency.columns else None)
            bound_col_a = '수송' if '수송' in df_agency.columns else ('Bound' if 'Bound' in df_agency.columns else None)
            time_col_a = '출발시간대' if '출발시간대' in df_agency.columns else None
            
            # 📌 22개 마스터 노선 중 실적(Value > 0)이 존재하는 KE 취항 노선만 추출
            df_agency['노선_clean'] = df_agency['노선'].astype(str).str.strip()
            df_ag_has_val = df_agency[(df_agency['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER)) & (df_agency['Value'] > 0)]
            ag_route_sum = df_ag_has_val.groupby('노선_clean', observed=False)['Value'].sum().sort_values(ascending=False)
            all_routes_a = [str(x).strip() for x in ag_route_sum.index.tolist() if str(x) != 'nan']
            
            all_months_a = sorted([str(x) for x in df_agency[month_col_a].dropna().unique()]) if month_col_a else []
            all_bounds_a = sorted([str(x) for x in df_agency[bound_col_a].dropna().unique()]) if bound_col_a else []
            all_tt_a = sorted([str(x) for x in df_agency['Ticket Type'].dropna().unique()]) if 'Ticket Type' in df_agency.columns else []
            all_time_a = sorted([str(x) for x in df_agency[time_col_a].dropna().unique()]) if time_col_a else []
            
            raw_ag_al = sorted([str(x) for x in df_agency['Dominant Marketing Airline'].dropna().unique()])
            all_al_a = ['KE'] + [x for x in raw_ag_al if x != 'KE'] if 'KE' in raw_ag_al else raw_ag_al

            with st.expander("🔍 **대리점 & RBD 분석 피벗 슬라이서 필터 설정** (KE 취항노선 전용)", expanded=True):
                ac1, ac2, ac3 = st.columns(3)
                sel_route_ag_str = render_slicer_box(ac1, "1. 노선", all_routes_a, "slicer_route_ag_fixed")
                sel_month_ag_str = render_slicer_box(ac2, "2. 출발 월", all_months_a, "slicer_month_ag_fixed") if month_col_a else ALL_OPTION
                sel_bound_ag_str = render_slicer_box(ac3, "3. 수송 구분 (3TF/4TF/OTHERS)", all_bounds_a, "slicer_bound_ag_fixed") if bound_col_a else ALL_OPTION

                ac4, ac5, ac6 = st.columns(3)
                sel_tt_ag_str = render_slicer_box(ac4, "4. TRIP TYPE", all_tt_a, "slicer_tt_ag_fixed") if 'Ticket Type' in df_agency.columns else ALL_OPTION
                sel_time_ag_str = render_slicer_box(ac5, "5. 출발 시간대", all_time_a, "slicer_time_ag_fixed") if time_col_a else ALL_OPTION
                sel_al_ag_str = render_slicer_box(ac6, "6. 항공사", all_al_a, "slicer_al_ag_fixed")

            mask_ag = pd.Series(True, index=df_agency.index)
            if sel_route_ag_str != ALL_OPTION:
                mask_ag &= (df_agency['노선_clean'] == sel_route_ag_str)
            else:
                mask_ag &= (df_agency['노선_clean'].isin(all_routes_a))

            if sel_al_ag_str != ALL_OPTION: mask_ag &= (df_agency['Dominant Marketing Airline'].astype(str) == sel_al_ag_str)
            if month_col_a and sel_month_ag_str != ALL_OPTION: mask_ag &= (df_agency[month_col_a].astype(str) == sel_month_ag_str)
            if bound_col_a and sel_bound_ag_str != ALL_OPTION: mask_ag &= (df_agency[bound_col_a].astype(str) == sel_bound_ag_str)
            if 'Ticket Type' in df_agency.columns and sel_tt_ag_str != ALL_OPTION: mask_ag &= (df_agency['Ticket Type'].astype(str) == sel_tt_ag_str)
            if time_col_a and sel_time_ag_str != ALL_OPTION: mask_ag &= (df_agency[time_col_a].astype(str) == sel_time_ag_str)

            df_ag_filtered = df_agency[mask_ag]

            expand_toggle_all = st.toggle("📂 전체 항목 펼쳐보기 (열기/닫기)", value=True, key="expand_toggle_all_key_fixed")
            open_attr = "open" if expand_toggle_all else ""

            sub_tab_rbd, sub_tab_agency = st.tabs(["📊 RBD별 판매현황", "🏢 대리점별 판매현황 (상위 20개 대리점)"])

            with sub_tab_rbd:
                if not df_ag_filtered.empty and 'O&D RBKD' in df_ag_filtered.columns and week_col_a:
                    week_list = sorted([str(x) for x in df_ag_filtered[week_col_a].dropna().unique()], reverse=True)
                    ag_al_sum = df_ag_filtered.groupby('Dominant Marketing Airline', observed=False)['Value'].sum().sort_values(ascending=False)
                    ag_al_list = ['KE'] + [str(x) for x in ag_al_sum.index if x != 'KE' and ag_al_sum[x] > 0]

                    rbd_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead><tr><th class="header-main" style="width:180px; text-align:center;">항공사 / RBD 클래스</th>'
                    for wk in week_list: rbd_html += f'<th class="header-main">{wk}</th>'
                    rbd_html += '<th class="header-main">총합계</th></tr></thead><tbody>'

                    for al_code in ag_al_list:
                        al_sub = df_ag_filtered[df_ag_filtered['Dominant Marketing Airline'] == al_code]
                        al_tot_pax = al_sub['Value'].sum()

                        if al_tot_pax > 0:
                            piv_rbd = al_sub.pivot_table(index='O&D RBKD', columns=week_col_a, values='Value', aggfunc='sum', fill_value=0, observed=False)
                            piv_rbd['총합계'] = piv_rbd.sum(axis=1)

                            piv_rbd = piv_rbd[piv_rbd['총합계'] > 0]

                            if not piv_rbd.empty:
                                if al_code in RBD_HIERARCHY:
                                    hierarchy_order = RBD_HIERARCHY[al_code]
                                    existing_rbds = piv_rbd.index.tolist()
                                    sorted_rbds = [r for r in hierarchy_order if r in existing_rbds] + [r for r in existing_rbds if r not in hierarchy_order]
                                    piv_rbd = piv_rbd.loc[sorted_rbds]

                                rbd_html += f'<tr><td colspan="{len(week_list)+2}" style="padding:0; border:none;"><details class="rbd-details-group" {open_attr}><summary><table style="width:100%; border-collapse:collapse;"><tr class="row-summary-top-dark"><td style="width:180px; text-align:center;">▼ ★ {al_code} 총계</td>'
                                for wk in week_list: rbd_html += f'<td style="text-align:center;">{al_sub[al_sub[week_col_a] == wk]["Value"].sum():,.0f}</td>'
                                rbd_html += f'<td style="text-align:center;">{al_tot_pax:,.0f}</td></tr></table></summary><table style="width:100%; border-collapse:collapse;">'

                                for rbd_code, rbd_row in piv_rbd.iterrows():
                                    rbd_html += f'<tr class="rbd-child-row"><td style="width:180px; text-align:center; font-weight:700;">{rbd_code}</td>'
                                    for wk in week_list: rbd_html += f'<td style="text-align:center;">{rbd_row[wk]:,.0f}</td>'
                                    rbd_html += f'<td style="text-align:center; font-weight:700;">{rbd_row["총합계"]:,.0f}</td></tr>'
                                rbd_html += '</table></details></td></tr>'

                    rbd_html += '</tbody></table></div>'
                    st.markdown(rbd_html, unsafe_allow_html=True)

            with sub_tab_agency:
                if not df_ag_filtered.empty and 'Travel Agency Name' in df_ag_filtered.columns and week_col_a:
                    week_list_ag = sorted([str(x) for x in df_ag_filtered[week_col_a].dropna().unique()], reverse=True)
                    agency_totals = df_ag_filtered.groupby('Travel Agency Name', observed=False)['Value'].sum().sort_values(ascending=False)
                    top_20_agencies = [ag for ag in agency_totals.index if agency_totals[ag] > 0][:20]

                    ag_html = '<div class="custom-piv-container"><table class="custom-piv-table"><thead><tr><th class="header-main" style="width:180px; text-align:center;">대리점 / 항공사</th>'
                    for wk in week_list_ag: ag_html += f'<th class="header-main">{wk}</th>'
                    ag_html += '<th class="header-main">총 판매량</th></tr></thead><tbody>'

                    for ag_name in top_20_agencies:
                        ag_sub = df_ag_filtered[df_ag_filtered['Travel Agency Name'] == ag_name]
                        ag_tot_val = ag_sub['Value'].sum()

                        if ag_tot_val > 0:
                            piv_ag_sub = ag_sub.pivot_table(index='Dominant Marketing Airline', columns=week_col_a, values='Value', aggfunc='sum', fill_value=0, observed=False)
                            piv_ag_sub['총합계'] = piv_ag_sub.sum(axis=1)
                            
                            piv_ag_sub = piv_ag_sub[piv_ag_sub['총합계'] > 0]

                            if not piv_ag_sub.empty:
                                ag_html += f'<tr><td colspan="{len(week_list_ag)+2}" style="padding:0; border:none;"><details class="rbd-details-group" {open_attr}><summary><table style="width:100%; border-collapse:collapse;"><tr class="row-summary-top-dark"><td style="width:180px; text-align:center;">▼ ★ {ag_name} 총계</td>'
                                for wk in week_list_ag: ag_html += f'<td style="text-align:center;">{ag_sub[ag_sub[week_col_a] == wk]["Value"].sum():,.0f}</td>'
                                ag_html += f'<td style="text-align:center;">{ag_tot_val:,.0f}</td></tr></table></summary><table style="width:100%; border-collapse:collapse;">'

                                for al_code, al_row in piv_ag_sub.iterrows():
                                    is_ke_flag = (al_code == 'KE')
                                    cell_style = 'font-weight:700; color:#16a34a;' if is_ke_flag else 'color:#475569;'
                                    ag_html += f'<tr class="rbd-child-row"><td style="width:180px; text-align:center; {cell_style}">{"★ KE" if is_ke_flag else al_code}</td>'
                                    for wk in week_list_ag: ag_html += f'<td style="text-align:center; {cell_style}">{al_row[wk]:,.0f}</td>'
                                    ag_html += f'<td style="text-align:center; font-weight:700; {cell_style}">{al_row["총합계"]:,.0f}</td></tr>'
                                ag_html += '</table></details></td></tr>'

                    ag_html += '</tbody></table></div>'
                    st.markdown(ag_html, unsafe_allow_html=True)

    # 4. 👥 단체실적 탭 (KE 취항 노선 전용 필터 보정 완수)
    with tab_34_4:
        st.subheader("👥 발매 - 항공사별/대리점별 단체 발매 현황")
        if df_iss_merged is not None:
            df_grp_raw = df_iss_merged.copy()
            
            # 📌 22개 마스터 노선 중 실적(Value > 0)이 있는 KE 취항 노선으로 정확히 제한
            df_grp_raw['노선_clean'] = df_grp_raw['노선'].astype(str).str.strip()
            df_g_has_val = df_grp_raw[(df_grp_raw['노선_clean'].isin(EXCEL_KE_ROUTES_MASTER)) & (df_grp_raw['Value'] > 0)]
            g_route_sum = df_g_has_val.groupby('노선_clean', observed=False)['Value'].sum().sort_values(ascending=False)
            g_routes = [str(x).strip() for x in g_route_sum.index.tolist() if str(x) != 'nan']

            g_m_col = '출발월' if '출발월' in df_grp_raw.columns else ('출발 월' if '출발 월' in df_grp_raw.columns else None)
            g_months = sorted([str(x) for x in df_grp_raw[g_m_col].dropna().unique()]) if g_m_col else []
            g_b_col = '수송' if '수송' in df_grp_raw.columns else ('Bound' if 'Bound' in df_grp_raw.columns else None)
            g_bounds = sorted([str(x) for x in df_grp_raw[g_b_col].dropna().unique()]) if g_b_col else []
            g_tts = sorted([str(x) for x in df_grp_raw['Ticket Type'].dropna().unique()]) if 'Ticket Type' in df_grp_raw.columns else []
            g_t_col = '출발시간대' if '출발시간대' in df_grp_raw.columns else None
            g_times = sorted([str(x) for x in df_grp_raw[g_t_col].dropna().unique()]) if g_t_col else []
            g_als = sorted([str(x) for x in df_grp_raw['Dominant Marketing Airline'].dropna().unique()]) if 'Dominant Marketing Airline' in df_grp_raw.columns else []

            with st.expander("🔍 **단체 실적 분석 피벗 슬라이서 필터 설정** (KE 취항노선 전용)", expanded=True):
                gc1, gc2, gc3 = st.columns(3)
                sel_g_route = render_slicer_box(gc1, "1. 노선", g_routes, "slicer_g_route_fixed")
                sel_g_month = render_slicer_box(gc2, "2. 출발 월", g_months, "slicer_g_month_fixed") if g_m_col else ALL_OPTION
                sel_g_bound = render_slicer_box(gc3, "3. 수송 구분 (3TF/4TF/OTHERS)", g_bounds, "slicer_g_bound_fixed") if g_b_col else ALL_OPTION

                gc4, gc5, gc6 = st.columns(3)
                sel_g_tt = render_slicer_box(gc4, "4. TRIP TYPE", g_tts, "slicer_g_tt_fixed")
                sel_g_time = render_slicer_box(gc5, "5. 출발 시간대", g_times, "slicer_g_time_fixed") if g_t_col else ALL_OPTION
                sel_g_al = render_slicer_box(gc6, "6. 항공사", g_als, "slicer_g_al_fixed")

            mask_grp = pd.Series(True, index=df_grp_raw.index)
            if sel_g_route != ALL_OPTION:
                mask_grp &= (df_grp_raw['노선_clean'] == sel_g_route)
            else:
                mask_grp &= (df_grp_raw['노선_clean'].isin(g_routes))

            if g_m_col and sel_g_month != ALL_OPTION: mask_grp &= (df_grp_raw[g_m_col].astype(str) == sel_g_month)
            if g_b_col and sel_g_bound != ALL_OPTION: mask_grp &= (df_grp_raw[g_b_col].astype(str) == sel_g_bound)
            if 'Ticket Type' in df_grp_raw.columns and sel_g_tt != ALL_OPTION: mask_grp &= (df_grp_raw['Ticket Type'].astype(str) == sel_g_tt)
            if g_t_col and sel_g_time != ALL_OPTION: mask_grp &= (df_grp_raw[g_t_col].astype(str) == sel_g_time)
            if 'Dominant Marketing Airline' in df_grp_raw.columns and sel_g_al != ALL_OPTION: mask_grp &= (df_grp_raw['Dominant Marketing Airline'].astype(str) == sel_g_al)

            is_grp_cond = (((df_grp_raw['Dominant Marketing Airline'] == '7C') & (df_grp_raw['O&D RBKD'] == 'V')) | ((df_grp_raw['Dominant Marketing Airline'] != '7C') & (df_grp_raw['O&D RBKD'] == 'G')))
            df_grp_filtered = df_grp_raw[mask_grp & is_grp_cond].copy()

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
    if df_6th_raw is None:
        st.warning("👈 좌측 사이드바 3번 위치에서 6수송 CSV 파일을 업로드해 주세요.")
        st.stop()

    @st.cache_data(max_entries=2, ttl=3600)
    def prepare_6th_freedom_dataset(df_in):
        if df_in is None or df_in.empty: return None, {}
        df_6_raw = df_in.copy()
        df_6_raw.columns = [str(c).strip() for c in df_6_raw.columns]
        
        col_map_6th = {
            'TRIP MONTH': ['TRIP MONTH', 'Travel Month', '출발 월', '출발 월 ', 'Trip Month', 'TRIP_MONTH', 'MONTH', 'Travel_Month'],
            '4.OD RGN': ['4.OD RGN', 'OD REGION', 'Region', 'OD 권역', '4. OD RGN', 'OD RGN', 'OD_REGION', '4.OD_RGN', 'ODREGION'],
            'DIRECTION': ['DIRECTION', 'Bound', 'Direction', 'DIR', 'BOUND'],
            'STOP OVER': ['STOP OVER', 'Stopover', 'Stops', 'STOPOVER', 'STOP_OVER'],
            'OD ON/OFF': ['O&D Market', 'OD Market', 'OD ON/OFF', 'OD Pair', 'O&D ON/OFF', 'OD_PAIR', 'O&D Pair', 'O&D', 'OD_NAME', 'O&D_NAME', 'OD ON-OFF', 'OD_ON_OFF', 'Trip O&D Market'],
            'Sub-Route': ['Sub-Route', '소노선', 'Sub Route', 'SUB_ROUTE', 'SUBROUTE', '일본 APO', 'Japan Airport', 'Origin Code', 'Destination Code', 'JPN APO'],
            'ON/OFF 여부': ['JPN-해외', 'ON/OFF 여부', 'ON/OFF', 'ON_OFF', 'ON/OFF_여부'],
            '해외 APO': ['해외 APO', 'Overseas Airport', 'Foreign Airport', '해외APO', 'OVERSEAS_APO'],
            '항공사': ['Dominant Marketing Airline', 'Op Airline Code', 'Airline', '항공사', 'CARRIER', 'AIRLINE', 'Marketing Airline', 'Mkt Al', 'MKT_AL', 'DOMINANT_MARKETING_AIRLINE'],
            '금전구분': ['금/전', '금전구분', '구분', 'Year_Type', '금년/전년', 'YEAR_TYPE', 'CY_PY', '금년_전년']
        }

        def get_actual_col(df_curr, possible_names):
            for c in possible_names:
                if c in df_curr.columns: return c
            return None

        actual_cols = {key: get_actual_col(df_6_raw, p_list) for key, p_list in col_map_6th.items()}

        if not actual_cols['OD ON/OFF']:
            for c in df_6_raw.columns:
                if any(x in c.upper() for x in ['MARKET', 'OD', 'PAIR', 'O&D']):
                    actual_cols['OD ON/OFF'] = c
                    break
            if not actual_cols['OD ON/OFF']: actual_cols['OD ON/OFF'] = df_6_raw.columns[0]

        if not actual_cols['항공사']:
            for c in df_6_raw.columns:
                if any(x in c.upper() for x in ['AIRLINE', 'CARRIER', '항공사', 'AL']):
                    actual_cols['항공사'] = c
                    break
            if not actual_cols['항공사']: actual_cols['항공사'] = df_6_raw.columns[1] if len(df_6_raw.columns) > 3 else df_6_raw.columns[0]

        val_col_candidates = ['Value', 'VALUE', 'Pax', 'PAX', '실적', '발매량', 'Seats', 'Flights']
        val_col_6 = None
        for vc in val_col_candidates:
            if vc in df_6_raw.columns:
                val_col_6 = vc
                break
        if not val_col_6: val_col_6 = df_6_raw.columns[-1]

        df_6_raw['Val_raw'] = pd.to_numeric(df_6_raw[val_col_6].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)

        year_type_col = actual_cols['금전구분']
        if year_type_col and year_type_col in df_6_raw.columns:
            cy_mask = df_6_raw[year_type_col].astype(str).str.strip().str.contains('금년|CY', na=False)
            py_mask = df_6_raw[year_type_col].astype(str).str.strip().str.contains('전년|PY', na=False)
            
            df_cy_only = df_6_raw[cy_mask].copy()
            df_py_only = df_6_raw[py_mask].copy()
            
            df_cy_only['Val_num'] = df_cy_only['Val_raw']
            df_cy_only['Val_PY_num'] = 0.0
            
            df_py_only['Val_num'] = 0.0
            df_py_only['Val_PY_num'] = df_py_only['Val_raw']
            
            df_out = pd.concat([df_cy_only, df_py_only], ignore_index=True)
        else:
            df_out = df_6_raw.copy()
            df_out['Val_num'] = df_out['Val_raw']
            df_out['Val_PY_num'] = 0.0

        return optimize_df(df_out), actual_cols

    df_6, actual_cols = prepare_6th_freedom_dataset(df_6th_raw)

    if df_6 is None or df_6.empty:
        st.warning("6수송 데이터를 파싱하지 못했습니다. 업로드된 파일의 형태를 확인해 주세요.")
        st.stop()

    al_col_6 = actual_cols['항공사']
    od_col_6 = actual_cols['OD ON/OFF']
    month_col_6 = actual_cols['TRIP MONTH']

    m_list_6 = sorted([str(x).strip() for x in df_6[month_col_6].dropna().unique() if str(x).strip() != 'nan']) if month_col_6 and month_col_6 in df_6.columns else []
    dynamic_dep_6th = f"{m_list_6[0]} ~ {m_list_6[-1]}" if m_list_6 else dep_range_str

    st.markdown(f"""
    <div class="source-header-box">
        <b>📌 출처: DDS & OAG 데이터 (6수송 대시보드)</b> &nbsp;|&nbsp; 
        <b>🗓️ 발매기간 (Purchase Month):</b> {issue_range_str_6th} &nbsp;|&nbsp; 
        <b>✈️ 출발기간 (Trip Month):</b> {dynamic_dep_6th}
    </div>
    """, unsafe_allow_html=True)

    if al_col_6 and al_col_6 in df_6.columns:
        al_order_6th = df_6.groupby(al_col_6, observed=False)['Val_num'].sum().sort_values(ascending=False).index.astype(str).tolist()
        if 'KE' in al_order_6th:
            al_order_6th.remove('KE')
            sorted_6th_airlines = ['KE'] + al_order_6th
        else:
            sorted_6th_airlines = ['KE'] + al_order_6th
    else:
        sorted_6th_airlines = ['KE']

    all_raw_m = sorted([str(x) for x in df_6[df_6['Val_num'] > 0][month_col_6].dropna().unique()]) if month_col_6 and month_col_6 in df_6.columns else []

    act_dir_c = actual_cols['DIRECTION']
    all_dir_6 = sorted([str(x) for x in df_6[act_dir_c].dropna().unique()]) if act_dir_c and act_dir_c in df_6.columns else []

    act_stop_c = actual_cols['STOP OVER']
    all_stop_6 = sorted([str(x) for x in df_6[act_stop_c].dropna().unique()]) if act_stop_c and act_stop_c in df_6.columns else []

    act_onoff_c = actual_cols['ON/OFF 여부']
    all_onoff_6 = sorted([str(x) for x in df_6[act_onoff_c].dropna().unique()]) if act_onoff_c and act_onoff_c in df_6.columns else []

    act_reg_c = actual_cols['4.OD RGN']
    all_reg_6 = sorted([str(x) for x in df_6[act_reg_c].dropna().unique()]) if act_reg_c and act_reg_c in df_6.columns else []

    act_sub_c = actual_cols['Sub-Route']
    if act_sub_c and act_sub_c in df_6.columns:
        sub_sum = df_6.groupby(act_sub_c, observed=False)['Val_num'].sum().sort_values(ascending=False)
        all_sub_6 = [str(x) for x in sub_sum.index if pd.notnull(x)]
    else: all_sub_6 = []

    act_ov_c = actual_cols['해외 APO']
    all_ov_6 = sorted([str(x) for x in df_6[act_ov_c].dropna().unique()]) if act_ov_c and act_ov_c in df_6.columns else []

    def filter_month_yoy(df_target, selected_m_val):
        if selected_m_val == ALL_OPTION or not month_col_6 or month_col_6 not in df_target.columns:
            return pd.Series(True, index=df_target.index)
        if '-' in str(selected_m_val):
            sub_m = str(selected_m_val).split('-')[-1]
            return df_target[month_col_6].astype(str).str.endswith(sub_m) | (df_target[month_col_6].astype(str) == selected_m_val)
        return df_target[month_col_6].astype(str) == selected_m_val

    tab6_1, tab6_2 = st.tabs(["📊 O&D별 종합 M/S 분석 및 Carrier별 상세 비교", "📋 6수송 Raw Data View"])

    with tab6_1:
        # 📌 1. 제목 명칭 변경 (✈️ 6수송 발매 M/S 현황)
        st.markdown('<div class="unified-sub-header">✈️ 6수송 발매 M/S 현황</div>', unsafe_allow_html=True)
        f1_col1, f1_col2, f1_col3, f1_col4 = st.columns(4)
        sel_1_month = render_slicer_box(f1_col1, "1. 출발월 (Trip Month)", all_raw_m, "slicer1_m_fixed")
        sel_1_region = render_slicer_box(f1_col2, "2. OD Region", all_reg_6, "slicer1_reg_fixed")
        sel_1_dir = render_slicer_box(f1_col3, "3. 일본발/일본행 (Direction)", all_dir_6, "slicer1_dir_fixed")
        sel_1_stop = render_slicer_box(f1_col4, "4. 경유/직항 (Stopover)", all_stop_6, "slicer1_stop_fixed")

        f1_col5, f1_col6, f1_col7, f1_col8 = st.columns(4)
        sel_1_onoff = render_slicer_box(f1_col5, "5. Online/Offline", all_onoff_6, "slicer1_onoff_fixed")
        sel_1_jp_route = render_slicer_box(f1_col6, "6. 일본공항 (Sub-Route)", all_sub_6, "slicer1_sub_fixed")
        sel_1_ov_apo = render_slicer_box(f1_col7, "7. 해외공항 (해외 APO)", all_ov_6, "slicer1_ov_fixed")

        # 📌 상단 첫번째 종합 요약 표용 필터링 마스크
        mask_base_1_to_7 = filter_month_yoy(df_6, sel_1_month)
        if act_reg_c and act_reg_c in df_6.columns and sel_1_region != ALL_OPTION: mask_base_1_to_7 &= (df_6[act_reg_c].astype(str) == sel_1_region)
        if act_dir_c and act_dir_c in df_6.columns and sel_1_dir != ALL_OPTION: mask_base_1_to_7 &= (df_6[act_dir_c].astype(str) == sel_1_dir)
        if act_stop_c and act_stop_c in df_6.columns and sel_1_stop != ALL_OPTION: mask_base_1_to_7 &= (df_6[act_stop_c].astype(str) == sel_1_stop)
        if act_onoff_c and act_onoff_c in df_6.columns and sel_1_onoff != ALL_OPTION: mask_base_1_to_7 &= (df_6[act_onoff_c].astype(str) == sel_1_onoff)
        if act_sub_c and act_sub_c in df_6.columns and sel_1_jp_route != ALL_OPTION: mask_base_1_to_7 &= (df_6[act_sub_c].astype(str) == sel_1_jp_route)
        if act_ov_c and act_ov_c in df_6.columns and sel_1_ov_apo != ALL_OPTION: mask_base_1_to_7 &= (df_6[act_ov_c].astype(str) == sel_1_ov_apo)

        df_dep_for_od = df_6[mask_base_1_to_7]
        if od_col_6 and od_col_6 in df_dep_for_od.columns and not df_dep_for_od.empty:
            od_sum_dep = df_dep_for_od.groupby(od_col_6, observed=False)['Val_num'].sum().sort_values(ascending=False)
            dependent_od_list = [str(x) for x in od_sum_dep.index if pd.notnull(x)]
        else: dependent_od_list = sorted([str(x) for x in df_6[od_col_6].dropna().unique()]) if od_col_6 and od_col_6 in df_6.columns else []

        sel_1_od_mkt = render_slicer_box(f1_col8, "8. Trip O&D Market", dependent_od_list, "slicer1_od_mkt_fixed")

        mask_tab1 = mask_base_1_to_7.copy()
        if od_col_6 and od_col_6 in df_6.columns and sel_1_od_mkt != ALL_OPTION: mask_tab1 &= (df_6[od_col_6].astype(str) == sel_1_od_mkt)

        filtered_tab1 = df_6[mask_tab1].copy()

        if not filtered_tab1.empty and al_col_6 in filtered_tab1.columns:
            al_agg = filtered_tab1.groupby(al_col_6, observed=False)[['Val_num', 'Val_PY_num']].sum().reset_index()
            al_agg = al_agg.sort_values(by='Val_num', ascending=False).reset_index(drop=True)
            
            full_al_ranking = [str(x) for x in al_agg[al_col_6].tolist()]
            ke_rank = (full_al_ranking.index('KE') + 1) if 'KE' in full_al_ranking else "-"

            top_10_no_ke = [x for x in full_al_ranking if x != 'KE'][:10]
            airline_rank_list = ['KE'] + top_10_no_ke

            html_table = '<div class="yoy-table-container"><table class="yoy-table"><thead><tr><th class="mkt-header" style="width:110px;">월별 M/S</th><th class="mkt-header" style="width:110px;">총합계</th>'
            for al_code in airline_rank_list:
                if al_code == 'KE': html_table += f'<th class="ke-header" style="width:130px;">KE (대한항공 - {ke_rank}위)</th>'
                else:
                    rank_num = full_al_ranking.index(al_code) + 1 if al_code in full_al_ranking else "-"
                    html_table += f'<th class="carrier-header" style="width:110px;"><div style="font-size:10px; opacity:0.85;">{rank_num}위</div>{al_code}</th>'
            html_table += '</tr></thead><tbody>'

            t_curr = al_agg['Val_num'].sum()
            t_prev = al_agg['Val_PY_num'].sum()
            t_yoy_pct = ((t_curr - t_prev) / t_prev * 100) if t_prev > 0 else 0

            html_table += f'<tr class="row-title"><td>전체 발매</td><td><b>{t_curr:,.0f}</b></td>'
            for al_code in airline_rank_list:
                row_val = al_agg[al_agg[al_col_6] == al_code]['Val_num'].sum()
                html_table += f'<td><b>{row_val:,.0f}</b></td>'
            html_table += '</tr>'

            html_table += f'<tr><td style="color:#64748b; font-weight:600;">YOY</td><td>{format_yoy_html(t_yoy_pct) if t_prev>0 else "-"}</td>'
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[al_col_6] == al_code]['Val_num'].sum()
                p_val = al_agg[al_agg[al_col_6] == al_code]['Val_PY_num'].sum()
                indiv_yoy = ((c_val - p_val) / p_val * 100) if p_val > 0 else 0
                html_table += f'<td>{format_yoy_html(indiv_yoy) if p_val>0 else "-"}</td>'
            html_table += '</tr>'

            html_table += '<tr class="row-title"><td>전체 M/S</td><td><b>100%</b></td>'
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[al_col_6] == al_code]['Val_num'].sum()
                ms_val = (c_val / t_curr * 100) if t_curr > 0 else 0
                html_table += f'<td><b>{ms_val:.0f}%</b></td>'
            html_table += '</tr>'

            diff_total_ms = 0
            html_table += f'<tr class="row-ms-yoy"><td style="color:#64748b; font-weight:600;">YOY</td><td>{format_yoy_html(diff_total_ms, True) if t_prev>0 else "-"}</td>'
            
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[al_col_6] == al_code]['Val_num'].sum()
                p_val = al_agg[al_agg[al_col_6] == al_code]['Val_PY_num'].sum()
                ms_c = (c_val / t_curr * 100) if t_curr > 0 else 0
                ms_p = (p_val / t_prev * 100) if t_prev > 0 else 0
                diff_p = ms_c - ms_p
                html_table += f'<td>{format_yoy_html(diff_p, True) if t_prev>0 and p_val>0 else "-"}</td>'
            html_table += '</tr></tbody></table></div>'
            st.markdown(html_table, unsafe_allow_html=True)

            # 📌 2. 하단 제목 명칭 변경 (📊 항공사별 TOP20 O&D)
            st.markdown("---")
            st.markdown('<div class="unified-sub-header">📊 항공사별 TOP20 O&D</div>', unsafe_allow_html=True)
            
            with st.expander("🔍 **항공사별 TOP20 O&D 분석 슬라이서 필터 설정**", expanded=True):
                c_f_col1, c_f_col2, c_f_col3, c_f_col4 = st.columns(4)
                sel_2_month = render_slicer_box(c_f_col1, "1. 출발월 (Trip Month)", all_raw_m, "slicer2_m_carrier")
                sel_2_region = render_slicer_box(c_f_col2, "2. OD Region", all_reg_6, "slicer2_reg_carrier")
                sel_2_dir = render_slicer_box(c_f_col3, "3. 일본발/일본행 (Direction)", all_dir_6, "slicer2_dir_carrier")
                sel_2_stop = render_slicer_box(c_f_col4, "4. 경유/직항 (Stopover)", all_stop_6, "slicer2_stop_carrier")

                c_f_col5, c_f_col6, c_f_col7, c_f_col8 = st.columns(4)
                sel_2_onoff = render_slicer_box(c_f_col5, "5. Online/Offline", all_onoff_6, "slicer2_onoff_carrier")
                sel_2_jp_route = render_slicer_box(c_f_col6, "6. 일본공항 (Sub-Route)", all_sub_6, "slicer2_sub_carrier")
                sel_2_ov_apo = render_slicer_box(c_f_col7, "7. 해외공항 (해외 APO)", all_ov_6, "slicer2_ov_carrier")
                sel_2_carrier = render_slicer_box(c_f_col8, "8. CARRIER (항공사)", sorted_6th_airlines, "slicer2_carrier")

            # 📌 하단 테이블 전용 필터 마스크 생성
            mask_carrier_tab = filter_month_yoy(df_6, sel_2_month)
            if act_reg_c and act_reg_c in df_6.columns and sel_2_region != ALL_OPTION: mask_carrier_tab &= (df_6[act_reg_c].astype(str) == sel_2_region)
            if act_dir_c and act_dir_c in df_6.columns and sel_2_dir != ALL_OPTION: mask_carrier_tab &= (df_6[act_dir_c].astype(str) == sel_2_dir)
            if act_stop_c and act_stop_c in df_6.columns and sel_2_stop != ALL_OPTION: mask_carrier_tab &= (df_6[act_stop_c].astype(str) == sel_2_stop)
            if act_onoff_c and act_onoff_c in df_6.columns and sel_2_onoff != ALL_OPTION: mask_carrier_tab &= (df_6[act_onoff_c].astype(str) == sel_2_onoff)
            if act_sub_c and act_sub_c in df_6.columns and sel_2_jp_route != ALL_OPTION: mask_carrier_tab &= (df_6[act_sub_c].astype(str) == sel_2_jp_route)
            if act_ov_c and act_ov_c in df_6.columns and sel_2_ov_apo != ALL_OPTION: mask_carrier_tab &= (df_6[act_ov_c].astype(str) == sel_2_ov_apo)

            filtered_carrier_df = df_6[mask_carrier_tab].copy()

            if not filtered_carrier_df.empty:
                # 📌 3. 항공사 선택 시 해당 항공사 실적이 있는 O&D 기반 상위 20개 추출 로직
                if sel_2_carrier != ALL_OPTION:
                    carrier_only_df = filtered_carrier_df[filtered_carrier_df[al_col_6] == sel_2_carrier]
                    top_ods = carrier_only_df.groupby(od_col_6, observed=False)['Val_num'].sum().sort_values(ascending=False).head(20).index.tolist()
                else:
                    od_totals_all = filtered_carrier_df.groupby(od_col_6, observed=False)['Val_num'].sum()
                    top_ods = od_totals_all.sort_values(ascending=False).head(20).index.tolist()

                od_carrier_df = filtered_carrier_df.groupby([od_col_6, al_col_6], observed=False)[['Val_num', 'Val_PY_num']].sum().reset_index()
                od_totals = filtered_carrier_df.groupby(od_col_6, observed=False)[['Val_num', 'Val_PY_num']].sum().reset_index()

                target_carrier = sel_2_carrier if sel_2_carrier != ALL_OPTION else "1위 항공사"

                # 📌 4. 테이블 헤더 디자인 및 테마 색상 (#cfe2f3, #9fc5e8, #6fa8dc) 반영
                c_html = '<div class="carrier-excel-container"><table class="carrier-excel-table"><thead>'
                c_html += '<tr><th rowspan="2" class="th-dark-blue">순위</th><th rowspan="2" class="th-dark-blue">TOP O&D</th>'
                c_html += '<th colspan="3" class="th-mkt-blue">시장 전체</th>'
                c_html += f'<th colspan="3" class="th-sel-blue">선택 항공사 ({target_carrier}) 발매량</th>'
                c_html += f'<th colspan="3" class="th-sel-light">선택 항공사 ({target_carrier}) M/S</th>'
                c_html += '<th colspan="3" class="th-ke-green">KE 발매량</th>'
                c_html += '<th colspan="3" class="th-ke-light">KE M/S</th></tr>'
                
                c_html += '<tr><th class="th-mkt-blue">금년</th><th class="th-mkt-blue">전년</th><th class="th-mkt-blue">YOY</th>'
                c_html += '<th class="th-sel-blue">금년</th><th class="th-sel-blue">전년</th><th class="th-sel-blue">YOY</th>'
                c_html += '<th class="th-sel-light">M/S</th><th class="th-sel-light">전년</th><th class="th-sel-light">YOY</th>'
                c_html += '<th class="th-ke-green">금년</th><th class="th-ke-green">전년</th><th class="th-ke-green">YOY</th>'
                c_html += '<th class="th-ke-light">M/S</th><th class="th-ke-light">전년</th><th class="th-ke-light">YOY</th></tr></thead><tbody>'

                for rank_idx, od_code in enumerate(top_ods, 1):
                    # 시장 전체
                    mkt_sub = od_totals[od_totals[od_col_6] == od_code]
                    m_cy = mkt_sub['Val_num'].sum() if not mkt_sub.empty else 0
                    m_py = mkt_sub['Val_PY_num'].sum() if not mkt_sub.empty else 0
                    m_yoy = ((m_cy - m_py) / m_py * 100) if m_py > 0 else 0
                    m_yoy_html = format_yoy_html(m_yoy) if m_py > 0 else "-"

                    # 선택 항공사
                    od_al_sub = od_carrier_df[od_carrier_df[od_col_6] == od_code]
                    if sel_2_carrier != ALL_OPTION:
                        top_al_row = od_al_sub[od_al_sub[al_col_6] == sel_2_carrier]
                        s_cy = top_al_row['Val_num'].sum() if not top_al_row.empty else 0
                        s_py = top_al_row['Val_PY_num'].sum() if not top_al_row.empty else 0
                    else:
                        top_al_row = od_al_sub.sort_values(by='Val_num', ascending=False).iloc[0] if not od_al_sub.empty else None
                        s_cy = top_al_row['Val_num'] if top_al_row is not None else 0
                        s_py = top_al_row['Val_PY_num'] if top_al_row is not None else 0

                    s_cy_display = f"{s_cy:,.0f}" if s_cy > 0 else "-"
                    s_py_display = f"{s_py:,.0f}" if s_py > 0 else "-"

                    s_yoy = ((s_cy - s_py) / s_py * 100) if s_py > 0 else 0
                    s_yoy_html = format_yoy_html(s_yoy) if s_py > 0 else "-"

                    s_ms_cy = (s_cy / m_cy * 100) if m_cy > 0 else 0
                    s_ms_py = (s_py / m_py * 100) if m_py > 0 else 0
                    s_ms_diff = s_ms_cy - s_ms_py
                    s_ms_yoy_html = format_yoy_html(s_ms_diff, True) if m_py > 0 else "-"

                    # KE
                    ke_al_row = od_al_sub[od_al_sub[al_col_6] == 'KE']
                    k_cy = ke_al_row['Val_num'].sum() if not ke_al_row.empty else 0
                    k_py = ke_al_row['Val_PY_num'].sum() if not ke_al_row.empty else 0
                    
                    k_cy_display = f"{k_cy:,.0f}" if k_cy > 0 else "-"
                    k_py_display = f"{k_py:,.0f}" if k_py > 0 else "-"

                    k_yoy = ((k_cy - k_py) / k_py * 100) if k_py > 0 else 0
                    k_yoy_html = format_yoy_html(k_yoy) if k_py > 0 else "-"

                    k_ms_cy = (k_cy / m_cy * 100) if m_cy > 0 else 0
                    k_ms_py = (k_py / m_py * 100) if m_py > 0 else 0
                    k_ms_diff = k_ms_cy - k_ms_py
                    k_ms_yoy_html = format_yoy_html(k_ms_diff, True) if m_py > 0 else "-"

                    c_html += f'<tr><td>{rank_idx}</td><td style="font-weight:700;">{od_code}</td>'
                    c_html += f'<td>{m_cy:,.0f}</td><td>{m_py:,.0f}</td><td>{m_yoy_html}</td>'
                    c_html += f'<td>{s_cy_display}</td><td>{s_py_display}</td><td>{s_yoy_html}</td>'
                    c_html += f'<td>{s_ms_cy:.0f}%</td><td>{s_ms_py:.0f}%</td><td>{s_ms_yoy_html}</td>'
                    c_html += f'<td>{k_cy_display}</td><td>{k_py_display}</td><td>{k_yoy_html}</td>'
                    c_html += f'<td>{k_ms_cy:.1f}%</td><td>{k_ms_py:.1f}%</td><td>{k_ms_yoy_html}</td></tr>'

                # 필터 연동 총합계 요약 행
                tot_m_cy = od_totals['Val_num'].sum()
                tot_m_py = od_totals['Val_PY_num'].sum()
                tot_m_yoy = ((tot_m_cy - tot_m_py) / tot_m_py * 100) if tot_m_py > 0 else 0
                
                if sel_2_carrier != ALL_OPTION:
                    sel_tot_cy = filtered_carrier_df[filtered_carrier_df[al_col_6] == sel_2_carrier]['Val_num'].sum()
                    sel_tot_py = filtered_carrier_df[filtered_carrier_df[al_col_6] == sel_2_carrier]['Val_PY_num'].sum()
                else:
                    sel_tot_cy = tot_m_cy
                    sel_tot_py = tot_m_py

                sel_tot_yoy = ((sel_tot_cy - sel_tot_py) / sel_tot_py * 100) if sel_tot_py > 0 else 0
                sel_tot_ms_cy = (sel_tot_cy / tot_m_cy * 100) if tot_m_cy > 0 else 0
                sel_tot_ms_py = (sel_tot_py / tot_m_py * 100) if tot_m_py > 0 else 0
                sel_tot_ms_diff = sel_tot_ms_cy - sel_tot_ms_py

                ke_tot_cy = filtered_carrier_df[filtered_carrier_df[al_col_6] == 'KE']['Val_num'].sum()
                ke_tot_py = filtered_carrier_df[filtered_carrier_df[al_col_6] == 'KE']['Val_PY_num'].sum()
                ke_tot_yoy = ((ke_tot_cy - ke_tot_py) / ke_tot_py * 100) if ke_tot_py > 0 else 0
                ke_tot_ms_cy = (ke_tot_cy / tot_m_cy * 100) if tot_m_cy > 0 else 0
                ke_tot_ms_py = (ke_tot_py / tot_m_py * 100) if tot_m_py > 0 else 0
                ke_tot_ms_diff = ke_tot_ms_cy - ke_tot_ms_py

                c_html += f'<tr class="tr-summary-footer"><td colspan="2">금년 요약</td>'
                c_html += f'<td>{tot_m_cy:,.0f}</td><td>{tot_m_py:,.0f}</td><td>{format_yoy_html(tot_m_yoy)}</td>'
                c_html += f'<td>{sel_tot_cy:,.0f}</td><td>{sel_tot_py:,.0f}</td><td>{format_yoy_html(sel_tot_yoy)}</td>'
                c_html += f'<td>{sel_tot_ms_cy:.0f}%</td><td>{sel_tot_ms_py:.0f}%</td><td>{format_yoy_html(sel_tot_ms_diff, True)}</td>'
                c_html += f'<td>{ke_tot_cy:,.0f}</td><td>{ke_tot_py:,.0f}</td><td>{format_yoy_html(ke_tot_yoy)}</td>'
                c_html += f'<td>{ke_tot_ms_cy:.0f}%</td><td>{ke_tot_ms_py:.0f}%</td><td>{format_yoy_html(ke_tot_ms_diff, True)}</td></tr>'

                c_html += '</tbody></table></div>'
                st.markdown(c_html, unsafe_allow_html=True)

        st.markdown("---")

    with tab6_2:
        st.markdown("*(속도 최적화를 위해 상위 100건만 표출합니다)*")
        st.dataframe(df_6.head(100), width="stretch")

# ==========================================
# GROUP 3: 🔗 W26 연결 네트워크
# ==========================================
else:
    st.markdown('<div class="unified-sub-header">🔗 대한항공 W26 연결 네트워크 외부 연동 시스템</div>', unsafe_allow_html=True)
    st.iframe(EXT_WEB_APP_URL, height=850)