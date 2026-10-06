# batch_processor.py
import pandas as pd
import numpy as np
import os
import sys

def find_column_by_candidates(columns, candidates):
    for c in columns:
        cleaned_col = str(c).lower().replace(" ", "").replace("_", "").replace(".", "")
        for cand in candidates:
            if cand in cleaned_col:
                return c
    return None

def process_batch_parquet():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"📂 작업 폴더: {base_dir}", flush=True)

    all_dir_files = os.listdir(base_dir)
    all_excel_csv = [f for f in all_dir_files if (f.endswith('.xlsx') or f.endswith('.csv')) and not f.startswith('cache_') and not f.startswith('~$')]
    
    # 1. 3/4수송 원본 데이터 탐색
    input_file = None
    suso_files = [f for f in all_excel_csv if '34수송' in f or '수송' in f or '10월' in f]
    if suso_files:
        input_file = os.path.join(base_dir, suso_files[0])
    else:
        non_weight_files = [f for f in all_excel_csv if '가중치' not in f and 'weight' not in f.lower()]
        if non_weight_files:
            input_file = os.path.join(base_dir, non_weight_files[0])

    if not input_file:
        print("❌ [오류] 3/4수송 원본 데이터 파일(.csv)을 찾지 못했습니다!", flush=True)
        return

    print(f"📖 1/3. 원본 데이터 읽는 중: {os.path.basename(input_file)}", flush=True)
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

    val_col_name = find_column_by_candidates(df.columns, ['value', 'pax', '수송량', '발매량', '실적']) or 'Value'
    df['Value'] = pd.to_numeric(df[val_col_name].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

    # 2. 가중치 파일 읽기 및 매핑 사전 구축
    weight_file = None
    wt_files = [f for f in all_dir_files if ('가중치' in f or 'weight' in f.lower()) and not f.startswith('~$')]
    if wt_files:
        weight_file = os.path.join(base_dir, wt_files[0])

    if weight_file:
        print(f"⚖️ 2/3. 가중치 매핑 연산 중: {os.path.basename(weight_file)}", flush=True)
        try:
            w_df = pd.read_csv(weight_file, low_memory=False, encoding='utf-8-sig')
        except Exception:
            w_df = pd.read_csv(weight_file, low_memory=False, encoding='cp949')

        w_df.columns = [str(c).strip() for c in w_df.columns]

        pax_c = '합계 : Pax' if '합계 : Pax' in w_df.columns else find_column_by_candidates(w_df.columns, ['pax', '실적', '합계'])
        obd_c = 'OBD' if 'OBD' in w_df.columns else find_column_by_candidates(w_df.columns, ['obd', '보정'])
        al_c  = 'Dominant Marketing Airline' if 'Dominant Marketing Airline' in w_df.columns else find_column_by_candidates(w_df.columns, ['dominant', 'al', 'airline'])
        rt_c  = 'Route Code' if 'Route Code' in w_df.columns else find_column_by_candidates(w_df.columns, ['routecode', 'route', 'subroute', 'key'])

        w_df['pax_num'] = pd.to_numeric(w_df[pax_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        w_df['obd_num'] = pd.to_numeric(w_df[obd_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        w_df['weight_ratio'] = np.where(w_df['pax_num'] > 0, w_df['obd_num'] / w_df['pax_num'], 1.0)

        w_df['rt_clean'] = w_df[rt_c].astype(str).str.strip().str.upper()
        w_df['al_clean'] = w_df[al_c].astype(str).str.strip().str.upper()

        weight_dict = dict(zip(zip(w_df['rt_clean'], w_df['al_clean']), w_df['weight_ratio']))

        main_rt_col = find_column_by_candidates(df.columns, ['노선', 'route', 'subroute'])
        main_al_col = find_column_by_candidates(df.columns, ['dominant', 'mktal', 'marketing', 'al', 'carrier', '항공사'])

        def apply_wt(row):
            rt = str(row[main_rt_col]).strip().upper() if main_rt_col and main_rt_col in row else ''
            al = str(row[main_al_col]).strip().upper() if main_al_col and main_al_col in row else ''
            return weight_dict.get((rt, al), 1.0)

        df['Mult_map'] = df.apply(apply_wt, axis=1)
        df['Calc_Weighted_Value'] = df['Value'] * df['Mult_map']
        df['Weighted_Value'] = df['Calc_Weighted_Value']
        print("  └ 💡 노선(Route Code) + 항공사 가중치가 정상 매핑되었습니다!", flush=True)
    else:
        df['Calc_Weighted_Value'] = df['Value']
        df['Weighted_Value'] = df['Value']

    # 3. Parquet 캐시 저장
    print("💾 3/3. cache_34_data.parquet 저장 중...", flush=True)
    output_parquet = os.path.join(base_dir, 'cache_34_data.parquet')
    df.to_parquet(output_parquet, engine='pyarrow', index=False)
    print(f"\n🎉 [성공] 파케 캐시 파일 생성 완료!", flush=True)

if __name__ == '__main__':
    process_batch_parquet()