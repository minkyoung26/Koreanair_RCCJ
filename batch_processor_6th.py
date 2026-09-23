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
    except Exception: pass

    encoding = 'cp949'
    with open(file_path, 'r', encoding='cp949', errors='ignore') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            row_str = " ".join(row).lower()
            if ("trip" in row_str or "ticket" in row_str or "market" in row_str) and ("origin" in row_str or "destination" in row_str or "airline" in row_str):
                return idx, encoding

    return 0, 'utf-8-sig'

# 📌 중복 헤더에 고유 번호 부여 함수
def make_unique_col_names(cols):
    seen = {}
    new_cols = []
    for c in cols:
        c_str = str(c).strip()
        if c_str in seen:
            seen[c_str] += 1
            new_cols.append(f"{c_str}_dup_{seen[c_str]}")
        else:
            seen[c_str] = 0
            new_cols.append(c_str)
    return new_cols

def load_file_and_clean_columns(file_path):
    skip_rows, encoding = find_header_row_index(file_path)
    print(f"  └ '{os.path.basename(file_path)}' 로딩 및 필요 필드 추출 중...")

    # 1. Pandas로 안전하게 읽기
    pdf = pd.read_csv(file_path, skiprows=skip_rows, encoding=encoding, low_memory=False, on_bad_lines='skip')
    pdf.columns = make_unique_col_names(pdf.columns)

    # 2. 정확한 분석 대상 컬럼 찾기 (대소문자/공백 무시)
    col_map = {c.lower().replace(" ", "").replace("_", "").replace(".", ""): c for c in pdf.columns}

    def get_col(target):
        cleaned = target.lower().replace(" ", "").replace("_", "").replace(".", "")
        if cleaned in col_map: return col_map[cleaned]
        for k, v in col_map.items():
            if cleaned in k or k in cleaned: return v
        return None

    c_pur_m = get_col("Ticket Purchase Month-YYYY MM") or get_col("Ticket Purchase month")
    c_trip_m = get_col("Trip Month-YYYY MM") or get_col("Trip Month")
    c_dest_country = get_col("Trip Destination Country Name Code") or get_col("Trip Destination Country Code")
    c_orig_country = get_col("Trip Origin Country Name Code") or get_col("Trip Origin Country Code")
    c_dest_code = get_col("Trip Destination Code")
    c_orig_code = get_col("Trip Origin Code")
    c_market = get_col("Trip Market") or get_col("Trip O&D")
    c_airline = get_col("Dominant Marketing Airline")
    c_value = get_col("Value")

    # 📌 필요한 9개 컬럼만 고유한 표준 명칭으로 재정의 후 추출 (중복 'Origin' 등 원천 차단)
    clean_pdf = pd.DataFrame()
    clean_pdf["Ticket Purchase month"] = pdf[c_pur_m] if c_pur_m else ""
    clean_pdf["Trip Month"] = pdf[c_trip_m] if c_trip_m else ""
    clean_pdf["Trip Origin Country Code"] = pdf[c_orig_country] if c_orig_country else ""
    clean_pdf["Trip Destination Country Code"] = pdf[c_dest_country] if c_dest_country else ""
    clean_pdf["Trip Origin Code"] = pdf[c_orig_code] if c_orig_code else ""
    clean_pdf["Trip Destination Code"] = pdf[c_dest_code] if c_dest_code else ""
    clean_pdf["Trip Market"] = pdf[c_market] if c_market else ""
    clean_pdf["Dominant Marketing Airline"] = pdf[c_airline] if c_airline else ""
    clean_pdf["Value"] = pdf[c_value] if c_value else 0

    return pl.from_pandas(clean_pdf)

def process_and_aggregate_6th_data(cy_file_path, py_file_path, dim_file_path, output_parquet_path="cache_6th_data.parquet"):
    print("🚀 6수송 RAW 데이터 정밀 매핑 및 사전 집계를 시작합니다...")
    if not os.path.exists(cy_file_path) or not os.path.exists(py_file_path):
        print("❌ 원본 CSV 파일을 찾을 수 없습니다.")
        return

    df_cy = load_file_and_clean_columns(cy_file_path).with_columns([pl.lit("금년").alias("금년/전년")])
    df_py = load_file_and_clean_columns(py_file_path).with_columns([pl.lit("전년").alias("금년/전년")])
    
    df_merged = pl.concat([df_cy, df_py], how="diagonal")

    month_dict = {"jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06","jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12"}
    
    def parse_str_to_ym(s):
        if not s: return ""
        st_s = str(s).strip()
        if "-" in st_s:
            parts = st_s.split("-")
            if len(parts) == 2:
                m_str, y_str = parts[0].lower(), parts[1]
                if m_str in month_dict:
                    y_full = "20" + y_str if len(y_str) == 2 else y_str
                    return f"{y_full}-{month_dict[m_str]}"
                if y_str.lower() in month_dict:
                    y_full = "20" + m_str if len(m_str) == 2 else m_str
                    return f"{y_full}-{month_dict[y_str.lower()]}"
        return st_s

    # 📌 10. Trip O&D v.v. (일본 공항 무조건 앞 배치)
    def make_vv_market(mkt_str, o_code, d_code, o_cntry):
        if not mkt_str or "/" in str(mkt_str): return str(mkt_str)
        p = str(mkt_str).replace(" ", "").split("-")
        if len(p) == 2:
            a1, a2 = p[0], p[1]
            is_o_jp = str(o_cntry).upper() in ["JP", "JPN"]
            if is_o_jp: return f"{a1}-{a2} v.v."
            else: return f"{a2}-{a1} v.v."
        return f"{mkt_str} v.v."

    is_jp_expr = pl.col("Trip Origin Country Code").cast(pl.Utf8).str.to_uppercase().str.strip_chars().is_in(["JP", "JPN"])

    # 📌 요청 조건 반영 연산
    df_processed = df_merged.with_columns([
        pl.col("Ticket Purchase month").cast(pl.Utf8).map_elements(parse_str_to_ym, return_dtype=pl.Utf8).alias("Ticket Purchase month"),
        pl.col("Trip Month").cast(pl.Utf8).map_elements(parse_str_to_ym, return_dtype=pl.Utf8).alias("Trip Month"),
        
        pl.when(is_jp_expr).then(pl.lit("일본발")).otherwise(pl.lit("일본행")).alias("DIRECTION"),
        
        pl.struct(["Trip Market", "Trip Origin Code", "Trip Destination Code", "Trip Origin Country Code"]).map_elements(
            lambda x: make_vv_market(x["Trip Market"], x["Trip Origin Code"], x["Trip Destination Code"], x["Trip Origin Country Code"]), return_dtype=pl.Utf8
        ).alias("Trip O&D Market"),
        
        pl.when(is_jp_expr).then(pl.col("Trip Origin Code").cast(pl.Utf8)).otherwise(pl.col("Trip Destination Code").cast(pl.Utf8)).alias("일본 APO"),
        pl.when(is_jp_expr).then(pl.col("Trip Destination Code").cast(pl.Utf8)).otherwise(pl.col("Trip Origin Code").cast(pl.Utf8)).alias("해외 APO"),
        
        pl.when(is_jp_expr)
          .then(pl.col("Trip Destination Country Code").cast(pl.Utf8).str.to_uppercase().str.strip_chars())
          .otherwise(pl.col("Trip Origin Country Code").cast(pl.Utf8).str.to_uppercase().str.strip_chars())
          .alias("DIM_LOOKUP_KEY"),
          
        pl.col("Value").cast(pl.Utf8).str.replace_all(",", "").cast(pl.Float64, strict=False).fill_null(0.0).alias("Value_num")
    ])

    # 📌 Dimension 파일 조인 (JPN- + AB열 값 조합)
    if os.path.exists(dim_file_path):
        dim_df = pd.read_excel(dim_file_path) if dim_file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(dim_file_path)
        dim_pl = pl.from_pandas(dim_df)
        dim_pl = dim_pl.rename({dim_pl.columns[0]: "DIM_KEY", dim_pl.columns[1]: "RGN_NAME"})
        dim_pl = dim_pl.with_columns([
            pl.col("DIM_KEY").cast(pl.Utf8).str.to_uppercase().str.strip_chars().alias("DIM_KEY"),
            pl.col("RGN_NAME").cast(pl.Utf8).str.strip_chars().alias("RGN_NAME")
        ])
        
        df_processed = df_processed.join(dim_pl, left_on="DIM_LOOKUP_KEY", right_on="DIM_KEY", how="left").with_columns([
            pl.when(pl.col("RGN_NAME").is_not_null() & (pl.col("RGN_NAME") != "") & (pl.col("RGN_NAME") != "nan"))
              .then(pl.lit("JPN-") + pl.col("RGN_NAME"))
              .otherwise(pl.lit("기타"))
              .alias("4.OD RGN")
        ]).drop(["RGN_NAME", "DIM_LOOKUP_KEY"])
    else:
        df_processed = df_processed.with_columns([pl.lit("기타").alias("4.OD RGN")]).drop(["DIM_LOOKUP_KEY"])

    final_group_cols = [
        "Ticket Purchase month", "Trip Month", "4.OD RGN", "DIRECTION",
        "Trip Origin Country Code", "Trip Destination Country Code", 
        "일본 APO", "해외 APO", "Trip O&D Market", "Dominant Marketing Airline", "금년/전년"
    ]

    df_aggregated = df_processed.group_by(final_group_cols).agg([pl.col("Value_num").sum().alias("Value")])
    df_aggregated.write_parquet(output_parquet_path, compression="snappy")
    print(f"🎉 성공! 캐시 파켓 파일('{output_parquet_path}')이 에러 없이 깔끔하게 생성되었습니다! ({len(df_aggregated):,}행)")

if __name__ == "__main__":
    process_and_aggregate_6th_data("6수송_금년.csv", "6수송_전년.csv", "Dimension.xlsx")