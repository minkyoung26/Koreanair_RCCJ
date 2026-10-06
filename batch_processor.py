# batch_processor.py
import pandas as pd
import numpy as np
import os
import datetime

def find_column_by_candidates(columns, candidates):
    for c in columns:
        cleaned_col = str(c).lower().replace(" ", "").replace("_", "").replace(".", "")
        for cand in candidates:
            if cand in cleaned_col:
                return c
    return None

def process_batch_parquet():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. 원본 데이터 파일 탐색 (xlsx, csv 등)
    input_file = None
    possible_inputs = ['data_new.xlsx', '34수송.xlsx', '34수송.csv', '원본데이터.xlsx', '원본데이터.csv']
    
    for f in possible_inputs:
        full_path = os.path.join(base_dir, f)
        if os.path.exists(full_path):
            input_file = full_path
            break
            
    if not input_file:
        files = [f for f in os.listdir(base_dir) if f.endswith('.xlsx') or f.endswith('.csv')]
        files = [f for f in files if not f.startswith('cache_') and not f.startswith('~$') and '가중치' not in f]
        if files:
            input_file = os.path.join(base_dir, files[0])

    if not input_file:
        print("❌ 원본 데이터 파일을 찾을 수 없습니다.")
        return

    print(f"📖 원본 파일 읽는 중: {os.path.basename(input_file)}")
    
    if input_file.endswith('.xlsx'):
        df = pd.read_excel(input_file)
    else:
        df = pd.read_csv(input_file, low_memory=False)

    # 2. 컬럼명 공백 제거 및 표준화
    df.columns = [str(c).strip() for c in df.columns]

    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()

    # 3. 실적 수치형 변환
    if 'Value' in df.columns:
        df['Value'] = pd.to_numeric(df['Value'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    else:
        df['Value'] = 0

    # 4. 🔑 가중치 파일(가중치 파일_7월.csv 등) 탐색 및 노선+항공사별 가중치 매핑
    weight_file = None
    possible_weights = ['가중치 파일_7월.csv', '가중치.csv', '가중치.xlsx', 'LCC_weight.csv']
    for wf in possible_weights:
        w_path = os.path.join(base_dir, wf)
        if os.path.exists(w_path):
            weight_file = w_path
            break

    if not weight_file:
        wt_files = [f for f in os.listdir(base_dir) if ('가중치' in f or 'weight' in f.lower()) and not f.startswith('~$')]
        if wt_files:
            weight_file = os.path.join(base_dir, wt_files[0])

    if weight_file:
        print(f"⚖️ 가중치 파일 적용 중: {os.path.basename(weight_file)}")
        if weight_file.endswith('.xlsx'):
            w_df = pd.read_excel(weight_file)
        else:
            w_df = pd.read_csv(weight_file, low_memory=False)

        w_df.columns = [str(c).strip() for c in w_df.columns]

        # 가중치 파일 내 컬럼 찾기 (Pax, OBD, 노선, 항공사)
        pax_c = find_column_by_candidates(w_df.columns, ['pax', '실적', '합계'])
        obd_c = find_column_by_candidates(w_df.columns, ['obd', '보정'])
        al_c  = find_column_by_candidates(w_df.columns, ['dominant', 'mkt', 'al', 'airline', '항공사'])
        rt_c  = find_column_by_candidates(w_df.columns, ['subroute', 'route', '노선'])

        if pax_c and obd_c and al_c and rt_c:
            w_df['pax_num'] = pd.to_numeric(w_df[pax_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            w_df['obd_num'] = pd.to_numeric(w_df[obd_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            # Pax 대비 OBD 배수(가중치 비율) 산출
            w_df['weight_ratio'] = np.where(w_df['pax_num'] > 0, w_df['obd_num'] / w_df['pax_num'], 1.0)

            w_df['rt_clean'] = w_df[rt_c].astype(str).str.strip().str.upper()
            w_df['al_clean'] = w_df[al_c].astype(str).str.strip().str.upper()

            # (노선, 항공사) -> 가중치 배수 딕셔너리 생성
            weight_map = dict(zip(zip(w_df['rt_clean'], w_df['al_clean']), w_df['weight_ratio']))

            # 원본 데이터 컬럼 찾기
            route_col_target = find_column_by_candidates(df.columns, ['subroute', '노선', 'route'])
            al_col_target    = find_column_by_candidates(df.columns, ['dominant', 'mktal', 'marketing', 'al', 'carrier', '항공사'])

            def get_weight_multiplier(row):
                rt_val = str(row[route_col_target]).strip().upper() if route_col_target and route_col_target in row else ''
                al_val = str(row[al_col_target]).strip().upper() if al_col_target and al_col_target in row else ''
                return weight_map.get((rt_val, al_val), 1.0)

            df['Mult_map'] = df.apply(get_weight_multiplier, axis=1)
            df['Calc_Weighted_Value'] = df['Value'] * df['Mult_map']
            df['Weighted_Value'] = df['Calc_Weighted_Value']
            print("  └ 💡 노선+항공사별 가중치가 성공적으로 매핑되었습니다.")
        else:
            print("  └ ⚠️ 가중치 파일 컬럼을 인식하지 못하여 Raw 실적을 사용합니다.")
            df['Calc_Weighted_Value'] = df['Value']
            df['Weighted_Value'] = df['Value']
    else:
        print("  └ ⚠️ 가중치 파일을 찾지 못하여 Raw 실적을 사용합니다.")
        df['Calc_Weighted_Value'] = df['Value']
        df['Weighted_Value'] = df['Value']

    # 5. 최신 Parquet 파일로 저장
    output_parquet = os.path.join(base_dir, 'cache_34_data.parquet')
    df.to_parquet(output_parquet, engine='pyarrow', index=False)
    
    print(f"✅ 파켓 캐시 파일 생성 성공: {output_parquet}")
    print(f"📌 저장된 총 행 수: {len(df):,}개 | 포함된 컬럼: {list(df.columns)}")

if __name__ == '__main__':
    process_batch_parquet()