# batch_processor.py
import pandas as pd
import numpy as np
import os
import sys
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
    print(f"📂 작업 폴더 경로: {base_dir}", flush=True)

    # 1. 원본 데이터 파일 탐색 ('34수송_10월1주차' 등 엑셀/CSV 탐색)
    input_file = None
    all_dir_files = os.listdir(base_dir)
    all_excel_csv = [f for f in all_dir_files if (f.endswith('.xlsx') or f.endswith('.csv')) and not f.startswith('cache_') and not f.startswith('~$')]
    
    suso_files = [f for f in all_excel_csv if '34수송' in f or '수송' in f or '10월' in f]
    if suso_files:
        input_file = os.path.join(base_dir, suso_files[0])
    else:
        non_weight_files = [f for f in all_excel_csv if '가중치' not in f and 'weight' not in f.lower()]
        if non_weight_files:
            input_file = os.path.join(base_dir, non_weight_files[0])

    if not input_file:
        print("❌ [오류] 3/4수송 원본 데이터 파일(.csv)을 폴더에서 찾지 못했습니다!", flush=True)
        return

    print(f"📖 1/3. 원본 데이터 읽는 중 (용량이 커서 5~10초 소요될 수 있습니다): {os.path.basename(input_file)}", flush=True)
    try:
        df = pd.read_csv(input_file, low_memory=False, encoding='utf-8-sig')
    except Exception:
        try:
            df = pd.read_csv(input_file, low_memory=False, encoding='cp949')
        except Exception:
            df = pd.read_excel(input_file) if input_file.endswith('.xlsx') else pd.read_csv(input_file, low_memory=False)

    df.columns = [str(c).strip() for c in df.columns]

    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()

    if 'Value' in df.columns:
        df['Value'] = pd.to_numeric(df['Value'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    else:
        df['Value'] = 0

    # 2. 가중치 파일 탐색 (가중치 파일_7월.csv 등)
    weight_file = None
    wt_files = [f for f in all_dir_files if ('가중치' in f or 'weight' in f.lower()) and not f.startswith('~$')]
    if wt_files:
        weight_file = os.path.join(base_dir, wt_files[0])

    if weight_file:
        print(f"⚖️ 2/3. 가중치 파일 노선+항공사 매핑 연산 중: {os.path.basename(weight_file)}", flush=True)
        w_df = pd.read_excel(weight_file) if weight_file.endswith('.xlsx') else pd.read_csv(weight_file, low_memory=False)
        w_df.columns = [str(c).strip() for c in w_df.columns]

        pax_c = find_column_by_candidates(w_df.columns, ['pax', '실적', '합계'])
        obd_c = find_column_by_candidates(w_df.columns, ['obd', '보정'])
        al_c  = find_column_by_candidates(w_df.columns, ['dominant', 'mkt', 'al', 'airline', '항공사'])
        rt_c  = find_column_by_candidates(w_df.columns, ['routecode', 'key', 'subroute', '노선'])

        if pax_c and obd_c and al_c and rt_c:
            w_df['pax_num'] = pd.to_numeric(w_df[pax_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            w_df['obd_num'] = pd.to_numeric(w_df[obd_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            w_df['weight_ratio'] = np.where(w_df['pax_num'] > 0, w_df['obd_num'] / w_df['pax_num'], 1.0)

            w_df['rt_clean'] = w_df[rt_c].astype(str).str.strip().str.upper()
            w_df['al_clean'] = w_df[al_c].astype(str).str.strip().str.upper()

            weight_map = dict(zip(zip(w_df['rt_clean'], w_df['al_clean']), w_df['weight_ratio']))

            route_col_target = find_column_by_candidates(df.columns, ['노선', 'route', 'subroute'])
            al_col_target    = find_column_by_candidates(df.columns, ['dominant', 'mktal', 'marketing', 'al', 'carrier', '항공사'])

            def get_weight_multiplier(row):
                rt_val = str(row[route_col_target]).strip().upper() if route_col_target and route_col_target in row else ''
                al_val = str(row[al_col_target]).strip().upper() if al_col_target and al_col_target in row else ''
                
                if (rt_val, al_val) in weight_map:
                    return weight_map[(rt_val, al_val)]
                
                key_combined = (rt_val + al_val).upper()
                for (r_k, a_k), ratio in weight_map.items():
                    r_k_str = str(r_k).strip().upper()
                    a_k_str = str(a_k).strip().upper()
                    if r_k_str == key_combined or (rt_val and r_k_str.startswith(rt_val) and a_k_str == al_val):
                        return ratio
                        
                return 1.0

            df['Mult_map'] = df.apply(get_weight_multiplier, axis=1)
            df['Calc_Weighted_Value'] = df['Value'] * df['Mult_map']
            df['Weighted_Value'] = df['Calc_Weighted_Value']
            print("  └ 💡 노선 + 항공사 가중치가 성공적으로 매핑되었습니다.", flush=True)
        else:
            df['Calc_Weighted_Value'] = df['Value']
            df['Weighted_Value'] = df['Value']
    else:
        print("  └ ⚠️ 가중치 파일을 찾지 못하여 Raw 실적만 사용합니다.", flush=True)
        df['Calc_Weighted_Value'] = df['Value']
        df['Weighted_Value'] = df['Value']

    # 3. Parquet 캐시 저장
    print("💾 3/3. 초고속 Parquet 캐시 파일 저장 중...", flush=True)
    output_parquet = os.path.join(base_dir, 'cache_34_data.parquet')
    df.to_parquet(output_parquet, engine='pyarrow', index=False)
    print(f"\n🎉 [성공] 파케 캐시 파일 생성 완료: {output_parquet}", flush=True)
    print(f"📊 총 저장된 데이터 행 수: {len(df):,}개", flush=True)

if __name__ == '__main__':
    process_batch_parquet()