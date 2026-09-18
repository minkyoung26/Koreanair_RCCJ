# batch_processor.py
import os
import glob
import pandas as pd
import numpy as np

def normalize_route_code(route_str):
    if not isinstance(route_str, str): return ""
    r = route_str.strip().upper()
    r = r.replace('ICN/', 'I/').replace('/ICN', '/I')
    r = r.replace('GMP/', 'G/').replace('/GMP', '/G')
    r = r.replace('PUS/', 'P/').replace('/PUS', '/P')
    r = r.replace('CJJ/', 'C/').replace('/CJJ', '/C')
    r = r.replace('TAE/', 'T/').replace('/TAE', '/T')
    return r

def process_34_transport_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. 3/4수송 파일 탐색
    csv_candidates = glob.glob(os.path.join(base_dir, "*34수송*.csv")) + glob.glob(os.path.join(base_dir, "*34*.csv"))
    if not csv_candidates:
        print("❌ 3/4수송 원본 CSV 파일을 찾을 수 없습니다.")
        return False
        
    main_csv_file = csv_candidates[0]
    print(f"📂 3/4수송 원본 CSV 로딩: {os.path.basename(main_csv_file)}")
    
    # 2. 가중치 파일 탐색
    wt_candidates = glob.glob(os.path.join(base_dir, "*가중치*.csv")) + glob.glob(os.path.join(base_dir, "*가중치*.xlsx"))
    wt_file = wt_candidates[0] if wt_candidates else None
    
    try:
        df = pd.read_csv(main_csv_file, low_memory=False)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Value 수치형 정제
        if 'Value' in df.columns:
            df['Value'] = pd.to_numeric(df['Value'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
        else:
            df['Value'] = 0.0

        al_col = 'Dominant Marketing Airline' if 'Dominant Marketing Airline' in df.columns else ('AL' if 'AL' in df.columns else '항공사')
        route_col = '노선' if '노선' in df.columns else 'Route'

        df['AL_join'] = df[al_col].astype(str).str.strip().str.upper() if al_col in df.columns else ''
        df['Route_norm'] = df[route_col].apply(normalize_route_code) if route_col in df.columns else ''

        # 3. 가중치 매핑
        if wt_file:
            print(f"📂 가중치 파일 로딩: {os.path.basename(wt_file)}")
            df_wt = pd.read_excel(wt_file) if wt_file.endswith('.xlsx') else pd.read_csv(wt_file)
            df_wt.columns = [str(c).strip() for c in df_wt.columns]
            
            wt_route_col = 'Route Code' if 'Route Code' in df_wt.columns else ('노선' if '노선' in df_wt.columns else df_wt.columns[0])
            wt_al_col = 'Dominant Marketing Airline' if 'Dominant Marketing Airline' in df_wt.columns else ('항공사' if '항공사' in df_wt.columns else df_wt.columns[1])
            wt_val_col = 'Weight' if 'Weight' in df_wt.columns else ('가중치' if '가중치' in df_wt.columns else df_wt.columns[-1])

            df_wt['Route_norm'] = df_wt[wt_route_col].apply(normalize_route_code)
            df_wt['AL_join'] = df_wt[wt_al_col].astype(str).str.strip().str.upper()
            
            def parse_weight_pct(val):
                v_str = str(val).replace('%', '').strip()
                try:
                    num = float(v_str)
                    return num / 100.0 if num > 5.0 else num
                except:
                    return 1.0

            df_wt['Weight_num'] = df_wt[wt_val_col].apply(parse_weight_pct)
            df_wt_sub = df_wt[['Route_norm', 'AL_join', 'Weight_num']].drop_duplicates(subset=['Route_norm', 'AL_join'])
            
            df = pd.merge(df, df_wt_sub, on=['Route_norm', 'AL_join'], how='left')
            df['Weight'] = df['Weight_num'].fillna(1.0)
            df.drop(columns=['Weight_num', 'AL_join', 'Route_norm'], inplace=True, errors='ignore')
            print("✅ 노선 코드 규격화 및 가중치 매핑 완료!")
        else:
            df['Weight'] = 1.0

        df['Weighted_Value'] = df['Value'] * df['Weight']

        b_col = '수송' if '수송' in df.columns else ('Bound' if 'Bound' in df.columns else None)
        if b_col: df['수송'] = df[b_col].astype(str).str.strip()

        output_parquet = os.path.join(base_dir, 'cache_34_data.parquet')
        df.to_parquet(output_parquet, index=False, compression='snappy')
        print(f"🎉 가중치 매핑 파켓 생성 완료: {os.path.basename(output_parquet)} (행 수: {len(df):,}개)")
        return True

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

if __name__ == "__main__":
    process_34_transport_data()