# -*- coding: utf-8 -*-

import datetime
import pandas as pd
from pandas.tseries.offsets import MonthEnd
import requests as rq
import streamlit as st
#from mylib import mykey
import os
from dotenv import load_dotenv

# 1. 페이지 설정 (넓은 화면 모드)
st.set_page_config(page_title="청약홈 APT분양정보", layout="wide")

# API Key 가져오기
#data_key = mykey.key1()
load_dotenv()
data_key = os.getenv('DATA_API_KEY')


# 2. 데이터 호출 함수 (캐싱 적용으로 중복 호출 방지)
@st.cache_data(show_spinner="분양정보 조회 중...")
def get_apt_list(selected_date):
    
    # 로컬 .env 또는 서버 환경 변수에서 가져옴
    data_key = st.secrets["DATA_API_KEY"]
    url = (
        "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"
        f"?page=1&perPage=30000&cond%5BRCRIT_PBLANC_DE%3A%3AGTE%5D={selected_date}&serviceKey={data_key}"
    )
    res = rq.get(url)
    json_data = res.json()

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

    df = df_temp[alist].copy()
    df.columns = blist
    return df


@st.cache_data(show_spinner="상세정보 조회 중...")
def get_apt_detail(house_manage_no):
    url = (
        "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancMdl"
        f"?page=1&perPage=100&cond%5BHOUSE_MANAGE_NO%3A%3AEQ%5D={house_manage_no}&serviceKey={data_key}"
    )
    res = rq.get(url)
    json_data = res.json()

    if "data" not in json_data or not json_data["data"]:
        return pd.DataFrame()

    df = pd.DataFrame(json_data["data"])
    df2 = df[["HOUSE_TY", "SUPLY_AR", "LTTOT_TOP_AMOUNT"]].copy()
    df2.columns = ["주택형", "공급면적", "타입최고가"]
    df2["공급면적"] = pd.to_numeric(df2["공급면적"], errors="coerce")
    df2 = df2.sort_values(by="공급면적", ascending=True)
    return df2


# 3. 레이아웃 구성 (좌 7 : 우 3)
st.title("🏢 청약홈 APT분양정보")
col_left, col_right = st.columns([7, 3])

# --- [좌측: 분양정보] ---
with col_left:
    with st.container(border=True):
        st.subheader("검색조건")
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
        sido = c1.selectbox("공급지역", short_sido, index=11)  # 기본값 '충남'

        sdate = datetime.datetime.now() + MonthEnd(-6)
        edate = datetime.datetime.now() + MonthEnd(0)
        dates = [i.strftime("%Y-%m-%d") for i in pd.date_range(sdate, edate, freq="ME")]
        selected_date = c2.selectbox("모집공고월(yyyy-mm-dd)", dates, index=len(dates) - 1)

        c3.write("")  # 수직 여백 정렬
        c3.write("")
        search_clicked = c3.button("검색실행", use_container_width=True, type="primary")

    if search_clicked:
        st.session_state["search_active"] = True

    # 세션 상태에 데이터 보존
    if st.session_state.get("search_active", False):
        raw_df = get_apt_list(selected_date)

        if not raw_df.empty:
            filtered_df = raw_df[
                (raw_df["공급지역명"] == sido) & (raw_df["모집공고일"] >= selected_date)
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
            display_df = filtered_df[clist].reset_index(drop=True)

            with st.container(border=True):
                st.subheader(f"검색내용 (총 {len(display_df)}건)")

                # 행 선택이 가능한 데이터프레임
                event = st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=520,
                    selection_mode="single-row",
                    on_select="rerun",
                    hide_index=True,
                )

                # 데이터 다운로드 (Tkinter의 클립보드 복사 대응)
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
        st.subheader("상세정보")
        st.caption("좌측 목록에서 주택을 클릭하면 타입별 최고가가 조회됩니다.")

    selected_rows = []
    if "event" in locals() and event.selection.rows:
        selected_rows = event.selection.rows

    if selected_rows:
        selected_row_idx = selected_rows[0]
        house_no = display_df.iloc[selected_row_idx]["주택관리번호"]
        house_name = display_df.iloc[selected_row_idx]["주택명"]

        detail_df = get_apt_detail(house_no)

        with st.container(border=True):
            st.write(f"**[{house_name}] 타입별 상세**")
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

