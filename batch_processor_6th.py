# batch_processor_6th.py
import pandas as pd
import numpy as np
import os
import glob
import sys
import time

def normalize_ym_key(val_str):
    """
    날짜/월 텍스트에서 숫자만 추출하여 6자리 표준 연월 키(YYYYMM) 생성
    """
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
    print("🚀 [6수송 캐시 생성기] cache_6th_data.parquet 안정화 파이프라인")
    print("=" * 70)

    # 1. 파일 검색 패턴 설정
    cy_patterns = ["*6수송*금년*.csv", "*6수송*금년*.xlsx", "*6th*CY*.csv", "*6th*CY*.xlsx", "*금년*6수송*.csv"]
    py_patterns = ["*6수송*전년*.csv", "*6수송*전년*.xlsx", "*6th*PY*.csv", "*6th*PY*.xlsx", "*전년*6수송*.csv"]
    
    cy_files, py_files = [], []
    for pat in cy_patterns: cy_files.extend(glob.glob(os.path.join(base_dir, pat)))
    for pat in py_patterns: py_files.extend(glob.glob(os.path.join(base_dir, pat)))
    
    cy_files = sorted(list(set(cy_files)))
    py_files = sorted(list(set(py_files)))

    df_cy_list, df_py_list = [], []

    # 2. 금년(CY) 데이터 로드 및 명시적 구분 필드 태깅
    print(f"\n📂 [1/4] 금년(CY) 데이터 로드 중... (파일 {len(cy_files)}개)")
    for f_path in cy_files:
        fname = os.path.basename(f_path)
        try:
            df = pd.read_excel(f_path) if f_path.endswith(('.xlsx', '.xls')) else pd.read_csv(f_path, low_memory=False)
            df.columns = [str(c).strip() for c in df.columns]
            
            # 🔥 파일 출처 기반 명시적 전용 필드 태깅
            df['금년/전년'] = '금년'
            df['발매_연도구분'] = '금년 발매'
            df['출발_연도구분'] = '금년 출발'
            df['source_file'] = fname
            df_cy_list.append(df)
            print(f"  ├─ 🟢 성공: {fname} ({len(df):,}행)")
        except Exception as e:
            print(f"  ├─ ❌ 실패: {fname} | {e}")

    # 3. 전년(PY) 데이터 로드 및 명시적 구분 필드 태깅
    print(f"\n📂 [2/4] 전년(PY) 데이터 로드 중... (파일 {len(py_files)}개)")
    for f_path in py_files:
        fname = os.path.basename(f_path)
        try:
            df = pd.read_excel(f_path) if f_path.endswith(('.xlsx', '.xls')) else pd.read_csv(f_path, low_memory=False)
            df.columns = [str(c).strip() for c in df.columns]
            
            # 🔥 파일 출처 기반 명시적 전용 필드 태깅
            df['금년/전년'] = '전년'
            df['발매_연도구분'] = '전년 발매'
            df['출발_연도구분'] = '전년 출발'
            df['source_file'] = fname
            df_py_list.append(df)
            print(f"  ├─ 🟢 성공: {fname} ({len(df):,}행)")
        except Exception as e:
            print(f"  ├─ ❌ 실패: {fname} | {e}")

    if not df_cy_list and not df_py_list:
        print("\n❌ 원천 CSV/XLSX 파일을 찾지 못했습니다. 파일명을 확인해주세요.")
        sys.exit(1)

    # 4. 데이터 통합 및 유연한 컬럼 정제
    print("\n⚙️ [3/4] 데이터 통합 및 키 컬럼 정제 중...")
    df_merged = pd.concat(df_cy_list + df_py_list, ignore_index=True)

    # 한글/영문 다양한 컬럼명 유연 대응
    col_pur_m = find_column_by_candidates(df_merged.columns, ["ticketpurchasemonth", "purchasemonth", "발매월", "발매일자", "issuemonth"])
    col_trip_m = find_column_by_candidates(df_merged.columns, ["tripmonth", "travelmonth", "출발월", "출발일자", "depmonth"])
    col_val = find_column_by_candidates(df_merged.columns, ["value", "pax", "수송량", "발매량", "실적"])

    if col_pur_m and col_pur_m != 'Ticket Purchase month':
        df_merged['Ticket Purchase month'] = df_merged[col_pur_m]
    if col_trip_m and col_trip_m != 'Trip Month':
        df_merged['Trip Month'] = df_merged[col_trip_m]

    # 슬라이서 연동용 6자리 표준 키 사전 추출
    df_merged['Pur_YM_Key'] = df_merged['Ticket Purchase month'].apply(normalize_ym_key) if 'Ticket Purchase month' in df_merged.columns else ""
    df_merged['Trip_YM_Key'] = df_merged['Trip Month'].apply(normalize_ym_key) if 'Trip Month' in df_merged.columns else ""

    # 실적 수치 안전 변환
    if col_val:
        df_merged['Value'] = pd.to_numeric(
            df_merged[col_val].astype(str).str.replace(',', '').str.strip(), 
            errors='coerce'
        ).fillna(0.0)

    # 5. 안전한 데이터 타입 보장 (Category 변환 완전 제거 - Streamlit 크래시 방지)
    print("\n💾 [4/4] 안전한 데이터 포맷 정제 및 Parquet 파일 생성 중...")
    for col in df_merged.columns:
        if df_merged[col].dtype == 'object' or str(df_merged[col].dtype) == 'category':
            df_merged[col] = df_merged[col].astype(str).fillna('')
        elif 'int' in str(df_merged[col].dtype):
            df_merged[col] = df_merged[col].fillna(0).astype('int64')
        elif 'float' in str(df_merged[col].dtype):
            df_merged[col] = df_merged[col].fillna(0.0).astype('float64')

    output_path = os.path.join(base_dir, "cache_6th_data.parquet")
    
    # pyarrow 엔진 기반으로 안전하게 parquet 생성
    df_merged.to_parquet(output_path, engine='pyarrow', index=False)

    print("\n" + "=" * 70)
    print(f"🎉 성공적으로 Parquet 파일이 안정적으로 완성되었습니다!")
    print(f"⏱️ 소요 시간: {time.time() - start_time:.2f}초")
    print(f"📊 총 레코드 수: {len(df_merged):,} 행")
    print(f"📁 총 칼럼 수: {len(df_merged.columns)} 개")
    print(f"📍 저장 위치: {output_path}")
    print("=" * 70)

if __name__ == "__main__":
    process_and_create_6th_parquet()