# batch_processor.py
import pandas as pd
import numpy as np
import os

def run_data_pipeline():
    print("⏳ [1/2] 3/4수송 데이터 읽기, 수송 구분 정제 및 엑셀 가중치 연산 수행 중...")
    
    # --- 1. 3/4 수송 처리 ---
    df_iss = None
    if os.path.exists('34수송_9월2주차.csv'):
        df_iss = pd.read_csv('34수송_9월2주차.csv', low_memory=False)
    elif os.path.exists('34수송_9월1주차_CSV_2.csv'):
        df_iss = pd.read_csv('34수송_9월1주차_CSV_2.csv', low_memory=False)
        
    df_wt = pd.read_csv('가중치 파일.csv', low_memory=False) if os.path.exists('가중치 파일.csv') else None

    if df_iss is not None and df_wt is not None:
        df = df_iss.copy()
        df_wt_c = df_wt.copy()
        
        df.columns = [str(c).strip() for c in df.columns]
        df_wt_c.columns = [str(c).strip() for c in df_wt_c.columns]

        # 3TF, 4TF, OTHERS 수송 필드 정제
        bound_col = '수송' if '수송' in df.columns else ('Bound' if 'Bound' in df.columns else None)
        if bound_col:
            df['수송'] = df[bound_col].astype(str).str.strip()
            df['수송'] = df['수송'].replace({'nan': 'OTHERS', '': 'OTHERS', 'None': 'OTHERS', 'NaN': 'OTHERS'})

        # KE취항여부 필터링
        ke_service_col = 'KE취항여부' if 'KE취항여부' in df.columns else ('KE취항노선 여부' if 'KE취항노선 여부' in df.columns else None)
        if ke_service_col:
            df = df[df[ke_service_col].astype(str) == '취항'].reset_index(drop=True)

        df['노선'] = df['노선'].astype(str).str.strip()
        df['Dominant Marketing Airline'] = df['Dominant Marketing Airline'].astype(str).str.strip()

        date_sub_col = '발매일자 ' if '발매일자 ' in df.columns else ('발매일자' if '발매일자' in df.columns else None)
        week_col_raw = '발매 주차' if '발매 주차' in df.columns else ('발매주차' if '발매주차' in df.columns else None)
        if week_col_raw and date_sub_col and date_sub_col in df.columns:
            df['발매주차_일자'] = df[week_col_raw].astype(str) + " " + df[date_sub_col].astype(str)

        wt_val_col = 'Weight' if 'Weight' in df_wt_c.columns else df_wt_c.columns[-1]
        df_wt_c['Weight_clean'] = df_wt_c[wt_val_col].astype(str).str.replace('%', '').str.strip()
        df_wt_c['Weight_ratio'] = pd.to_numeric(df_wt_c['Weight_clean'], errors='coerce') / 100.0
        
        wt_col_route = 'Route Code' if 'Route Code' in df_wt_c.columns else df_wt_c.columns[0]
        wt_col_al = 'Dominant Marketing Airline' if 'Dominant Marketing Airline' in df_wt_c.columns else df_wt_c.columns[1]

        df_wt_subset = df_wt_c[[wt_col_route, wt_col_al, 'Weight_ratio']].dropna(subset=[wt_col_route, wt_col_al]).copy()
        df_wt_subset['Route Code'] = df_wt_subset[wt_col_route].astype(str).str.strip()
        df_wt_subset['Dominant Marketing Airline'] = df_wt_subset[wt_col_al].astype(str).str.strip()
        df_wt_subset = df_wt_subset.drop_duplicates(subset=['Route Code', 'Dominant Marketing Airline'], keep='first')

        merged_df = pd.merge(
            df, 
            df_wt_subset[['Route Code', 'Dominant Marketing Airline', 'Weight_ratio']], 
            left_on=['노선', 'Dominant Marketing Airline'], 
            right_on=['Route Code', 'Dominant Marketing Airline'], 
            how='left'
        )

        merged_df['Weight_ratio'] = pd.to_numeric(merged_df['Weight_ratio'], errors='coerce')
        merged_df['Weight_num'] = merged_df['Weight_ratio'].apply(lambda r: 1.0 / r if (pd.notna(r) and r > 0) else 1.0)
        
        merged_df['Value'] = pd.to_numeric(merged_df['Value'], errors='coerce').fillna(0)
        merged_df['Raw_Weighted_Value'] = merged_df['Value'] * merged_df['Weight_num']

        route_sumproduct = merged_df.groupby('노선', observed=False)['Raw_Weighted_Value'].transform('sum')
        route_raw_sum = merged_df.groupby('노선', observed=False)['Value'].transform('sum')

        merged_df['Weighted_Ratio'] = np.where(route_sumproduct > 0, merged_df['Raw_Weighted_Value'] / route_sumproduct, 0)
        merged_df['Weighted_Value'] = merged_df['Weighted_Ratio'] * route_raw_sum

        merged_df.to_parquet('cache_34_data.parquet', index=False)
        print("✨ [1/2 완료] 'cache_34_data.parquet' 생성 성공!")
    else:
        print("⚠️ 3/4수송 CSV 또는 가중치 파일이 없습니다. 건너뜁니다.")

    # --- 2. 6수송 처리 (190MB 메모리 압축) ---
    print("⏳ [2/2] 6수송 대용량 데이터 압축 캐싱 수행 중...")
    df_6th = None
    if os.path.exists('6수송_9월2주차.csv'):
        df_6th = pd.read_csv('6수송_9월2주차.csv', low_memory=False)
    elif os.path.exists('6TRF TEST.csv'):
        df_6th = pd.read_csv('6TRF TEST.csv', low_memory=False)

    if df_6th is not None:
        df_6th.columns = [str(c).strip() for c in df_6th.columns]
        df_6th.to_parquet('cache_6th_data.parquet', index=False)
        print("✨ [2/2 완료] 'cache_6th_data.parquet' 생성 성공!")
    else:
        print("⚠️ 6수송 CSV 파일이 없습니다. 건너뜁니다.")

if __name__ == '__main__':
    run_data_pipeline()