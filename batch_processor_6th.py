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
    print("🚀 [배치 프로세서] 6수송 cache_6th_data.parquet 안정화 가공 시작")
    print("=" * 70)

    # 1. 파일 검색 (경로 내 원천 파일 싹 뒤지기)
    all_files = glob.glob(os.path.join(base_dir, "*.csv")) + glob.glob(os.path.join(base_dir, "*.xlsx"))
    
    cy_files, py_files = [], []
    for f_path in all_files:
        fname = os.path.basename(f_path)
        if "cache" in fname or "공급" in fname or "~$" in fname:
            continue
        fname_upper = fname.upper()
        if "금년" in fname or "CY" in fname_upper or "2026" in fname:
            cy_files.append(f_path)
        elif "전년" in fname or "PY" in fname_upper or "2025" in fname:
            py_files.append(f_path)

    df_cy_list, df_py_list = [], []

    # 2. 금년 데이터 읽기 & 명시적 태깅
    print(f"\n📂 [1/3] 금년(CY) 데이터 로드 중... ({len(cy_files)}개 파일)")
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
            print(f"  ├─ ❌ 금년 로드 실패: {fname} | {e}")

    # 3. 전년 데이터 읽기 & 명시적 태깅
    print(f"\n📂 [2/3] 전년(PY) 데이터 로드 중... ({len(py_files)}개 파일)")
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
            print(f"  ├─ ❌ 전년 로드 실패: {fname} | {e}")

    if not df_cy_list and not df_py_list:
        print("\n❌ 원천 CSV/XLSX 파일이 인식되지 않았습니다. 파일명을 확인해주세요.")
        sys.exit(1)

    # 4. 데이터 통합 및 주요 키 칼럼 정제
    print("\n⚙️ [3/3] 데이터 통합 및 파케 변환 중...")
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

    # 🔥 [중요] Streamlit Oh no 크래시 원인 차단: Category 변환을 아예 없애고 일반 dtype 유지
    for col in df_merged.columns:
        if str(df_merged[col].dtype) == 'category' or df_merged[col].dtype == 'object':
            df_merged[col] = df_merged[col].astype(str).fillna('')

    output_path = os.path.join(base_dir, "cache_6th_data.parquet")
    
    # 파일 잠금(Lock) 에러 방지를 위해 임시 파일 생성 후 교체
    temp_path = os.path.join(base_dir, "cache_6th_data_tmp.parquet")
    df_merged.to_parquet(temp_path, engine='pyarrow', index=False)
    
    if os.path.exists(output_path):
        try: os.remove(output_path)
        except: pass
    os.rename(temp_path, output_path)

    print("\n" + "=" * 70)
    print(f"🎉 성공적으로 [cache_6th_data.parquet] 생성 완료!")
    print(f"📊 저장된 총 레코드 수: {len(df_merged):,} 행")
    print(f"⏱️ 소요시간: {time.time() - start_time:.2f}초")
    print("=" * 70)

if __name__ == "__main__":
    process_and_create_6th_parquet()