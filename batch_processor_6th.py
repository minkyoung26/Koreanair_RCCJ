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
    print("🚀 [6수송 캐시 파켓 생성기] 데이터 완전 검증 배치 실행")
    print("=" * 70)

    # 폴더 내 모든 csv, xlsx 파일 검색
    all_csv_xlsx = glob.glob(os.path.join(base_dir, "*.csv")) + glob.glob(os.path.join(base_dir, "*.xlsx"))
    
    cy_files, py_files, uncategorized_files = [], [], []

    for f_path in all_csv_xlsx:
        fname = os.path.basename(f_path)
        if "cache" in fname or "공급" in fname or "~$" in fname:
            continue
            
        fname_upper = fname.upper()
        if "금년" in fname or "CY" in fname_upper or "2026" in fname:
            cy_files.append(f_path)
        elif "전년" in fname or "PY" in fname_upper or "2025" in fname:
            py_files.append(f_path)
        elif "6수송" in fname or "6TH" in fname_upper:
            uncategorized_files.append(f_path)

    df_cy_list, df_py_list = [], []

    # 1. 금년 파일 로드
    print(f"\n📂 [1/3] 금년(CY) 후보 파일 로드 중... ({len(cy_files)}개)")
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

    # 2. 전년 파일 로드
    print(f"\n📂 [2/3] 전년(PY) 후보 파일 로드 중... ({len(py_files)}개)")
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

    # 구분되지 않은 6수송 파일 Fallback 로드
    if not df_cy_list and not df_py_list and uncategorized_files:
        print(f"\n🔍 명시적 파일 미발견 -> 미구분 6수송 파일 로드 시도... ({len(uncategorized_files)}개)")
        for f_path in uncategorized_files:
            fname = os.path.basename(f_path)
            try:
                df = pd.read_excel(f_path) if f_path.endswith(('.xlsx', '.xls')) else pd.read_csv(f_path, low_memory=False)
                df.columns = [str(c).strip() for c in df.columns]
                df['금년/전년'] = '금년'
                df['발매_연도구분'] = '금년 발매'
                df['출발_연도구분'] = '금년 출발'
                df['source_file'] = fname
                df_cy_list.append(df)
                print(f"  ├─ 🟢 일반 로드 성공: {fname} ({len(df):,}행)")
            except Exception as e:
                print(f"  ├─ ❌ 일반 로드 실패: {fname} | {e}")

    if not df_cy_list and not df_py_list:
        print("\n❌ [비상 오류] 로드된 데이터가 0행입니다! 폴더 안의 CSV/XLSX 파일명을 확인하세요.")
        sys.exit(1)

    # 3. 병합 및 칼럼 정제
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

    # 객체형/Category형을 순수 표준 문자열로 안전 고정
    for col in df_merged.columns:
        if str(df_merged[col].dtype) == 'category' or df_merged[col].dtype == 'object':
            df_merged[col] = df_merged[col].astype(str).fillna('')

    output_path = os.path.join(base_dir, "cache_6th_data.parquet")
    df_merged.to_parquet(output_path, engine='pyarrow', index=False)

    print("\n" + "=" * 70)
    print(f"🎉 성공적으로 [cache_6th_data.parquet] 완벽 저장 완료!")
    print(f"📊 저장된 총 행 수: {len(df_merged):,} 행")
    print(f"📍 저장 위치: {output_path}")
    print("=" * 70)

if __name__ == "__main__":
    process_and_create_6th_parquet()