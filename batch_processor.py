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
    
    # 1. 원본 데이터 파일 탐색
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
    df = pd.read_excel(input_file) if input_file.endswith('.xlsx') else pd.read_csv(input_file, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]

    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()

    if 'Value' in df.columns:
        df['Value'] = pd.to_numeric(df['Value'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    else:
        df['Value'] = 0

    # 2. 가중치 파일 탐색
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
        print(f"⚖️ 가중치 파일 매핑 시작: {os.path.basename(weight_file)}")
        w_df = pd.read_excel(weight_file) if weight_file.endswith('.xlsx') else pd.read_csv(weight_file, low_memory=False)
        w_df.columns = [str(c).strip() for c in w_df.columns]

        pax_c = find_column_by_candidates(w_df.columns, ['pax', '실적', '합계'])
        obd_c = find_column_by_candidates(w_df.columns, ['obd', '보정'])
        al_c  = find_column_by_candidates(w_df.columns, ['dominant', 'mkt', 'al', 'airline', '항공사'])
        key_c = find_column_by_candidates(w_df.columns, ['keyroute', 'key', 'subroute', '노선'])

        if pax_c and obd_c and al_c and key_c:
            w_df['pax_num'] = pd.to_numeric(w_df[pax_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            w_df['obd_num'] = pd.to_numeric(w_df[obd_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            w_df['weight_ratio'] = np.where(w_df['pax_num'] > 0, w_df['obd_num'] / w_df['pax_num'], 1.0)

            # Key Route Code (예: G/KIX7C -> G/KIX 노선 추출)
            def extract_clean_route(val):
                s = str(val).strip().upper()
                if '/' in s:
                    parts = s.split('/')
                    origin = parts[0]
                    dest = parts[1][:3] # 공항 3자리 추출 (KIX, CTS 등)
                    return f"{origin}/{dest}"
                return s

            w_df['rt_clean'] = w_df[key_c].apply(extract_clean_route)
            w_df['al_clean'] = w_df[al_c].astype(str).str.strip().str.upper()

            weight_map = dict(zip(zip(w_df['rt_clean'], w_df['al_clean']), w_df['weight_ratio']))

            route_col_target = find_column_by_candidates(df.columns, ['노선', 'route', 'subroute'])
            al_col_target    = find_column_by_candidates(df.columns, ['dominant', 'mktal', 'marketing', 'al', 'carrier', '항공사'])

            def get_weight_multiplier(row):
                rt_val = extract_clean_route(row[route_col_target]) if route_col_target and route_col_target in row else ''
                al_val = str(row[al_col_target]).strip().upper() if al_col_target and al_col_target in row else ''
                return weight_map.get((rt_val, al_val), 1.0)

            df['Mult_map'] = df.apply(get_weight_multiplier, axis=1)
            df['Calc_Weighted_Value'] = df['Value'] * df['Mult_map']
            df['Weighted_Value'] = df['Calc_Weighted_Value']
            print("  └ 💡 노선(G/KIX) + 항공사 매핑 완료!")
        else:
            df['Calc_Weighted_Value'] = df['Value']
            df['Weighted_Value'] = df['Value']
    else:
        df['Calc_Weighted_Value'] = df['Value']
        df['Weighted_Value'] = df['Value']

    # 3. 파케 저장
    output_parquet = os.path.join(base_dir, 'cache_34_data.parquet')
    df.to_parquet(output_parquet, engine='pyarrow', index=False)
    print(f"✅ 파켓 캐시 파일 생성 성공: {output_parquet}")

if __name__ == '__main__':
    process_batch_parquet()