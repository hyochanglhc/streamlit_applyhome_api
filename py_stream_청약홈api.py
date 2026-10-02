# -*- coding: utf-8 -*-

import datetime
import os
import urllib.parse
from dotenv import load_dotenv
import pandas as pd
from pandas.tseries.offsets import MonthEnd
import requests as rq
import streamlit as st

# 1. 페이지 설정
st.set_page_config(page_title="청약홈 APT분양정보", layout="wide")

# 폰트 및 여백 조절 CSS (글자 크기를 컴팩트하게 조절)
st.markdown(
    """
<style>
    /* 메인 타이틀 크기 */
    .main-title {
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 12px;
    }
    /* 섹션 제목 크기 */
    .sub-title {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 8px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 2. API Key 로드 (Streamlit Cloud secrets 우선, 로컬 .env 보조)
if "DATA_API_KEY" in st.secrets:
    data_key = st.secrets["DATA_API_KEY"]
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(current_dir, ".env")
    load_dotenv(dotenv_path=env_path)
    data_key = os.getenv("DATA_API_KEY")

if not data_key:
    st.error("❌ API 인증키가 설정되지 않았습니다. (.env 또는 st.secrets 확인)")
    st.stop()

data_key = urllib.parse.unquote(data_key)


# 3. API 호출 함수
@st.cache_data(show_spinner="분양정보 조회 중...")
def get_apt_list(selected_date):
    url = (
        "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"
    )
    params = {
        "page": 1,
        "perPage": 30000,
        "cond[RCRIT_PBLANC_DE::GTE]": selected_date,
        "serviceKey": data_key,
    }

    try:
        res = rq.get(url, params=params, timeout=10)
        json_data = res.json()
    except Exception as e:
        st.error(f"API 요청 오류: {e}")
        return pd.DataFrame()

    if "data" not in json_data or not json_data["data"]:
        return pd.DataFrame()

    df_temp = pd.DataFrame(json_data["data"])

    alist = [
        "HOUSE_MANAGE_NO",
        "PBLANC_NO",
        "HOUSE_SECD",
        "SUBSCRPT_AREA_CODE_NM",
        "RCRIT_PBLANC_DE",
        "HOUSE_NM",
        "HOUSE_SECD_NM",
        "HSSPLY_ZIP",
        "HSSPLY_ADRES",
        "TOT_SUPLY_HSHLDCO",
        "RCEPT_BGNDE",
        "RCEPT_ENDDE",
        "PRZWNER_PRESNATN_DE",
        "CNTRCT_CNCLS_BGNDE",
        "CNTRCT_CNCLS_ENDDE",
        "HMPG_ADRES",
        "CNSTRCT_ENTRPS_NM",
        "MDHS_TELNO",
        "BSNS_MBY_NM",
        "MVN_PREARNGE_YM",
        "PARCPRC_ULS_AT",
        "PBLANC_URL",
    ]
    b = "주택관리번호,공고번호,주택구분코드,공급지역명,모집공고일,주택명,주택구분코드명,우편번호,공급위치,공급규모,청약접수시작일,청약접수종료일,당첨자발표일,계약시작일,계약종료일,홈페이지주소,건설업체명(시공사),문의처,사업주체명(시행사),입주예정월,상한제,모집공고상세URL"
    blist = b.split(",")

    valid_cols = [c for c in alist if c in df_temp.columns]
    df = df_temp[valid_cols].copy()
    col_dict = dict(zip(alist, blist))
    df.rename(columns=col_dict, inplace=True)
    return df


@st.cache_data(show_spinner="상세정보 조회 중...")
def get_apt_detail(house_manage_no):
    url = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancMdl"
    params = {
        "page": 1,
        "perPage": 100,
        "cond[HOUSE_MANAGE_NO::EQ]": house_manage_no,
        "serviceKey": data_key,
    }

    try:
        res = rq.get(url, params=params, timeout=10)
        json_data = res.json()
    except Exception as e:
        st.error(f"상세정보 조회 오류: {e}")
        return pd.DataFrame()

    if "data" not in json_data or not json_data["data"]:
        return pd.DataFrame()

    df = pd.DataFrame(json_data["data"])
    cols = ["HOUSE_TY", "SUPLY_AR", "LTTOT_TOP_AMOUNT"]
    exist_cols = [c for c in cols if c in df.columns]

    df2 = df[exist_cols].copy()
    rename_map = {
        "HOUSE_TY": "주택형",
        "SUPLY_AR": "공급면적",
        "LTTOT_TOP_AMOUNT": "타입최고가",
    }
    df2.rename(columns=rename_map, inplace=True)

    if "공급면적" in df2.columns:
        df2["공급면적"] = pd.to_numeric(df2["공급면적"], errors="coerce")
        df2 = df2.sort_values(by="공급면적", ascending=True)
    return df2


# 4. 레이아웃
st.markdown('<div class="main-title">🏢 청약홈 APT분양정보</div>', unsafe_allow_html=True)
col_left, col_right = st.columns([7, 3])

# --- [좌측: 분양정보] ---
with col_left:
    with st.container(border=True):
        st.markdown('<div class="sub-title">검색조건</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 2, 1])

        short_sido = [
            "서울",
            "경기",
            "인천",
            "부산",
            "대전",
            "대구",
            "광주",
            "울산",
            "세종",
            "강원",
            "충북",
            "충남",
            "전북",
            "전남",
            "경북",
            "경남",
            "제주",
        ]
        sido = c1.selectbox("공급지역", short_sido, index=11)

        sdate = datetime.datetime.now() + MonthEnd(-6)
        edate = datetime.datetime.now() + MonthEnd(0)
        dates = [
            i.strftime("%Y-%m-%d") for i in pd.date_range(sdate, edate, freq="ME")
        ]
        selected_date = c2.selectbox(
            "모집공고월(yyyy-mm-dd)", dates, index=len(dates) - 1
        )

        c3.write("")
        c3.write("")
        search_clicked = c3.button("검색실행", use_container_width=True, type="primary")

    # [핵심] '검색실행' 버튼을 눌렀을 때만 데이터를 받아 세션에 저장
    if search_clicked:
        raw_df = get_apt_list(selected_date)

        if not raw_df.empty:
            filtered_df = raw_df[
                (raw_df["공급지역명"] == sido)
                & (raw_df["모집공고일"] >= selected_date)
            ]

            clist = [
                "모집공고일",
                "주택관리번호",
                "주택명",
                "공급규모",
                "공급위치",
                "사업주체명(시행사)",
                "입주예정월",
                "상한제",
            ]
            valid_clist = [c for c in clist if c in filtered_df.columns]
            st.session_state["display_df"] = filtered_df[valid_clist].reset_index(
                drop=True
            )
        else:
            st.session_state["display_df"] = pd.DataFrame()

    # 세션에 검색된 결과 데이터가 있을 때만 표를 렌더링
    if "display_df" in st.session_state:
        display_df = st.session_state["display_df"]

        if not display_df.empty:
            with st.container(border=True):
                st.markdown(
                    f'<div class="sub-title">검색내용 (총 {len(display_df)}건)</div>',
                    unsafe_allow_html=True,
                )

                event = st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=520,
                    selection_mode="single-row",
                    on_select="rerun",
                    hide_index=True,
                )

                csv = display_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="📥 검색결과 CSV 다운로드",
                    data=csv,
                    file_name=f"apt_list_{sido}_{selected_date}.csv",
                    mime="text/csv",
                )
        else:
            st.info("조회된 데이터가 없습니다.")

# --- [우측: 상세정보] ---
with col_right:
    with st.container(border=True):
        st.markdown('<div class="sub-title">상세정보</div>', unsafe_allow_html=True)
        st.caption("좌측 목록에서 주택을 클릭하면 타입별 최고가가 조회됩니다.")

    selected_rows = []
    if "event" in locals() and event.selection.rows:
        selected_rows = event.selection.rows

    if selected_rows and "display_df" in st.session_state:
        display_df = st.session_state["display_df"]
        selected_row_idx = selected_rows[0]
        house_no = display_df.iloc[selected_row_idx]["주택관리번호"]
        house_name = display_df.iloc[selected_row_idx]["주택명"]

        detail_df = get_apt_detail(house_no)

        with st.container(border=True):
            st.markdown(
                f'<div class="sub-title">[{house_name}] 타입별 상세</div>',
                unsafe_allow_html=True,
            )
            if not detail_df.empty:
                st.dataframe(
                    detail_df,
                    use_container_width=True,
                    height=450,
                    hide_index=True,
                )

                csv_detail = detail_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="📥 상세정보 CSV 다운로드",
                    data=csv_detail,
                    file_name=f"apt_detail_{house_no}.csv",
                    mime="text/csv",
                )
            else:
                st.info("해당 단지의 세부 타입 정보가 없습니다.")
    else:
        with st.container(border=True):
            st.info("👈 좌측 표에서 단지를 선택하세요.")
