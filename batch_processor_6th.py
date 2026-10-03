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
    print("🚀 [배치 프로세서] cache_6th_data.parquet 안정화 생성")
    print("=" * 70)

    cy_patterns = ["*6수송*금년*.csv", "*6수송*금년*.xlsx", "*6th*CY*.csv", "*6th*CY*.xlsx", "*금년*6수송*.csv"]
    py_patterns = ["*6수송*전년*.csv", "*6수송*전년*.xlsx", "*6th*PY*.csv", "*6th*PY*.xlsx", "*전년*6수송*.csv"]
    
    cy_files, py_files = [], []
    for pat in cy_patterns: cy_files.extend(glob.glob(os.path.join(base_dir, pat)))
    for pat in py_patterns: py_files.extend(glob.glob(os.path.join(base_dir, pat)))
    
    cy_files = sorted(list(set(cy_files)))
    py_files = sorted(list(set(py_files)))

    df_cy_list, df_py_list = [], []

    print(f"\n📂 [1/4] 금년(CY) 데이터 로드... ({len(cy_files)}개)")
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
            print(f"  ├─ 🟢 성공: {fname} ({len(df):,}행)")
        except Exception as e:
            print(f"  ├─ ❌ 실패: {fname} | {e}")

    print(f"\n📂 [2/4] 전년(PY) 데이터 로드... ({len(py_files)}개)")
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
            print(f"  ├─ 🟢 성공: {fname} ({len(df):,}행)")
        except Exception as e:
            print(f"  ├─ ❌ 실패: {fname} | {e}")

    if not df_cy_list and not df_py_list:
        print("\n❌ 원천 CSV/XLSX 파일을 찾지 못했습니다.")
        sys.exit(1)

    print("\n⚙️ [3/4] 데이터 통합 및 키 칼럼 표준화...")
    df_merged = pd.concat(df_cy_list + df_py_list, ignore_index=True)

    col_pur_m = find_column_by_candidates(df_merged.columns, ["ticketpurchasemonth", "purchasemonth", "발매월", "발매일자", "issuemonth"])
    col_trip_m = find_column_by_candidates(df_merged.columns, ["tripmonth", "travelmonth", "출발월", "출발일자", "depmonth"])
    col_val = find_column_by_candidates(df_merged.columns, ["value", "pax", "수송량", "발매량", "실적"])

    if col_pur_m and col_pur_m != 'Ticket Purchase month':
        df_merged['Ticket Purchase month'] = df_merged[col_pur_m]
    if col_trip_m and col_trip_m != 'Trip Month':
        df_merged['Trip Month'] = df_merged[col_trip_m]

    df_merged['Pur_YM_Key'] = df_merged['Ticket Purchase month'].apply(normalize_ym_key) if 'Ticket Purchase month' in df_merged.columns else ""
    df_merged['Trip_YM_Key'] = df_merged['Trip Month'].apply(normalize_ym_key) if 'Trip Month' in df_merged.columns else ""

    if col_val:
        df_merged['Value'] = pd.to_numeric(
            df_merged[col_val].astype(str).str.replace(',', '').str.strip(), 
            errors='coerce'
        ).fillna(0.0)

    # 🔥 [핵심] Streamlit Crash 차단: Category 타입을 절대 사용하지 않도록 강제 변환
    print("\n💾 [4/4] 안전한 데이터 타입 변환 및 Parquet 생성...")
    for col in df_merged.columns:
        if str(df_merged[col].dtype) == 'category' or df_merged[col].dtype == 'object':
            df_merged[col] = df_merged[col].astype(str).fillna('')
        elif 'int' in str(df_merged[col].dtype):
            df_merged[col] = df_merged[col].fillna(0).astype('int64')
        elif 'float' in str(df_merged[col].dtype):
            df_merged[col] = df_merged[col].fillna(0.0).astype('float64')

    output_path = os.path.join(base_dir, "cache_6th_data.parquet")
    
    # 기존 파케 파일이 켜져있을 때의 Lock 방지를 위해 원자적 파일 교체
    temp_output_path = os.path.join(base_dir, "cache_6th_data_temp.parquet")
    df_merged.to_parquet(temp_output_path, engine='pyarrow', index=False)
    
    if os.path.exists(output_path):
        try: os.remove(output_path)
        except: pass
    os.rename(temp_output_path, output_path)

    print("\n" + "=" * 70)
    print(f"🎉 Parquet 파일 생성 완료! (소요 시간: {time.time() - start_time:.2f}초)")
    print(f"📊 총 {len(df_merged):,} 행 저장됨")
    print("=" * 70)

if __name__ == "__main__":
    process_and_create_6th_parquet()