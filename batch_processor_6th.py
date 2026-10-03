# batch_processor_6th.py
import pandas as pd
import numpy as np
import os
import glob
import sys
import time

def normalize_ym_key(val_str):
    if pd.isna(val_str):
        return ""
    s = str(val_str).replace('-', '').replace('.', '').replace('/', '').replace('월', '').strip()
    return s[:6] if len(s) >= 6 and s[:6].isdigit() else ""

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
    print("🚀 [배치 프로세서] 6수송 데이터 통합 및 cache_6th_data.parquet 생성")
    print("=" * 70)

    cy_patterns = ["*6수송*금년*.csv", "*6수송*금년*.xlsx", "*6th*CY*.csv", "*6th*CY*.xlsx", "*금년*6수송*.csv"]
    py_patterns = ["*6수송*전년*.csv", "*6수송*전년*.xlsx", "*6th*PY*.csv", "*6th*PY*.xlsx", "*전년*6수송*.csv"]
    
    cy_files, py_files = [], []
    for pat in cy_patterns: cy_files.extend(glob.glob(os.path.join(base_dir, pat)))
    for pat in py_patterns: py_files.extend(glob.glob(os.path.join(base_dir, pat)))
    
    cy_files = sorted(list(set(cy_files)))
    py_files = sorted(list(set(py_files)))

    df_cy_list, df_py_list = [], []

    print(f"\n📂 [1/4] 금년(CY) 원천 데이터 로드 중... (파일 {len(cy_files)}개)")
    for f_path in cy_files:
        fname = os.path.basename(f_path)
        try:
            df = pd.read_excel(f_path) if f_path.endswith(('.xlsx', '.xls')) else pd.read_csv(f_path, low_memory=False)
            df.columns = [str(c).strip() for c in df.columns]
            
            df['금년/전년'] = '금년'
            df['발매_연도구분'] = '금년 발매'
            df['출발_연도구분'] = '금년 출발'
            df['source_file'] = fname
            df_cy_list.append(df)
            print(f"  ├─ 🟢 금년 로드 성공: {fname} ({len(df):,}행)")
        except Exception as e:
            print(f"  ├─ ❌ 실패: {fname} | 오류: {e}")

    print(f"\n📂 [2/4] 전년(PY) 원천 데이터 로드 중... (파일 {len(py_files)}개)")
    for f_path in py_files:
        fname = os.path.basename(f_path)
        try:
            df = pd.read_excel(f_path) if f_path.endswith(('.xlsx', '.xls')) else pd.read_csv(f_path, low_memory=False)
            df.columns = [str(c).strip() for c in df.columns]
            
            df['금년/전년'] = '전년'
            df['발매_연도구분'] = '전년 발매'
            df['출발_연도구분'] = '전년 출발'
            df['source_file'] = fname
            df_py_list.append(df)
            print(f"  ├─ 🟢 전년 로드 성공: {fname} ({len(df):,}행)")
        except Exception as e:
            print(f"  ├─ ❌ 실패: {fname} | 오류: {e}")

    if not df_cy_list and not df_py_list:
        print("\n❌ 원천 파일을 찾을 수 없습니다. 파일명을 확인해 주세요.")
        sys.exit(1)

    print("\n⚙️ [3/4] 데이터 병합 및 유연한 컬럼 인식 로직 실행 중...")
    df_merged = pd.concat(df_cy_list + df_py_list, ignore_index=True)

    # 유연한 컬럼명 감지
    col_pur_m = find_column_by_candidates(df_merged.columns, ["ticketpurchasemonth", "purchasemonth", "발매월", "발매일자", "issuemonth"])
    col_trip_m = find_column_by_candidates(df_merged.columns, ["tripmonth", "travelmonth", "출발월", "출발일자", "depmonth"])
    col_val = find_column_by_candidates(df_merged.columns, ["value", "pax", "수송량", "발매량", "실적"])

    if col_pur_m:
        df_merged['Ticket Purchase month'] = df_merged[col_pur_m]
        df_merged['Pur_YM_Key'] = df_merged[col_pur_m].apply(normalize_ym_key)
    else:
        df_merged['Pur_YM_Key'] = ""

    if col_trip_m:
        df_merged['Trip Month'] = df_merged[col_trip_m]
        df_merged['Trip_YM_Key'] = df_merged[col_trip_m].apply(normalize_ym_key)
    else:
        df_merged['Trip_YM_Key'] = ""

    if col_val:
        df_merged['Value'] = pd.to_numeric(df_merged[col_val].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0.0)

    print("\n💾 [4/4] Parquet 최적화 및 저장 중...")
    for col in df_merged.columns:
        if df_merged[col].dtype == 'object':
            if df_merged[col].nunique() < len(df_merged) * 0.5:
                df_merged[col] = df_merged[col].astype('category')
        elif df_merged[col].dtype == 'int64':
            df_merged[col] = df_merged[col].astype('int32')
        elif df_merged[col].dtype == 'float64':
            df_merged[col] = df_merged[col].astype('float32')

    output_path = os.path.join(base_dir, "cache_6th_data.parquet")
    df_merged.to_parquet(output_path, engine='pyarrow', index=False)

    print("\n" + "=" * 70)
    print(f"🎉 성공적으로 Parquet 생성 완료! (소요 시간: {time.time() - start_time:.2f}초)")
    print(f"📊 총 레코드 수: {len(df_merged):,} 행")
    print(f"📍 저장 경로: {output_path}")
    print("=" * 70)

if __name__ == "__main__":
    process_and_create_6th_parquet()