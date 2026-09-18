# batch_processor.py
import os
import glob
import pandas as pd
import numpy as np

def process_34_transport_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. 3/4수송 원본 CSV 파일 찾기
    csv_candidates = glob.glob(os.path.join(base_dir, "*34수송*.csv")) + glob.glob(os.path.join(base_dir, "*34*.csv"))
    
    if not csv_candidates:
        print("❌ 3/4수송 원본 CSV 파일을 찾을 수 없습니다.")
        return False
        
    csv_file = csv_candidates[0]
    print(f"📂 원본 CSV 파일 로딩 중: {os.path.basename(csv_file)}")
    
    try:
        # 2. 원본 CSV 파일 읽기
        df = pd.read_csv(csv_file, low_memory=False)
        df.columns = [str(c).strip() for c in df.columns]
        
        # 3. 수치형 컬럼 정제 및 가중치(Weighted_Value) 실시간 강제 계산
        if 'Value' in df.columns:
            v_clean = df['Value'].astype(str).str.replace(',', '').str.strip()
            df['Value'] = pd.to_numeric(v_clean, errors='coerce').fillna(0)
        else:
            df['Value'] = 0

        # Weight(가중치) 컬럼 추출 및 계산 (KMJ 등 가중치 노선 수치 보정)
        if 'Weight' in df.columns:
            w_clean = df['Weight'].astype(str).str.replace(',', '').str.strip()
            w_num = pd.to_numeric(w_clean, errors='coerce').fillna(1.0)
            df['Weight'] = w_num
            df['Weighted_Value'] = df['Value'] * w_num
        elif 'Weighted_Value' in df.columns:
            wv_clean = df['Weighted_Value'].astype(str).str.replace(',', '').str.strip()
            df['Weighted_Value'] = pd.to_numeric(wv_clean, errors='coerce').fillna(0)
        else:
            df['Weight'] = 1.0
            df['Weighted_Value'] = df['Value']

        # 4. Bound/수송 컬럼 공백 제거
        b_col = '수송' if '수송' in df.columns else ('Bound' if 'Bound' in df.columns else None)
        if b_col:
            df['수송'] = df[b_col].astype(str).str.strip()

        # 5. 경량화된 Parquet 파일로 저장
        output_parquet = os.path.join(base_dir, 'cache_34_data.parquet')
        df.to_parquet(output_parquet, index=False, compression='snappy')
        print(f"✅ 가중치가 반영된 파켓 캐시 생성 완료: {os.path.basename(output_parquet)} (행 수: {len(df):,}개)")
        return True

    except Exception as e:
        print(f"❌ 파켓 캐시 생성 중 오류 발생: {e}")
        return False

if __name__ == "__main__":
    process_34_transport_data()