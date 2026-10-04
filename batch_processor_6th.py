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
    print("🚀 [6수송 파케 생성기] Dimension 매핑 로직 완벽 복원판")
    print("=" * 70)

    all_files = glob.glob(os.path.join(base_dir, "*.csv")) + glob.glob(os.path.join(base_dir, "*.xlsx"))
    
    cy_files, py_files = [], []
    for f_path in all_files:
        fname = os.path.basename(f_path)
        fname_upper = fname.upper() 
        
        # 원천 데이터 헌팅 (Dimension, Cache 등 제외)
        if "CACHE" in fname_upper or "공급" in fname or "~$" in fname or "DIMENSION" in fname_upper or "디멘전" in fname or "매핑" in fname:
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

    print("\n⚙️ [3/4] 원천 데이터 1차 병합 중...")
    df_merged = pd.concat(df_list, ignore_index=True)

    # =========================================================================
    # 🌟 [핵심 복원] Dimension 파일 자동 탐색 및 병합 로직 🌟
    # =========================================================================
    print("\n🔗 [파생 변수 생성] Dimension 파일 매핑 중...")
    dim_files = [f for f in all_files if "DIMENSION" in os.path.basename(f).upper() or "디멘전" in os.path.basename(f) or "매핑" in os.path.basename(f)]
    
    if dim_files:
        dim_path = dim_files[0]
        print(f"  ├─ Dimension 파일 발견: {os.path.basename(dim_path)}")
        df_dim = pd.read_excel(dim_path) if dim_path.endswith(('.xlsx', '.xls')) else pd.read_csv(dim_path)
        df_dim.columns = [str(c).strip() for c in df_dim.columns]
        
        # 매핑 기준 키(Key) 찾기: 원천과 Dimension 파일에 공통으로 있는 컬럼 기준 병합
        common_cols = list(set(df_merged.columns) & set(df_dim.columns))
        
        if common_cols:
            print(f"  ├─ 매핑 기준 컬럼(Key): {common_cols}")
            df_merged = pd.merge(df_merged, df_dim, on=common_cols, how='left')
            print("  ├─ 🟢 OD Region (JPN-EUR 등), 직항/경유 매핑 완벽 적용!")
        else:
            print("  ├─ ❌ 오류: 원천 데이터와 Dimension 파일 간 공통 컬럼(이름)이 없습니다.")
            print(f"     - 원천 데이터 컬럼 예시: {list(df_merged.columns)[:5]}")
            print(f"     - Dimension 컬럼 예시: {list(df_dim.columns)}")
    else:
        print("  ├─ ⚠ 폴더에 Dimension 파일이 없어 매핑을 건너뜁니다.")

    # DIRECTION (일본발/행) 컬럼이 Dimension에 없고 누락되었을 경우를 대비한 자동 생성
    if 'Trip Origin Country Code' in df_merged.columns and 'DIRECTION' not in df_merged.columns and 'Direction' not in df_merged.columns:
        df_merged['DIRECTION'] = np.where(
            df_merged['Trip Origin Country Code'].astype(str).str.strip().str.upper() == 'JP',
            '일본발', '일본행'
        )
    # =========================================================================

    print("\n⚙️ [4/4] 최종 표준화 및 파케 파일 생성 중...")
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

    # 그룹화 키 (Dimension 병합으로 생겨난 파생 컬럼들 모두 포함)
    group_cols = [
        'Ticket Purchase month', 'Trip Month', '4.OD RGN', 'OD Region', 'DIRECTION', 'Direction', 
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