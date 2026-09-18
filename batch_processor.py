# batch_processor.py
import pandas as pd
import numpy as np
import os
import glob

def process_and_save_cache():
    print("⚡ [Batch Processor] 원본 전체 데이터 파켓 캐시 재생성 시작...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 원본 3/4수송 파일 탐색
    iss_files = glob.glob(os.path.join(base_dir, '*34수송*.csv')) + glob.glob('*34수송*.csv') + glob.glob(os.path.join(base_dir, '*34수송*.xlsx'))
    if not iss_files:
        print("❌ 3/4수송 원본 CSV/XLSX 파일을 찾을 수 없습니다. 폴더 위치를 확인해 주세요.")
        return

    latest_iss = sorted(iss_files, key=os.path.getmtime, reverse=True)[0]
    print(f"📄 읽어올 원본 파일: {os.path.basename(latest_iss)}")
    
    if latest_iss.endswith('.csv'):
        df = pd.read_csv(latest_iss, low_memory=False)
    else:
        df = pd.read_excel(latest_iss)
        
    df.columns = [str(c).strip() for c in df.columns]
    
    # 수치형 변환
    if 'Value' in df.columns:
        df['Value'] = pd.to_numeric(df['Value'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    
    # Weight 가중치 정확 산출 (Raw Value * Weight)
    if 'Weight' in df.columns:
        w_num = pd.to_numeric(df['Weight'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(1.0)
        df['Weighted_Value'] = df['Value'] * w_num
    else:
        df['Weighted_Value'] = df['Value']

    # 수송 컬럼 정제
    b_col = '수송' if '수송' in df.columns else ('Bound' if 'Bound' in df.columns else None)
    if b_col:
        df['수송'] = df[b_col].astype(str).str.strip()

    # 결과 출력 (검증용)
    total_raw = df['Value'].sum()
    total_wt = df['Weighted_Value'].sum()
    print(f"📊 원본 데이터 총 행 수: {len(df):,}행")
    print(f"📊 Raw Value 총합: {total_raw:,.0f} | Weighted Value 총합: {total_wt:,.0f}")

    # 파켓 캐시 저장
    output_path = os.path.join(base_dir, 'cache_34_data.parquet')
    df.to_parquet(output_path, index=False)
    print("✅ [성공] 가중치 포함 전체 파켓 캐시(cache_34_data.parquet) 생성 완료!")

if __name__ == "__main__":
    process_and_save_cache()