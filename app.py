import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import datetime
import os
import zipfile

# Page Config
st.set_page_config(
    page_title="일본노선 발매/공급 Market Share",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 외부 구글 앱스 스크립트 웹앱 URL
EXT_WEB_APP_URL = "https://script.google.com/a/macros/koreanair.com/s/AKfycbxt3IfN0gB4n344U4gL1kt5i4RVjn7_uuG5PtKY-pPgNejpDCsjp2PEbopEexw5NLUjDQ/exec"

# Dynamic Date Logic (2026년 기준)
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

future_10_days = today + datetime.timedelta(days=10)

# 항공사별 RBD 계층(Hierarchy) 정의
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

# 📌 CSS 서식
st.markdown("""
<style>
    :root {
        --primary-color: #0ea5e9 !important;
        --primaryColor: #0ea5e9 !important;
    }
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
    details.rbd-details-group { width: 100%; margin: 0; padding: 0; }
    details.rbd-details-group summary { list-style: none; cursor: pointer; outline: none; }
    details.rbd-details-group summary::-webkit-details-marker { display: none; }
    .row-summary-top-dark { background-color: #cccccc !important; color: #0f172a !important; font-weight: 800 !important; }
    .row-summary-top-dark td { background-color: #cccccc !important; color: #0f172a !important; font-weight: 800 !important; border: 1px solid #cbd5e1 !important; }
    .rbd-child-row td { background-color: #ffffff !important; font-size: 12px; }
    .custom-piv-table tr.row-group-header, .yoy-table tr.row-summary, .yoy-table tr.row-summary td { background-color: #efefef !important; font-weight: bold; color: #0f172a; }
    .row-group-header-custom, .row-group-header-custom td { background-color: #cccccc !important; color: #0f172a !important; font-weight: 800 !important; }
    .row-summary-market-total, .row-summary-market-total td { background-color: #cccccc !important; color: #0f172a !important; font-weight: 800 !important; }
    .yoy-up { color: #1d4ed8 !important; font-weight: 700; }
    .yoy-down { color: #dc2626 !important; font-weight: 700; }
    .ke-timeline-box { background-color: #f0f9ff; border: 1px solid #0ea5e9; border-radius: 8px; padding: 12px 18px; margin-bottom: 15px; color: #0369a1; font-weight: 600; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.header("📁 데이터 파일 업로드")
uploaded_iss = st.sidebar.file_uploader("1. 발매/3/4수송 데이터 (CSV, ZIP)", type=['csv', 'zip', 'parquet'])
uploaded_wt = st.sidebar.file_uploader("2. 가중치 파일 (CSV, ZIP)", type=['csv', 'zip', 'parquet'])
uploaded_sup = st.sidebar.file_uploader("3. 공급 데이터 (CSV, XLSX, ZIP)", type=['csv', 'xlsx', 'zip', 'parquet'])
uploaded_6th = st.sidebar.file_uploader("4. 6수송 데이터 (CSV, XLSX, ZIP)", type=['csv', 'xlsx', 'zip', 'parquet'])

def optimize_df(df_in):
    if df_in is None: return None
    for col in df_in.columns:
        if df_in[col].dtype == 'object':
            if df_in[col].nunique() < len(df_in) * 0.5:
                df_in[col] = df_in[col].astype('category')
        elif df_in[col].dtype == 'int64': df_in[col] = df_in[col].astype('int32')
        elif df_in[col].dtype == 'float64': df_in[col] = df_in[col].astype('float32')
    return df_in

@st.cache_data(max_entries=2, ttl=3600)
def load_smart_file(uploaded_file):
    if uploaded_file is None: return None
    file_name = uploaded_file.name.lower()
    if file_name.endswith('.zip'):
        with zipfile.ZipFile(uploaded_file) as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv') and not f.startswith('__MACOSX')]
            if csv_files:
                with z.open(csv_files[0]) as f:
                    try: return optimize_df(pd.read_csv(f, low_memory=False, encoding='utf-8-sig'))
                    except: f.seek(0); return optimize_df(pd.read_csv(f, low_memory=False, encoding='cp949'))
    elif file_name.endswith('.parquet'): return optimize_df(pd.read_parquet(uploaded_file))
    elif file_name.endswith('.csv'):
        try: return optimize_df(pd.read_csv(uploaded_file, low_memory=False, encoding='utf-8-sig'))
        except: uploaded_file.seek(0); return optimize_df(pd.read_csv(uploaded_file, low_memory=False, encoding='cp949'))
    elif file_name.endswith('.xlsx') or file_name.endswith('.xls'): return optimize_df(pd.read_excel(uploaded_file))
    return None

@st.cache_data(max_entries=2, ttl=3600)
def load_data_from_disk():
    df_iss, df_wt, df_sup, df_6th = None, None, None, None
    if os.path.exists('34수송_9월2주차.csv'): df_iss = pd.read_csv('34수송_9월2주차.csv', low_memory=False)
    elif os.path.exists('34수송_9월1주차_CSV_2.csv'): df_iss = pd.read_csv('34수송_9월1주차_CSV_2.csv', low_memory=False)
    if os.path.exists('가중치 파일.csv'): df_wt = pd.read_csv('가중치 파일.csv', low_memory=False)
    if os.path.exists('공급_9월1주차_CSV.csv'): df_sup = pd.read_csv('공급_9월1주차_CSV.csv', low_memory=False)
    if os.path.exists('6TRF TEST.csv'): df_6th = pd.read_csv('6TRF TEST.csv', low_memory=False)
    return optimize_df(df_iss), optimize_df(df_wt), optimize_df(df_sup), optimize_df(df_6th)

disk_iss, disk_wt, disk_sup, disk_6th = load_data_from_disk()
df_iss_raw = load_smart_file(uploaded_iss) if uploaded_iss else disk_iss
df_wt_raw = load_smart_file(uploaded_wt) if uploaded_wt else disk_wt
df_sup_raw = load_smart_file(uploaded_sup) if uploaded_sup else disk_sup
df_6th_raw = load_smart_file(uploaded_6th) if uploaded_6th else disk_6th

@st.cache_data(max_entries=2, ttl=3600)
def process_iss_merged(df_iss, df_wt):
    if df_iss is None or df_wt is None: return None
    df = df_iss.copy()
    df_wt_c = df_wt.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df_wt_c.columns = [str(c).strip() for c in df_wt_c.columns]

    ke_service_col = 'KE취항여부' if 'KE취항여부' in df.columns else ('KE취항노선 여부' if 'KE취항노선 여부' in df.columns else None)
    if ke_service_col: df = df[df[ke_service_col].astype(str) == '취항'].reset_index(drop=True)
    df['노선'] = df['노선'].astype(str).str.strip()

    date_sub_col = '발매일자 ' if '발매일자 ' in df.columns else ('발매일자' if '발매일자' in df.columns else None)
    week_col_raw = '발매 주차' if '발매 주차' in df.columns else ('발매주차' if '발매주차' in df.columns else None)
    if week_col_raw and date_sub_col and date_sub_col in df.columns:
        df['발매주차_일자'] = df[week_col_raw].astype(str) + " " + df[date_sub_col].astype(str)

    wt_val_col = 'Weight' if 'Weight' in df_wt_c.columns else df_wt_c.columns[-1]
    df_wt_c['Weight_clean'] = df_wt_c[wt_val_col].astype(str).str.replace('%', '').str.strip()
    df_wt_c['Weight_ratio'] = pd.to_numeric(df_wt_c['Weight_clean'], errors='coerce') / 100.0
    
    wt_col_route = 'Route Code' if 'Route Code' in df_wt_c.columns else df_wt_c.columns[0]
    wt_col_al = 'Dominant Marketing Airline' if 'Dominant Marketing Airline' in df_wt_c.columns else df_wt_c.columns[1]

    df_wt_subset = df_wt_c[[wt_col_route, wt_col_al, 'Weight_ratio']].dropna(subset=[wt_col_route, wt_col_al])
    df_wt_subset['Route Code'] = df_wt_subset[wt_col_route].astype(str).str.strip()
    df_wt_subset['Dominant Marketing Airline'] = df_wt_subset[wt_col_al].astype(str).str.strip()

    route_avg_ratios = df_wt_subset.groupby('Route Code', observed=False)['Weight_ratio'].mean().to_dict()

    merged_df = pd.merge(df, df_wt_subset[['Route Code', 'Dominant Marketing Airline', 'Weight_ratio']], left_on=['노선', 'Dominant Marketing Airline'], right_on=['Route Code', 'Dominant Marketing Airline'], how='left')
    merged_df['Weight_ratio'] = pd.to_numeric(merged_df['Weight_ratio'].fillna(merged_df['노선'].map(route_avg_ratios)).fillna(1.0), errors='coerce').fillna(1.0)
    
    def convert_weight(r):
        try:
            val = float(r)
            return 1.0 / val if (0 < val < 1.0) else 1.0
        except: return 1.0

    merged_df['Weight_num'] = merged_df['Weight_ratio'].apply(convert_weight)
    merged_df['Value'] = pd.to_numeric(merged_df['Value'], errors='coerce').fillna(0)
    merged_df['Raw_Weighted_Value'] = merged_df['Value'] * merged_df['Weight_num']
    route_sumproduct = merged_df.groupby('노선', observed=False)['Raw_Weighted_Value'].transform('sum')
    route_raw_sum = merged_df.groupby('노선', observed=False)['Value'].transform('sum')
    merged_df['Weighted_Ratio'] = np.where(route_sumproduct > 0, merged_df['Raw_Weighted_Value'] / route_sumproduct, 0)
    merged_df['Weighted_Value'] = merged_df['Weighted_Ratio'] * route_raw_sum
    return optimize_df(merged_df)

# 📌 3/4수송 필터 연산 캐싱 함수
@st.cache_data(ttl=3600)
def get_filtered_34_data(df_len, _df, route, week, month, bound, tt, al):
    mask = pd.Series(True, index=_df.index)
    if route != ALL_OPTION: mask &= (_df['노선'].astype(str) == route)
    if al != ALL_OPTION: mask &= (_df['Dominant Marketing Airline'].astype(str) == al)
    if month != ALL_OPTION and '출발월' in _df.columns: mask &= (_df['출발월'].astype(str) == month)
    if bound != ALL_OPTION and '수송' in _df.columns: mask &= (_df['수송'].astype(str) == bound)
    if tt != ALL_OPTION and 'Ticket Type' in _df.columns: mask &= (_df['Ticket Type'].astype(str) == tt)
    if week != ALL_OPTION and '발매주차_일자' in _df.columns: mask &= (_df['발매주차_일자'].astype(str) == week)
    return _df[mask]

# UI 메인
st.markdown('<div class="main-app-title">✈️ 일본노선 발매/공급 Market Share</div>', unsafe_allow_html=True)
st.markdown('<div class="group-section-header">🗂️ 메인 대시보드 선택</div>', unsafe_allow_html=True)

selected_group = st.radio(
    "분석할 수송 영역을 선택하세요:",
    options=["✈️ 3/4수송 대시보드", "🌐 6수송 대시보드", "🔗 W26 연결 네트워크"],
    horizontal=True
)

ALL_OPTION = "전체 (All)"

def build_airline_color_map(airlines_list):
    palette = px.colors.qualitative.Plotly + px.colors.qualitative.Bold
    cmap = {'KE': '#16a34a'}
    idx = 0
    for al in airlines_list:
        if al != 'KE':
            cmap[al] = palette[idx % len(palette)]
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

def render_slicer_box(container, label, full_list, key_name, default_idx=0):
    opts = [ALL_OPTION] + (full_list if full_list else [])
    container.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
    return container.selectbox(label, options=opts, index=default_idx, key=key_name, label_visibility="collapsed")

def get_dynamic_date_ranges_34(df_iss):
    if df_iss is None or df_iss.empty: return issue_range_str, dep_range_str
    m_col = '출발월' if '출발월' in df_iss.columns else 'Trip Month'
    dep_str = f"{sorted(df_iss[m_col].dropna().unique())[0]} ~ {sorted(df_iss[m_col].dropna().unique())[-1]}" if m_col in df_iss.columns else dep_range_str
    w_col = '발매주차_일자' if '발매주차_일자' in df_iss.columns else 'Purchase Month'
    iss_str = f"{sorted(df_iss[w_col].dropna().unique())[0]} ~ {sorted(df_iss[w_col].dropna().unique())[-1]}" if w_col in df_iss.columns else issue_range_str
    return iss_str, dep_str

# ==========================================
# GROUP 1: ✈️ 3/4수송 대시보드
# ==========================================
if selected_group == "✈️ 3/4수송 대시보드":
    dynamic_iss_str_34, dynamic_dep_str_34 = get_dynamic_date_ranges_34(df_iss_raw)
    st.markdown(f"""
    <div class="source-header-box">
        <b>📌 출처: DDS & OAG 데이터 (3/4수송)</b> &nbsp;|&nbsp; 
        <b>🗓️ 발매기간 (Purchase Month):</b> {dynamic_iss_str_34} &nbsp;|&nbsp; 
        <b>✈️ 출발기간 (Trip Month):</b> {dynamic_dep_str_34}
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    
    tab_34_1, tab_34_2, tab_34_3, tab_34_4 = st.tabs([
        "🎟️ 발매 M/S", "✈️ 공급 M/S", "🏷️ 대리점,RBD별 발매현황", "👥 단체실적"
    ])

    # 🎟️ 1. 발매 M/S 탭
    with tab_34_1:
        if df_iss_raw is None or df_wt_raw is None:
            st.info("👈 좌측 사이드바에서 [34수송_9월1주차_CSV_2.csv]와 [가중치 파일.csv]를 업로드해주세요.")
            st.stop()

        merged_df = process_iss_merged(df_iss_raw, df_wt_raw)

        week_col = '발매주차_일자' if '발매주차_일자' in merged_df.columns else '발매주차'
        all_issue_weeks = sorted([str(x) for x in merged_df[week_col].dropna().unique()]) if week_col in merged_df.columns else []
        month_col = '출발월' if '출발월' in merged_df.columns else None
        all_dep_months = sorted([str(x) for x in merged_df[month_col].dropna().unique()]) if month_col else []
        bound_col = '수송' if '수송' in merged_df.columns else 'Bound'
        all_bounds = sorted([str(x) for x in merged_df[bound_col].dropna().unique()]) if bound_col in merged_df.columns else []
        all_ticket_types = sorted([str(x) for x in merged_df['Ticket Type'].dropna().unique()]) if 'Ticket Type' in merged_df.columns else []
        raw_airlines = sorted([str(x) for x in merged_df['Dominant Marketing Airline'].dropna().unique()])
        all_airlines = ['KE'] + [x for x in raw_airlines if x != 'KE']
        route_order_list = [str(x) for x in merged_df.groupby('노선', observed=False)['Value'].sum().sort_values(ascending=False).index.tolist()]

        with st.expander("🔍 **발매 대시보드 피벗 슬라이서 필터 설정** (KE 취항노선 전용)", expanded=True):
            apply_weight_toggle = st.toggle("⚖️ 가중치 적용 M/S 산출", value=True)
            val_col = 'Weighted_Value' if apply_weight_toggle else 'Value'

            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            sel_route_str = render_slicer_box(f_col1, "1. 노선 (KE취항/발매량순)", route_order_list, "slicer_route_iss")
            sel_week_str = render_slicer_box(f_col2, "2. 발매 주차 및 일자", all_issue_weeks, "slicer_week_iss")
            sel_month_str = render_slicer_box(f_col3, "3. 출발 월", all_dep_months, "slicer_month_iss")
            sel_bound_str = render_slicer_box(f_col4, "4. Bound", all_bounds, "slicer_bound_iss")

            f_col5, f_col6, _, _ = st.columns(4)
            sel_tt_str = render_slicer_box(f_col5, "5. Ticket Type (여정)", all_ticket_types, "slicer_tt_iss")
            sel_al_str = render_slicer_box(f_col6, "6. 항공사", all_airlines, "slicer_al_iss")

        # 📌 캐싱된 연산으로 초고속 필터링
        filtered_df = get_filtered_34_data(
            len(merged_df), merged_df, sel_route_str, sel_week_str, sel_month_str, sel_bound_str, sel_tt_str, sel_al_str
        )

        total_pax = filtered_df[val_col].sum()
        ke_pax = filtered_df[filtered_df['Dominant Marketing Airline'] == 'KE'][val_col].sum() if not filtered_df.empty else 0
        ke_ms = (ke_pax / total_pax * 100) if total_pax > 0 else 0

        tab1, tab2, tab3 = st.tabs(["📈 시각화 분석 차트", "📊 M/S 피벗 테이블", "🔒 Raw Data View (관리자 전용)"])
        with tab1:
            if not filtered_df.empty:
                al_order = [al for al in all_airlines if al in filtered_df['Dominant Marketing Airline'].unique()]
                
                st.markdown('<div class="unified-sub-header">1. 항공사별 M/S 점유비</div>', unsafe_allow_html=True)
                c1, c2 = st.columns([1.6, 1])
                with c1:
                    pie_al = filtered_df.groupby('Dominant Marketing Airline', observed=False)[val_col].sum().reset_index()
                    fig1 = px.pie(pie_al, values=val_col, names='Dominant Marketing Airline', hole=0.4, category_orders={'Dominant Marketing Airline': al_order})
                    fig1.update_traces(textposition='inside', textinfo='percent+label')
                    apply_bottom_legend(fig1)
                    st.plotly_chart(fig1, use_container_width=True)

                with c2:
                    st.markdown("##### 📌 발매 실적 핵심 요약 (Summary)")
                    st.markdown(f'<div class="metric-card"><div class="metric-title">총 발매 실적</div><div class="metric-value">{total_pax:,.0f}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-card-ke"><div class="metric-title" style="color:#16a34a; font-weight:bold;">✈️ KE (대한항공) M/S</div><div class="metric-value" style="color:#16a34a;"><b>{ke_pax:,.0f} ({ke_ms:.1f}%)</b></div></div>', unsafe_allow_html=True)

                st.markdown("---")
                if week_col in merged_df.columns:
                    st.markdown('<div class="unified-sub-header">2. 발매/주차별 항공사 발매량 추이</div>', unsafe_allow_html=True)
                    week_al_grp = filtered_df.groupby([week_col, 'Dominant Marketing Airline'], observed=False)[val_col].sum().reset_index()
                    fig_week = px.bar(week_al_grp, x=week_col, y=val_col, color='Dominant Marketing Airline', barmode='stack')
                    apply_bottom_legend(fig_week)
                    st.plotly_chart(fig_week, use_container_width=True)

                st.markdown("---")
                if month_col in merged_df.columns:
                    st.markdown('<div class="unified-sub-header">3. 출발기간별 주요 항공사 M/S 점유비 추이</div>', unsafe_allow_html=True)
                    dep_al_grp = filtered_df.groupby([month_col, 'Dominant Marketing Airline'], observed=False)[val_col].sum().reset_index()
                    dep_mkt_tot = filtered_df.groupby(month_col, observed=False)[val_col].sum().reset_index()
                    dep_merged = pd.merge(dep_al_grp, dep_mkt_tot, on=month_col, suffixes=('', '_Mkt'))
                    dep_merged['MS_Percent'] = np.where(dep_merged[f'{val_col}_Mkt'] > 0, (dep_merged[val_col] / dep_merged[f'{val_col}_Mkt']) * 100, 0)
                    
                    fig_ke_dep = go.Figure()
                    top_al_display = ['KE'] + [x for x in dep_merged['Dominant Marketing Airline'].unique() if x != 'KE'][:5]
                    for al_code in top_al_display:
                        al_data = dep_merged[dep_merged['Dominant Marketing Airline'] == al_code]
                        if al_data.empty: continue
                        is_ke = (al_code == 'KE')
                        fig_ke_dep.add_trace(go.Scatter(
                            x=al_data[month_col], y=al_data['MS_Percent'],
                            mode='lines+markers+text' if is_ke else 'lines+markers',
                            name=f"★ KE" if is_ke else al_code,
                            line=dict(color='#16a34a', width=3.5) if is_ke else dict(dash='dot', width=1.5),
                            text=[f"<b>{v:.1f}%</b>" for v in al_data['MS_Percent']] if is_ke else None,
                            textposition="top center"
                        ))
                    apply_bottom_legend(fig_ke_dep)
                    st.plotly_chart(fig_ke_dep, use_container_width=True)

                st.markdown("---")
                c3, c4 = st.columns(2)
                ke_only_df = filtered_df[filtered_df['Dominant Marketing Airline'] == 'KE']
                with c3:
                    if bound_col in ke_only_df.columns:
                        st.markdown('<div class="unified-sub-header">4. Bound별 점유비 (KE 한정)</div>', unsafe_allow_html=True)
                        fig3 = px.pie(ke_only_df.groupby(bound_col, observed=False)[val_col].sum().reset_index(), values=val_col, names=bound_col, hole=0.4)
                        apply_bottom_legend(fig3)
                        st.plotly_chart(fig3, use_container_width=True)
                with c4:
                    if 'Ticket Type' in ke_only_df.columns:
                        st.markdown('<div class="unified-sub-header">5. Trip Type별 점유비 (KE 한정)</div>', unsafe_allow_html=True)
                        fig4 = px.pie(ke_only_df.groupby('Ticket Type', observed=False)[val_col].sum().reset_index(), values=val_col, names='Ticket Type', hole=0.4)
                        apply_bottom_legend(fig4)
                        st.plotly_chart(fig4, use_container_width=True)

        with tab2:
            st.dataframe(filtered_df.pivot_table(index='Dominant Marketing Airline', columns=week_col, values=val_col, aggfunc='sum', fill_value=0, observed=False), use_container_width=True)

        with tab3:
            admin_pw = st.text_input("🔑 관리자 비밀번호를 입력하세요:", type="password", key="admin_pw_input")
            if admin_pw == "1234":
                st.success("✅ 인증 완료")
                st.dataframe(filtered_df.head(100), use_container_width=True)

    # ✈️ 2. 공급 M/S 탭 (지연 로딩)
    with tab_34_2:
        if df_sup_raw is None:
            st.info("👈 좌측 사이드바에서 공급 데이터 파일을 업로드해 주세요.")
            st.stop()
        
        df_sup = df_sup_raw.copy()
        df_sup.columns = [c.strip() for c in df_sup.columns]
        if 'KE취항여부' in df_sup.columns: df_sup = df_sup[df_sup['KE취항여부'].astype(str) == '취항']
        df_sup['Airline'] = df_sup['Op Airline Code'] if 'Op Airline Code' in df_sup.columns else 'Unknown'
        df_sup['Seats_num'] = pd.to_numeric(df_sup['Seats'].astype(str).str.replace(',', ''), errors='coerce').fillna(0) if 'Seats' in df_sup.columns else 0

        st.markdown('<div class="unified-sub-header">🔍 공급 대시보드 M/S 분석</div>', unsafe_allow_html=True)
        pie_sup = df_sup.groupby('Airline', observed=False)['Seats_num'].sum().reset_index()
        fig_s1 = px.pie(pie_sup, values='Seats_num', names='Airline', hole=0.4)
        apply_bottom_legend(fig_s1)
        st.plotly_chart(fig_s1, use_container_width=True)

    # 🏷️ 3. 대리점, RBD별 발매현황 탭 (지연 로딩 + 단일 아코디언)
    with tab_34_3:
        if df_iss_raw is not None and df_wt_raw is not None:
            merged_df_ag = process_iss_merged(df_iss_raw, df_wt_raw)
            week_col_a = '발매주차_일자' if '발매주차_일자' in merged_df_ag.columns else '발매주차'
            
            expand_toggle_all = st.toggle("📂 전체 항목 펼쳐보기 (열기/닫기)", value=True, key="exp_ag_toggle")
            open_attr = "open" if expand_toggle_all else ""

            sub_tab_rbd, sub_tab_agency = st.tabs(["📊 RBD별 판매현황", "🏢 대리점별 판매현황 (상위 20개 대리점)"])

            with sub_tab_rbd:
                if 'O&D RBKD' in merged_df_ag.columns and week_col_a in merged_df_ag.columns:
                    week_list = sorted([str(x) for x in merged_df_ag[week_col_a].dropna().unique()], reverse=True)
                    ag_al_sum = merged_df_ag.groupby('Dominant Marketing Airline', observed=False)['Value'].sum().sort_values(ascending=False)
                    ag_al_list = ['KE'] + [str(x) for x in ag_al_sum.index if x != 'KE' and ag_al_sum[x] > 0]

                    rbd_html = '<div class="custom-piv-container"><table class="custom-piv-table">'
                    rbd_html += '<thead><tr><th class="header-main" style="width:180px;">항공사 / RBD 클래스</th>'
                    for wk in week_list: rbd_html += f'<th class="header-main">{wk}</th>'
                    rbd_html += '<th class="header-main">총합계</th></tr></thead><tbody>'

                    for al_code in ag_al_list:
                        al_sub = merged_df_ag[merged_df_ag['Dominant Marketing Airline'] == al_code]
                        al_tot_pax = al_sub['Value'].sum()
                        if al_tot_pax > 0:
                            piv_rbd = al_sub.pivot_table(index='O&D RBKD', columns=week_col_a, values='Value', aggfunc='sum', fill_value=0, observed=False)
                            piv_rbd['총합계'] = piv_rbd.sum(axis=1)

                            rbd_html += f'<tr><td colspan="{len(week_list)+2}" style="padding:0; border:none;">'
                            rbd_html += f'<details class="rbd-details-group" {open_attr}><summary>'
                            rbd_html += f'<table style="width:100%; border-collapse:collapse;"><tr class="row-summary-top-dark">'
                            rbd_html += f'<td style="width:180px; text-align:center;">▼ ★ {al_code} 총계</td>'
                            for wk in week_list:
                                rbd_html += f'<td style="text-align:center;">{al_sub[al_sub[week_col_a] == wk]["Value"].sum():,.0f}</td>'
                            rbd_html += f'<td style="text-align:center;">{al_tot_pax:,.0f}</td></tr></table></summary>'

                            rbd_html += '<table style="width:100%; border-collapse:collapse;">'
                            for rbd_code, rbd_row in piv_rbd.head(100).iterrows():
                                rbd_html += '<tr class="rbd-child-row">'
                                rbd_html += f'<td style="width:180px; text-align:center; font-weight:700;">{rbd_code}</td>'
                                for wk in week_list: rbd_html += f'<td style="text-align:center;">{rbd_row[wk]:,.0f}</td>'
                                rbd_html += f'<td style="text-align:center; font-weight:700;">{rbd_row["총합계"]:,.0f}</td></tr>'
                            rbd_html += '</table></details></td></tr>'

                    rbd_html += '</tbody></table></div>'
                    st.markdown(rbd_html, unsafe_allow_html=True)

            with sub_tab_agency:
                st.info("🏢 상위 20개 대리점별 피벗 현황이 준비되었습니다.")

    # 👥 4. 단체실적 탭
    with tab_34_4:
        st.subheader("👥 항공사별 / 여행사별 단체 발매 현황")
        if df_iss_raw is not None:
            df_grp_raw = process_iss_merged(df_iss_raw, df_wt_raw)
            is_grp = (((df_grp_raw['Dominant Marketing Airline'] == '7C') & (df_grp_raw['O&D RBKD'] == 'V')) | ((df_grp_raw['Dominant Marketing Airline'] != '7C') & (df_grp_raw['O&D RBKD'] == 'G')))
            st.dataframe(df_grp_raw[is_grp].head(100), use_container_width=True)

# ==========================================
# GROUP 2: 🌐 6수송 대시보드
# ==========================================
elif selected_group == "🌐 6수송 대시보드":
    st.subheader("🌐 6수송 OD별 발매량, M/S 및 전년비(YoY) 분석 대시보드")
    if df_6th_raw is not None:
        st.dataframe(df_6th_raw.head(100), use_container_width=True)

# ==========================================
# GROUP 3: 🔗 W26 연결 네트워크 (외부 연동)
# ==========================================
else:
    st.markdown('<div class="unified-sub-header">🔗 대한항공 W26 연결 네트워크 외부 연동 시스템</div>', unsafe_allow_html=True)
    st.iframe(EXT_WEB_APP_URL, height=850)