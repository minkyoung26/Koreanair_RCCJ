# batch_processor.py
import os
import glob
import pandas as pd
import numpy as np

def process_34_transport_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. 3/4수송 데이터 파일 탐색
    csv_candidates = glob.glob(os.path.join(base_dir, "*34수송*.csv")) + glob.glob(os.path.join(base_dir, "*34*.csv"))
    if not csv_candidates:
        print("❌ 3/4수송 원본 CSV 파일을 찾을 수 없습니다.")
        return False
        
    main_csv_file = csv_candidates[0]
    print(f"📂 3/4수송 원본 CSV 로딩: {os.path.basename(main_csv_file)}")
    
    # 2. 가중치 파일 탐색 (가중치 파일_7월.csv, 가중치 파일_8월.csv 등)
    wt_candidates = glob.glob(os.path.join(base_dir, "*가중치*.csv")) + glob.glob(os.path.join(base_dir, "*가중치*.xlsx"))
    wt_file = wt_candidates[0] if wt_candidates else None
    
    try:
        # 3/4수송 데이터 로드
        df = pd.read_csv(main_csv_file, low_memory=False)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Value 수치형 정제
        if 'Value' in df.columns:
            df['Value'] = pd.to_numeric(df['Value'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
        else:
            df['Value'] = 0.0

        # 항공사 및 노선 컬럼 확인
        al_col = 'Dominant Marketing Airline' if 'Dominant Marketing Airline' in df.columns else ('AL' if 'AL' in df.columns else '항공사')
        route_col = '노선' if '노선' in df.columns else 'Route'

        df['AL_join'] = df[al_col].astype(str).str.strip().str.upper() if al_col in df.columns else ''
        df['Route_join'] = df[route_col].astype(str).str.strip() if route_col in df.columns else ''

        # 3. 가중치 파일 매핑 처리
        if wt_file:
            print(f"📂 가중치 파일 로딩 및 매핑 중: {os.path.basename(wt_file)}")
            if wt_file.endswith('.xlsx'):
                df_wt = pd.read_excel(wt_file)
            else:
                df_wt = pd.read_csv(wt_file)
                
            df_wt.columns = [str(c).strip() for c in df_wt.columns]
            
            # 가중치 파일 컬럼 정제
            wt_route_col = 'Route Code' if 'Route Code' in df_wt.columns else ('노선' if '노선' in df_wt.columns else df_wt.columns[0])
            wt_al_col = 'Dominant Marketing Airline' if 'Dominant Marketing Airline' in df_wt.columns else ('항공사' if '항공사' in df_wt.columns else df_wt.columns[1])
            wt_val_col = 'Weight' if 'Weight' in df_wt.columns else ('가중치' if '가중치' in df_wt.columns else df_wt.columns[-1])

            df_wt['Route_join'] = df_wt[wt_route_col].astype(str).str.strip()
            df_wt['AL_join'] = df_wt[wt_al_col].astype(str).str.strip().str.upper()
            
            # Weight % 수치 파싱 보정 (121% -> 1.21, 12% -> 0.12)
            def parse_weight_pct(val):
                val_str = str(val).replace('%', '').strip()
                try:
                    num = float(val_str)
                    return num / 100.0 if num > 5.0 else num
                except:
                    return 1.0

            df_wt['Weight_num'] = df_wt[wt_val_col].apply(parse_weight_pct)
            
            # 중복 키 제거 후 조인
            df_wt_sub = df_wt[['Route_join', 'AL_join', 'Weight_num']].drop_duplicates(subset=['Route_join', 'AL_join'])
            
            df = pd.merge(df, df_wt_sub, on=['Route_join', 'AL_join'], how='left')
            df['Weight'] = df['Weight_num'].fillna(1.0)
            df.drop(columns=['Weight_num', 'AL_join', 'Route_join'], inplace=True, errors='ignore')
            print("✅ 가중치 파일 조인 연산 성공!")
        else:
            print("⚠️ 가중치 파일을 찾지 못해 기본 가중치 1.0 적용")
            df['Weight'] = 1.0

        # Weighted_Value 실시간 계산
        df['Weighted_Value'] = df['Value'] * df['Weight']

        # 수송 컬럼 정제
        b_col = '수송' if '수송' in df.columns else ('Bound' if 'Bound' in df.columns else None)
        if b_col: df['수송'] = df[b_col].astype(str).str.strip()

        # 파켓으로 저장
        output_parquet = os.path.join(base_dir, 'cache_34_data.parquet')
        df.to_parquet(output_parquet, index=False, compression='snappy')
        print(f"🎉 가중치 매핑 파켓 생성 완료: {os.path.basename(output_parquet)} (행 수: {len(df):,}개)")
        return True

    except Exception as e:
        print(f"❌ 가중치 매핑 파켓 생성 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    process_34_transport_data()