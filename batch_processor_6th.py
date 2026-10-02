# batch_processor_6th.py
import polars as pl
import pandas as pd
import os
import csv

def find_header_row_index(file_path):
    keywords = ["trip", "ticket", "market", "airline", "origin", "destination", "value", "pax"]
    encoding = 'utf-8-sig'
    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                row_str = " ".join(row).lower()
                if any(k in row_str for k in keywords):
                    return idx, encoding
    except Exception: pass

    encoding = 'cp949'
    with open(file_path, 'r', encoding='cp949', errors='ignore') as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            row_str = " ".join(row).lower()
            if any(k in row_str for k in keywords):
                return idx, encoding

    return 0, 'utf-8-sig'

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
    print(f"\n📂 '{os.path.basename(file_path)}' 파일 분석 시작 (헤더 시작점: {skip_rows}행)...")

    pdf = pd.read_csv(file_path, skiprows=skip_rows, encoding=encoding, low_memory=False, on_bad_lines='skip')
    pdf.columns = make_unique_col_names(pdf.columns)

    col_map = {str(c).lower().replace(" ", "").replace("_", "").replace(".", ""): c for c in pdf.columns}

    # 🔥 비슷한 이름에 낚이지 않도록 '엄격한 일치' 방식으로 변경
    def get_col_strict(*targets):
        for t in targets:
            t_clean = t.lower().replace(" ", "").replace("_", "").replace(".", "")
            if t_clean in col_map: return col_map[t_clean]
        return None

    # 🌟 공항코드와 국가코드가 절대 섞이지 않도록 완벽 분리 🌟
    # 1. 국가 코드 (JP, US 등)
    c_orig_cntry_code = get_col_strict("Trip Origin Country Code", "Origin Country Code", "Orig Country Code", "출발국가코드")
    c_dest_cntry_code = get_col_strict("Trip Destination Country Code", "Destination Country Code", "Dest Country Code", "도착국가코드")
    
    # 2. 국가 이름 (JAPAN, UNITED STATES 등)
    c_orig_name = get_col_strict("Trip Origin Country Name", "Origin Country Name", "Trip Origin Country", "Origin Country", "출발국가")
    c_dest_name = get_col_strict("Trip Destination Country Name", "Destination Country Name", "Trip Destination Country", "Destination Country", "도착국가")

    # 3. 공항 코드 (NRT, LAX 등)
    c_orig_city = get_col_strict("Trip Origin Code", "Origin Code", "Trip Origin", "Origin", "출발공항", "출발")
    c_dest_city = get_col_strict("Trip Destination Code", "Destination Code", "Trip Destination", "Destination", "Dest", "도착공항", "도착")
    
    c_pur_m = get_col_strict("Ticket Purchase Month-YYYY MM", "Ticket Purchase month", "Purchase Month")
    c_trip_m = get_col_strict("Trip Month-YYYY MM", "Trip Month")
    c_market = get_col_strict("Trip Market", "Trip O&D", "Market", "O&D", "노선")
    c_airline = get_col_strict("Dominant Marketing Airline", "Marketing Airline", "Airline", "Carrier", "항공사")
    c_value = get_col_strict("Value", "Pax", "Passengers", "Passenger", "Bookings", "Tickets", "Total", "수송", "실적")
    c_stop1 = get_col_strict("STOP1", "Stops", "Stop", "경유")

    print(f"  ✔️ 매핑 결과 확인:")
    print(f"    - 출발 국가코드 컬럼 : {c_orig_cntry_code} (여기에 공항코드가 매핑되면 안됨!)")
    print(f"    - 도착 국가코드 컬럼 : {c_dest_cntry_code}")
    print(f"    - 출발 공항코드 컬럼 : {c_orig_city}")
    print(f"    - 도착 공항코드 컬럼 : {c_dest_city}")

    clean_pdf = pd.DataFrame()
    clean_pdf["Ticket Purchase month"] = pdf[c_pur_m] if c_pur_m else ""
    clean_pdf["Trip Month"] = pdf[c_trip_m] if c_trip_m else ""
    clean_pdf["Trip Origin Country Code"] = pdf[c_orig_cntry_code] if c_orig_cntry_code else ""
    clean_pdf["Trip Destination Country Code"] = pdf[c_dest_cntry_code] if c_dest_cntry_code else ""
    clean_pdf["Trip Origin Country Name"] = pdf[c_orig_name] if c_orig_name else ""
    clean_pdf["Trip Destination Country Name"] = pdf[c_dest_name] if c_dest_name else ""
    clean_pdf["Trip Origin Code"] = pdf[c_orig_city] if c_orig_city else ""
    clean_pdf["Trip Destination Code"] = pdf[c_dest_city] if c_dest_city else ""
    clean_pdf["Trip Market"] = pdf[c_market] if c_market else ""
    clean_pdf["Dominant Marketing Airline"] = pdf[c_airline] if c_airline else ""
    clean_pdf["Value"] = pdf[c_value] if c_value else 0
    clean_pdf["STOP1"] = pdf[c_stop1] if c_stop1 else ""

    clean_pdf = clean_pdf.dropna(subset=["Trip Origin Code", "Trip Destination Code"])
    clean_pdf = clean_pdf[
        (~clean_pdf["Trip Origin Code"].astype(str).str.lower().isin(['nan', 'none', '', 'null'])) &
        (~clean_pdf["Trip Destination Code"].astype(str).str.lower().isin(['nan', 'none', '', 'null']))
    ]
    
    return pl.from_pandas(clean_pdf)

def process_and_aggregate_6th_data(cy_file_path, py_file_path, dim_file_path, output_parquet_path="cache_6th_data.parquet"):
    print("\n🚀 6수송 RAW 데이터 정밀 매핑 및 사전 집계를 시작합니다...")
    
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

    def parse_simple_od(mkt_str, o_code, d_code):
        mkt_clean = str(mkt_str).replace(" ", "").replace("/", "").replace("-", "").strip()
        if mkt_clean and mkt_clean.lower() != "nan" and mkt_clean.lower() != "none" and len(mkt_clean) >= 6: 
            return f"{mkt_clean[:3]}-{mkt_clean[-3:]}"
        return f"{str(o_code).strip()}-{str(d_code).strip()}"

    def make_vv_market(o_code, d_code, o_cntry_code, d_cntry_code):
        o_c = str(o_cntry_code).upper().strip()
        d_c = str(d_cntry_code).upper().strip()
        o_str = str(o_code).strip()
        d_str = str(d_code).strip()
        is_o_jp = o_c in ["JP", "JPN", "JAPAN"]
        is_d_jp = d_c in ["JP", "JPN", "JAPAN"]

        if is_o_jp: return f"{o_str}-{d_str} v.v."
        elif is_d_jp: return f"{d_str}-{o_str} v.v."
        else: return f"{o_str}-{d_str} v.v."

    # 🌟 올바르게 분리된 국가코드 및 이름에서 'JP' 찾기 🌟
    is_jp_expr = pl.col("Trip Origin Country Code").cast(pl.Utf8).str.to_uppercase().str.strip_chars().is_in(["JP", "JPN", "JAPAN"]) | \
                 pl.col("Trip Origin Country Name").cast(pl.Utf8).str.to_uppercase().str.strip_chars().is_in(["JP", "JPN", "JAPAN"])
    is_dest_jp_expr = pl.col("Trip Destination Country Code").cast(pl.Utf8).str.to_uppercase().str.strip_chars().is_in(["JP", "JPN", "JAPAN"]) | \
                      pl.col("Trip Destination Country Name").cast(pl.Utf8).str.to_uppercase().str.strip_chars().is_in(["JP", "JPN", "JAPAN"])

    is_direct_expr = pl.col("STOP1").cast(pl.Utf8).str.strip_chars().str.to_lowercase().is_in(['', 'nan', 'none', 'null']) | pl.col("STOP1").is_null()

    df_processed = df_merged.with_columns([
        pl.col("Ticket Purchase month").cast(pl.Utf8).map_elements(parse_str_to_ym, return_dtype=pl.Utf8).alias("Ticket Purchase month"),
        pl.col("Trip Month").cast(pl.Utf8).map_elements(parse_str_to_ym, return_dtype=pl.Utf8).alias("Trip Month"),
        
        pl.col("Ticket Purchase month").cast(pl.Utf8).str.slice(-2, 2).map_elements(lambda x: f"{x}월" if x else "", return_dtype=pl.Utf8).alias("발매월_표시"),
        pl.col("Trip Month").cast(pl.Utf8).str.slice(-2, 2).map_elements(lambda x: f"{x}월" if x else "", return_dtype=pl.Utf8).alias("출발월_표시"),

        pl.when(is_jp_expr).then(pl.lit("일본발"))
          .when(is_dest_jp_expr).then(pl.lit("일본행"))
          .otherwise(pl.lit("기타")).alias("DIRECTION"),
          
        pl.when(is_direct_expr).then(pl.lit("직항")).otherwise(pl.lit("경유")).alias("직항/경유"),

        pl.struct(["Trip Market", "Trip Origin Code", "Trip Destination Code"]).map_elements(
            lambda x: parse_simple_od(x["Trip Market"], x["Trip Origin Code"], x["Trip Destination Code"]), return_dtype=pl.Utf8
        ).alias("Trip O&D"),

        pl.struct(["Trip Origin Code", "Trip Destination Code", "Trip Origin Country Code", "Trip Destination Country Code"]).map_elements(
            lambda x: make_vv_market(x["Trip Origin Code"], x["Trip Destination Code"], x["Trip Origin Country Code"], x["Trip Destination Country Code"]), return_dtype=pl.Utf8
        ).alias("Trip O&D Market"),
        
        pl.when(is_jp_expr).then(pl.col("Trip Origin Code").cast(pl.Utf8)).otherwise(pl.col("Trip Destination Code").cast(pl.Utf8)).alias("일본 APO"),
        pl.when(is_jp_expr).then(pl.col("Trip Destination Code").cast(pl.Utf8)).otherwise(pl.col("Trip Origin Code").cast(pl.Utf8)).alias("해외 APO"),
        
        # 🔥 Dimension 매핑을 위해 일본의 '상대방 국가코드'를 추출
        pl.when(is_jp_expr).then(pl.col("Trip Destination Country Code"))
          .when(is_dest_jp_expr).then(pl.col("Trip Origin Country Code"))
          .otherwise(pl.lit(""))
          .cast(pl.Utf8).str.to_uppercase().str.strip_chars().alias("DIM_LOOKUP_KEY_CODE"),
          
        pl.col("Value").cast(pl.Utf8).str.replace_all(",", "").cast(pl.Float64, strict=False).fill_null(0.0).alias("Value_num")
    ])

    # 🌟 지시하신 대로 Dimension.xlsx의 AA열(Country Code)과 AB열(Region Name) 강제 매핑 🌟
    if os.path.exists(dim_file_path):
        print("  ✔️ Dimension 파일 처리 중 (AA열: 국가코드, AB열: 권역명 고정 매핑)...")
        # AA:AB 열 강제 지정 (AA=첫 번째 데이터, AB=두 번째 데이터)
        dim_df = pd.read_excel(dim_file_path, usecols="AA:AB")
        dim_df.columns = ["DIM_KEY", "RGN_NAME"]
        dim_df = dim_df.dropna(how='all')
        
        dim_pl = pl.from_pandas(dim_df).with_columns([
            pl.col("DIM_KEY").cast(pl.Utf8).str.to_uppercase().str.strip_chars(),
            pl.col("RGN_NAME").cast(pl.Utf8).str.strip_chars()
        ])
        
        df_processed = df_processed.join(dim_pl, left_on="DIM_LOOKUP_KEY_CODE", right_on="DIM_KEY", how="left").with_columns([
            pl.when(pl.col("RGN_NAME").is_not_null() & (pl.col("RGN_NAME") != "") & (pl.col("RGN_NAME") != "nan"))
              .then(pl.lit("JPN-") + pl.col("RGN_NAME"))
              .otherwise(pl.lit("기타"))
              .alias("4.OD RGN")
        ]).drop(["RGN_NAME", "DIM_LOOKUP_KEY_CODE"])
    else:
        print("  🚨 Dimension.xlsx 파일을 찾을 수 없어 권역이 '기타'로 세팅됩니다.")
        df_processed = df_processed.with_columns([pl.lit("기타").alias("4.OD RGN")]).drop(["DIM_LOOKUP_KEY_CODE"])

    final_group_cols = [
        "Ticket Purchase month", "Trip Month", "발매월_표시", "출발월_표시", "4.OD RGN", "DIRECTION", "직항/경유",
        "Trip Origin Country Code", "Trip Destination Country Code", 
        "일본 APO", "해외 APO", "Trip O&D", "Trip O&D Market", "Dominant Marketing Airline", "금년/전년"
    ]

    df_aggregated = df_processed.group_by(final_group_cols).agg([pl.col("Value_num").sum().alias("Value")])
    df_aggregated.write_parquet(output_parquet_path, compression="snappy")
    print(f"\n🎉 성공! 캐시 파켓 파일('{output_parquet_path}')이 생성되었습니다! ({len(df_aggregated):,}행)")

if __name__ == "__main__":
    process_and_aggregate_6th_data("6수송_금년.csv", "6수송_전년.csv", "Dimension.xlsx")