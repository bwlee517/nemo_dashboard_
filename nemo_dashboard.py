import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import ast
import numpy as np

# 페이지 설정
st.set_page_config(page_title="NemoStore v2 - Premium Insight", layout="wide", initial_sidebar_state="expanded")

# 커스텀 CSS (UI 개선)
st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .metric-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e2e8f0;
    }
    .benchmark-high { color: #e53e3e; font-weight: bold; }
    .benchmark-low { color: #38a169; font-weight: bold; }
    .gallery-title {
        font-size: 0.9rem;
        font-weight: 600;
        margin-top: 0.5rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .detail-header {
        background: linear-gradient(90deg, #1e293b 0%, #334155 100%);
        color: white;
        padding: 2rem;
        border-radius: 0.75rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# 변수 상환 (Friendly Column Names)
COLUMN_MAPPING = {
    'title': '매물명',
    'businessMiddleCodeName': '업종',
    'deposit': '보증금(만원)',
    'monthlyRent': '월세(만원)',
    'premium': '권리금(만원)',
    'maintenanceFee': '관리비(만원)',
    'size': '전용면적(㎡)',
    'floor': '층',
    'nearSubwayStation': '인근역',
    'viewCount': '조회수',
    'favoriteCount': '찜하기'
}

# 데이터 로드
@st.cache_data
def load_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    db_path = os.path.join(parent_dir, "data", "nemostore.db") 
    if not os.path.exists(db_path): db_path = "nemostore.db"
    
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM stores", conn)
    conn.close()
    
    # 전처리 루틴
    for col in ['deposit', 'monthlyRent', 'premium', 'maintenanceFee']:
        df[col] = df[col].fillna(0)
    
    # 평당가
    df['py_rent'] = df['monthlyRent'] / (df['size'] / 3.3).replace(0, 1)
    
    # 사진 데이터 파싱 (문자열 리스트 -> 실제 리스트)
    def parse_urls(x):
        try:
            if isinstance(x, str) and (x.startswith('[') or x.startswith('{')):
                return ast.literal_eval(x)
            return []
        except: return []
        
    df['photo_list'] = df['smallPhotoUrls'].apply(parse_urls)
    
    # 지도용 가상 좌표 생성 (을지로 1가 기준)
    np.random.seed(42)
    df['lat'] = 37.5665 + np.random.normal(0, 0.005, len(df))
    df['lon'] = 126.9850 + np.random.normal(0, 0.005, len(df))
    
    return df

df = load_data()

# 세션 상태 초기화
if 'selected_store_id' not in st.session_state:
    st.session_state.selected_store_id = None

# 사이드바
st.sidebar.title("🔍 Nemo Dashboard v2")
search_query = st.sidebar.text_input("매물명 또는 업종 검색", "")

# 카테고리 필터
categories = ["전체"] + sorted(df['businessMiddleCodeName'].unique().tolist())
selected_cat = st.sidebar.selectbox("업종 필터", categories)

# 가격 필터
st.sidebar.subheader("💰 상세 필터")
deposit_range = st.sidebar.slider("보증금(만원)", 0, int(df['deposit'].max()), (0, int(df['deposit'].max())))
rent_range = st.sidebar.slider("월세(만원)", 0, int(df['monthlyRent'].max()), (0, int(df['monthlyRent'].max())))

# 필터링 적용
filtered_df = df[
    (df['deposit'].between(deposit_range[0], deposit_range[1])) &
    (df['monthlyRent'].between(rent_range[0], rent_range[1]))
]
if selected_cat != "전체":
    filtered_df = filtered_df[filtered_df['businessMiddleCodeName'] == selected_cat]
if search_query:
    filtered_df = filtered_df[filtered_df['title'].str.contains(search_query, case=False, na=False)]

# --- 화면 전환 로직 ---
if st.session_state.selected_store_id is not None:
    # --- 상세페이지 뷰 ---
    store = df[df['id'] == st.session_state.selected_store_id].iloc[0]
    
    if st.button("⬅️ 목록으로 돌아가기"):
        st.session_state.selected_store_id = None
        st.rerun()
        
    st.markdown(f"""
    <div class="detail-header">
        <h1>{store['title']}</h1>
        <p>📍 {store['nearSubwayStation']} | 🏢 {store['businessMiddleCodeName']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col_img, col_info = st.columns([1, 1])
    
    with col_img:
        photos = store['photo_list']
        if photos:
            st.image(photos[0], use_container_width=True, caption="Main Photo")
            if len(photos) > 1:
                sub_cols = st.columns(min(4, len(photos)-1))
                for idx, p in enumerate(photos[1:5]):
                    sub_cols[idx].image(p, use_container_width=True)
        else:
            st.warning("이미지가 없습니다.")
            
    with col_info:
        st.subheader("📋 매물 상세 정보")
        info_df = pd.DataFrame({
            "항목": [COLUMN_MAPPING[k] for k in ['deposit', 'monthlyRent', 'premium', 'maintenanceFee', 'size', 'floor']],
            "정보": [
                f"{store['deposit']:,.0f} 만원", f"{store['monthlyRent']:,.0f} 만원",
                f"{store['premium']:,.0f} 만원", f"{store['maintenanceFee']:,.0f} 만원",
                f"{store['size']:.2f} ㎡", f"{store['floor']}층"
            ]
        })
        st.table(info_df)
        
        # Benchmarking
        st.subheader("⚖️ 시장 가치 분석 (Peers Benchmarking)")
        peer_df = df[df['businessMiddleCodeName'] == store['businessMiddleCodeName']]
        avg_rent_peer = peer_df['monthlyRent'].mean()
        diff_rent = ((store['monthlyRent'] - avg_rent_peer) / avg_rent_peer) * 100
        
        color = "benchmark-high" if diff_rent > 0 else "benchmark-low"
        status = "비쌈" if diff_rent > 0 else "저렴"
        st.markdown(f"""
        <div class="card">
            <p>동일 업종({store['businessMiddleCodeName']}) 평균 월세 <b>{avg_rent_peer:,.0f}만원</b> 대비 
            <span class="{color}"> {abs(diff_rent):.1f}% {status}</span> 합니다.
            </p>
        </div>
        """, unsafe_allow_html=True)

else:
    # --- 메인 대시보드 (갤러리/지도/테이블) ---
    st.title("🏙️ NemoStore Premium Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["🖼️ 갤러리 뷰", "🗺️ 지도 시각화", "📈 데이터 분석"])
    
    with tab1:
        st.write(f"총 {len(filtered_df)}개의 매물")
        # 갤러리 구현 (Grid)
        cols_per_row = 4
        rows = int(len(filtered_df) / cols_per_row) + 1
        
        for r in range(rows):
            grid_cols = st.columns(cols_per_row)
            for c in range(cols_per_row):
                idx = r * cols_per_row + c
                if idx < len(filtered_df):
                    row = filtered_df.iloc[idx]
                    with grid_cols[c]:
                        photos = row['photo_list']
                        img_url = photos[0] if photos else "https://via.placeholder.com/300x200?text=No+Image"
                        st.image(img_url, use_container_width=True)
                        st.markdown(f"<div class='gallery-title'>{row['title']}</div>", unsafe_allow_html=True)
                        st.caption(f"{row['monthlyRent']:,.0f} / {row['deposit']:,.0f}")
                        if st.button("상세보기", key=f"btn_{row['id']}"):
                            st.session_state.selected_store_id = row['id']
                            st.rerun()

    with tab2:
        st.subheader("📍 매물 위치 및 밀집도")
        # Map View
        st.map(filtered_df[['lat', 'lon']], zoom=13)
        st.info("💡 위 지도는 역 주변(을지로 권역)을 중심으로 한 시뮬레이션 위치입니다.")

    with tab3:
        # 기존 분석 + 가독성 높은 테이블
        st.subheader("📊 매물 상세 리스트")
        # 컬럼명 변경 적용
        display_df = filtered_df[['title', 'businessMiddleCodeName', 'deposit', 'monthlyRent', 'premium', 'maintenanceFee', 'size', 'floor', 'nearSubwayStation']].copy()
        display_df.columns = [COLUMN_MAPPING[c] for c in display_df.columns]
        st.dataframe(display_df, use_container_width=True)
        
        st.divider()
        st.subheader("🏢 층별 월세 비교")
        fig_floor = px.box(filtered_df, x='floor', y='monthlyRent', color='floor',
                           labels={'floor': '층', 'monthlyRent': '월세(만원)'},
                           template="plotly_white")
        st.plotly_chart(fig_floor, use_container_width=True)

# Footer
st.markdown("---")
st.caption("Premium Dashboard v2.0 - Intelligence for NemoStore Listings")
