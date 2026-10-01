# batch_processor.py
import pandas as pd
import numpy as np
import os
import datetime

def process_batch_parquet():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. 원본 데이터 파일 탐색 (xlsx, csv 등)
    input_file = None
    possible_inputs = ['data_new.xlsx', '34수송.xlsx', '34수송.csv', '원본데이터.xlsx', '원본데이터.csv']
    
    for f in possible_inputs:
        full_path = os.path.join(base_dir, f)
        if os.path.exists(full_path):
            input_file = full_path
            break
            
    if not input_file:
        # 폴더 내 xlsx 또는 csv 파일 자동 탐색
        files = [f for f in os.listdir(base_dir) if f.endswith('.xlsx') or f.endswith('.csv')]
        files = [f for f in files if not f.startswith('cache_') and not f.startswith('~$')]
        if files:
            input_file = os.path.join(base_dir, files[0])

    if not input_file:
        print("❌ 원본 데이터 파일을 찾을 수 없습니다.")
        return

    print(f"📖 원본 파일 읽는 중: {os.path.basename(input_file)}")
    
    if input_file.endswith('.xlsx'):
        df = pd.read_excel(input_file)
    else:
        df = pd.read_csv(input_file, low_memory=False)

    # 2. 컬럼명 공백 제거 및 표준화
    df.columns = [str(c).strip() for c in df.columns]

    # 문자열 타입 정리
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip()

    # 3. 실적 수치형 변환
    if 'Value' in df.columns:
        df['Value'] = pd.to_numeric(df['Value'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    else:
        df['Value'] = 0

    if 'Weighted_Value' in df.columns:
        df['Weighted_Value'] = pd.to_numeric(df['Weighted_Value'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    else:
        df['Weighted_Value'] = df['Value']

    # 4. 안전한 HTML 피벗 생성 테스트 (KeyError 방지 예외 처리)
    week_col = '발매주차_일자' if '발매주차_일자' in df.columns else ('발매 주차' if '발매 주차' in df.columns else None)
    if week_col and 'O&D RBKD' in df.columns:
        week_list = sorted([str(x) for x in df[week_col].dropna().unique()], reverse=True)
        
        piv_rbd = df.pivot_table(index='O&D RBKD', columns=week_col, values='Value', aggfunc='sum', fill_value=0, observed=False)
        piv_rbd['총합계'] = piv_rbd.sum(axis=1)

        # KeyError 원인이었던 주차별 동적 참조 안전 처리 (.get 방식)
        rbd_html = ""
        for rbd_code, rbd_row in piv_rbd.iterrows():
            rbd_html += f'<tr><td style="width:180px; text-align:center; font-weight:700;">{rbd_code}</td>'
            for wk in week_list:
                # 핵심 보정: 해당 주차가 피벗 테이블 컬럼에 없더라도 0으로 안나게 처리
                wk_val = rbd_row.get(wk, 0)
                rbd_html += f'<td style="text-align:center;">{wk_val:,.0f}</td>'
            rbd_html += f'<td style="text-align:center; font-weight:700;">{rbd_row.get("총합계", 0):,.0f}</td></tr>'

    # 5. 최신 Parquet 파일로 최종 저장
    output_parquet = os.path.join(base_dir, 'cache_34_data.parquet')
    df.to_parquet(output_parquet, engine='pyarrow', index=False)
    
    print(f"✅ 파켓 캐시 파일 생성 성공: {output_parquet}")
    print(f"📌 저장된 총 행 수: {len(df):,}개 | 포함된 컬럼: {list(df.columns)}")

if __name__ == '__main__':
    process_batch_parquet()