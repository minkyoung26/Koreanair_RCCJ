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
    print(f"📂 작업 폴더 경로: {base_dir}", flush=True)

    all_dir_files = os.listdir(base_dir)
    all_excel_csv = [f for f in all_dir_files if (f.endswith('.xlsx') or f.endswith('.csv')) and not f.startswith('cache_') and not f.startswith('~$')]
    
    # 1. 3/4수송 원본 데이터 파일 탐색
    input_file = None
    suso_files = [f for f in all_excel_csv if '34수송' in f or '수송' in f or '10월' in f]
    if suso_files:
        input_file = os.path.join(base_dir, suso_files[0])
    else:
        non_weight_files = [f for f in all_excel_csv if '가중치' not in f and 'weight' not in f.lower()]
        if non_weight_files:
            input_file = os.path.join(base_dir, non_weight_files[0])

    if not input_file:
        print("❌ [오류] 원본 데이터 파일(.csv)을 찾을 수 없습니다!", flush=True)
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

    if 'Value' in df.columns:
        df['Value'] = pd.to_numeric(df['Value'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    else:
        df['Value'] = 0

    # 2. 가중치 파일 탐색 및 병합(Merge) 연산
    weight_file = None
    wt_files = [f for f in all_dir_files if ('가중치' in f or 'weight' in f.lower()) and not f.startswith('~$')]
    if wt_files:
        weight_file = os.path.join(base_dir, wt_files[0])

    if weight_file:
        print(f"⚖️ 2/3. 가중치 파일 병합(Merge) 연산 시작: {os.path.basename(weight_file)}", flush=True)
        w_df = pd.read_excel(weight_file) if weight_file.endswith('.xlsx') else pd.read_csv(weight_file, low_memory=False)
        w_df.columns = [str(c).strip() for c in w_df.columns]

        pax_c = find_column_by_candidates(w_df.columns, ['pax', '실적', '합계'])
        obd_c = find_column_by_candidates(w_df.columns, ['obd', '보정'])
        al_c  = find_column_by_candidates(w_df.columns, ['dominant', 'mkt', 'al', 'airline', '항공사'])
        rt_c  = find_column_by_candidates(w_df.columns, ['routecode', 'route', 'subroute', '노선', 'key'])

        if pax_c and obd_c and al_c and rt_c:
            w_df['pax_num'] = pd.to_numeric(w_df[pax_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            w_df['obd_num'] = pd.to_numeric(w_df[obd_c].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            # OBD / Pax 가중치 비율
            w_df['_wt_ratio'] = np.where(w_df['pax_num'] > 0, w_df['obd_num'] / w_df['pax_num'], 1.0)

            w_df['_rt_merge'] = w_df[rt_c].astype(str).str.strip().str.upper()
            w_df['_al_merge'] = w_df[al_c].astype(str).str.strip().str.upper()

            # 가중치 테이블 정돈
            w_sub = w_df[['_rt_merge', '_al_merge', '_wt_ratio']].drop_duplicates(subset=['_rt_merge', '_al_merge'])

            # 원본 데이터 매핑 컬럼 추출
            main_rt_col = find_column_by_candidates(df.columns, ['노선', 'route', 'subroute'])
            main_al_col = find_column_by_candidates(df.columns, ['dominant', 'mktal', 'marketing', 'al', 'carrier', '항공사'])

            if main_rt_col and main_al_col:
                df['_rt_merge'] = df[main_rt_col].astype(str).str.strip().str.upper()
                df['_al_merge'] = df[main_al_col].astype(str).str.strip().str.upper()

                # Left Merge를 통한 정밀 가중치 매핑
                df = pd.merge(df, w_sub, on=['_rt_merge', '_al_merge'], how='left')
                df['_wt_ratio'] = df['_wt_ratio'].fillna(1.0)

                df['Mult_map'] = df['_wt_ratio']
                df['Calc_Weighted_Value'] = df['Value'] * df['Mult_map']
                df['Weighted_Value'] = df['Calc_Weighted_Value']

                # 임시 매핑 컬럼 정리
                df.drop(columns=['_rt_merge', '_al_merge', '_wt_ratio'], errors='ignore', inplace=True)
                print("  └ 💡 노선 + 항공사 가중치가 Merge 방식으로 정밀 적용되었습니다!", flush=True)
            else:
                df['Calc_Weighted_Value'] = df['Value']
                df['Weighted_Value'] = df['Value']
        else:
            df['Calc_Weighted_Value'] = df['Value']
            df['Weighted_Value'] = df['Value']
    else:
        df['Calc_Weighted_Value'] = df['Value']
        df['Weighted_Value'] = df['Value']

    # 3. Parquet 캐시 저장
    print("💾 3/3. Parquet 캐시 저장 중...", flush=True)
    output_parquet = os.path.join(base_dir, 'cache_34_data.parquet')
    df.to_parquet(output_parquet, engine='pyarrow', index=False)
    print(f"\n🎉 [성공] 파케 캐시 파일 저장 완료: {output_parquet}", flush=True)
    print(f"📊 총 저장된 데이터 행 수: {len(df):,}개", flush=True)

if __name__ == '__main__':
    process_batch_parquet()