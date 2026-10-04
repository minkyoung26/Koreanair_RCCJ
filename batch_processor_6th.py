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
    print("🚀 [6수송 파케 생성기] 고객님 고유 비즈니스 로직(Dimension/직항/방향) 완벽 적용판")
    print("=" * 70)

    all_files = glob.glob(os.path.join(base_dir, "*.csv")) + glob.glob(os.path.join(base_dir, "*.xlsx"))
    
    cy_files, py_files = [], []
    dim_path = None
    
    for f_path in all_files:
        fname = os.path.basename(f_path)
        fname_upper = fname.upper() 
        
        # 🚨 [수정됨] 엑셀 열림 임시 파일(~$), 캐시 등 불필요한 파일을 가장 먼저 완벽히 차단
        if "CACHE" in fname_upper or "공급" in fname or "~$" in fname or "OD" in fname_upper or "매핑" in fname:
            continue
            
        # Dimension 파일 식별 (위에서 ~$ 파일이 걸러진 후 진짜 파일만 탐색)
        if "DIMENSION" in fname_upper or "디멘전" in fname:
            dim_path = f_path
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
    # 🌟 [고객님 요청 파생 변수 로직 100% 반영] 🌟
    # =========================================================================
    print("🛠 고객님의 고유 비즈니스 로직(Dimension 연동, Stop1, JP) 처리 중...")

    # [1] OD Region 생성 (Dimension.xlsx AA열/AB열 연동)
    if dim_path:
        print(f"  ├─ Dimension 파일 로드 중: {os.path.basename(dim_path)}")
        df_dim = pd.read_excel(dim_path)
        
        # AA열(26번째 인덱스)과 AB열(27번째 인덱스) 추출
        col_aa = df_dim.columns[26]
        col_ab = df_dim.columns[27]
        
        # 매핑 딕셔너리 생성 (비교를 위해 소문자 변환)
        mapping_dict = dict(zip(df_dim[col_aa].astype(str).str.strip().str.lower(), df_dim[col_ab].astype(str).str.strip()))
        
        def get_od_region(row):
            orig_name = str(row.get('Trip Origin Country Name', '')).strip().lower()
            dest_name = str(row.get('Trip Destination Country Name', '')).strip().lower()
            orig_code = str(row.get('Trip Origin Country Code', '')).strip().lower()
            dest_code = str(row.get('Trip Destination Country Code', '')).strip().lower()
            
            # 일본(Japan)일 경우 그 반대 국가를 찾음
            target_country = ""
            if orig_name == 'japan' or orig_code == 'jp':
                target_country = dest_name
            elif dest_name == 'japan' or dest_code == 'jp':
                target_country = orig_name
            else:
                target_country = dest_name
                
            rgn_value = mapping_dict.get(target_country, 'OTHER')
            if rgn_value == 'nan': rgn_value = 'OTHER'
            
            # 무조건 'JPN-'을 앞에 붙이도록 설정
            if str(rgn_value).upper().startswith("JPN-"):
                return str(rgn_value).upper()
            else:
                return f"JPN-{str(rgn_value).upper()}"
                
        df_merged['4.OD RGN'] = df_merged.apply(get_od_region, axis=1)
        df_merged['OD Region'] = df_merged['4.OD RGN']
        print("  ├─ 🟢 OD Region 매핑 완료 (Dimension.xlsx의 AA열->AB열 적용 및 JPN- 추가)")
    else:
        print("  ├─ ⚠ Dimension 파일을 찾을 수 없어 매핑을 건너뜁니다.")
        df_merged['4.OD RGN'] = 'JPN-OTHER'
        df_merged['OD Region'] = 'JPN-OTHER'

    # [2] 직항/경유 로직 (Stop1 값 여부 기준)
    if 'Stop1' in df_merged.columns:
        is_transit = df_merged['Stop1'].notna() & (df_merged['Stop1'].astype(str).str.strip() != '') & (df_merged['Stop1'].astype(str).str.lower() != 'nan')
        df_merged['직항/경유'] = np.where(is_transit, '경유', '직항')
        print("  ├─ 🟢 직항/경유 판단 완료 (Stop1 값 존재 시 경유, 없으면 직항)")
    else:
        print("  ├─ ⚠ 'Stop1' 컬럼이 원천 데이터에 없습니다.")
        df_merged['직항/경유'] = '직항'

    # [3] Direction (일본행/일본발) 로직 (Origin Country Name 또는 Code 기준)
    col_orig_name = 'Trip Origin Country Name' if 'Trip Origin Country Name' in df_merged.columns else None
    col_orig_code = 'Trip Origin Country Code' if 'Trip Origin Country Code' in df_merged.columns else None

    if col_orig_name or col_orig_code:
        is_jp_orig = pd.Series(False, index=df_merged.index)
        if col_orig_name:
            is_jp_orig = is_jp_orig | (df_merged[col_orig_name].astype(str).str.strip().str.lower() == 'japan')
        if col_orig_code:
            is_jp_orig = is_jp_orig | (df_merged[col_orig_code].astype(str).str.strip().str.upper() == 'JP')
            
        df_merged['DIRECTION'] = np.where(is_jp_orig, '일본발', '일본행')
        df_merged['Direction'] = df_merged['DIRECTION']
        print("  ├─ 🟢 일본행/일본발 판단 완료 (Origin이 Japan/JP이면 일본발, 반대면 일본행)")
    else:
        print("  ├─ ⚠ Origin Country 컬럼이 원천 데이터에 없습니다.")
        df_merged['DIRECTION'] = '기타'
        df_merged['Direction'] = '기타'
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

    # 필터 옵션으로 나올 모든 컬럼을 그룹화 키에 명시
    group_cols = [
        'Ticket Purchase month', 'Trip Month', '4.OD RGN', 'OD Region', 'DIRECTION', 'Direction', 
        '직항/경유', 'Trip Origin Country Code', 'Trip Destination Country Code', 
        'Trip Origin Country Name', 'Trip Destination Country Name', 'Stop1',
        '일본 APO', '해외 APO', 'Trip O&D', 'Trip O&D Market', 
        'Dominant Marketing Airline', '금년/전년', '발매_연도구분', '출발_연도구분',
        'Pur_M_Norm', 'Trip_M_Norm'
    ]
    existing_cols = [c for c in group_cols if c in df_merged.columns]
    
    # dropna=False 로 그룹핑시 결측치 행 유지 방어
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