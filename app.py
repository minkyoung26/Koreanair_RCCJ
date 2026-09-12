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

# 📌 고급 CSS 서식
st.markdown("""
<style>
    :root {
        --primary-color: #0ea5e9 !important;
        --primaryColor: #0ea5e9 !important;
    }

    /* 메인 타이틀 크기 축소 */
    .main-app-title {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #0f172a;
        margin-bottom: 12px;
    }

    /* 모든 서브 섹션 제목 폰트 크기 일관 통일 (16px) */
    .unified-sub-header {
        font-size: 16px !important;
        font-weight: 700 !important;
        color: #0f172a;
        margin-top: 10px;
        margin-bottom: 10px;
    }

    div[role="radiogroup"] label div[role="radio"][aria-checked="true"] {
        background-color: #0ea5e9 !important;
        border-color: #0ea5e9 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #0ea5e9 !important;
        border-bottom-color: #0ea5e9 !important;
    }
    div[data-testid="stToggle"] input:checked + div {
        background-color: #0ea5e9 !important;
    }

    .source-header-box {
        background-color: #f0f9ff;
        border-left: 5px solid #0284c7;
        padding: 12px 18px;
        border-radius: 6px;
        margin-bottom: 15px;
        font-size: 14px;
        color: #0f172a;
        font-weight: 500;
    }
    .group-section-header {
        font-size: 17px !important;
        font-weight: 700 !important;
        color: #0f172a;
        padding-bottom: 8px;
        border-bottom: 2px solid #cbd5e1;
        margin-top: 10px;
        margin-bottom: 12px;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        margin-bottom: 10px;
    }
    .metric-card-ke {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        margin-bottom: 10px;
    }
    .metric-title {
        font-size: 13px;
        color: #64748b;
        margin-bottom: 4px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 22px;
        color: #1e293b;
        font-weight: 700;
    }

    /* 📌 [표 서식 통일] 둥근 모서리, 회색 테두리(#cbd5e1) */
    .custom-piv-container, .yoy-table-container {
        width: 100%;
        overflow-x: auto;
        margin-bottom: 20px;
        border-radius: 8px;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
    }
    .custom-piv-table, .yoy-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12.5px;
        background-color: #ffffff;
        text-align: center !important;
    }
    
    /* 📌 [컬럼 헤더 기본 색상] #cfe2f3 적용 */
    .custom-piv-table th.header-main, .yoy-table th, .yoy-table th.mkt-header, .yoy-table th.carrier-header {
        background-color: #cfe2f3 !important;
        color: #0f172a !important;
        padding: 8px 6px;
        border: 1px solid #cbd5e1 !important;
        font-weight: 700;
        text-align: center !important;
        white-space: nowrap;
    }

    /* 📌 KE 컬럼 제목(헤더) 파스텔 초록색 지정 */
    .yoy-table th.ke-header {
        background-color: #dcfce7 !important;
        color: #15803d !important;
        padding: 8px 6px;
        border: 1px solid #cbd5e1 !important;
        font-size: 13px !important;
        font-weight: 800 !important;
        text-align: center !important;
        white-space: nowrap;
    }

    /* 📌 모든 데이터 셀 배경색 흰색(#ffffff) 통일 */
    .custom-piv-table td, .yoy-table td, .yoy-table td.ke-cell, .yoy-table tr.ke-row td.ke-cell {
        padding: 6px 10px;
        border: 1px solid #cbd5e1 !important;
        color: #334155 !important;
        background-color: #ffffff !important;
        text-align: center !important;
    }
    
    .yoy-table tr:hover {
        background-color: #f8fafc !important;
    }
    .yoy-table tr.row-title {
        background-color: #f8fafc !important;
        font-weight: bold;
        color: #0f172a;
    }
    
    /* 📌 RBD/대리점 통합 표 아코디언 전용 커스텀 스타일 */
    details.rbd-details-group {
        width: 100%;
        margin: 0;
        padding: 0;
    }
    details.rbd-details-group summary {
        list-style: none;
        cursor: pointer;
        outline: none;
    }
    details.rbd-details-group summary::-webkit-details-marker {
        display: none;
    }
    
    /* 📌 총계 배경색 #cccccc 적용 */
    .row-summary-top-dark {
        background-color: #cccccc !important;
        color: #0f172a !important;
        font-weight: 800 !important;
    }
    .row-summary-top-dark td {
        background-color: #cccccc !important;
        color: #0f172a !important;
        font-weight: 800 !important;
        border: 1px solid #cbd5e1 !important;
    }
    .rbd-child-row td {
        background-color: #ffffff !important;
        font-size: 12px;
    }

    /* 📌 [소계 배경] #efefef */
    .custom-piv-table tr.row-group-header, .yoy-table tr.row-summary, .yoy-table tr.row-summary td {
        background-color: #efefef !important;
        font-weight: bold;
        color: #0f172a;
    }

    /* 📌 단체실적 총계 행 배경색 #cccccc */
    .row-group-header-custom, .row-group-header-custom td {
        background-color: #cccccc !important;
        color: #0f172a !important;
        font-weight: 800 !important;
    }

    /* 📌 [전체 시장 총합 배경] #cccccc */
    .row-summary-market-total, .row-summary-market-total td {
        background-color: #cccccc !important;
        color: #0f172a !important;
        font-weight: 800 !important;
    }
    
    .yoy-up { color: #1d4ed8 !important; font-weight: 700; }
    .yoy-down { color: #dc2626 !important; font-weight: 700; }

    .ke-timeline-box {
        background-color: #f0f9ff;
        border: 1px solid #0ea5e9;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 15px;
        color: #0369a1;
        font-weight: 600;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar File Uploader Section
st.sidebar.header("📁 데이터 파일 업로드")

uploaded_iss = st.sidebar.file_uploader("1. 발매/3/4수송 데이터 (CSV, ZIP)", type=['csv', 'zip', 'parquet'])
uploaded_wt = st.sidebar.file_uploader("2. 가중치 파일 (CSV, ZIP)", type=['csv', 'zip', 'parquet'])
uploaded_sup = st.sidebar.file_uploader("3. 공급 데이터 (CSV, XLSX, ZIP)", type=['csv', 'xlsx', 'zip', 'parquet'])
uploaded_6th = st.sidebar.file_uploader("4. 6수송 데이터 (CSV, XLSX, ZIP)", type=['csv', 'xlsx', 'zip', 'parquet'])

def optimize_df(df_in):
    if df_in is None:
        return None
    for col in df_in.columns:
        if df_in[col].dtype == 'object':
            num_unique = df_in[col].nunique()
            if num_unique < len(df_in) * 0.5:
                df_in[col] = df_in[col].astype('category')
        elif df_in[col].dtype == 'int64':
            df_in[col] = df_in[col].astype('int32')
        elif df_in[col].dtype == 'float64':
            df_in[col] = df_in[col].astype('float32')
    return df_in

@st.cache_data(max_entries=2, ttl=3600)
def load_smart_file(uploaded_file):
    if uploaded_file is None:
        return None
    file_name = uploaded_file.name.lower()
    
    if file_name.endswith('.zip'):
        with zipfile.ZipFile(uploaded_file) as z:
            csv_files = [f for f in z.namelist() if f.endswith('.csv') and not f.startswith('__MACOSX')]
            if csv_files:
                with z.open(csv_files[0]) as f:
                    try:
                        return optimize_df(pd.read_csv(f, low_memory=False, encoding='utf-8-sig'))
                    except:
                        f.seek(0)
                        return optimize_df(pd.read_csv(f, low_memory=False, encoding='cp949'))
    elif file_name.endswith('.parquet'):
        return optimize_df(pd.read_parquet(uploaded_file))
    elif file_name.endswith('.csv'):
        try:
            return optimize_df(pd.read_csv(uploaded_file, low_memory=False, encoding='utf-8-sig'))
        except:
            uploaded_file.seek(0)
            return optimize_df(pd.read_csv(uploaded_file, low_memory=False, encoding='cp949'))
    elif file_name.endswith('.xlsx') or file_name.endswith('.xls'):
        return optimize_df(pd.read_excel(uploaded_file))
    return None

@st.cache_data(max_entries=2, ttl=3600)
def load_data_from_disk():
    df_iss, df_wt, df_sup, df_6th = None, None, None, None
    if os.path.exists('34수송_9월2주차.csv'):
        df_iss = pd.read_csv('34수송_9월2주차.csv', low_memory=False)
    elif os.path.exists('34수송_9월1주차_CSV_2.csv'):
        df_iss = pd.read_csv('34수송_9월1주차_CSV_2.csv', low_memory=False)
        
    if os.path.exists('가중치 파일.csv'):
        df_wt = pd.read_csv('가중치 파일.csv', low_memory=False)
        
    if os.path.exists('공급_9월1주차_CSV.csv'):
        df_sup = pd.read_csv('공급_9월1주차_CSV.csv', low_memory=False)
        
    if os.path.exists('6TRF TEST.csv'):
        df_6th = pd.read_csv('6TRF TEST.csv', low_memory=False)
        
    return optimize_df(df_iss), optimize_df(df_wt), optimize_df(df_sup), optimize_df(df_6th)

disk_iss, disk_wt, disk_sup, disk_6th = load_data_from_disk()

df_iss_raw = load_smart_file(uploaded_iss) if uploaded_iss else disk_iss
df_wt_raw = load_smart_file(uploaded_wt) if uploaded_wt else disk_wt
df_sup_raw = load_smart_file(uploaded_sup) if uploaded_sup else disk_sup
df_6th_raw = load_smart_file(uploaded_6th) if uploaded_6th else disk_6th

@st.cache_data(max_entries=2, ttl=3600)
def process_iss_merged(df_iss, df_wt):
    if df_iss is None or df_wt is None:
        return None
    df = df_iss.copy()
    df_wt_c = df_wt.copy()

    df.columns = [str(c).strip() for c in df.columns]
    df_wt_c.columns = [str(c).strip() for c in df_wt_c.columns]

    ke_service_col = 'KE취항여부' if 'KE취항여부' in df.columns else ('KE취항노선 여부' if 'KE취항노선 여부' in df.columns else None)
    if ke_service_col:
        df = df[df[ke_service_col].astype(str) == '취항'].reset_index(drop=True)

    df['노선'] = df['노선'].astype(str).str.strip()

    date_sub_col = '발매일자 ' if '발매일자 ' in df.columns else ('발매일자' if '발매일자' in df.columns else None)
    week_col_raw = '발매 주차' if '발매 주차' in df.columns else ('발매주차' if '발매주차' in df.columns else None)

    if week_col_raw and date_sub_col and date_sub_col in df.columns:
        df['발매주차_일자'] = df[week_col_raw].astype(str) + " " + df[date_sub_col].astype(str)

    wt_val_col = None
    for target in ['Weight', 'weight', '가중치', 'WEIGHT']:
        if target in df_wt_c.columns:
            wt_val_col = target
            break
    if not wt_val_col:
        wt_val_col = df_wt_c.columns[-1]

    df_wt_c['Weight_clean'] = df_wt_c[wt_val_col].astype(str).str.replace('%', '').str.strip()
    df_wt_c['Weight_ratio'] = pd.to_numeric(df_wt_c['Weight_clean'], errors='coerce') / 100.0
    
    wt_col_route = 'Route Code' if 'Route Code' in df_wt_c.columns else ('노선' if '노선' in df_wt_c.columns else df_wt_c.columns[0])
    wt_col_al = 'Dominant Marketing Airline' if 'Dominant Marketing Airline' in df_wt_c.columns else ('항공사' if '항공사' in df_wt_c.columns else (df_wt_c.columns[1] if len(df_wt_c.columns) > 1 else df_wt_c.columns[0]))

    df_wt_subset = df_wt_c[[wt_col_route, wt_col_al, 'Weight_ratio']].dropna(subset=[wt_col_route, wt_col_al])
    df_wt_subset['Route Code'] = df_wt_subset[wt_col_route].astype(str).str.strip()
    df_wt_subset['Dominant Marketing Airline'] = df_wt_subset[wt_col_al].astype(str).str.strip()

    route_avg_ratios = df_wt_subset.groupby('Route Code', observed=False)['Weight_ratio'].mean().to_dict()

    merged_df = pd.merge(
        df, df_wt_subset[['Route Code', 'Dominant Marketing Airline', 'Weight_ratio']],
        left_on=['노선', 'Dominant Marketing Airline'],
        right_on=['Route Code', 'Dominant Marketing Airline'],
        how='left'
    )

    merged_df['Weight_ratio'] = pd.to_numeric(merged_df['Weight_ratio'].fillna(merged_df['노선'].map(route_avg_ratios)).fillna(1.0), errors='coerce').fillna(1.0)
    
    def convert_to_reciprocal_weight(ratio):
        try:
            r_val = float(ratio)
            if pd.isna(r_val) or r_val <= 0 or r_val >= 1.0:
                return 1.0
            return 1.0 / r_val
        except:
            return 1.0

    merged_df['Weight_num'] = merged_df['Weight_ratio'].apply(convert_to_reciprocal_weight)
    merged_df['Value'] = pd.to_numeric(merged_df['Value'], errors='coerce').fillna(0)

    merged_df['Raw_Weighted_Value'] = merged_df['Value'] * merged_df['Weight_num']
    route_sumproduct = merged_df.groupby('노선', observed=False)['Raw_Weighted_Value'].transform('sum')
    route_raw_sum = merged_df.groupby('노선', observed=False)['Value'].transform('sum')

    merged_df['Weighted_Ratio'] = np.where(route_sumproduct > 0, merged_df['Raw_Weighted_Value'] / route_sumproduct, 0)
    merged_df['Weighted_Value'] = merged_df['Weighted_Ratio'] * route_raw_sum

    return optimize_df(merged_df)

# 메인 타이틀
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
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            title=dict(text="")
        ),
        margin=dict(b=80)
    )
    return fig

def format_dep_time(dep_val):
    try:
        val_str = str(int(dep_val)).zfill(4)
        hh = int(val_str[:2])
        mm = int(val_str[2:])
        if hh >= 24: hh = 23
        if mm >= 60: mm = 59
        return f"2026-08-01 {hh:02d}:{mm:02d}:00", f"2026-08-01 {(hh+2)%24:02d}:{mm:02d}:00"
    except:
        return "2026-08-01 09:00:00", "2026-08-01 11:00:00"

def render_slicer_box(container, label, full_list, key_name, default_idx=0):
    opts = [ALL_OPTION] + (full_list if full_list else [])
    container.markdown(f"<b>{label}</b>", unsafe_allow_html=True)
    selected = container.selectbox(label, options=opts, index=default_idx, key=key_name, label_visibility="collapsed")
    return selected

def get_dynamic_date_ranges_34(df_iss):
    if df_iss is None or df_iss.empty:
        return issue_range_str, dep_range_str

    m_col = '출발월' if '출발월' in df_iss.columns else ('출발 월' if '출발 월' in df_iss.columns else ('Trip Month' if 'Trip Month' in df_iss.columns else None))
    if m_col and m_col in df_iss.columns:
        valid_months = sorted([str(x).strip() for x in df_iss[m_col].dropna().unique() if str(x).strip() != 'nan'])
        dep_str = f"{valid_months[0]} ~ {valid_months[-1]}" if valid_months else dep_range_str
    else:
        dep_str = dep_range_str

    w_col = '발매주차_일자' if '발매주차_일자' in df_iss.columns else ('발매 주차' if '발매 주차' in df_iss.columns else ('Purchase Month' if 'Purchase Month' in df_iss.columns else None))
    if w_col and w_col in df_iss.columns:
        valid_weeks = sorted([str(x).strip() for x in df_iss[w_col].dropna().unique() if str(x).strip() != 'nan'])
        iss_str = f"{valid_weeks[0]} ~ {valid_weeks[-1]}" if valid_weeks else issue_range_str
    else:
        iss_str = issue_range_str

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
        "🎟️ 발매 M/S", 
        "✈️ 공급 M/S", 
        "🏷️ 대리점,RBD별 발매현황", 
        "👥 단체실적"
    ])

    # -------------------------------------------------------------
    # 1. 🎟️ 발매 M/S 탭
    # -------------------------------------------------------------
    with tab_34_1:
        if df_iss_raw is None or df_wt_raw is None:
            st.info("👈 좌측 사이드바에서 [34수송_9월1주차_CSV_2.csv]와 [가중치 파일.csv]를 업로드해주세요.")
            st.stop()

        merged_df = process_iss_merged(df_iss_raw, df_wt_raw)

        week_col = '발매주차_일자' if '발매주차_일자' in merged_df.columns else ('발매 주차' if '발매 주차' in merged_df.columns else '발매주차')
        all_issue_weeks = sorted([str(x) for x in merged_df[week_col].dropna().unique()]) if week_col else []

        month_col = '출발월' if '출발월' in merged_df.columns else ('출발 월' if '출발 월' in merged_df.columns else None)
        all_dep_months = sorted([str(x) for x in merged_df[month_col].dropna().unique()]) if month_col else []
        
        bound_col = '수송' if '수송' in merged_df.columns else ('Bound' if 'Bound' in merged_df.columns else None)
        all_bounds = sorted([str(x) for x in merged_df[bound_col].dropna().unique()]) if bound_col else []

        all_ticket_types = sorted([str(x) for x in merged_df['Ticket Type'].dropna().unique()]) if 'Ticket Type' in merged_df.columns else []

        raw_airlines = sorted([str(x) for x in merged_df['Dominant Marketing Airline'].dropna().unique()])
        all_airlines = ['KE'] + [x for x in raw_airlines if x != 'KE'] if 'KE' in raw_airlines else raw_airlines

        full_route_sum = merged_df.groupby('노선', observed=False)['Value'].sum().sort_values(ascending=False)
        route_order_list = [str(x) for x in full_route_sum.index.tolist() if str(x) != 'nan']

        with st.expander("🔍 **발매 대시보드 피벗 슬라이서 필터 설정** (KE 취항노선 전용)", expanded=True):
            apply_weight_toggle = st.toggle("⚖️ 가중치 적용 M/S 산출", value=True)
            val_col = 'Weighted_Value' if apply_weight_toggle else 'Value'

            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            sel_route_str = render_slicer_box(f_col1, "1. 노선 (KE취항/발매량순)", route_order_list, "slicer_route_iss")
            sel_week_str = render_slicer_box(f_col2, "2. 발매 주차 및 일자", all_issue_weeks, "slicer_week_iss") if week_col else ALL_OPTION
            sel_month_str = render_slicer_box(f_col3, "3. 출발 월", all_dep_months, "slicer_month_iss") if month_col else ALL_OPTION
            sel_bound_str = render_slicer_box(f_col4, "4. Bound", all_bounds, "slicer_bound_iss") if bound_col else ALL_OPTION

            f_col5, f_col6, _, _ = st.columns(4)
            sel_tt_str = render_slicer_box(f_col5, "5. Ticket Type (여정)", all_ticket_types, "slicer_tt_iss")
            sel_al_str = render_slicer_box(f_col6, "6. 항공사", all_airlines, "slicer_al_iss")

        filter_mask = pd.Series(True, index=merged_df.index)
        if sel_route_str != ALL_OPTION: filter_mask &= (merged_df['노선'].astype(str) == sel_route_str)
        if sel_al_str != ALL_OPTION: filter_mask &= (merged_df['Dominant Marketing Airline'].astype(str) == sel_al_str)
        if month_col and sel_month_str != ALL_OPTION: filter_mask &= (merged_df[month_col].astype(str) == sel_month_str)

        main_filtered_mask = filter_mask.copy()
        if bound_col and sel_bound_str != ALL_OPTION: main_filtered_mask &= (merged_df[bound_col].astype(str) == sel_bound_str)
        if 'Ticket Type' in merged_df.columns and sel_tt_str != ALL_OPTION: main_filtered_mask &= (merged_df['Ticket Type'].astype(str) == sel_tt_str)
        if week_col and sel_week_str != ALL_OPTION: main_filtered_mask &= (merged_df[week_col].astype(str) == sel_week_str)

        filtered_df = merged_df[main_filtered_mask]

        total_pax = filtered_df[val_col].sum()
        ke_pax = filtered_df[filtered_df['Dominant Marketing Airline'] == 'KE'][val_col].sum() if not filtered_df.empty else 0
        ke_ms = (ke_pax / total_pax * 100) if total_pax > 0 else 0

        top_al = "-"
        top_ms = 0.0
        if not filtered_df.empty and total_pax > 0:
            al_sum = filtered_df.groupby('Dominant Marketing Airline', observed=False)[val_col].sum()
            top_al = str(al_sum.idxmax())
            top_ms = (al_sum.max() / total_pax) * 100

        if not filtered_df.empty and total_pax > 0:
            filtered_route_sum = filtered_df.groupby('노선', observed=False)[val_col].sum()
            top_route = str(filtered_route_sum.idxmax())
        else:
            top_route = "-"

        status_wt_label = " (가중치)" if apply_weight_toggle else " (Raw)"

        tab1, tab2, tab3 = st.tabs(["📈 시각화 분석 차트", "📊 M/S 피벗 테이블", "🔒 Raw Data View (관리자 전용)"])
        with tab1:
            if not filtered_df.empty:
                al_order = [al for al in all_airlines if al in filtered_df['Dominant Marketing Airline'].unique()]
                
                # 📌 1. 항공사별 M/S 점유비
                st.markdown('<div class="unified-sub-header">1. 항공사별 M/S 점유비</div>', unsafe_allow_html=True)
                c1, c2 = st.columns([1.6, 1])
                with c1:
                    pie_al = filtered_df.groupby('Dominant Marketing Airline', observed=False)[val_col].sum().reset_index()
                    fig1 = px.pie(
                        pie_al, values=val_col, names='Dominant Marketing Airline',
                        hole=0.4, category_orders={'Dominant Marketing Airline': al_order}
                    )
                    fig1.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>항공사: %{label}</b><br>실적: %{value:,.0f}<br>점유율: %{percent:.1%}<extra></extra>")
                    apply_bottom_legend(fig1)
                    st.plotly_chart(fig1, width="stretch")

                with c2:
                    st.markdown("##### 📌 발매 실적 핵심 요약 (Summary)")
                    st.markdown(f'<div class="metric-card"><div class="metric-title">총 발매 실적{status_wt_label}</div><div class="metric-value">{total_pax:,.0f}</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-card-ke"><div class="metric-title" style="color:#16a34a; font-weight:bold;">✈️ <span class="ke-highlight">KE (대한항공) M/S</span></div><div class="metric-value" style="color:#16a34a;"><b>{ke_pax:,.0f} ({ke_ms:.1f}%)</b></div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-card"><div class="metric-title">1위 항공사 (M/S)</div><div class="metric-value" style="color:#1d4ed8;"><b>{top_al}</b> ({top_ms:.1f}%)</div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="metric-card"><div class="metric-title">최대 실적 노선</div><div class="metric-value" style="color:#047857;">{top_route}</div></div>', unsafe_allow_html=True)

                st.markdown("---")
                
                # 📌 2. 발매/주차별 항공사 발매량 추이
                if week_col and week_col in merged_df.columns:
                    st.markdown('<div class="unified-sub-header">2. 발매/주차별 항공사 발매량 추이</div>', unsafe_allow_html=True)
                    
                    mask_no_week = filter_mask.copy()
                    if bound_col and sel_bound_str != ALL_OPTION: mask_no_week &= (merged_df[bound_col].astype(str) == sel_bound_str)
                    if 'Ticket Type' in merged_df.columns and sel_tt_str != ALL_OPTION: mask_no_week &= (merged_df['Ticket Type'].astype(str) == sel_tt_str)

                    df_no_week = merged_df[mask_no_week]

                    if not df_no_week.empty:
                        week_al_grp = df_no_week.groupby([week_col, 'Dominant Marketing Airline'], observed=False)[val_col].sum().reset_index()
                        week_totals = week_al_grp.groupby(week_col, observed=False)[val_col].sum().reset_index()
                        week_totals_dict = dict(zip(week_totals[week_col].astype(str), week_totals[val_col]))
                        ke_week_grp = week_al_grp[week_al_grp['Dominant Marketing Airline'] == 'KE'].set_index(week_col)[val_col].to_dict()

                        week_al_grp['Week_Total'] = week_al_grp[week_col].map(week_totals_dict)
                        week_tot_num = pd.to_numeric(week_al_grp['Week_Total'], errors='coerce').fillna(0)
                        val_col_num = pd.to_numeric(week_al_grp[val_col], errors='coerce').fillna(0)
                        week_al_grp['MS_Percent'] = np.where(week_tot_num > 0, (val_col_num / week_tot_num) * 100, 0)
                        week_al_grp['Text_Display'] = week_al_grp['MS_Percent'].map(lambda x: f"{x:.1f}%" if x >= 3.0 else "")

                        fig_week = px.bar(
                            week_al_grp, x=week_col, y=val_col, color='Dominant Marketing Airline',
                            barmode='stack', text='Text_Display',
                            category_orders={'Dominant Marketing Airline': al_order, week_col: all_issue_weeks},
                            custom_data=['Dominant Marketing Airline', val_col, 'MS_Percent']
                        )
                        fig_week.update_traces(textposition='inside', hovertemplate="<b>항공사: %{customdata[0]}</b><br>발매 실적: %{customdata[1]:,.0f}<br>점유비: %{customdata[2]:.1f}%<extra></extra>")

                        valid_weeks = [w for w in all_issue_weeks if w in week_totals_dict]
                        top_bar_labels = [f"<b>{week_totals_dict.get(w, 0):,.0f}</b><br><span style='color:#16a34a;'>(★KE {(ke_week_grp.get(w, 0)/week_totals_dict.get(w,0)*100) if week_totals_dict.get(w,0)>0 else 0:.1f}%)</span>" for w in valid_weeks]

                        fig_week.add_trace(go.Scatter(x=valid_weeks, y=[week_totals_dict[w] for w in valid_weeks], mode='text', text=top_bar_labels, textposition='top center', showlegend=False, hoverinfo='skip'))
                        fig_week.update_layout(yaxis_title=f"발매 실적{' (가중치)' if apply_weight_toggle else ''}")
                        apply_bottom_legend(fig_week)
                        st.plotly_chart(fig_week, width="stretch")

                st.markdown("---")

                # 📌 3. 출발기간별 주요 항공사 M/S 점유비 추이 (KE 강조 + 타사 점선)
                if month_col and month_col in merged_df.columns:
                    st.markdown('<div class="unified-sub-header">3. 출발기간별 주요 항공사 M/S 점유비 추이</div>', unsafe_allow_html=True)
                    
                    mask_dep_al = filter_mask.copy()
                    if week_col and sel_week_str != ALL_OPTION: mask_dep_al &= (merged_df[week_col].astype(str) == sel_week_str)
                    if bound_col and sel_bound_str != ALL_OPTION: mask_dep_al &= (merged_df[bound_col].astype(str) == sel_bound_str)
                    if 'Ticket Type' in merged_df.columns and sel_tt_str != ALL_OPTION: mask_dep_al &= (merged_df['Ticket Type'].astype(str) == sel_tt_str)

                    df_dep_al = merged_df[mask_dep_al]

                    if not df_dep_al.empty:
                        dep_al_grp = df_dep_al.groupby([month_col, 'Dominant Marketing Airline'], observed=False)[val_col].sum().reset_index()
                        dep_mkt_tot = df_dep_al.groupby(month_col, observed=False)[val_col].sum().reset_index()
                        
                        dep_al_grp[month_col] = dep_al_grp[month_col].astype(str)
                        dep_mkt_tot[month_col] = dep_mkt_tot[month_col].astype(str)

                        dep_merged = pd.merge(dep_al_grp, dep_mkt_tot, on=month_col, suffixes=('', '_Mkt'))
                        dep_merged[val_col] = dep_merged[val_col].fillna(0)
                        dep_merged['MS_Percent'] = np.where(dep_merged[f'{val_col}_Mkt'] > 0, (dep_merged[val_col] / dep_merged[f'{val_col}_Mkt']) * 100, 0)

                        top_al_in_dep = df_dep_al.groupby('Dominant Marketing Airline', observed=False)[val_col].sum().sort_values(ascending=False).index.tolist()
                        top_al_display = ['KE'] + [al for al in top_al_in_dep if al != 'KE'][:5]

                        dep_merged_top = dep_merged[dep_merged['Dominant Marketing Airline'].isin(top_al_display)].copy()

                        fig_ke_dep = go.Figure()

                        for al_code in top_al_display:
                            al_data = dep_merged_top[dep_merged_top['Dominant Marketing Airline'] == al_code]
                            if al_data.empty:
                                continue

                            is_ke = (al_code == 'KE')
                            line_style = dict(color='#16a34a', width=3.5) if is_ke else dict(dash='dot', width=1.5)
                            marker_style = dict(size=8, symbol='circle') if is_ke else dict(size=4)
                            mode_setting = 'lines+markers+text' if is_ke else 'lines+markers'
                            text_labels = [f"<b>{v:.1f}%</b>" for v in al_data['MS_Percent']] if is_ke else None

                            fig_ke_dep.add_trace(go.Scatter(
                                x=al_data[month_col],
                                y=al_data['MS_Percent'],
                                mode=mode_setting,
                                name=f"★ KE (대한항공)" if is_ke else al_code,
                                line=line_style,
                                marker=marker_style,
                                text=text_labels,
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
                        st.plotly_chart(fig_ke_dep, width="stretch")

                st.markdown("---")
                
                # 📌 4 및 5번 차트 컬럼 레이아웃
                c3, c4 = st.columns(2)
                ke_only_df = merged_df[merged_df['Dominant Marketing Airline'] == 'KE']
                
                with c3:
                    if bound_col:
                        st.markdown('<div class="unified-sub-header">4. Bound별 점유비 (KE 한정)</div>', unsafe_allow_html=True)
                        mask_ke_bound = filter_mask.copy()
                        if week_col and sel_week_str != ALL_OPTION: mask_ke_bound &= (merged_df[week_col].astype(str) == sel_week_str)
                        if 'Ticket Type' in merged_df.columns and sel_tt_str != ALL_OPTION: mask_ke_bound &= (merged_df['Ticket Type'].astype(str) == sel_tt_str)

                        df_ke_bound = ke_only_df[mask_ke_bound.reindex(ke_only_df.index, fill_value=False)]
                        bound_pie_df = df_ke_bound.groupby(bound_col, observed=False)[val_col].sum().reset_index()
                        
                        fig3 = px.pie(bound_pie_df, values=val_col, names=bound_col, hole=0.4)
                        fig3.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>Bound: %{label}</b><br>실적: %{value:,.0f}<br>점유율: %{percent:.1%}<extra></extra>")
                        apply_bottom_legend(fig3)
                        st.plotly_chart(fig3, width="stretch")

                with c4:
                    if 'Ticket Type' in merged_df.columns:
                        st.markdown('<div class="unified-sub-header">5. Trip Type별 점유비 (KE 한정)</div>', unsafe_allow_html=True)
                        mask_ke_tt = filter_mask.copy()
                        if week_col and sel_week_str != ALL_OPTION: mask_ke_tt &= (merged_df[week_col].astype(str) == sel_week_str)
                        if bound_col and sel_bound_str != ALL_OPTION: mask_ke_tt &= (merged_df[bound_col].astype(str) == sel_bound_str)

                        df_ke_tt = ke_only_df[mask_ke_tt.reindex(ke_only_df.index, fill_value=False)]
                        tt_pie_df = df_ke_tt.groupby('Ticket Type', observed=False)[val_col].sum().reset_index()

                        fig4 = px.pie(tt_pie_df, values=val_col, names='Ticket Type', hole=0.4)
                        fig4.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>Trip Type: %{label}</b><br>실적: %{value:,.0f}<br>점유율: %{percent:.1%}<extra></extra>")
                        apply_bottom_legend(fig4)
                        st.plotly_chart(fig4, width="stretch")

        with tab2:
            st.markdown("##### 📌 주차별 및 노선별 발매 M/S 매트릭스")
            t1, t2 = st.columns([1.1, 1])
            with t1:
                if week_col and week_col in filtered_df.columns:
                    piv_w = filtered_df.pivot_table(index='Dominant Marketing Airline', columns=week_col, values=val_col, aggfunc='sum', fill_value=0, observed=False)
                    piv_w_ms = piv_w.divide(piv_w.sum(axis=0), axis=1) * 100
                    al_sorted = ['KE'] + [x for x in piv_w_ms.index if x != 'KE'] if 'KE' in piv_w_ms.index else piv_w_ms.index
                    st.dataframe(piv_w_ms.loc[al_sorted].head(100).map(lambda x: f"{x:.1f}%"), width="stretch")
            with t2:
                piv_r = filtered_df.pivot_table(index='노선', columns='Dominant Marketing Airline', values=val_col, aggfunc='sum', fill_value=0, observed=False)
                cols_ke = ['KE'] + [x for x in piv_r.columns if x != 'KE'] if 'KE' in piv_r.columns else piv_r.columns
                piv_r_ms = piv_r[cols_ke].divide(piv_r.sum(axis=1), axis=0) * 100
                st.dataframe(piv_r_ms.head(100).map(lambda x: f"{x:.1f}%"), width="stretch")

        with tab3:
            st.subheader("🔒 관리자 전용 Raw Data 조회 및 다운로드")
            admin_pw = st.text_input("🔑 관리자 비밀번호를 입력하세요:", type="password", key="admin_pw_input")
            
            if admin_pw == "1234":
                st.success("✅ 관리자 인증이 완료되었습니다.")
                csv_data = filtered_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 필터링된 발매 Raw Data (CSV) 전체 다운로드",
                    data=csv_data,
                    file_name=f"Ticketing_Raw_Data_{datetime.date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
                st.dataframe(filtered_df.head(100), width="stretch")
            else:
                if admin_pw:
                    st.error("❌ 비밀번호가 올바르지 않습니다.")
                else:
                    st.info("ℹ️ 관리자 비밀번호 입력 시 이용할 수 있습니다.")

    # -------------------------------------------------------------
    # 2. ✈️ 공급 M/S 탭
    # -------------------------------------------------------------
    with tab_34_2:
        if df_sup_raw is None:
            st.info("👈 좌측 사이드바에서 [공급_9월1주차_CSV.csv] 파일을 업로드해주세요.")
            st.stop()

        df_sup = df_sup_raw.copy()
        df_sup.columns = [c.strip() for c in df_sup.columns]

        sup_ke_col = 'KE취항여부' if 'KE취항여부' in df_sup.columns else ('KE취항노선 여부' if 'KE취항노선 여부' in df_sup.columns else None)
        if sup_ke_col:
            df_sup = df_sup[df_sup[sup_ke_col].astype(str) == '취항'].reset_index(drop=True)
        
        if 'Op Airline Code' in df_sup.columns:
            df_sup['Airline'] = df_sup['Op Airline Code']
        elif 'Mkt Al' in df_sup.columns:
            df_sup['Airline'] = df_sup['Mkt Al']
        else:
            df_sup['Airline'] = 'Unknown'

        df_sup['Seats_num'] = pd.to_numeric(df_sup['Seats'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if 'Seats' in df_sup.columns else 0
        df_sup['Flights_num'] = pd.to_numeric(df_sup['Flights'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0) if 'Flights' in df_sup.columns else 1

        sup_routes = df_sup.groupby('노선', observed=False)['Seats_num'].sum().sort_values(ascending=False).index.astype(str).tolist()
        sup_month_col = '출발월' if '출발월' in df_sup.columns else ('출발 월' if '출발 월' in df_sup.columns else ('Travel Month' if 'Travel Month' in df_sup.columns else None))
        sup_months = sorted([str(x) for x in df_sup[sup_month_col].dropna().unique()]) if sup_month_col else []
        sup_time_cats = sorted([str(x) for x in df_sup['출발 시간대'].dropna().unique()]) if '출발 시간대' in df_sup.columns else []

        raw_sup_al = sorted([str(x) for x in df_sup['Airline'].dropna().unique()])
        sup_airlines = ['KE'] + [x for x in raw_sup_al if x != 'KE'] if 'KE' in raw_sup_al else raw_sup_al
        sup_color_map = build_airline_color_map(sup_airlines)

        st.markdown('<div class="unified-sub-header">🔍 공급 대시보드 필터 설정 (KE 취항노선 전용)</div>', unsafe_allow_html=True)
        metric_mode = st.radio("📊 분석 공급 지표 선택:", options=["공급석 (Seats)", "운항 편수 (Flight Frequencies)"], horizontal=True)
        
        sf_col1, sf_col2, sf_col3, sf_col4 = st.columns(4)
        selected_sup_route_str = render_slicer_box(sf_col1, "1. 노선", sup_routes, "slicer_route_sup")
        selected_sup_month_str = render_slicer_box(sf_col2, "2. 출발 월", sup_months, "slicer_month_sup") if sup_month_col else ALL_OPTION
        selected_sup_time_str = render_slicer_box(sf_col3, "3. 출발 시간대", sup_time_cats, "slicer_time_sup")
        selected_sup_al_str = render_slicer_box(sf_col4, "4. 항공사", sup_airlines, "slicer_al_sup")

        target_val = 'Seats_num' if "공급석" in metric_mode else 'Flights_num'

        filter_mask_sup = pd.Series(True, index=df_sup.index)
        if selected_sup_route_str != ALL_OPTION: filter_mask_sup &= (df_sup['노선'].astype(str) == selected_sup_route_str)
        if selected_sup_al_str != ALL_OPTION: filter_mask_sup &= (df_sup['Airline'].astype(str) == selected_sup_al_str)
        if sup_month_col and selected_sup_month_str != ALL_OPTION: filter_mask_sup &= (df_sup[sup_month_col].astype(str) == selected_sup_month_str)
        if '출발 시간대' in df_sup.columns and selected_sup_time_str != ALL_OPTION: filter_mask_sup &= (df_sup['출발 시간대'].astype(str) == selected_sup_time_str)

        filtered_sup = df_sup[filter_mask_sup]

        csv_sup = filtered_sup.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 필터링된 공급 Raw Data (CSV) 전체 다운로드",
            data=csv_sup,
            file_name=f"Supply_Raw_Data_{datetime.date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

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
                fig_s1 = px.pie(
                    pie_sup_al, values=target_val, names='Airline',
                    hole=0.4, category_orders={'Airline': sup_al_order},
                    color='Airline', color_discrete_map=sup_color_map
                )
                fig_s1.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="<b>항공사: %{label}</b><br>공급량: %{value:,.0f}<br>점유율: %{percent:.1%}<extra></extra>")
                apply_bottom_legend(fig_s1)
                st.plotly_chart(fig_s1, width="stretch")

            with cs2:
                st.markdown(f'<div class="unified-sub-header">2. 항공사별 공급 실적 및 M/S 요약</div>', unsafe_allow_html=True)
                pie_sup_al['공급 M/S (%)'] = (pie_sup_al[target_val] / pie_sup_al[target_val].sum()) * 100
                pie_sup_al = pie_sup_al.sort_values(by=target_val, ascending=False).reset_index(drop=True).head(100)
                pie_sup_al.index = range(1, len(pie_sup_al) + 1)
                
                sup_pivot_html = '<div class="custom-piv-container"><table class="custom-piv-table">'
                sup_pivot_html += '<thead><tr><th class="header-main" style="width:60px;">순위</th><th class="header-main">항공사</th>'
                sup_pivot_html += f'<th class="header-main">공급 실적 ({metric_mode.split()[0]})</th><th class="header-main">공급 M/S (%)</th></tr></thead><tbody>'

                for rank_idx, row in pie_sup_al.iterrows():
                    al_name = str(row['Airline'])
                    s_val = row[target_val]
                    s_ms = row['공급 M/S (%)']
                    is_ke = (al_name == 'KE')
                    row_style = ' class="row-group-header"' if is_ke else ''
                    
                    sup_pivot_html += f'<tr{row_style}>'
                    sup_pivot_html += f'<td style="text-align:center;"><b>{rank_idx}위</b></td>'
                    sup_pivot_html += f'<td style="text-align:center; font-weight:700;">{"★ KE" if is_ke else al_name}</td>'
                    sup_pivot_html += f'<td style="text-align:center;"><b>{s_val:,.0f}</b></td>'
                    sup_pivot_html += f'<td style="text-align:center;"><b>{s_ms:.1f}%</b></td></tr>'

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
                df_schedule = filtered_sup[filtered_sup['노선'] == selected_single_route].copy()
                if not df_schedule.empty and 'Dep Time' in df_schedule.columns:
                    time_tuples = df_schedule['Dep Time'].apply(format_dep_time)
                    df_schedule['Start_Time'] = [t[0] for t in time_tuples]
                    df_schedule['End_Time'] = [t[1] for t in time_tuples]

                    fig_timeline = px.timeline(
                        df_schedule, x_start="Start_Time", x_end="End_Time",
                        y="Airline", color="Airline", text="Airline",
                        title=f"[{selected_single_route}] 노선 하루 출발 시간대별 운항 스케줄 타임라인",
                        color_discrete_map=sup_color_map, category_orders={'Airline': sup_airlines}
                    )
                    fig_timeline.update_yaxes(autorange="reversed", title="항공사")
                    fig_timeline.update_xaxes(title="하루 시간대 (00:00 ~ 24:00)", dtick=3600000, tickformat="%H:%M")
                    fig_timeline.update_traces(textposition='inside', hovertemplate="<b>항공사: %{y}</b><br>출발시각: %{x}<br>공급석: %{customdata[0]:,.0f}석<extra></extra>", customdata=df_schedule[['Seats_num']])
                    fig_timeline.update_layout(height=400, showlegend=True)
                    apply_bottom_legend(fig_timeline)
                    st.plotly_chart(fig_timeline, width="stretch")

    # -------------------------------------------------------------
    # 3. 🏷️ 대리점,RBD별 발매현황 탭
    # -------------------------------------------------------------
    with tab_34_3:
        if df_iss_raw is None:
            st.info("👈 좌측 사이드바에서 [34수송_9월1주차_CSV_2.csv] 파일이 업로드되어 있는지 확인해주세요.")
            st.stop()

        df_agency = process_iss_merged(df_iss_raw, df_wt_raw)

        week_col_a = '발매주차_일자' if '발매주차_일자' in df_agency.columns else ('발매 주차' if '발매 주차' in df_agency.columns else '발매주차')
        month_col_a = '출발월' if '출발월' in df_agency.columns else ('출발 월' if '출발 월' in df_agency.columns else None)
        bound_col_a = '수송' if '수송' in df_agency.columns else ('Bound' if 'Bound' in df_agency.columns else None)
        time_col_a = '출발시간대' if '출발시간대' in df_agency.columns else None
        
        all_routes_a = sorted([str(x) for x in df_agency['노선'].dropna().unique()])
        all_months_a = sorted([str(x) for x in df_agency[month_col_a].dropna().unique()]) if month_col_a else []
        all_bounds_a = sorted([str(x) for x in df_agency[bound_col_a].dropna().unique()]) if bound_col_a else []
        all_tt_a = sorted([str(x) for x in df_agency['Ticket Type'].dropna().unique()]) if 'Ticket Type' in df_agency.columns else []
        all_time_a = sorted([str(x) for x in df_agency[time_col_a].dropna().unique()]) if time_col_a else []
        
        raw_ag_al = sorted([str(x) for x in df_agency['Dominant Marketing Airline'].dropna().unique()])
        all_al_a = ['KE'] + [x for x in raw_ag_al if x != 'KE'] if 'KE' in raw_ag_al else raw_ag_al

        with st.expander("🔍 **대리점 & RBD 분석 피벗 슬라이서 필터 설정**", expanded=True):
            ac1, ac2, ac3 = st.columns(3)
            sel_route_ag_str = render_slicer_box(ac1, "1. 노선", all_routes_a, "slicer_route_ag")
            sel_month_ag_str = render_slicer_box(ac2, "2. 출발 월", all_months_a, "slicer_month_ag") if month_col_a else ALL_OPTION
            sel_bound_ag_str = render_slicer_box(ac3, "3. BOUND (수송)", all_bounds_a, "slicer_bound_ag") if bound_col_a else ALL_OPTION

            ac4, ac5, ac6 = st.columns(3)
            sel_tt_ag_str = render_slicer_box(ac4, "4. TRIP TYPE", all_tt_a, "slicer_tt_ag") if 'Ticket Type' in df_agency.columns else ALL_OPTION
            sel_time_ag_str = render_slicer_box(ac5, "5. 출발 시간대", all_time_a, "slicer_time_ag") if time_col_a else ALL_OPTION
            sel_al_ag_str = render_slicer_box(ac6, "6. 항공사", all_al_a, "slicer_al_ag")

        mask_ag = pd.Series(True, index=df_agency.index)
        if sel_route_ag_str != ALL_OPTION: mask_ag &= (df_agency['노선'].astype(str) == sel_route_ag_str)
        if sel_al_ag_str != ALL_OPTION: mask_ag &= (df_agency['Dominant Marketing Airline'].astype(str) == sel_al_ag_str)
        if month_col_a and sel_month_ag_str != ALL_OPTION: mask_ag &= (df_agency[month_col_a].astype(str) == sel_month_ag_str)
        if bound_col_a and sel_bound_ag_str != ALL_OPTION: mask_ag &= (df_agency[bound_col_a].astype(str) == sel_bound_ag_str)
        if 'Ticket Type' in df_agency.columns and sel_tt_ag_str != ALL_OPTION: mask_ag &= (df_agency['Ticket Type'].astype(str) == sel_tt_ag_str)
        if time_col_a and sel_time_ag_str != ALL_OPTION: mask_ag &= (df_agency[time_col_a].astype(str) == sel_time_ag_str)

        df_ag_filtered = df_agency[mask_ag]

        csv_ag = df_ag_filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 필터링된 대리점/RBD Raw Data (CSV) 전체 다운로드",
            data=csv_ag,
            file_name=f"Agency_RBD_Raw_Data_{datetime.date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

        expand_toggle_all = st.toggle("📂 전체 항목 펼쳐보기 (열기/닫기)", value=True, key="expand_toggle_all_key")
        open_attr = "open" if expand_toggle_all else ""

        sub_tab_rbd, sub_tab_agency = st.tabs(["📊 RBD별 판매현황", "🏢 대리점별 판매현황 (상위 20개 대리점)"])

        with sub_tab_rbd:
            if not df_ag_filtered.empty and 'O&D RBKD' in df_ag_filtered.columns and week_col_a:
                week_list = sorted([str(x) for x in df_ag_filtered[week_col_a].dropna().unique()], reverse=True)
                ag_al_sum = df_ag_filtered.groupby('Dominant Marketing Airline', observed=False)['Value'].sum().sort_values(ascending=False)
                ag_al_list = [str(x) for x in ag_al_sum.index if ag_al_sum[x] > 0]
                if 'KE' in ag_al_list:
                    ag_al_list.remove('KE')
                    ag_al_list = ['KE'] + ag_al_list

                rbd_html = '<div class="custom-piv-container"><table class="custom-piv-table">'
                rbd_html += '<thead><tr><th class="header-main" style="width:180px; text-align:center;">항공사 / RBD 클래스</th>'
                for wk in week_list:
                    rbd_html += f'<th class="header-main">{wk}</th>'
                rbd_html += '<th class="header-main">총합계</th></tr></thead><tbody>'

                for al_code in ag_al_list:
                    al_sub = df_ag_filtered[df_ag_filtered['Dominant Marketing Airline'] == al_code]
                    al_tot_pax = al_sub['Value'].sum()

                    if al_tot_pax > 0:
                        piv_rbd = al_sub.pivot_table(index='O&D RBKD', columns=week_col_a, values='Value', aggfunc='sum', fill_value=0, observed=False)
                        piv_rbd['총합계'] = piv_rbd.sum(axis=1)
                        piv_rbd = piv_rbd[piv_rbd['총합계'] > 0]

                        if al_code in RBD_HIERARCHY:
                            hierarchy_order = RBD_HIERARCHY[al_code]
                            existing_rbds = piv_rbd.index.tolist()
                            sorted_rbds = [r for r in hierarchy_order if r in existing_rbds] + [r for r in existing_rbds if r not in hierarchy_order]
                            piv_rbd = piv_rbd.loc[sorted_rbds]
                        else:
                            piv_rbd = piv_rbd.sort_values(by='총합계', ascending=False)

                        rbd_html += f'<tr><td colspan="{len(week_list)+2}" style="padding:0; border:none;">'
                        rbd_html += f'<details class="rbd-details-group" {open_attr}><summary>'
                        rbd_html += f'<table style="width:100%; border-collapse:collapse;"><tr class="row-summary-top-dark">'
                        rbd_html += f'<td style="width:180px; text-align:center;">▼ ★ {al_code} 총계</td>'
                        for wk in week_list:
                            wk_tot = al_sub[al_sub[week_col_a] == wk]['Value'].sum()
                            rbd_html += f'<td style="text-align:center;">{wk_tot:,.0f}</td>'
                        rbd_html += f'<td style="text-align:center;">{al_tot_pax:,.0f}</td>'
                        rbd_html += '</tr></table></summary>'

                        rbd_html += '<table style="width:100%; border-collapse:collapse;">'
                        for rbd_code, rbd_row in piv_rbd.head(100).iterrows():
                            rbd_html += '<tr class="rbd-child-row">'
                            rbd_html += f'<td style="width:180px; text-align:center; font-weight:700;">{rbd_code}</td>'
                            for wk in week_list:
                                v_num = rbd_row[wk] if wk in rbd_row else 0
                                v_str = f"{v_num:,.0f}" if v_num > 0 else ""
                                rbd_html += f'<td style="text-align:center;">{v_str}</td>'
                            tot_v = rbd_row['총합계']
                            rbd_html += f'<td style="text-align:center; font-weight:700;">{tot_v:,.0f}</td></tr>'
                        rbd_html += '</table></details></td></tr>'

                rbd_html += '</tbody></table></div>'
                st.markdown(rbd_html, unsafe_allow_html=True)
            else:
                st.warning("선택된 조건의 RBD 데이터가 없습니다.")

        with sub_tab_agency:
            if not df_ag_filtered.empty and 'Travel Agency Name' in df_ag_filtered.columns and week_col_a:
                week_list_ag = sorted([str(x) for x in df_ag_filtered[week_col_a].dropna().unique()], reverse=True)
                top_20_agencies = df_ag_filtered.groupby('Travel Agency Name', observed=False)['Value'].sum().sort_values(ascending=False).head(20).index.tolist()

                ag_html = '<div class="custom-piv-container"><table class="custom-piv-table">'
                ag_html += '<thead><tr><th class="header-main" style="width:180px; text-align:center;">대리점 / 항공사</th>'
                for wk in week_list_ag:
                    ag_html += f'<th class="header-main">{wk}</th>'
                ag_html += '<th class="header-main">총 판매량</th></tr></thead><tbody>'

                for ag_name in top_20_agencies:
                    ag_sub = df_ag_filtered[df_ag_filtered['Travel Agency Name'] == ag_name]
                    ag_tot_val = ag_sub['Value'].sum()

                    if ag_tot_val > 0:
                        piv_ag_sub = ag_sub.pivot_table(index='Dominant Marketing Airline', columns=week_col_a, values='Value', aggfunc='sum', fill_value=0, observed=False)
                        piv_ag_sub['총합계'] = piv_ag_sub.sum(axis=1)
                        piv_ag_sub = piv_ag_sub[piv_ag_sub['총합계'] > 0]

                        piv_ag_sub = piv_ag_sub.reset_index()
                        piv_ag_sub['is_ke'] = (piv_ag_sub['Dominant Marketing Airline'] == 'KE')
                        piv_ag_sub = piv_ag_sub.sort_values(by=['is_ke', '총합계'], ascending=[False, False]).drop(columns=['is_ke'])
                        piv_ag_sub = piv_ag_sub.set_index('Dominant Marketing Airline')

                        ag_html += f'<tr><td colspan="{len(week_list_ag)+2}" style="padding:0; border:none;">'
                        ag_html += f'<details class="rbd-details-group" {open_attr}><summary>'
                        ag_html += f'<table style="width:100%; border-collapse:collapse;"><tr class="row-summary-top-dark">'
                        ag_html += f'<td style="width:180px; text-align:center;">▼ ★ {ag_name} 총계</td>'
                        for wk in week_list_ag:
                            wk_tot_ag = ag_sub[ag_sub[week_col_a] == wk]['Value'].sum()
                            ag_html += f'<td style="text-align:center;">{wk_tot_ag:,.0f}</td>'
                        ag_html += f'<td style="text-align:center;">{ag_tot_val:,.0f}</td>'
                        ag_html += '</tr></table></summary>'

                        ag_html += '<table style="width:100%; border-collapse:collapse;">'
                        for al_code, al_row in piv_ag_sub.head(100).iterrows():
                            is_ke_flag = (al_code == 'KE')
                            cell_style = 'font-weight:700; color:#16a34a;' if is_ke_flag else 'color:#475569;'
                            
                            ag_html += '<tr class="rbd-child-row">'
                            ag_html += f'<td style="width:180px; text-align:center; {cell_style}">{"★ KE" if is_ke_flag else al_code}</td>'
                            for wk in week_list_ag:
                                v_num = al_row[wk] if wk in al_row else 0
                                v_str = f"{v_num:,.0f}" if v_num > 0 else ""
                                ag_html += f'<td style="text-align:center; {cell_style}">{v_str}</td>'
                            tot_v = al_row['총합계']
                            ag_html += f'<td style="text-align:center; font-weight:700; {cell_style}">{tot_v:,.0f}</td></tr>'
                        ag_html += '</table></details></td></tr>'

                ag_html += '</tbody></table></div>'
                st.markdown(ag_html, unsafe_allow_html=True)
            else:
                st.warning("선택된 조건의 대리점 데이터가 없습니다.")

    # -------------------------------------------------------------
    # 4. 👥 단체실적 탭
    # -------------------------------------------------------------
    with tab_34_4:
        st.subheader("👥 발매 - 항공사별/대리점별 단체 발매 현황")
        
        if df_iss_raw is None:
            st.info("👈 좌측 사이드바에서 [34수송_9월1주차_CSV_2.csv] 파일이 업로드되어 있는지 확인해주세요.")
            st.stop()

        df_grp_raw = process_iss_merged(df_iss_raw, df_wt_raw)

        dep_date_col = 'Dep Date' if 'Dep Date' in df_grp_raw.columns else ('출발일자' if '출발일자' in df_grp_raw.columns else None)
        if dep_date_col:
            df_grp_raw['Date_Obj'] = pd.to_datetime(df_grp_raw[dep_date_col].astype(str), errors='coerce')
            target_today_dt = pd.to_datetime(today)
            target_future_dt = pd.to_datetime(future_10_days)
            df_grp_raw = df_grp_raw[(df_grp_raw['Date_Obj'] >= target_today_dt) & (df_grp_raw['Date_Obj'] <= target_future_dt)]

        with st.expander("🔍 **단체실적 검색 피벗 슬라이서 필터 설정**", expanded=True):
            gf_col1, gf_col2, gf_col3 = st.columns(3)
            all_g_routes = sorted([str(x) for x in df_grp_raw['노선'].dropna().unique()])
            sel_g_route_str = render_slicer_box(gf_col1, "1. 노선", all_g_routes, "slicer_route_grp")

            g_month_col = '출발월' if '출발월' in df_grp_raw.columns else ('출발 월' if '출발 월' in df_grp_raw.columns else None)
            all_g_months = sorted([str(x) for x in df_grp_raw[g_month_col].dropna().unique()]) if g_month_col else []
            sel_g_month_str = render_slicer_box(gf_col2, "2. 출발월", all_g_months, "slicer_month_grp") if g_month_col else ALL_OPTION

            raw_g_al = sorted([str(x) for x in df_grp_raw['Dominant Marketing Airline'].dropna().unique()])
            all_g_al = ['KE'] + [x for x in raw_g_al if x != 'KE'] if 'KE' in raw_g_al else raw_g_al
            sel_g_al_str = render_slicer_box(gf_col3, "3. 항공사", all_g_al, "slicer_al_grp")

        mask_grp = pd.Series(True, index=df_grp_raw.index)
        if sel_g_route_str != ALL_OPTION: mask_grp &= (df_grp_raw['노선'].astype(str) == sel_g_route_str)
        if g_month_col and sel_g_month_str != ALL_OPTION: mask_grp &= (df_grp_raw[g_month_col].astype(str) == sel_g_month_str)
        if sel_g_al_str != ALL_OPTION: mask_grp &= (df_grp_raw['Dominant Marketing Airline'].astype(str) == sel_g_al_str)

        is_grp_cond = (
            ((df_grp_raw['Dominant Marketing Airline'] == '7C') & (df_grp_raw['O&D RBKD'] == 'V')) |
            ((df_grp_raw['Dominant Marketing Airline'] != '7C') & (df_grp_raw['O&D RBKD'] == 'G'))
        )
        mask_grp &= is_grp_cond

        df_grp_filtered = df_grp_raw[mask_grp].copy()

        csv_grp = df_grp_filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 필터링된 단체실적 Raw Data (CSV) 전체 다운로드",
            data=csv_grp,
            file_name=f"Group_Raw_Data_{datetime.date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

        if not df_grp_filtered.empty and 'Travel Agency Name' in df_grp_filtered.columns:
            st.markdown(f"##### 📌 항공사별 / 여행사(대리점)별 단체 실적 현황 (상위 100개 대리점)")

            ag_sum_df = df_grp_filtered.groupby(['Dominant Marketing Airline', 'Travel Agency Name'], observed=False)['Value'].sum().reset_index()
            ag_sum_df = ag_sum_df[ag_sum_df['Value'] > 0]

            al_totals = ag_sum_df.groupby('Dominant Marketing Airline', observed=False)['Value'].sum().sort_values(ascending=False)
            al_sorted_list = [str(x) for x in al_totals.index]
            if 'KE' in al_sorted_list:
                al_sorted_list.remove('KE')
                al_sorted_list = ['KE'] + al_sorted_list

            for al_code in al_sorted_list:
                al_sub = ag_sum_df[ag_sum_df['Dominant Marketing Airline'] == al_code]
                al_tot_val = al_sub['Value'].sum()

                if al_tot_val > 0:
                    exp_title = f"✈️ 항공사: **{al_code}**  |  총 단체 실적: **{al_tot_val:,.0f}**건"
                    
                    with st.expander(exp_title, expanded=(al_code == 'KE')):
                        top_ag_sub = al_sub.sort_values(by='Value', ascending=False).head(100).reset_index(drop=True)
                        top_ag_sub.index = range(1, len(top_ag_sub) + 1)

                        g_html = '<div class="custom-piv-container"><table class="custom-piv-table">'
                        g_html += '<thead><tr>'
                        g_html += '<th class="header-main" style="width:80px; text-align:center;">순위</th>'
                        g_html += '<th class="header-main" style="text-align:center;">여행사(대리점)명</th>'
                        g_html += '<th class="header-main" style="width:200px; text-align:center;">단체 예약 실적 (석)</th>'
                        g_html += '</tr></thead><tbody>'

                        g_html += '<tr class="row-group-header-custom">'
                        g_html += f'<td style="text-align:center;">-</td>'
                        g_html += f'<td style="text-align:center; font-weight:800;">★ {al_code} 전체 총합계</td>'
                        g_html += f'<td style="text-align:center;"><b>{al_tot_val:,.0f}</b></td></tr>'

                        for r_idx, ag_row in top_ag_sub.iterrows():
                            ag_name = ag_row['Travel Agency Name']
                            v_num = ag_row['Value']
                            g_html += f'<tr><td style="text-align:center;">{r_idx}위</td>'
                            g_html += f'<td style="text-align:center; font-weight:600;">{ag_name}</td>'
                            g_html += f'<td style="text-align:center; font-weight:700;">{v_num:,.0f}</td></tr>'

                        g_html += '</tbody></table></div>'
                        st.markdown(g_html, unsafe_allow_html=True)
        else:
            st.warning("선택된 조건의 단체 실적 데이터가 없습니다.")

# ==========================================
# GROUP 2: 🌐 6수송 대시보드
# ==========================================
elif selected_group == "🌐 6수송 대시보드":
    st.subheader("🌐 6수송 OD별 발매량, M/S 및 전년비(YoY) 분석 대시보드")
    
    if df_6th_raw is None:
        st.warning("👈 좌측 사이드바의 **[4. 6수송 데이터 (6TRF TEST.csv)]** 항목에 6수송 데이터 파일(CSV, XLSX, ZIP)을 업로드해 주세요.")
        
        in_tab_6th = st.file_uploader("📂 또는 여기에서 6수송 데이터 파일(CSV, XLSX, ZIP)을 업로드하세요:", type=['csv', 'xlsx', 'zip', 'parquet'], key="in_tab_6th_uploader")
        if in_tab_6th:
            df_6th_raw = load_smart_file(in_tab_6th)
        else:
            st.stop()

    @st.cache_data(max_entries=2, ttl=3600)
    def prepare_6th_freedom_dataset(df_in):
        if df_in is None or df_in.empty:
            return None, {}
            
        df_6_raw = df_in.copy()
        df_6_raw.columns = [str(c).strip() for c in df_6_raw.columns]
        
        col_map_6th = {
            'TRIP MONTH': ['TRIP MONTH', 'Travel Month', '출발 월', '출발 월 ', 'Trip Month', 'TRIP_MONTH', 'MONTH', 'Travel_Month'],
            '4.OD RGN': ['4.OD RGN', 'OD REGION', 'Region', 'OD 권역', '4. OD RGN', 'OD RGN', 'OD_REGION', '4.OD_RGN', 'ODREGION'],
            'DIRECTION': ['DIRECTION', 'Bound', 'Direction', 'DIR', 'BOUND'],
            'STOP OVER': ['STOP OVER', 'Stopover', 'Stops', 'STOPOVER', 'STOP_OVER'],
            'OD ON/OFF': ['O&D Market', 'OD Market', 'OD ON/OFF', 'OD Pair', 'O&D ON/OFF', 'OD_PAIR', 'O&D Pair', 'O&D', 'OD_NAME', 'O&D_NAME', 'OD ON-OFF', 'OD_ON_OFF'],
            'Sub-Route': ['Sub-Route', '소노선', 'Sub Route', 'SUB_ROUTE', 'SUBROUTE', '일본 APO', 'Japan Airport', 'Origin Code', 'Destination Code', 'JPN APO'],
            'ON/OFF 여부': ['JPN-해외', 'ON/OFF 여부', 'ON/OFF', 'ON_OFF', 'ON/OFF_여부'],
            '해외 APO': ['해외 APO', 'Overseas Airport', 'Foreign Airport', '해외APO', 'OVERSEAS_APO'],
            '항공사': ['Dominant Marketing Airline', 'Op Airline Code', 'Airline', '항공사', 'CARRIER', 'AIRLINE', 'Marketing Airline', 'Mkt Al', 'MKT_AL', 'DOMINANT_MARKETING_AIRLINE'],
            '금전구분': ['금/전', '금전구분', '구분', 'Year_Type', '금년/전년', 'YEAR_TYPE', 'CY_PY', '금년_전년']
        }

        def get_actual_col(df_curr, possible_names):
            for c in possible_names:
                if c in df_curr.columns:
                    return c
            return None

        actual_cols = {}
        for key, p_list in col_map_6th.items():
            actual_cols[key] = get_actual_col(df_6_raw, p_list)

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
            if not actual_cols['항공사']: actual_cols['항공사'] = df_6_raw.columns[1] if len(df_6_raw.columns) > 1 else df_6_raw.columns[0]

        val_col_candidates = ['Value', 'VALUE', 'Pax', 'PAX', '실적', '발매량', 'Seats', 'Flights']
        val_col_6 = None
        for vc in val_col_candidates:
            if vc in df_6_raw.columns:
                val_col_6 = vc
                break
        if not val_col_6:
            val_col_6 = df_6_raw.columns[-1]

        df_6_raw['Val_raw'] = pd.to_numeric(df_6_raw[val_col_6].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)

        month_col_6 = actual_cols['TRIP MONTH']
        year_type_col = actual_cols['금전구분']

        is_cy_mask = pd.Series(False, index=df_6_raw.index)
        is_py_mask = pd.Series(False, index=df_6_raw.index)

        if year_type_col and year_type_col in df_6_raw.columns:
            is_cy_mask |= df_6_raw[year_type_col].astype(str).str.contains('금년|CY|2026', na=False)
            is_py_mask |= df_6_raw[year_type_col].astype(str).str.contains('전년|PY|2025', na=False)

        if month_col_6 and month_col_6 in df_6_raw.columns:
            m_str = df_6_raw[month_col_6].astype(str).str.strip()
            is_cy_mask |= m_str.str.startswith('2026') | m_str.str.contains('2026|26년|26.', na=False)
            is_py_mask |= m_str.str.startswith('2025') | m_str.str.contains('2025|25년|25.', na=False)

        if not is_cy_mask.any() and not is_py_mask.any():
            is_cy_mask = pd.Series(True, index=df_6_raw.index)

        df_cy = df_6_raw[is_cy_mask].copy()
        df_cy['Val_num'] = df_cy['Val_raw']
        df_cy['Val_PY_num'] = 0.0

        df_py = df_6_raw[is_py_mask].copy()
        df_py['Val_num'] = 0.0
        df_py['Val_PY_num'] = df_py['Val_raw']

        if not df_cy.empty or not df_py.empty:
            df_out = pd.concat([df_cy, df_py], ignore_index=True)
        else:
            df_out = df_6_raw.copy()
            df_out['Val_num'] = df_out['Val_raw']
            df_out['Val_PY_num'] = df_out['Val_raw'] * 0.483

        return optimize_df(df_out), actual_cols

    df_6, actual_cols = prepare_6th_freedom_dataset(df_6th_raw)

    if df_6 is None or df_6.empty:
        st.warning("6수송 데이터를 파싱하지 못했습니다. 업로드된 파일의 형태를 확인해 주세요.")
        st.stop()

    al_col_6 = actual_cols['항공사']
    od_col_6 = actual_cols['OD ON/OFF']
    month_col_6 = actual_cols['TRIP MONTH']

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
    else:
        all_sub_6 = []

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
        # 📌 1. 항공사/O&D별 발매 M/S
        st.markdown('<div class="unified-sub-header">1. 항공사/O&D별 발매 M/S</div>', unsafe_allow_html=True)
        f1_col1, f1_col2, f1_col3, f1_col4 = st.columns(4)
        sel_1_month = render_slicer_box(f1_col1, "1. 출발월 (Trip Month)", all_raw_m, "slicer1_m")
        sel_1_region = render_slicer_box(f1_col2, "2. OD Region", all_reg_6, "slicer1_reg")
        sel_1_dir = render_slicer_box(f1_col3, "3. 일본발/일본행 (Direction)", all_dir_6, "slicer1_dir")
        sel_1_stop = render_slicer_box(f1_col4, "4. 경유/직항 (Stopover)", all_stop_6, "slicer1_stop")

        f1_col5, f1_col6, f1_col7, f1_col8 = st.columns(4)
        sel_1_onoff = render_slicer_box(f1_col5, "5. Online/Offline", all_onoff_6, "slicer1_onoff")
        sel_1_jp_route = render_slicer_box(f1_col6, "6. 일본공항 (Sub-Route)", all_sub_6, "slicer1_sub")
        sel_1_ov_apo = render_slicer_box(f1_col7, "7. 해외공항 (해외 APO)", all_ov_6, "slicer1_ov")

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
        else:
            dependent_od_list = sorted([str(x) for x in df_6[od_col_6].dropna().unique()]) if od_col_6 and od_col_6 in df_6.columns else []

        sel_1_od_mkt = render_slicer_box(f1_col8, "8. Trip O&D Market", dependent_od_list, "slicer1_od_mkt")

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

            html_table = '<div class="yoy-table-container"><table class="yoy-table">'
            html_table += '<thead><tr><th class="mkt-header" style="width:110px;">월별 M/S</th><th class="mkt-header" style="width:110px;">총합계</th>'
            
            for al_code in airline_rank_list:
                if al_code == 'KE':
                    html_table += f'<th class="ke-header" style="width:130px;">KE (대한항공 - {ke_rank}위)</th>'
                else:
                    rank_num = full_al_ranking.index(al_code) + 1 if al_code in full_al_ranking else "-"
                    html_table += f'<th class="carrier-header" style="width:110px;"><div style="font-size:10px; opacity:0.85;">{rank_num}위</div>{al_code}</th>'
            html_table += '</tr></thead><tbody>'

            t_curr = al_agg['Val_num'].sum()
            t_prev = al_agg['Val_PY_num'].sum()
            t_yoy_pct = ((t_curr - t_prev) / t_prev * 100) if t_prev > 0 else 0

            # ROW 1: 전체 발매
            html_table += '<tr class="row-title"><td>전체 발매</td>'
            html_table += f'<td><b>{t_curr:,.0f}</b></td>'
            for al_code in airline_rank_list:
                row_val = al_agg[al_agg[al_col_6] == al_code]['Val_num'].sum()
                html_table += f'<td><b>{row_val:,.0f}</b></td>'
            html_table += '</tr>'

            # ROW 2: YOY (발매)
            html_table += '<tr><td style="color:#64748b; font-weight:600;">YOY</td>'
            t_yoy_icon = f'<span class="yoy-up">▲ {t_yoy_pct:.0f}%</span>' if t_yoy_pct >= 0 else f'<span class="yoy-down">▼ {abs(t_yoy_pct):.0f}%</span>'
            html_table += f'<td>{t_yoy_icon if t_prev>0 else "-"}</td>'
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[al_col_6] == al_code]['Val_num'].sum()
                p_val = al_agg[al_agg[al_col_6] == al_code]['Val_PY_num'].sum()
                indiv_yoy = ((c_val - p_val) / p_val * 100) if p_val > 0 else 0
                icon_str = f'<span class="yoy-up">▲ {indiv_yoy:.0f}%</span>' if indiv_yoy >= 0 else f'<span class="yoy-down">▼ {abs(indiv_yoy):.0f}%</span>'
                html_table += f'<td>{icon_str if p_val>0 else "-"}</td>'
            html_table += '</tr>'

            # ROW 3: 전체 M/S
            html_table += '<tr class="row-title"><td>전체 M/S</td>'
            html_table += '<td><b>100%</b></td>'
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[al_col_6] == al_code]['Val_num'].sum()
                ms_val = (c_val / t_curr * 100) if t_curr > 0 else 0
                html_table += f'<td><b>{ms_val:.0f}%</b></td>'
            html_table += '</tr>'

            # ROW 4: YOY (M/S %p)
            html_table += '<tr class="row-ms-yoy"><td style="color:#64748b; font-weight:600;">YOY</td>'
            html_table += f'<td>{"▲ 0%p" if t_prev>0 else "-"}</td>'
            for al_code in airline_rank_list:
                c_val = al_agg[al_agg[al_col_6] == al_code]['Val_num'].sum()
                p_val = al_agg[al_agg[al_col_6] == al_code]['Val_PY_num'].sum()
                ms_c = (c_val / t_curr * 100) if t_curr > 0 else 0
                ms_p = (p_val / t_prev * 100) if t_prev > 0 else 0
                diff_p = ms_c - ms_p
                icon_p = f'<span class="yoy-up">▲ {diff_p:.0f}%p</span>' if diff_p >= 0 else f'<span class="yoy-down">▼ {abs(diff_p):.0f}%p</span>'
                html_table += f'<td>{icon_p if t_prev>0 and p_val>0 else "-"}</td>'
            html_table += '</tr>'

            html_table += '</tbody></table></div>'
            st.markdown(html_table, unsafe_allow_html=True)

        st.markdown("---")
        
        # 📌 2. 항공사별 상위 O&D
        st.markdown('<div class="unified-sub-header">2. 항공사별 상위 O&D</div>', unsafe_allow_html=True)
        f2_col1, f2_col2, f2_col3 = st.columns(3)
        sel_2_month = render_slicer_box(f2_col1, "1. 출발월 (Trip Month)", all_raw_m, "slicer2_m")
        sel_2_region = render_slicer_box(f2_col2, "2. OD Region", all_reg_6, "slicer2_reg")
        sel_2_dir = render_slicer_box(f2_col3, "3. 일본발/일본행 (Direction)", all_dir_6, "slicer2_dir")

        f2_col4, f2_col5 = st.columns(2)
        sel_2_stop = render_slicer_box(f2_col4, "4. 경유/직항 (Stopover)", all_stop_6, "slicer2_stop")
        selected_carrier = render_slicer_box(f2_col5, "5. 항공사 (Carrier) 선택", sorted_6th_airlines, "slicer2_carrier")

        display_carrier_label = selected_carrier if selected_carrier != ALL_OPTION else "전체 시장"

        mask_tab2 = filter_month_yoy(df_6, sel_2_month)
        if act_reg_c and act_reg_c in df_6.columns and sel_2_region != ALL_OPTION: mask_tab2 &= (df_6[act_reg_c].astype(str) == sel_2_region)
        if act_dir_c and act_dir_c in df_6.columns and sel_2_dir != ALL_OPTION: mask_tab2 &= (df_6[act_dir_c].astype(str) == sel_2_dir)
        if act_stop_c and act_stop_c in df_6.columns and sel_2_stop != ALL_OPTION: mask_tab2 &= (df_6[act_stop_c].astype(str) == sel_2_stop)

        df_mkt_full_2 = df_6[mask_tab2].copy()

        if not df_mkt_full_2.empty and od_col_6 and od_col_6 in df_mkt_full_2.columns and al_col_6 and al_col_6 in df_mkt_full_2.columns:

            if selected_carrier != ALL_OPTION:
                carrier_df_for_top = df_mkt_full_2[df_mkt_full_2[al_col_6].astype(str) == selected_carrier]
                if not carrier_df_for_top.empty:
                    od_totals = carrier_df_for_top.groupby(od_col_6, observed=False)['Val_num'].sum().reset_index()
                else:
                    od_totals = df_mkt_full_2.groupby(od_col_6, observed=False)['Val_num'].sum().reset_index()
            else:
                od_totals = df_mkt_full_2.groupby(od_col_6, observed=False)['Val_num'].sum().reset_index()

            od_totals = od_totals.sort_values(by='Val_num', ascending=False).head(30)
            top_od_list = [str(x) for x in od_totals[od_col_6].tolist() if pd.notnull(x)]

            df_top = df_mkt_full_2[df_mkt_full_2[od_col_6].astype(str).isin(top_od_list)].copy()

            if not df_top.empty and top_od_list:
                carrier_html = '<div class="yoy-table-container"><table class="yoy-table">'
                carrier_html += '<thead><tr>'
                carrier_html += '<th class="mkt-header" style="width:50px; text-align:center;" rowspan="2">순위</th>'
                carrier_html += '<th class="mkt-header" style="width:140px; text-align:center;" rowspan="2">TOP O&D Market</th>'
                
                carrier_html += '<th class="mkt-header" colspan="2" style="text-align:center;">시장 전체</th>'
                carrier_html += f'<th class="carrier-header" colspan="2" style="text-align:center;">선택 항공사 발매량 ({display_carrier_label})</th>'
                carrier_html += f'<th class="carrier-header" colspan="2" style="text-align:center;">선택 항공사 M/S ({display_carrier_label})</th>'
                carrier_html += '<th class="ke-header" colspan="2" style="text-align:center;">KE 발매량</th>'
                carrier_html += '<th class="ke-header" colspan="2" style="text-align:center;">KE M/S</th>'
                carrier_html += '</tr><tr>'
                
                carrier_html += '<th class="mkt-header" style="text-align:center;">26년</th><th class="mkt-header" style="text-align:center;">YOY</th>'
                carrier_html += '<th class="carrier-header" style="text-align:center;">26년</th><th class="carrier-header" style="text-align:center;">YOY</th>'
                carrier_html += '<th class="carrier-header" style="text-align:center;">M/S</th><th class="carrier-header" style="text-align:center;">YOY</th>'
                carrier_html += '<th class="ke-header" style="text-align:center;">26년</th><th class="ke-header" style="text-align:center;">YOY</th>'
                carrier_html += '<th class="ke-header" style="text-align:center;">M/S</th><th class="ke-header" style="text-align:center;">YOY</th>'
                carrier_html += '</tr></thead><tbody>'

                for idx, od_name in enumerate(top_od_list, start=1):
                    od_sub = df_top[df_top[od_col_6].astype(str) == od_name]
                    
                    # 1) 시장 전체 수치
                    m_cy = od_sub['Val_num'].sum()
                    m_py = od_sub['Val_PY_num'].sum()
                    m_yoy = ((m_cy - m_py) / m_py * 100) if m_py > 0 else 0
                    m_yoy_str = f'<span class="yoy-up">▲ {m_yoy:.0f}%</span>' if m_yoy >= 0 else f'<span class="yoy-down">▼ {abs(m_yoy):.0f}%</span>'

                    # 2) 선택 항공사 수치
                    if selected_carrier == ALL_OPTION:
                        c_sub = od_sub
                    else:
                        c_sub = od_sub[od_sub[al_col_6].astype(str) == selected_carrier]

                    c_cy = c_sub['Val_num'].sum()
                    c_py = c_sub['Val_PY_num'].sum()
                    c_yoy = ((c_cy - c_py) / c_py * 100) if c_py > 0 else 0
                    c_yoy_str = f'<span class="yoy-up">▲ {c_yoy:.0f}%</span>' if c_yoy >= 0 else f'<span class="yoy-down">▼ {abs(c_yoy):.0f}%</span>'

                    c_ms_cy = (c_cy / m_cy * 100) if m_cy > 0 else 0
                    c_ms_py = (c_py / m_py * 100) if m_py > 0 else 0
                    c_ms_diff = c_ms_cy - c_ms_py
                    c_ms_diff_str = f'<span class="yoy-up">▲ {c_ms_diff:.0f}%p</span>' if c_ms_diff >= 0 else f'<span class="yoy-down">▼ {abs(c_ms_diff):.0f}%p</span>'

                    # 3) KE 전용 수치
                    k_sub = od_sub[od_sub[al_col_6].astype(str) == 'KE']
                    k_cy = k_sub['Val_num'].sum()
                    k_py = k_sub['Val_PY_num'].sum()
                    k_yoy = ((k_cy - k_py) / k_py * 100) if k_py > 0 else 0
                    k_yoy_str = f'<span class="yoy-up">▲ {k_yoy:.0f}%</span>' if k_yoy >= 0 else f'<span class="yoy-down">▼ {abs(k_yoy):.0f}%</span>'

                    k_ms_cy = (k_cy / m_cy * 100) if m_cy > 0 else 0
                    k_ms_py = (k_py / m_py * 100) if m_py > 0 else 0
                    k_ms_diff = k_ms_cy - k_ms_py
                    k_ms_diff_str = f'<span class="yoy-up">▲ {k_ms_diff:.1f}%p</span>' if k_ms_diff >= 0 else f'<span class="yoy-down">▼ {abs(k_ms_diff):.1f}%p</span>'

                    carrier_html += f'<tr>'
                    carrier_html += f'<td style="text-align:center;">{idx}</td>'
                    carrier_html += f'<td style="font-weight:600; text-align:center;">{od_name}</td>'
                    carrier_html += f'<td style="text-align:center;"><b>{m_cy:,.0f}</b></td><td style="text-align:center;">{m_yoy_str if m_py>0 else "-"}</td>'
                    carrier_html += f'<td style="text-align:center;">{c_cy:,.0f}</td><td style="text-align:center;">{c_yoy_str if c_py>0 else "-"}</td>'
                    carrier_html += f'<td style="text-align:center;"><b>{c_ms_cy:.0f}%</b></td><td style="text-align:center;">{c_ms_diff_str if m_py>0 and c_py>0 else "-"}</td>'
                    k_cy_display = f"{k_cy:,.0f}" if k_cy > 0 else "-"
                    carrier_html += f'<td style="text-align:center;">{k_cy_display}</td><td style="text-align:center;">{k_yoy_str if k_cy>0 and k_py>0 else "-"}</td>'
                    carrier_html += f'<td style="text-align:center;"><b>{k_ms_cy:.1f}%</b></td><td style="text-align:center;">{k_ms_diff_str if m_py>0 and k_py>0 else "-"}</td>'
                    carrier_html += '</tr>'

                # TOP 30 요약행 (#efefef)
                tot_m_cy = df_top['Val_num'].sum()
                tot_m_py = df_top['Val_PY_num'].sum()
                tot_m_yoy = ((tot_m_cy - tot_m_py) / tot_m_py * 100) if tot_m_py > 0 else 0

                if selected_carrier == ALL_OPTION:
                    tot_c_sub = df_top
                else:
                    tot_c_sub = df_top[df_top[al_col_6].astype(str) == selected_carrier]

                tot_c_cy = tot_c_sub['Val_num'].sum()
                tot_c_py = tot_c_sub['Val_PY_num'].sum()
                tot_c_yoy = ((tot_c_cy - tot_c_py) / tot_c_py * 100) if tot_c_py > 0 else 0
                tot_c_ms_cy = (tot_c_cy / tot_m_cy * 100) if tot_m_cy > 0 else 0
                tot_c_ms_py = (tot_c_py / tot_m_py * 100) if tot_m_py > 0 else 0
                tot_c_ms_diff = tot_c_ms_cy - tot_c_ms_py

                tot_k_sub = df_top[df_top[al_col_6].astype(str) == 'KE']
                tot_k_cy = tot_k_sub['Val_num'].sum()
                tot_k_py = tot_k_sub['Val_PY_num'].sum()
                tot_k_yoy = ((tot_k_cy - tot_k_py) / tot_k_py * 100) if tot_k_py > 0 else 0
                tot_k_ms_cy = (tot_k_cy / tot_m_cy * 100) if tot_m_cy > 0 else 0
                tot_k_ms_py = (tot_k_py / tot_m_py * 100) if tot_m_py > 0 else 0
                tot_k_ms_diff = tot_k_ms_cy - tot_k_ms_py

                carrier_html += '<tr class="row-summary">'
                carrier_html += '<td colspan="2" style="text-align:center;">TOP 30 요약</td>'
                carrier_html += f'<td style="text-align:center;">{tot_m_cy:,.0f}</td><td style="text-align:center;">{"▲" if tot_m_yoy>=0 else "▼"} {abs(tot_m_yoy):.0f}%</td>'
                carrier_html += f'<td style="text-align:center;">{tot_c_cy:,.0f}</td><td style="text-align:center;">{"▲" if tot_c_yoy>=0 else "▼"} {abs(tot_c_yoy):.0f}%</td>'
                carrier_html += f'<td style="text-align:center;">{tot_c_ms_cy:.0f}%</td><td style="text-align:center;">{"▲" if tot_c_ms_diff>=0 else "▼"} {abs(tot_c_ms_diff):.0f}%p</td>'
                carrier_html += f'<td style="text-align:center;">{tot_k_cy:,.0f}</td><td style="text-align:center;">{"▲" if tot_k_yoy>=0 else "▼"} {abs(tot_k_yoy):.0f}%</td>'
                carrier_html += f'<td style="text-align:center;">{tot_k_ms_cy:.1f}%</td><td style="text-align:center;">{"▲" if tot_k_ms_diff>=0 else "▼"} {abs(tot_k_ms_diff):.1f}%p</td>'
                carrier_html += '</tr>'

                # 전체 시장 총합 (Market Total) 요약행 (#cccccc)
                mkt_all_cy = df_mkt_full_2['Val_num'].sum()
                mkt_all_py = df_mkt_full_2['Val_PY_num'].sum()
                mkt_all_yoy = ((mkt_all_cy - mkt_all_py) / mkt_all_py * 100) if mkt_all_py > 0 else 0

                if selected_carrier == ALL_OPTION:
                    mkt_c_sub = df_mkt_full_2
                else:
                    mkt_c_sub = df_mkt_full_2[df_mkt_full_2[al_col_6].astype(str) == selected_carrier]

                mkt_c_cy = mkt_c_sub['Val_num'].sum()
                mkt_c_py = mkt_c_sub['Val_PY_num'].sum()
                mkt_c_yoy = ((mkt_c_cy - mkt_c_py) / mkt_c_py * 100) if mkt_c_py > 0 else 0
                mkt_c_ms_cy = (mkt_c_cy / mkt_all_cy * 100) if mkt_all_cy > 0 else 0
                mkt_c_ms_py = (mkt_c_py / mkt_all_py * 100) if mkt_all_py > 0 else 0
                mkt_c_ms_diff = mkt_c_ms_cy - mkt_c_ms_py

                mkt_k_sub = df_mkt_full_2[df_mkt_full_2[al_col_6].astype(str) == 'KE']
                mkt_k_cy = mkt_k_sub['Val_num'].sum()
                mkt_k_py = mkt_k_sub['Val_PY_num'].sum()
                mkt_k_yoy = ((mkt_k_cy - mkt_k_py) / mkt_k_py * 100) if mkt_k_py > 0 else 0
                mkt_k_ms_cy = (mkt_k_cy / mkt_all_cy * 100) if mkt_all_cy > 0 else 0
                mkt_k_ms_py = (mkt_k_py / mkt_all_py * 100) if mkt_all_py > 0 else 0
                mkt_k_ms_diff = mkt_k_ms_cy - mkt_k_ms_py

                carrier_html += '<tr class="row-summary-market-total">'
                carrier_html += '<td colspan="2" style="text-align:center;">전체 시장 총합 (Market Total)</td>'
                carrier_html += f'<td style="text-align:center;"><b>{mkt_all_cy:,.0f}</b></td><td style="text-align:center;">{"▲" if mkt_all_yoy>=0 else "▼"} {abs(mkt_all_yoy):.0f}%</td>'
                carrier_html += f'<td style="text-align:center;"><b>{mkt_c_cy:,.0f}</b></td><td style="text-align:center;">{"▲" if mkt_c_yoy>=0 else "▼"} {abs(mkt_c_yoy):.0f}%</td>'
                carrier_html += f'<td style="text-align:center;"><b>{mkt_c_ms_cy:.0f}%</b></td><td style="text-align:center;">{"▲" if mkt_c_ms_diff>=0 else "▼"} {abs(mkt_c_ms_diff):.0f}%p</td>'
                carrier_html += f'<td style="text-align:center;"><b>{mkt_k_cy:,.0f}</b></td><td style="text-align:center;">{"▲" if mkt_k_yoy>=0 else "▼"} {abs(mkt_k_yoy):.0f}%</td>'
                carrier_html += f'<td style="text-align:center;"><b>{mkt_k_ms_cy:.1f}%</b></td><td style="text-align:center;">{"▲" if mkt_k_ms_diff>=0 else "▼"} {abs(mkt_k_ms_diff):.1f}%p</td>'
                carrier_html += '</tr>'

                carrier_html += '</tbody></table></div>'
                st.markdown(carrier_html, unsafe_allow_html=True)
            else:
                st.warning("선택된 조건의 TOP 30 O&D 데이터가 없습니다.")
        else:
            st.warning("6수송 데이터에서 O&D 또는 항공사 필드를 탐색 중입니다. 좌측 사이드바에서 [4. 6수송 데이터] 업로드 상태를 확인해 주세요.")

    with tab6_2:
        st.markdown("*(속도 최적화를 위해 상위 100건만 표출합니다)*")
        st.dataframe(df_6.head(100), width="stretch")

# ==========================================
# GROUP 3: 🔗 W26 연결 네트워크 (외부 연동)
# ==========================================
else:
    st.markdown('<div class="unified-sub-header">🔗 대한항공 W26 연결 네트워크 외부 연동 시스템</div>', unsafe_allow_html=True)
    st.iframe(EXT_WEB_APP_URL, height=850)