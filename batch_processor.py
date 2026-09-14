# batch_processor.py
import pandas as pd
import numpy as np
import os

def run_34_data_pipeline():
    print("⏳ [1/2] 3/4수송 데이터 읽기, 수송 구분 정제 및 엑셀 수식 동일 가중치 연산 수행 중...")
    
    # 1. 파일 로드
    df_iss = None
    if os.path.exists('34수송_9월2주차.csv'):
        df_iss = pd.read_csv('34수송_9월2주차.csv', low_memory=False)
    elif os.path.exists('34수송_9월1주차_CSV_2.csv'):
        df_iss = pd.read_csv('34수송_9월1주차_CSV_2.csv', low_memory=False)
        
    df_wt = pd.read_csv('가중치 파일.csv', low_memory=False) if os.path.exists('가중치 파일.csv') else None

    if df_iss is None or df_wt is None:
        print("❌ CSV 파일이 준비되지 않았습니다. '34수송_9월2주차.csv'(또는 1주차)와 '가중치 파일.csv'가 폴더에 있는지 확인해주세요.")
        return

    df = df_iss.copy()
    df_wt_c = df_wt.copy()
    
    # 컬럼명 공백 제거
    df.columns = [str(c).strip() for c in df.columns]
    df_wt_c.columns = [str(c).strip() for c in df_wt_c.columns]

    # 📌 3TF, 4TF, OTHERS 수송 필드 정제
    bound_col = '수송' if '수송' in df.columns else ('Bound' if 'Bound' in df.columns else None)
    if bound_col:
        df['수송'] = df[bound_col].astype(str).str.strip()
        df['수송'] = df['수송'].replace({'nan': 'OTHERS', '': 'OTHERS', 'None': 'OTHERS'})

    # KE취항여부 필터링 ('취항' 노선만 필터)
    ke_service_col = 'KE취항여부' if 'KE취항여부' in df.columns else ('KE취항노선 여부' if 'KE취항노선 여부' in df.columns else None)
    if ke_service_col:
        df = df[df[ke_service_col].astype(str) == '취항'].reset_index(drop=True)

    df['노선'] = df['노선'].astype(str).str.strip()
    df['Dominant Marketing Airline'] = df['Dominant Marketing Airline'].astype(str).str.strip()

    # 발매주차 및 일자 결합
    date_sub_col = '발매일자 ' if '발매일자 ' in df.columns else ('발매일자' if '발매일자' in df.columns else None)
    week_col_raw = '발매 주차' if '발매 주차' in df.columns else ('발매주차' if '발매주차' in df.columns else None)
    if week_col_raw and date_sub_col and date_sub_col in df.columns:
        df['발매주차_일자'] = df[week_col_raw].astype(str) + " " + df[date_sub_col].astype(str)

    # 2. 가중치 파일 컬럼 파싱 (노선 + 항공사 복합키)
    wt_val_col = 'Weight' if 'Weight' in df_wt_c.columns else df_wt_c.columns[-1]
    df_wt_c['Weight_clean'] = df_wt_c[wt_val_col].astype(str).str.replace('%', '').str.strip()
    df_wt_c['Weight_ratio'] = pd.to_numeric(df_wt_c['Weight_clean'], errors='coerce') / 100.0
    
    wt_col_route = 'Route Code' if 'Route Code' in df_wt_c.columns else df_wt_c.columns[0]
    wt_col_al = 'Dominant Marketing Airline' if 'Dominant Marketing Airline' in df_wt_c.columns else df_wt_c.columns[1]

    df_wt_subset = df_wt_c[[wt_col_route, wt_col_al, 'Weight_ratio']].dropna(subset=[wt_col_route, wt_col_al]).copy()
    df_wt_subset['Route Code'] = df_wt_subset[wt_col_route].astype(str).str.strip()
    df_wt_subset['Dominant Marketing Airline'] = df_wt_subset[wt_col_al].astype(str).str.strip()

    # 중복 키 제거 (첫 번째 매칭값 사용 - 엑셀 VLOOKUP 동작과 동일)
    df_wt_subset = df_wt_subset.drop_duplicates(subset=['Route Code', 'Dominant Marketing Airline'], keep='first')

    # 3. [노선 + 항공사] 병합 (VLOOKUP 매칭)
    merged_df = pd.merge(
        df, 
        df_wt_subset[['Route Code', 'Dominant Marketing Airline', 'Weight_ratio']], 
        left_on=['노선', 'Dominant Marketing Airline'], 
        right_on=['Route Code', 'Dominant Marketing Airline'], 
        how='left'
    )

    # 4. 엑셀 수식 100% 매칭: IFERROR(1/VLOOKUP(...), 1) 처리
    merged_df['Weight_ratio'] = pd.to_numeric(merged_df['Weight_ratio'], errors='coerce')
    
    def convert_excel_weight(ratio):
        try:
            if pd.isna(ratio) or ratio <= 0:
                return 1.0
            return 1.0 / ratio
        except:
            return 1.0

    merged_df['Weight_num'] = merged_df['Weight_ratio'].apply(convert_excel_weight)
    
    # 5. Raw 실적 및 역수 가중치 실적 계산
    merged_df['Value'] = pd.to_numeric(merged_df['Value'], errors='coerce').fillna(0)
    merged_df['Raw_Weighted_Value'] = merged_df['Value'] * merged_df['Weight_num']

    # 6. 엑셀 SUMPRODUCT 노선별 분모 계산
    route_sumproduct = merged_df.groupby('노선', observed=False)['Raw_Weighted_Value'].transform('sum')
    route_raw_sum = merged_df.groupby('노선', observed=False)['Value'].transform('sum')

    # 7. 최종 가중치 실적 산출
    merged_df['Weighted_Ratio'] = np.where(route_sumproduct > 0, merged_df['Raw_Weighted_Value'] / route_sumproduct, 0)
    merged_df['Weighted_Value'] = merged_df['Weighted_Ratio'] * route_raw_sum

    # 8. 초경량 `.parquet` 캐시 파일로 저장
    merged_df.to_parquet('cache_34_data.parquet', index=False)
    print("✨ [2/2] 'cache_34_data.parquet' 파일로 3TF/4TF/OTHERS 수송 필드가 포함된 초고속 캐시 저장 성공!")

if __name__ == '__main__':
    run_34_data_pipeline()