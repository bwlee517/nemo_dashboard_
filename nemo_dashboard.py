import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os

# 페이지 설정
st.set_page_config(page_title="NemoStore Advanced Dashboard", layout="wide", initial_sidebar_state="expanded")

# 커스텀 CSS (Premium Design)
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .insight-card {
        background-color: #e9ecef;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #007bff;
        margin-bottom: 20px;
    }
    h1 {
        color: #1e293b;
        font-weight: 800;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 데이터 로드 함수
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    db_path = os.path.join(parent_dir, "data", "nemostore.db") 
    
    if not os.path.exists(db_path):
        db_path = "nemostore.db"

    conn = sqlite3.connect(db_path)
    query = "SELECT * FROM stores"
    df = pd.read_sql(query, conn)
    conn.close()
    
    # 전처리
    df['deposit'] = df['deposit'].fillna(0)
    df['monthlyRent'] = df['monthlyRent'].fillna(0)
    df['premium'] = df['premium'].fillna(0)
    df['maintenanceFee'] = df['maintenanceFee'].fillna(0)
    
    # 상가당 평당가(만원/㎡) 계산
    df['rent_per_size'] = df['monthlyRent'] / df['size'].replace(0, 1)
    
    return df

# 글로벌 EDA 기준값 (eda_report.md 기반)
GLOBAL_AVG_DEPOSIT = 3450
GLOBAL_AVG_RENT = 260
GLOBAL_TOTAL_COUNT = 333

# 데이터 실행
try:
    df = load_data()
except Exception as e:
    st.error(f"데이터 로드 실패: {e}")
    st.stop()

# 사이드바 설정
st.sidebar.image("https://www.nemoapp.kr/image/common/nemo_logo.svg", width=150)
st.sidebar.title("💎 Premium Filter")

# 1. 텍스트 검색
search_query = st.sidebar.text_input("📍 키워드 검색 (제목/업종)", placeholder="예: 카페, 을지로, 대형")

# 2. 가격 조건 필터
st.sidebar.markdown("---")
st.sidebar.subheader("💰 Price Configuration")
deposit_range = st.sidebar.slider("보증금 (만원)", 0, int(df['deposit'].max()), (0, int(df['deposit'].max())))
rent_range = st.sidebar.slider("월세 (만원)", 0, int(df['monthlyRent'].max()), (0, int(df['monthlyRent'].max())))
premium_range = st.sidebar.slider("권리금 (만원)", 0, int(df['premium'].max()), (0, int(df['premium'].max())))
maint_range = st.sidebar.slider("관리비 (만원)", 0, int(df['maintenanceFee'].max()), (0, int(df['maintenanceFee'].max())))

# 필터링
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

# 메인 헤더
st.title("🏢 NemoStore Insight Dashboard")
st.markdown(f"선택된 조건에 따라 총 **{len(filtered_df)}**개의 매물을 분석 중입니다.")

# 💡 EDA Insight Section
with st.container():
    st.subheader("💡 Analysis Insights (from EDA Report)")
    cols = st.columns(3)
    
    # 동적 분석 로직
    avg_rent = filtered_df['monthlyRent'].mean() if not filtered_df.empty else 0
    top_biz = filtered_df['businessMiddleCodeName'].mode()[0] if not filtered_df.empty else "N/A"
    
    rent_diff = avg_rent - GLOBAL_AVG_RENT
    rent_status = "높음 📈" if rent_diff > 0 else "낮음 📉"
    
    with cols[0]:
        st.markdown(f"""
        <div class="insight-card">
            <h4>상권 특성</h4>
            <p>현재 검색된 매물 중 가장 많은 업종은 <b>{top_biz}</b>입니다. 이는 전체 상권의 중심 트렌드와 일치하는 경향을 보입니다.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with cols[1]:
        st.markdown(f"""
        <div class="insight-card">
            <h4>가격 수준 비교</h4>
            <p>필터링된 매물의 평균 월세는 <b>{avg_rent:.1f}만원</b>으로, 전체 평균({GLOBAL_AVG_RENT}만원) 대비 <b>{abs(rent_diff):.1f}만원 {rent_status}</b> 상태입니다.</p>
        </div>
        """, unsafe_allow_html=True)

    with cols[2]:
        st.markdown("""
        <div class="insight-card">
            <h4>입지 인사이트</h4>
            <p>보고서에 따르면 <b>을지로/종로 CBD</b> 구역은 높은 평당 임대료를 형성합니다. 대형 오피스 빌딩 내 지하 매물은 면적 대비 효율성을 고려하십시오.</p>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# 주요 지표
m1, m2, m3, m4 = st.columns(4)
m1.metric("평균 보증금", f"{filtered_df['deposit'].mean():,.0f} 만원", f"전체 평균 대비 {filtered_df['deposit'].mean() - GLOBAL_AVG_DEPOSIT:,.0f}")
m2.metric("평균 월세", f"{filtered_df['monthlyRent'].mean():,.0f} 만원", f"{rent_diff:,.1f}", delta_color="inverse")
m3.metric("평균 권리금", f"{filtered_df['premium'].mean():,.0f} 만원")
m4.metric("평균 면적", f"{filtered_df['size'].mean():.1f} ㎡")

# 시각화
st.divider()
c1, c2 = st.columns([2, 3])

with c1:
    st.subheader("📊 Category Distribution")
    biz_counts = filtered_df['businessMiddleCodeName'].value_counts().reset_index()
    biz_counts.columns = ['Category', 'Count']
    fig_pie = px.pie(biz_counts.head(10), values='Count', names='Category', hole=0.5,
                     color_discrete_sequence=px.colors.qualitative.Bold,
                     template="plotly_white")
    fig_pie.update_layout(showlegend=True, margin=dict(t=30, b=10, l=10, r=10))
    st.plotly_chart(fig_pie, use_container_width=True)

with c2:
    st.subheader("🎯 Size vs Rent Efficiency")
    fig_scatter = px.scatter(filtered_df, x='size', y='monthlyRent', 
                             color='businessMiddleCodeName', size='deposit',
                             hover_name='title',
                             labels={'size': 'Area (㎡)', 'monthlyRent': 'Rent (k KRW)'},
                             template="plotly_white",
                             color_discrete_sequence=px.colors.qualitative.Vivid)
    fig_scatter.update_layout(margin=dict(t=30, b=10, l=10, r=10))
    st.plotly_chart(fig_scatter, use_container_width=True)

# 하단 분석
st.divider()
st.subheader("📉 Price Distribution & Outliers")
fig_box = px.box(filtered_df, x='businessMiddleCodeName', y='monthlyRent', 
                 color='businessMiddleCodeName', points="all",
                 labels={'businessMiddleCodeName': 'Business Type', 'monthlyRent': 'Monthly Rent'},
                 template="plotly_white")
fig_box.update_layout(showlegend=False)
st.plotly_chart(fig_box, use_container_width=True)

# 데이터 테이블
st.divider()
st.subheader("🔎 Matched Listings Detail")
st.dataframe(
    filtered_df[['title', 'businessMiddleCodeName', 'deposit', 'monthlyRent', 'premium', 'maintenanceFee', 'size', 'floor', 'nearSubwayStation']],
    use_container_width=True,
    height=400
)

# Footer
st.markdown("---")
st.caption("Powered by NemoStore EDA Engine | Data analysis based on 2025 listings.")
