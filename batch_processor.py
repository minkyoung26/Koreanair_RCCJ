# batch_processor.py
import pandas as pd
import numpy as np
import os
import glob

def find_file_by_pattern(pattern):
    files = glob.glob(pattern)
    return files[0] if files else None

def run_data_pipeline():
    print("⏳ [1/2] 3/4수송 LCC 직판 보정 가중치(Fallback 연산) 수행 중...")
    
    # 📌 패턴 매칭으로 파일 자동 탐색
    file_34 = find_file_by_pattern('*34수송*.csv')
    file_wt = find_file_by_pattern('*가중치*.csv')
    file_6th = find_file_by_pattern('*6수송*.csv') or find_file_by_pattern('*6TRF*.csv')

    df_iss = pd.read_csv(file_34, low_memory=False) if file_34 else None
    df_wt = pd.read_csv(file_wt, low_memory=False) if file_wt else None

    if df_iss is not None and df_wt is not None:
        print(f"  └ 📄 3/4수송 파일 감지: {file_34}")
        print(f"  └ 📄 가중치 파일 감지: {file_wt}")
        
        df = df_iss.copy()
        df_wt_c = df_wt.copy()
        
        df.columns = [str(c).strip() for c in df.columns]
        df_wt_c.columns = [str(c).strip() for c in df_wt_c.columns]

        bound_col = '수송' if '수송' in df.columns else ('Bound' if 'Bound' in df.columns else None)
        if bound_col:
            df['수송'] = df[bound_col].astype(str).str.strip()
            df['수송'] = df['수송'].replace({'nan': 'OTHERS', '': 'OTHERS', 'None': 'OTHERS', 'NaN': 'OTHERS'})

        ke_service_col = 'KE취항여부' if 'KE취항여부' in df.columns else ('KE취항노선 여부' if 'KE취항노선 여부' in df.columns else None)
        if ke_service_col:
            df = df[df[ke_service_col].astype(str).str.strip() == '취항'].reset_index(drop=True)

        df['노선'] = df['노선'].astype(str).str.strip().str.upper()
        df['Dominant Marketing Airline'] = df['Dominant Marketing Airline'].astype(str).str.strip().str.upper()

        date_sub_col = '발매일자 ' if '발매일자 ' in df.columns else ('발매일자' if '발매일자' in df.columns else None)
        week_col_raw = '발매 주차' if '발매 주차' in df.columns else ('발매주차' if '발매주차' in df.columns else None)
        if week_col_raw and date_sub_col and date_sub_col in df.columns:
            df['발매주차_일자'] = df[week_col_raw].astype(str).str.strip() + " " + df[date_sub_col].astype(str).str.strip()

        wt_val_col = 'Weight' if 'Weight' in df_wt_c.columns else df_wt_c.columns[-1]
        wt_col_route = 'Route Code' if 'Route Code' in df_wt_c.columns else df_wt_c.columns[0]
        wt_col_al = 'Dominant Marketing Airline' if 'Dominant Marketing Airline' in df_wt_c.columns else df_wt_c.columns[1]

        wt_str = df_wt_c[wt_val_col].astype(str).str.replace('%', '', regex=False).str.strip()
        wt_num = pd.to_numeric(wt_str, errors='coerce')
        df_wt_c['Weight_ratio'] = np.where(wt_num > 1.0, wt_num / 100.0, wt_num)

        df_wt_subset = df_wt_c[[wt_col_route, wt_col_al, 'Weight_ratio']].dropna(subset=[wt_col_route, wt_col_al]).copy()
        df_wt_subset['Route Code'] = df_wt_subset[wt_col_route].astype(str).str.strip().str.upper()
        df_wt_subset['Dominant Marketing Airline'] = df_wt_subset[wt_col_al].astype(str).str.strip().str.upper()
        df_wt_subset = df_wt_subset.drop_duplicates(subset=['Route Code', 'Dominant Marketing Airline'], keep='first')

        valid_wt = df_wt_subset[df_wt_subset['Weight_ratio'] > 0]
        al_avg_weight_dict = valid_wt.groupby('Dominant Marketing Airline')['Weight_ratio'].mean().to_dict()

        merged_df = pd.merge(
            df, 
            df_wt_subset[['Route Code', 'Dominant Marketing Airline', 'Weight_ratio']], 
            left_on=['노선', 'Dominant Marketing Airline'], 
            right_on=['Route Code', 'Dominant Marketing Airline'], 
            how='left'
        )

        merged_df['Weight_ratio'] = pd.to_numeric(merged_df['Weight_ratio'], errors='coerce')

        mapped_avg = merged_df['Dominant Marketing Airline'].map(al_avg_weight_dict)
        merged_df['Weight_ratio_final'] = merged_df['Weight_ratio'].fillna(mapped_avg).fillna(1.0)

        merged_df['Weight_multiplier'] = merged_df['Weight_ratio_final'].apply(
            lambda r: (1.0 / r) if (pd.notna(r) and r > 0) else 1.0
        )
        
        merged_df['Value'] = pd.to_numeric(merged_df['Value'], errors='coerce').fillna(0)
        merged_df['Weighted_Value'] = merged_df['Value'] * merged_df['Weight_multiplier']

        merged_df.to_parquet('cache_34_data.parquet', index=False)
        print("✨ [1/2 완료] 'cache_34_data.parquet' 생성 성공!")
    else:
        print("⚠️ 3/4수송 CSV 또는 가중치 파일을 찾지 못했습니다. 파일명을 확인해 주세요.")

    # --- 2. 6수송 처리 ---
    print("⏳ [2/2] 6수송 대용량 데이터 압축 캐싱 수행 중...")
    if file_6th:
        print(f"  └ 📄 6수송 파일 감지: {file_6th}")
        df_6th = pd.read_csv(file_6th, low_memory=False)
        df_6th.columns = [str(c).strip() for c in df_6th.columns]
        df_6th.to_parquet('cache_6th_data.parquet', index=False)
        print("✨ [2/2 완료] 'cache_6th_data.parquet' 생성 성공!")
    else:
        print("⚠️ 6수송 CSV 파일을 찾지 못했습니다.")

if __name__ == '__main__':
    run_data_pipeline()