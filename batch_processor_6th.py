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

def find_exact_column(columns, exact_candidates):
    """APO나 Stop1처럼 이름 혼동 방지가 필요한 컬럼을 정확히 찾습니다."""
    for c in columns:
        cleaned = str(c).lower().replace(" ", "").replace("_", "").replace(".", "")
        if cleaned in exact_candidates:
            return c
    return None

def process_and_create_6th_parquet():
    start_time = time.time()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 70)
    print("🚀 [6수송 파케 생성기] 고객님 고유 비즈니스 로직 완벽 반영판")
    print("=" * 70)

    all_files = glob.glob(os.path.join(base_dir, "*.csv")) + glob.glob(os.path.join(base_dir, "*.xlsx"))
    
    cy_files, py_files = [], []
    dim_path = None
    
    for f_path in all_files:
        fname = os.path.basename(f_path)
        fname_upper = fname.upper() 
        
        # 엑셀 열림 임시 파일(~$), 캐시 등 불필요한 파일을 가장 먼저 차단
        if "CACHE" in fname_upper or "공급" in fname or "~$" in fname or "OD" in fname_upper or "매핑" in fname:
            continue
            
        # Dimension 파일 식별
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

    print("\n⚙️ [3/3] 데이터 병합 및 파생 변수 생성 중...")
    df_merged = pd.concat(df_list, ignore_index=True)

    # =========================================================================
    # 🌟 [고객님 요청 파생 변수 로직 100% 반영 구역] 🌟
    # =========================================================================

    # [1] OD Region 생성 (Dimension.xlsx 연동)
    if dim_path:
        print(f"  ├─ Dimension 파일 로드 중: {os.path.basename(dim_path)}")
        df_dim = pd.read_excel(dim_path)
        col_aa = df_dim.columns[26]
        col_ab = df_dim.columns[27]
        mapping_dict = dict(zip(df_dim[col_aa].astype(str).str.strip().str.lower(), df_dim[col_ab].astype(str).str.strip()))
        
        def get_od_region(row):
            orig_name = str(row.get('Trip Origin Country Name', '')).strip().lower()
            dest_name = str(row.get('Trip Destination Country Name', '')).strip().lower()
            orig_code = str(row.get('Trip Origin Country Code', '')).strip().lower()
            dest_code = str(row.get('Trip Destination Country Code', '')).strip().lower()
            
            target_country = ""
            if orig_name == 'japan' or orig_code == 'jp':
                target_country = dest_name
            elif dest_name == 'japan' or dest_code == 'jp':
                target_country = orig_name
            else:
                target_country = dest_name
                
            rgn_value = mapping_dict.get(target_country, 'OTHER')
            if rgn_value == 'nan': rgn_value = 'OTHER'
            
            if str(rgn_value).upper().startswith("JPN-"): return str(rgn_value).upper()
            else: return f"JPN-{str(rgn_value).upper()}"
                
        df_merged['4.OD RGN'] = df_merged.apply(get_od_region, axis=1)
        df_merged['OD Region'] = df_merged['4.OD RGN']
        print("  ├─ 🟢 OD Region 매핑 완료 (JPN- 텍스트 추가)")
    else:
        df_merged['4.OD RGN'] = 'JPN-OTHER'
        df_merged['OD Region'] = 'JPN-OTHER'
        print("  ├─ ⚠ Dimension 파일 없음.")

    # [2] 직항/경유 생성 (Stop1 존재 여부)
    col_stop1 = find_exact_column(df_merged.columns, ["stop1"])
    if col_stop1:
        # 빈칸, 널값(NaN, None) 철저히 필터링
        stop1_str = df_merged[col_stop1].fillna('').astype(str).str.strip().str.upper()
        is_transit = (stop1_str != '') & (stop1_str != 'NAN') & (stop1_str != 'NONE') & (stop1_str != 'NULL')
        df_merged['직항/경유'] = np.where(is_transit, '경유', '직항')
        print(f"  ├─ 🟢 직항/경유 생성 완료 ({col_stop1} 기준, 경유: {is_transit.sum():,}건)")
    else:
        df_merged['직항/경유'] = '직항'
        print("  ├─ ⚠ Stop1 컬럼을 찾을 수 없습니다.")

    # [3] Trip O&D 생성 (AAA-BBB 조합)
    col_trip_mkt = find_exact_column(df_merged.columns, ["tripodmarket", "tripmarket", "odmarket"])
    if col_trip_mkt:
        def make_trip_od(val):
            val_str = str(val).strip()
            if len(val_str) >= 6:
                return val_str[:3].upper() + "-" + val_str[-3:].upper()
            return val_str
        df_merged['Trip O&D'] = df_merged[col_trip_mkt].apply(make_trip_od)
        print(f"  ├─ 🟢 Trip O&D 생성 완료 ({col_trip_mkt} 컬럼 추출)")
    else:
        df_merged['Trip O&D'] = 'UNKNOWN'
        print("  ├─ ⚠ Trip Market 관련 컬럼을 찾을 수 없습니다.")

    # [4] Direction (일본발/행) & 일본/해외 APO 생성 로직
    col_orig_apo = find_exact_column(df_merged.columns, ["origin", "triporigin"])
    col_dest_apo = find_exact_column(df_merged.columns, ["destination", "tripdestination"])
    
    col_orig_c_name = find_exact_column(df_merged.columns, ["origincountryname", "triporigincountryname"])
    col_orig_c_code = find_exact_column(df_merged.columns, ["origincountrycode", "triporigincountrycode"])

    if col_orig_c_name or col_orig_c_code:
        is_jp_orig = pd.Series(False, index=df_merged.index)
        if col_orig_c_name:
            is_jp_orig = is_jp_orig | (df_merged[col_orig_c_name].astype(str).str.strip().str.lower() == 'japan')
        if col_orig_c_code:
            is_jp_orig = is_jp_orig | (df_merged[col_orig_c_code].astype(str).str.strip().str.upper() == 'JP')
            
        df_merged['DIRECTION'] = np.where(is_jp_orig, '일본발', '일본행')
        df_merged['Direction'] = df_merged['DIRECTION']
        print("  ├─ 🟢 일본발/일본행 Direction 생성 완료")
        
        # APO 값 추출 (Origin / Destination 스왑)
        if col_orig_apo and col_dest_apo:
            df_merged['일본 APO'] = np.where(is_jp_orig, df_merged[col_orig_apo], df_merged[col_dest_apo])
            df_merged['해외 APO'] = np.where(is_jp_orig, df_merged[col_dest_apo], df_merged[col_orig_apo])
            print(f"  ├─ 🟢 일본/해외 APO 분리 완료 ({col_orig_apo}, {col_dest_apo} 매핑)")
        else:
            df_merged['일본 APO'] = ''
            df_merged['해외 APO'] = ''
            print("  ├─ ⚠ 출발/도착 공항 코드를 찾을 수 없어 APO를 비웁니다.")
    else:
        df_merged['DIRECTION'] = '기타'
        df_merged['Direction'] = '기타'
        df_merged['일본 APO'] = ''
        df_merged['해외 APO'] = ''
        print("  ├─ ⚠ Origin Country 정보가 없어 Direction 및 APO 처리를 건너뜁니다.")
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
        'Ticket Purchase month', 'Trip Month', '4.OD RGN', 'OD Region', 'DIRECTION', 'Direction', 
        '직항/경유', 'Trip Origin Country Code', 'Trip Destination Country Code', 
        'Trip Origin Country Name', 'Trip Destination Country Name', 'Stop1',
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