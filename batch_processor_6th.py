# batch_processor_6th.py
import pandas as pd
import numpy as np
import os
import glob
import sys
import time

def extract_pure_month(val):
    if pd.isna(val): return ""
    s = str(val).replace('-', '').replace('.', '').replace('/', '').replace('월', '').strip()
    if len(s) >= 6 and s.isdigit(): return s[4:6].zfill(2)
    elif len(s) == 4 and s.isdigit(): return s[2:4].zfill(2)
    elif len(s) <= 2 and s.isdigit(): return s.zfill(2)
    return s

def find_column_by_candidates(columns, candidates):
    for c in columns:
        cleaned_col = str(c).lower().replace(" ", "").replace("_", "").replace(".", "")
        for cand in candidates:
            if cand in cleaned_col:
                return c
    return None

def process_and_create_6th_parquet():
    start_time = time.time()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 70)
    print("🚀 [6수송 파케 생성기] 파생 변수(OD/직항/방향) 자동 생성판")
    print("=" * 70)

    all_files = glob.glob(os.path.join(base_dir, "*.csv")) + glob.glob(os.path.join(base_dir, "*.xlsx"))
    
    cy_files, py_files = [], []
    for f_path in all_files:
        fname = os.path.basename(f_path)
        fname_upper = fname.upper() 
        
        if "cache" in fname or "공급" in fname or "~$" in fname or "OD" in fname_upper or "매핑" in fname:
            continue
            
        if "금년" in fname or "CY" in fname_upper:
            cy_files.append(f_path)
        elif "전년" in fname or "PY" in fname_upper:
            py_files.append(f_path)

    df_list = []

    print(f"\n📂 [1/3] 금년(CY) 파일 로드... ({len(cy_files)}개)")
    for f_path in cy_files:
        fname = os.path.basename(f_path)
        try:
            df = pd.read_excel(f_path) if f_path.endswith(('.xlsx', '.xls')) else pd.read_csv(f_path, low_memory=False)
            df.columns = [str(c).strip() for c in df.columns]
            df['금년/전년'] = '금년'
            df['발매_연도구분'] = '금년 발매'
            df['출발_연도구분'] = '금년 출발'
            df_list.append(df)
            print(f"  ├─ 🟢 성공: {fname} ({len(df):,}행)")
        except Exception as e:
            print(f"  ├─ ❌ 실패: {fname} | {e}")

    print(f"\n📂 [2/3] 전년(PY) 파일 로드... ({len(py_files)}개)")
    for f_path in py_files:
        fname = os.path.basename(f_path)
        try:
            df = pd.read_excel(f_path) if f_path.endswith(('.xlsx', '.xls')) else pd.read_csv(f_path, low_memory=False)
            df.columns = [str(c).strip() for c in df.columns]
            df['금년/전년'] = '전년'
            df['발매_연도구분'] = '전년 발매'
            df['출발_연도구분'] = '전년 출발'
            df_list.append(df)
            print(f"  ├─ 🟢 성공: {fname} ({len(df):,}행)")
        except Exception as e:
            print(f"  ├─ ❌ 실패: {fname} | {e}")

    if not df_list:
        print("\n❌ 원천 CSV/XLSX 파일을 찾지 못했습니다.")
        sys.exit(1)

    print("\n⚙️ [3/3] 데이터 병합 및 표준화 중...")
    df_merged = pd.concat(df_list, ignore_index=True)

    # =========================================================================
    # 🌟 [파생 변수 자동 생성 로직] 🌟
    # =========================================================================
    print("🛠 파생 컬럼(OD Region, Direction, 직항/경유) 자동 생성 중...")

    # [1] DIRECTION (일본발 / 일본행)
    if 'Trip Origin Country Code' in df_merged.columns:
        df_merged['DIRECTION'] = np.where(
            df_merged['Trip Origin Country Code'].astype(str).str.strip().str.upper() == 'JP',
            '일본발', 
            '일본행'
        )

    # [2] 직항/경유 분류 로직
    # 6수송 기준, 한국 국적기(KE, OZ 등)나 제3국 환승 특화 항공사가 일본-해외 노선을 운항하면 '경유'
    if 'Dominant Marketing Airline' in df_merged.columns:
        transit_carriers = ['KE', 'OZ', '7C', 'LJ', 'TW', 'BX', 'RS', 'CI', 'BR', 'CX', 'SQ', 'TG', 'PR', 'VN']
        df_merged['직항/경유'] = np.where(df_merged['Dominant Marketing Airline'].astype(str).str.strip().str.upper().isin(transit_carriers), '경유', '직항')

    # [3] 4.OD RGN (해외 국가 코드 기반 자동 대륙 매핑)
    if 'Trip Destination Country Code' in df_merged.columns and 'Trip Origin Country Code' in df_merged.columns:
        df_merged['Overseas_Country'] = np.where(
            df_merged['Trip Origin Country Code'].astype(str).str.strip().str.upper() == 'JP',
            df_merged['Trip Destination Country Code'],
            df_merged['Trip Origin Country Code']
        )
        
        def assign_region(cc):
            cc = str(cc).upper().strip()
            if cc in ['US', 'CA', 'MX', 'BR']: return '미주'
            elif cc in ['GB', 'FR', 'DE', 'IT', 'ES', 'NL', 'CH', 'TR', 'RU', 'AT', 'CZ', 'FI']: return '구주'
            elif cc in ['CN', 'HK', 'MO', 'TW']: return '중국'
            elif cc in ['VN', 'TH', 'SG', 'PH', 'MY', 'ID', 'KH', 'MM', 'IN']: return '동남아'
            elif cc in ['AU', 'NZ', 'GU', 'SP']: return '대양주'
            else: return '기타'
            
        df_merged['4.OD RGN'] = df_merged['Overseas_Country'].apply(assign_region)
    # =========================================================================

    col_pur_m = find_column_by_candidates(df_merged.columns, ["ticketpurchasemonth", "purchasemonth", "발매월", "발매일자", "issuemonth"])
    col_trip_m = find_column_by_candidates(df_merged.columns, ["tripmonth", "travelmonth", "출발월", "출발일자", "depmonth"])
    col_val = find_column_by_candidates(df_merged.columns, ["value", "pax", "수송량", "발매량", "실적"])

    if col_pur_m and col_pur_m != 'Ticket Purchase month':
        df_merged['Ticket Purchase month'] = df_merged[col_pur_m]
    if col_trip_m and col_trip_m != 'Trip Month':
        df_merged['Trip Month'] = df_merged[col_trip_m]

    df_merged['Pur_M_Norm'] = df_merged['Ticket Purchase month'].apply(extract_pure_month) if 'Ticket Purchase month' in df_merged.columns else ""
    df_merged['Trip_M_Norm'] = df_merged['Trip Month'].apply(extract_pure_month) if 'Trip Month' in df_merged.columns else ""

    if col_val:
        df_merged['Value'] = pd.to_numeric(
            df_merged[col_val].astype(str).str.replace(',', '').str.strip(), 
            errors='coerce'
        ).fillna(0.0)

    for col in df_merged.columns:
        if str(df_merged[col].dtype) == 'category' or df_merged[col].dtype == 'object':
            df_merged[col] = df_merged[col].astype(str).fillna('')
        elif 'int' in str(df_merged[col].dtype):
            df_merged[col] = df_merged[col].fillna(0).astype('int64')
        elif 'float' in str(df_merged[col].dtype):
            df_merged[col] = df_merged[col].fillna(0.0).astype('float64')

    group_cols = [
        'Ticket Purchase month', 'Trip Month', '4.OD RGN', 'DIRECTION', 
        '직항/경유', 'Trip Origin Country Code', 'Trip Destination Country Code', 
        '일본 APO', '해외 APO', 'Trip O&D', 'Trip O&D Market', 
        'Dominant Marketing Airline', '금년/전년', '발매_연도구분', '출발_연도구분',
        'Pur_M_Norm', 'Trip_M_Norm'
    ]
    existing_cols = [c for c in group_cols if c in df_merged.columns]
    
    if 'Value' in df_merged.columns and existing_cols:
        df_final = df_merged.groupby(existing_cols, observed=False, dropna=False, as_index=False)['Value'].sum()
    else:
        df_final = df_merged

    output_path = os.path.join(base_dir, "cache_6th_data.parquet")
    temp_path = os.path.join(base_dir, "cache_6th_data_tmp.parquet")
    
    df_final.to_parquet(temp_path, engine='pyarrow', index=False)
    
    if os.path.exists(output_path):
        try: os.remove(output_path)
        except: pass
    os.rename(temp_path, output_path)

    cy_cnt = len(df_final[df_final['금년/전년'] == '금년'])
    py_cnt = len(df_final[df_final['금년/전년'] == '전년'])

    print("\n" + "=" * 70)
    print(f"🎉 성공적으로 파케 파일이 재생성되었습니다!")
    print(f"📊 총 레코드 수: {len(df_final):,} 행")
    print(f"  ├─ 금년(CY) 행: {cy_cnt:,} 행")
    print(f"  └─ 전년(PY) 행: {py_cnt:,} 행")
    print(f"⏱ 소요시간: {time.time() - start_time:.2f}초")
    print("=" * 70)

if __name__ == "__main__":
    process_and_create_6th_parquet()