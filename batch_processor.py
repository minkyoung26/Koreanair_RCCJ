# batch_processor.py
import pandas as pd
import numpy as np
import os
import glob

def process_and_save_cache():
    print("⚡ [Batch Processor] 원본 CSV 전체(All) 데이터 캐시 생성 시작...")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 3/4수송 원본 파일 탐색
    iss_files = glob.glob(os.path.join(base_dir, '*34수송*.csv')) + glob.glob(os.path.join(base_dir, '*34수송*.xlsx')) + glob.glob('*34수송*.csv')
    if not iss_files:
        print("❌ 3/4수송 원본 CSV/XLSX 파일을 찾을 수 없습니다.")
        return

    latest_iss = sorted(iss_files, key=os.path.getmtime, reverse=True)[0]
    print(f"📄 읽어올 원본 파일: {os.path.basename(latest_iss)}")
    
    if latest_iss.endswith('.csv'):
        df = pd.read_csv(latest_iss, low_memory=False)
    else:
        df = pd.read_excel(latest_iss)
        
    df.columns = [str(c).strip() for c in df.columns]
    
    # Value 및 Weighted_Value 수치형 변환
    if 'Value' in df.columns:
        df['Value'] = pd.to_numeric(df['Value'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    
    if 'Weighted_Value' in df.columns:
        df['Weighted_Value'] = pd.to_numeric(df['Weighted_Value'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(0)
    elif 'Value' in df.columns and 'Weight' in df.columns:
        df['Weight_num'] = pd.to_numeric(df['Weight'].astype(str).str.replace(',', '').str.strip(), errors='coerce').fillna(1.0)
        df['Weighted_Value'] = df['Value'] * df['Weight_num']
    else:
        df['Weighted_Value'] = df['Value']

    # 수송 컬럼 정제
    b_col = '수송' if '수송' in df.columns else ('Bound' if 'Bound' in df.columns else None)
    if b_col:
        df['수송'] = df[b_col].astype(str).str.strip()

    # 📌 임의 필터링 없이 원본 전체 데이터를 Parquet 캐시로 저장
    output_path = os.path.join(base_dir, 'cache_34_data.parquet')
    df.to_parquet(output_path, index=False)
    print(f"✅ [완료] 원본 100% 반영 cache_34_data.parquet 생성 완료! (행 개수: {len(df):,}개)")

if __name__ == "__main__":
    process_and_save_cache()