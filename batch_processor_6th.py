# batch_processor_6th.py
import polars as pl
import pandas as pd
import os
import csv

def find_header_row_index(file_path):
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
    if file_path.endswith('.parquet'):
        return pl.read_parquet(file_path)
    
    skip_rows, encoding = find_header_row_index(file_path)
    print(f"  └ '{os.path.basename(file_path)}' 헤더 행({skip_rows + 1}번째) 파싱...")

    try:
        pdf = pd.read_csv(file_path, skiprows=skip_rows, encoding=encoding, low_memory=False, on_bad_lines='skip')
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

def process_and_aggregate_6th_data(cy_file_path, py_file_path, dim_file_path, output_parquet_path="cache_6th_data.parquet"):
    print("🚀 6수송 RAW 데이터 재가공 및 사전 집계를 시작합니다...")
    
    if not os.path.exists(cy_file_path) or not os.path.exists(py_file_path):
        print("❌ 금년/전년 원본 CSV 파일을 찾을 수 없습니다.")
        return

    # 1. RAW 데이터 로드
    print(f"📂 금년 데이터('{cy_file_path}') 읽는 중...")
    df_cy = load_file_to_polars(cy_file_path).with_columns([pl.lit("금년").alias("금년/전년")])
    
    print(f"📂 전년 데이터('{py_file_path}') 읽는 중...")
    df_py = load_file_to_polars(py_file_path).with_columns([pl.lit("전년").alias("금년/전년")])

    print(f"📊 원본 데이터: 금년 {len(df_cy):,}행 | 전년 {len(df_py):,}행")
    df_merged = pl.concat([df_cy, df_py], how="diagonal")

    # 2. 컬럼 매핑 자동 탐지
    col_map = {c.lower().replace(" ", "").replace("_", "").replace(".", ""): c for c in df_merged.columns}

    def get_actual_col_name(target_name):
        cleaned_target = target_name.lower().replace(" ", "").replace("_", "").replace(".", "")
        if cleaned_target in col_map: return col_map[cleaned_target]
        for k, v in col_map.items():
            if cleaned_target in k or k in cleaned_target: return v
        return target_name

    c_pur_m = get_actual_col_name("Ticket Purchase month")
    c_trip_m = get_actual_col_name("Trip Month")
    c_dest_country = get_actual_col_name("Trip Destination Country Code")
    c_orig_country = get_actual_col_name("Trip Origin Country Code")
    c_dest_code = get_actual_col_name("Trip Destination Code")
    c_orig_code = get_actual_col_name("Trip Origin Code")
    c_market = get_actual_col_name("Trip Market")
    c_airline = get_actual_col_name("Dominant Marketing Airline")
    c_value = get_actual_col_name("Value")

    # 📌 3. "X월" 포맷팅 처리 (숫자나 연월 뒤에 "월" 자동 부착)
    def format_month_expr(col_name):
        return (
            pl.when(pl.col(col_name).cast(pl.Utf8).str.ends_with("월"))
              .then(pl.col(col_name).cast(pl.Utf8))
              .otherwise(pl.col(col_name).cast(pl.Utf8) + pl.lit("월"))
        )

    # 📌 4. Dimension 조인용 Lookup Key 설정 (Origin이 "JP"이면 Destination Country, 아니면 Origin Country)
    df_processed = df_merged.with_columns([
        format_month_expr(c_pur_m).alias("Ticket Purchase month"),
        format_month_expr(c_trip_m).alias("Trip Month"),
        
        pl.when(pl.col(c_orig_country).cast(pl.Utf8) == "JP")
          .then(pl.lit("일본발"))
          .otherwise(pl.lit("일본행"))
          .alias("DIRECTION"),
          
        (pl.col(c_market).cast(pl.Utf8).str.slice(0, 3) + pl.lit("-") + pl.col(c_market).cast(pl.Utf8).str.slice(-3, 3)).alias("Trip O&D Market"),
        
        pl.when(pl.col(c_orig_country).cast(pl.Utf8) == "JP").then(pl.col(c_orig_code).cast(pl.Utf8)).otherwise(pl.col(c_dest_code).cast(pl.Utf8)).alias("일본 APO"),
        pl.when(pl.col(c_orig_country).cast(pl.Utf8) == "JP").then(pl.col(c_dest_code).cast(pl.Utf8)).otherwise(pl.col(c_orig_code).cast(pl.Utf8)).alias("해외 APO"),
        
        # OD Region 조인용 핵심 국가코드 Key
        pl.when(pl.col(c_orig_country).cast(pl.Utf8) == "JP")
          .then(pl.col(c_dest_country).cast(pl.Utf8).str.strip_chars())
          .otherwise(pl.col(c_orig_country).cast(pl.Utf8).str.strip_chars())
          .alias("DIM_LOOKUP_KEY"),
          
        pl.col(c_value).cast(pl.Utf8).str.replace_all(",", "").cast(pl.Float64, strict=False).fill_null(0.0).alias("Value_num")
    ])

    # 📌 5. Dimension 파일(AA열: Country Code, AB열: Region) 기반 O&D Region 매핑
    if os.path.exists(dim_file_path):
        print(f"📌 Dimension 마스터 파일('{dim_file_path}') 국가코드 조인 진행 중...")
        dim_df = pd.read_excel(dim_file_path) if dim_file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(dim_file_path)
        dim_pl = pl.from_pandas(dim_df)
        
        # 1번째 열(AA열): Country Code, 2번째 열(AB열): Region 명칭
        dim_pl = dim_pl.rename({dim_pl.columns[0]: "DIM_KEY", dim_pl.columns[1]: "RGN_NAME"})
        dim_pl = dim_pl.with_columns([
            pl.col("DIM_KEY").cast(pl.Utf8).str.strip_chars().alias("DIM_KEY"),
            pl.col("RGN_NAME").cast(pl.Utf8).str.strip_chars().alias("RGN_NAME")
        ])
        
        df_processed = df_processed.join(
            dim_pl, left_on="DIM_LOOKUP_KEY", right_on="DIM_KEY", how="left"
        ).with_columns([
            pl.when(pl.col("RGN_NAME").is_not_null() & (pl.col("RGN_NAME") != ""))
              .then(pl.lit("JPN-") + pl.col("RGN_NAME"))
              .otherwise(pl.lit("기타"))
              .alias("4.OD RGN")
        ]).drop(["RGN_NAME", "DIM_LOOKUP_KEY"])
    else:
        df_processed = df_processed.with_columns([pl.lit("기타").alias("4.OD RGN")]).drop(["DIM_LOOKUP_KEY"])

    # 6. 컬럼명 정돈 및 사전 집계 (Groupby Sum)
    df_processed = df_processed.rename({
        c_orig_country: "Trip Origin Country Code",
        c_dest_country: "Trip Destination Country Code",
        c_airline: "Dominant Marketing Airline"
    })
    
    final_group_cols = [
        "Ticket Purchase month", "Trip Month", "4.OD RGN", "DIRECTION",
        "Trip Origin Country Code", "Trip Destination Country Code", 
        "일본 APO", "해외 APO", "Trip O&D Market", "Dominant Marketing Airline", "금년/전년"
    ]

    print("⚡ 대시보드 로딩 최적화를 위한 10개 차원 기준 사전 집계 축소 진행 중...")
    df_aggregated = df_processed.group_by(final_group_cols).agg([
        pl.col("Value_num").sum().alias("Value")
    ])

    print(f"📉 축소 결과: 2,126,992행 ➔ {len(df_aggregated):,}행으로 압축 완료!")

    # 7. 최적화 파켓 파일 저장
    df_aggregated.write_parquet(output_parquet_path, compression="snappy")
    print(f"🎉 성공! 초고속 연동 캐시 파일 '{output_parquet_path}' 생성이 완료되었습니다!")

if __name__ == "__main__":
    CY_FILE_NAME = "6수송_금년.csv"
    PY_FILE_NAME = "6수송_전년.csv"
    DIM_FILE_NAME = "Dimension.xlsx"
    
    process_and_aggregate_6th_data(CY_FILE_NAME, PY_FILE_NAME, DIM_FILE_NAME)