# batch_processor_6th.py
import pandas as pd
import numpy as np
import os
import glob
import sys
import time

def normalize_ym_key(val_str):
    """
    '2026-03', '2026.03', '202603월' 등의 연월 문자열을 
    숫자 6자리 '202603' 형태의 표준 키로 변환합니다.
    """
    if pd.isna(val_str):
        return ""
    s = str(val_str).replace('-', '').replace('.', '').replace('/', '').replace('월', '').strip()
    return s[:6] if len(s) >= 6 and s[:6].isdigit() else ""

def process_and_create_6th_parquet():
    start_time = time.time()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 70)
    print("🚀 [배치 프로세서] 6수송 데이터 통합 및 cache_6th_data.parquet 생성")
    print("=" * 70)

    # 1. 파일 검색 및 목록 수집
    print("\n🔍 [1/5] 원천 파일 탐색 중...")
    
    cy_patterns = ["*6수송*금년*.csv", "*6수송*금년*.xlsx", "*6th*CY*.csv", "*6th*CY*.xlsx", "*금년*6수송*.csv"]
    py_patterns = ["*6수송*전년*.csv", "*6수송*전년*.xlsx", "*6th*PY*.csv", "*6th*PY*.xlsx", "*전년*6수송*.csv"]
    
    cy_files = []
    for pat in cy_patterns:
        cy_files.extend(glob.glob(os.path.join(base_dir, pat)))
        
    py_files = []
    for pat in py_patterns:
        py_files.extend(glob.glob(os.path.join(base_dir, pat)))
        
    cy_files = sorted(list(set(cy_files)))
    py_files = sorted(list(set(py_files)))

    df_cy_list = []
    df_py_list = []

    # 2. 금년(CY) 파일 로드 및 명시적 구분 필드 태깅
    print(f"\n📂 [2/5] 금년(CY) 원천 데이터 로드 중... (발견된 파일: {len(cy_files)}개)")
    for f_path in cy_files:
        fname = os.path.basename(f_path)
        try:
            if f_path.endswith('.xlsx') or f_path.endswith('.xls'):
                df = pd.read_excel(f_path)
            else:
                df = pd.read_csv(f_path, low_memory=False)
                
            df.columns = [str(c).strip() for c in df.columns]
            
            # 🔥 [요청 반영 핵심] 6수송_금년 출처 기반 명시적 필드 태깅
            df['금년/전년'] = '금년'
            df['발매_연도구분'] = '금년 발매'
            df['출발_연도구분'] = '금년 출발'
            df['source_file'] = fname
            
            df_cy_list.append(df)
            print(f"  ├─ 🟢 성공: {fname} | 행 수: {len(df):,}행 | 컬럼 수: {len(df.columns)}개")
        except Exception as e:
            print(f"  ├─ ❌ 실패: {fname} | 오류 메시지: {e}")

    # 3. 전년(PY) 파일 로드 및 명시적 구분 필드 태깅
    print(f"\n📂 [3/5] 전년(PY) 원천 데이터 로드 중... (발견된 파일: {len(py_files)}개)")
    for f_path in py_files:
        fname = os.path.basename(f_path)
        try:
            if f_path.endswith('.xlsx') or f_path.endswith('.xls'):
                df = pd.read_excel(f_path)
            else:
                df = pd.read_csv(f_path, low_memory=False)
                
            df.columns = [str(c).strip() for c in df.columns]
            
            # 🔥 [요청 반영 핵심] 6수송_전년 출처 기반 명시적 필드 태깅
            df['금년/전년'] = '전년'
            df['발매_연도구분'] = '전년 발매'
            df['출발_연도구분'] = '전년 출발'
            df['source_file'] = fname
            
            df_py_list.append(df)
            print(f"  ├─ 🟢 성공: {fname} | 행 수: {len(df):,}행 | 컬럼 수: {len(df.columns)}개")
        except Exception as e:
            print(f"  ├─ ❌ 실패: {fname} | 오류 메시지: {e}")

    # 파일명이 정형화되지 않았을 경우 Fallback 감지 로직
    if not df_cy_list and not df_py_list:
        print("\n⚠️️ 명시적 패턴(금년/전년)을 가진 파일이 없어 전체 6수송 파일 자동 감지를 시도합니다...")
        all_files = glob.glob(os.path.join(base_dir, "*6수송*.csv")) + glob.glob(os.path.join(base_dir, "*6수송*.xlsx"))
        
        for f_path in all_files:
            fname = os.path.basename(f_path)
            if "cache" in fname or "parquet" in fname:
                continue
            try:
                df = pd.read_excel(f_path) if f_path.endswith('.xlsx') else pd.read_csv(f_path, low_memory=False)
                df.columns = [str(c).strip() for c in df.columns]
                
                is_cy = ("금년" in fname) or ("CY" in fname.upper())
                tag_label = "금년" if is_cy else "전년"
                
                df['금년/전년'] = tag_label
                df['발매_연도구분'] = f"{tag_label} 발매"
                df['출발_연도구분'] = f"{tag_label} 출발"
                df['source_file'] = fname
                
                if is_cy:
                    df_cy_list.append(df)
                else:
                    df_py_list.append(df)
                print(f"  ├─ 🔍 자동 감지 태깅 완료: {fname} -> [{tag_label}] ({len(df):,}행)")
            except Exception as e:
                print(f"  ├─ ❌ 실패: {fname} | 오류: {e}")

    if not df_cy_list and not df_py_list:
        print("\n❌ [오류] 읽어올 수 있는 6수송 원천 데이터 파일이 존재하지 않습니다.")
        print("💡 6수송_금년.csv / 6수송_전년.csv 파일이 스크립트와 동일한 폴더에 있는지 확인해주세요.")
        sys.exit(1)

    # 4. 데이터 병합 및 표준화 전처리
    print("\n⚙️ [4/5] 데이터 병합 및 인덱스/수치형 데이터 정제 중...")
    df_merged = pd.concat(df_cy_list + df_py_list, ignore_index=True)

    # 대소문자 및 띄어쓰기 차이 정규화 맵
    lower_col_map = {c.lower().replace(" ", "").replace("_", "").replace(".", ""): c for c in df_merged.columns}
    
    col_pur_m = lower_col_map.get("ticketpurchasemonth", "Ticket Purchase month")
    col_trip_m = lower_col_map.get("tripmonth", "Trip Month")
    col_val = lower_col_map.get("value", "Value")

    # 🌟 대시보드 초속도 매칭을 위한 6자리 표준 연월 키(Pur_YM_Key, Trip_YM_Key) 생성
    if col_pur_m in df_merged.columns:
        df_merged['Pur_YM_Key'] = df_merged[col_pur_m].apply(normalize_ym_key)
    else:
        df_merged['Pur_YM_Key'] = ""

    if col_trip_m in df_merged.columns:
        df_merged['Trip_YM_Key'] = df_merged[col_trip_m].apply(normalize_ym_key)
    else:
        df_merged['Trip_YM_Key'] = ""

    # Value 값 콤마 제거 및 수치형 변환
    if col_val in df_merged.columns:
        df_merged[col_val] = pd.to_numeric(
            df_merged[col_val].astype(str).str.replace(',', '').str.strip(), 
            errors='coerce'
        ).fillna(0.0)

    # 5. 메모리 구조 및 파케(Parquet) 저장 최적화
    print("\n💾 [5/5] Parquet 압축 및 메모리 데이터 타입 최적화 진행 중...")
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

    elapsed_time = time.time() - start_time
    print("\n" + "=" * 70)
    print("🎉 [처리 완료] cache_6th_data.parquet 파일이 성공적으로 생성되었습니다!")
    print(f"⏱️ 소요 시간: {elapsed_time:.2f}초")
    print(f"📊 총 레코드 수: {len(df_merged):,} 행")
    print(f"📁 총 칼럼 수: {len(df_merged.columns)} 개")
    print(f"📍 파일 저장 경로: {output_path}")
    print("=" * 70)

if __name__ == "__main__":
    process_and_create_6th_parquet()