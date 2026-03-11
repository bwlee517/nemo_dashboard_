import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

# 페이지 설정
st.set_page_config(page_title="네모스토어 매물 대시보드", layout="wide")

# 데이터 로드 함수
@st.cache_data
def load_data():
    db_path = "/Users/crispin/Desktop/inner_circle/innercircle_6/antigravity/fcicb6_proj2/nemostore/data/nemostore.db"
    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM stores"
    df = pd.read_sql(query, conn)
    conn.close()
    
    # 데이터 전처리 (결측치 처리 등)
    df['deposit'] = df['deposit'].fillna(0)
    df['monthlyRent'] = df['monthlyRent'].fillna(0)
    df['premium'] = df['premium'].fillna(0)
    df['maintenanceFee'] = df['maintenanceFee'].fillna(0)
    
    return df

# 데이터 로드
try:
    df = load_data()
except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

# 사이드바: 검색 및 필터
st.sidebar.title("🔍 검색 및 필터")

# 1. 텍스트 검색
search_query = st.sidebar.text_input("매물 제목 또는 업종 검색", "")

# 2. 가격 조건 필터 (슬라이더)
st.sidebar.subheader("💰 가격 조건 (만원)")
deposit_range = st.sidebar.slider(
    "보증금", 
    int(df['deposit'].min()), int(df['deposit'].max()), 
    (int(df['deposit'].min()), int(df['deposit'].max()))
)
rent_range = st.sidebar.slider(
    "월세", 
    int(df['monthlyRent'].min()), int(df['monthlyRent'].max()), 
    (int(df['monthlyRent'].min()), int(df['monthlyRent'].max()))
)
premium_range = st.sidebar.slider(
    "권리금", 
    int(df['premium'].min()), int(df['premium'].max()), 
    (int(df['premium'].min()), int(df['premium'].max()))
)
maint_range = st.sidebar.slider(
    "관리비", 
    int(df['maintenanceFee'].min()), int(df['maintenanceFee'].max()), 
    (int(df['maintenanceFee'].min()), int(df['maintenanceFee'].max()))
)

# 데이터 필터링 로직
filtered_df = df[
    (df['deposit'].between(deposit_range[0], deposit_range[1])) &
    (df['monthlyRent'].between(rent_range[0], rent_range[1])) &
    (df['premium'].between(premium_range[0], premium_range[1])) &
    (df['maintenanceFee'].between(maint_range[0], maint_range[1]))
]

if search_query:
    filtered_df = filtered_df[
        filtered_df['title'].str.contains(search_query, case=False, na=False) |
        filtered_df['businessMiddleCodeName'].str.contains(search_query, case=False, na=False)
    ]

# 메인 화면
st.title("🏢 네모스토어 매물 대시보드")
st.markdown(f"현재 구역 내 총 **{len(filtered_df)}**개의 매물이 검색되었습니다.")

# 상단 지표 (Metrics)
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("평균 보증금", f"{filtered_df['deposit'].mean():,.0f} 만원")
with col2:
    st.metric("평균 월세", f"{filtered_df['monthlyRent'].mean():,.0f} 만원")
with col3:
    st.metric("평균 권리금", f"{filtered_df['premium'].mean():,.0f} 만원")
with col4:
    st.metric("평균 전용면적", f"{filtered_df['size'].mean():.2f} ㎡")

st.divider()

# 시각화 영역
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 업종별 매물 분포")
    biz_counts = filtered_df['businessMiddleCodeName'].value_counts().reset_index()
    biz_counts.columns = ['업종', '매물수']
    fig_pie = px.pie(biz_counts, values='매물수', names='업종', hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_right:
    st.subheader("📈 면적 대비 월세 상관관계")
    fig_scatter = px.scatter(filtered_df, x='size', y='monthlyRent', 
                             color='businessMiddleCodeName',
                             size='deposit',
                             hover_data=['title'],
                             labels={'size': '전용면적(㎡)', 'monthlyRent': '월세(만원)'},
                             color_discrete_sequence=px.colors.qualitative.Safe)
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

col_bottom1, col_bottom2 = st.columns(2)

with col_bottom1:
    st.subheader("💰 월세 분포 히스토그램")
    fig_hist = px.histogram(filtered_df, x='monthlyRent', nbins=30,
                            labels={'monthlyRent': '월세(만원)', 'count': '매물수'},
                            color_discrete_sequence=['#636EFA'])
    st.plotly_chart(fig_hist, use_container_width=True)

with col_bottom2:
    st.subheader("🏢 층수별 평당 임대료 추이 (예시)")
    # areaPrice가 있다면 활용, 없다면 계산
    if 'areaPrice' not in filtered_df.columns:
         filtered_df['areaPrice'] = filtered_df['monthlyRent'] / filtered_df['size']
    
    fig_box = px.box(filtered_df, x='floor', y='monthlyRent', 
                     points="all", 
                     labels={'floor': '층', 'monthlyRent': '월세(만원)'},
                     color_discrete_sequence=['#EF553B'])
    st.plotly_chart(fig_box, use_container_width=True)

# 상세 데이터 테이블
st.divider()
st.subheader("📋 매물 상세 정보")
st.dataframe(
    filtered_df[['title', 'businessMiddleCodeName', 'deposit', 'monthlyRent', 'premium', 'maintenanceFee', 'size', 'floor', 'nearSubwayStation']],
    use_container_width=True
)
