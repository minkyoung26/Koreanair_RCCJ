# batch_processor_6th.py
import polars as pl
import pandas as pd
import datetime
import os
import csv

def find_header_row_index(file_path):
    """
    CSV 파일에서 실제 열 이름(Trip Market, Trip Destination 등)이 있는 
    정확한 행 번호(0부터 시작)를 검출합니다.
    """
    keywords = ["trip destination", "ticket purchase", "trip market", "dominant marketing airline", "trip origin"]
    
    encoding = 'utf-8-sig'
    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                row_str = " ".join(row).lower()
                if ("trip" in row_str or "ticket" in row_str or "market" in row_str) and ("origin" in row_str or "destination" in row_str or "airline" in row_str):
                    return idx, encoding
    except Exception:
        pass

    encoding = 'cp949'
    with open(file_path, 'r', encoding='cp949', errors='ignore') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            row_str = " ".join(row).lower()
            if ("trip" in row_str or "ticket" in row_str or "market" in row_str) and ("origin" in row_str or "destination" in row_str or "airline" in row_str):
                return idx, encoding

    return 0, 'utf-8-sig'

def load_file_to_polars(file_path):
    """상단 피벗 헤더를 정확히 건너뛰고 실제 컬럼 헤더부터 파싱하는 함수"""
    if file_path.endswith('.parquet'):
        return pl.read_parquet(file_path)
    
    skip_rows, encoding = find_header_row_index(file_path)
    print(f"  └ '{os.path.basename(file_path)}' 탐지된 실제 헤더 위치: {skip_rows + 1}번째 행 (인코딩: {encoding})")

    try:
        pdf = pd.read_csv(
            file_path, 
            skiprows=skip_rows, 
            encoding=encoding, 
            low_memory=False, 
            on_bad_lines='skip'
        )
        pdf.columns = [str(c).strip() for c in pdf.columns]
        df = pl.from_pandas(pdf)
    except Exception:
        df = pl.read_csv(
            file_path,
            skip_rows=skip_rows,
            has_header=True,
            infer_schema_length=10000,
            ignore_errors=True,
            truncate_ragged_lines=True,
            encoding=encoding
        )
        df = df.rename({c: str(c).strip() for c in df.columns})

    return df

def process_split_6th_freedom_raw(cy_file_path, py_file_path, dim_file_path, output_parquet_path="cache_6th_data.parquet"):
    print("🚀 금년/전년 분할 6수송 RAW 데이터 가공을 시작합니다...")
    
    if not os.path.exists(cy_file_path):
        print(f"❌ 금년 RAW 파일을 찾을 수 없습니다: {cy_file_path}")
        return
    if not os.path.exists(py_file_path):
        print(f"❌ 전년 RAW 파일을 찾을 수 없습니다: {py_file_path}")
        return

    print(f"📂 금년 데이터('{cy_file_path}') 읽는 중...")
    df_cy = load_file_to_polars(cy_file_path).with_columns([pl.lit("금년").alias("금년/전년")])
    
    print(f"📂 전년 데이터('{py_file_path}') 읽는 중...")
    df_py = load_file_to_polars(py_file_path).with_columns([pl.lit("전년").alias("금년/전년")])

    print(f"📊 금년 데이터: {len(df_cy):,}행 | 전년 데이터: {len(df_py):,}행")

    print("🔗 금년 데이터와 전년 데이터를 하나로 병합하는 중...")
    df_merged = pl.concat([df_cy, df_py], how="diagonal")
    print(f"📈 총 병합 데이터: {len(df_merged):,}행")

    col_map = {c.lower().replace(" ", "").replace("_", "").replace(".", ""): c for c in df_merged.columns}

    def get_actual_col_name(target_name):
        cleaned_target = target_name.lower().replace(" ", "").replace("_", "").replace(".", "")
        if cleaned_target in col_map:
            return col_map[cleaned_target]
        for k, v in col_map.items():
            if cleaned_target in k or k in cleaned_target:
                return v
        return target_name

    c_dest_country = get_actual_col_name("Trip Destination Country Code")
    c_orig_country = get_actual_col_name("Trip Origin Country Code")
    c_dest_name = get_actual_col_name("Trip Destination")
    c_orig_name = get_actual_col_name("Trip Origin")
    c_dest_code = get_actual_col_name("Trip Destination Code")
    c_orig_code = get_actual_col_name("Trip Origin Code")
    c_market = get_actual_col_name("Trip Market")
    c_stop1 = get_actual_col_name("Stop1")

    print(f"🔍 자동 매핑된 핵심 컬럼:")
    print(f"  └ Destination Country: [{c_dest_country}]")
    print(f"  └ Origin Country: [{c_orig_country}]")
    print(f"  └ Trip Market: [{c_market}]")

    print("⚡ 조건별 파생 컬럼 생성 및 데이터 변환 중...")
    
    has_stop1 = c_stop1 in df_merged.columns
    stop_expr = (pl.col(c_stop1).is_not_null() & (pl.col(c_stop1).cast(pl.Utf8).str.strip_chars() != "")) if has_stop1 else pl.lit(False)

    df_processed = df_merged.with_columns([
        # [3] Subroute
        pl.when(pl.col(c_dest_country).cast(pl.Utf8) == "JP")
          .then(pl.col(c_dest_name).cast(pl.Utf8))
          .otherwise(pl.col(c_orig_name).cast(pl.Utf8))
          .alias("Sub-Route"),
          
        # [4] 일본발/일본행
        pl.when(pl.col(c_orig_country).cast(pl.Utf8) == "JP")
          .then(pl.lit("일본발"))
          .otherwise(pl.lit("일본행"))
          .alias("DIRECTION"),
          
        # [5] 직항/경유
        pl.when(stop_expr)
          .then(pl.lit("경유"))
          .otherwise(pl.lit("직항"))
          .alias("STOP OVER"),
          
        # [6] Trip O&D Market
        (pl.col(c_market).cast(pl.Utf8).str.slice(0, 3) + pl.lit("-") + pl.col(c_market).cast(pl.Utf8).str.slice(-3, 3)).alias("Trip O&D Market"),
        
        # [9] 일본APO
        pl.when(pl.col(c_orig_country).cast(pl.Utf8) == "JP")
          .then(pl.col(c_orig_code).cast(pl.Utf8))
          .otherwise(pl.col(c_dest_code).cast(pl.Utf8))
          .alias("일본 APO"),
          
        # [10] 해외APO
        pl.when(pl.col(c_orig_country).cast(pl.Utf8) == "JP")
          .then(pl.col(c_dest_code).cast(pl.Utf8))
          .otherwise(pl.col(c_orig_code).cast(pl.Utf8))
          .alias("해외 APO"),
    ])

    # [7] O&D Market
    df_processed = df_processed.with_columns([
        (
            pl.when(pl.col(c_orig_country).cast(pl.Utf8) == "JP")
              .then(pl.col(c_orig_code).cast(pl.Utf8) + pl.lit("-") + pl.col(c_dest_code).cast(pl.Utf8) + pl.lit("vv"))
              .otherwise(pl.col(c_dest_code).cast(pl.Utf8) + pl.lit("-") + pl.col(c_orig_code).cast(pl.Utf8) + pl.lit("vv"))
        ).alias("OD ON/OFF")
    ])

    # [8] O&D Region 매핑 (Dimension 마스터 파일 조인 + 데이터 타입 강제 변환)
    if os.path.exists(dim_file_path):
        print(f"📌 Dimension 마스터 파일('{dim_file_path}') 조인 진행 중...")
        if dim_file_path.endswith('.xlsx') or dim_file_path.endswith('.xls'):
            dim_df = pd.read_excel(dim_file_path)
            dim_pl = pl.from_pandas(dim_df)
        else:
            dim_pl = pl.read_csv(dim_file_path)
            
        dim_pl = dim_pl.rename({dim_pl.columns[0]: "APO_KEY", dim_pl.columns[1]: "RGN_NAME"})
        
        # 📌 [수정]: 조인 키 데이터 타입을 문자열(Utf8)로 강제 일치
        dim_pl = dim_pl.with_columns([
            pl.col("APO_KEY").cast(pl.Utf8).str.strip_chars().alias("APO_KEY"),
            pl.col("RGN_NAME").cast(pl.Utf8).alias("RGN_NAME")
        ])
        
        df_processed = df_processed.with_columns([
            pl.col("일본 APO").cast(pl.Utf8).str.strip_chars().alias("일본 APO")
        ])
        
        df_processed = df_processed.join(
            dim_pl, 
            left_on="일본 APO", 
            right_on="APO_KEY", 
            how="left"
        ).with_columns([
            pl.when(pl.col("RGN_NAME").is_not_null())
              .then(pl.lit("JPN-") + pl.col("RGN_NAME"))
              .otherwise(pl.lit("기타"))
              .alias("4.OD RGN")
        ]).drop(["RGN_NAME"])
    else:
        print(f"⚠️ Dimension 파일('{dim_file_path}')을 찾을 수 없어 O&D Region을 '기타'로 세팅합니다.")
        df_processed = df_processed.with_columns([pl.lit("기타").alias("4.OD RGN")])

    # 6. 대시보드 표현에 필요한 필수 컬럼 선택
    target_cols = [
        "Ticket Purchase month", "Trip Month", "Trip Origin Country Code", 
        "Trip Destination Country Code", "Dominant Marketing Airline",
        "금년/전년", "Sub-Route", "DIRECTION", "STOP OVER", "Trip O&D Market",
        "OD ON/OFF", "일본 APO", "해외 APO", "4.OD RGN", "Value"
    ]
    
    select_cols = []
    for tc in target_cols:
        matched = get_actual_col_name(tc)
        if matched in df_processed.columns:
            select_cols.append(matched)

    df_final = df_processed.select(list(set(select_cols)))

    # 7. 파켓 파일 저장
    df_final.write_parquet(output_parquet_path, compression="snappy")
    print(f"🎉 성공! 금년+전년 총 {len(df_final):,}행 가공 데이터가 '{output_parquet_path}' 파일로 완벽히 완성되었습니다!")

if __name__ == "__main__":
    CY_FILE_NAME = "6수송_금년.csv"    # 금년 RAW 파일명
    PY_FILE_NAME = "6수송_전년.csv"    # 전년 RAW 파일명
    DIM_FILE_NAME = "Dimension.xlsx"   # Dimension 마스터 파일명
    
    process_split_6th_freedom_raw(CY_FILE_NAME, PY_FILE_NAME, DIM_FILE_NAME)