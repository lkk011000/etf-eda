"""네이버 금융 API 실시간 수집 기반 Streamlit 종합 EDA 대시보드 메인 애플리케이션.

이 모듈은 네이버 금융의 ETF API를 통해 데이터를 실시간 메모리 수집하고,
사용자에게 다차원 탐색적 데이터 분석(EDA), KPI 시각화, 브랜드/테마별 필터링,
Plotly 대화형 차트 및 실시간 데이터 테이블을 제공합니다.
로컬 파일 저장은 일절 수행하지 않습니다.
"""

from datetime import datetime
import os
from pathlib import Path
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 실행 디렉토리 위치에 의존하지 않도록 파이썬 모듈 검색 경로(sys.path) 자동 등록
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# src 패키지 또는 모듈 단독 임포트 fallback 처리
try:
    from src.etf_data_fetcher import get_live_etf_dataframe
except ModuleNotFoundError:
    from etf_data_fetcher import get_live_etf_dataframe



# Streamlit 페이지 세팅 (Wide 레이아웃)
st.set_page_config(
    page_title="네이버 금융 ETF 실시간 종합 EDA 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS 스타일 지정 (Modern Dark/Light 테마 및 고급 인터페이스)
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E88E5;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #555555;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8F9FA;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #1E88E5;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 6px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30)
def load_etf_data() -> pd.DataFrame:
    """30초 동안 캐싱되는 실시간 ETF 데이터 로딩 함수.

    Returns:
        pd.DataFrame: 전처리가 완료된 실시간 ETF 데이터프레임.
    """
    return get_live_etf_dataframe()


def format_uk_wong(val_in_uk: float) -> str:
    """억원 단위 금액을 조원 또는 억원 형태의 문자열로 포맷팅합니다.

    Args:
        val_in_uk (float): 억원 단위 금액

    Returns:
        str: 포맷팅된 금액 문자열
    """
    if abs(val_in_uk) >= 10000:
        jo = val_in_uk / 10000.0
        return f"{jo:,.2f} 조 원"
    else:
        return f"{val_in_uk:,.0f} 억 원"


def main() -> None:
    """Streamlit 대시보드 메인 레이아웃 및 인터랙티브 UI 구성 로직."""

    # 1. 상단 타이틀 영역
    st.markdown('<div class="main-header">📈 네이버 금융 ETF 실시간 종합 EDA 대시보드</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">⚡ 로컬 저장 없이 메모리 상에서 실시간 수집 및 전처리되는 탐색적 데이터 분석 대시보드입니다.</div>',
        unsafe_allow_html=True,
    )

    # 2. 데이터 로드 및 수동 새로고침 처리
    try:
        df_raw = load_etf_data()
    except Exception as e:
        st.error(f"❌ 실시간 데이터 수집 중 오류가 발생했습니다: {e}")
        st.stop()

    collected_time = df_raw['collected_at'].iloc[0] if not df_raw.empty else "N/A"

    # 사이드바 상단 수동 새로고침 버튼 및 안내
    with st.sidebar:
        st.header("⚙️ 데이터 동기화 & 필터")
        st.caption(f"🕒 최근 수집 시각: **{collected_time}**")
        if st.button("🔄 실시간 데이터 즉시 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")

        # 3. 사이드바 인터랙티브 필터 컨트롤
        # 3-1. 브랜드 필터
        all_brands = sorted(list(df_raw['brand'].unique()))
        selected_brands = st.multiselect(
            "🏢 운용사 브랜드 선택",
            options=all_brands,
            default=all_brands,
            help="분석하고자 하는 ETF 운용사 브랜드를 선택하세요.",
        )

        # 3-2. 테마 필터
        all_themes = sorted(list(df_raw['theme'].unique()))
        selected_themes = st.multiselect(
            "🏷️ 자산/테마 유형 선택",
            options=all_themes,
            default=all_themes,
            help="관심 있는 ETF 자산 또는 테마 범주를 선택하세요.",
        )

        # 3-3. 키워드 검색
        search_query = st.text_input(
            "🔍 종목명 / 종목코드 검색",
            value="",
            placeholder="예: KODEX, 069500, 미국S&P500",
        )

        # 3-4. 수치 범위 필터 (시가총액 & 등락률)
        min_mkt, max_mkt = int(df_raw['marketSum'].min()), int(df_raw['marketSum'].max())
        selected_mkt_range = st.slider(
            "💰 시가총액 범위 (억원)",
            min_value=min_mkt,
            max_value=max_mkt,
            value=(min_mkt, max_mkt),
        )

        min_rate, max_rate = float(df_raw['changeRate'].min()), float(df_raw['changeRate'].max())
        selected_rate_range = st.slider(
            "📊 등락률 범위 (%)",
            min_value=min_rate,
            max_value=max_rate,
            value=(min_rate, max_rate),
        )

    # 4. 데이터 필터링 수행
    filtered_df = df_raw[
        (df_raw['brand'].isin(selected_brands)) &
        (df_raw['theme'].isin(selected_themes)) &
        (df_raw['marketSum'] >= selected_mkt_range[0]) &
        (df_raw['marketSum'] <= selected_mkt_range[1]) &
        (df_raw['changeRate'] >= selected_rate_range[0]) &
        (df_raw['changeRate'] <= selected_rate_range[1])
    ]

    # 키워드 검색 필터 적용
    if search_query.strip():
        q = search_query.strip().upper()
        filtered_df = filtered_df[
            filtered_df['itemname'].str.upper().str.contains(q) |
            filtered_df['itemcode'].str.contains(q)
        ]

    # 검색 결과가 없을 경우 경고 메시지
    if filtered_df.empty:
        st.warning("⚠️ 선택하신 필터 조건에 해당하는 ETF 종목이 없습니다. 필터를 조정해 주세요.")
        st.stop()

    # 5. 핵심 KPI 카운터 헤더 영역 (5 컬럼 배치)
    total_count = len(filtered_df)
    raw_count = len(df_raw)
    total_market_sum_uk = filtered_df['marketSum'].sum()
    avg_change_rate = filtered_df['changeRate'].mean()
    total_amount_uk = filtered_df['amount_uk'].sum()
    rise_cnt = (filtered_df['changeRate'] > 0).sum()
    fall_cnt = (filtered_df['changeRate'] < 0).sum()

    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    with kpi_col1:
        st.metric("📌 검색/필터 종목 수", f"{total_count:,} 개", f"전체 {raw_count:,} 개 중")
    with kpi_col2:
        st.metric("💰 총 시가총액 합계", format_uk_wong(total_market_sum_uk))
    with kpi_col3:
        st.metric("📊 평균 등락률", f"{avg_change_rate:+.2f}%")
    with kpi_col4:
        st.metric("📈 상승 / 하락 종목", f"{rise_cnt}개 / {fall_cnt}개")
    with kpi_col5:
        st.metric("💸 당일 총 거래대금", format_uk_wong(total_amount_uk))

    st.markdown("---")

    # 6. 메인 탐색 탭 구성 (4개 탭)
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 1. 시장 개요 & 브랜드 점유율",
        "📈 2. 상관관계 & NAV 괴리율 분석",
        "🏆 3. 랭킹 & 심층 EDA",
        "📋 4. 실시간 원본 데이터",
    ])

    # ---------------------------------------------------------
    # TAB 1: 시장 개요 & 브랜드 점유율
    # ---------------------------------------------------------
    with tab1:
        st.subheader("📊 ETF 시장 구조 및 브랜드 점유율")

        row1_col1, row1_col2 = st.columns(2)

        # 브랜드별 시가총액 점유율 (Treemap)
        with row1_col1:
            st.markdown("##### 🏢 브랜드별 시가총액 점유율 (Treemap)")
            brand_summary = filtered_df.groupby('brand').agg(
                marketSum_total=('marketSum', 'sum'),
                item_count=('itemcode', 'count')
            ).reset_index()

            fig_treemap = px.treemap(
                brand_summary,
                path=['brand'],
                values='marketSum_total',
                color='marketSum_total',
                color_continuous_scale='Blues',
                hover_data={'item_count': True, 'marketSum_total': ':,.0f'},
                labels={'marketSum_total': '시가총액(억원)', 'item_count': '종목 수', 'brand': '브랜드'}
            )
            fig_treemap.update_layout(margin=dict(t=20, l=10, r=10, b=10))
            st.plotly_chart(fig_treemap, use_container_width=True)

        # 자산/테마별 종목 수 및 시가총액 (Bar Chart)
        with row1_col2:
            st.markdown("##### 🏷️ 자산/테마 유형별 시가총액 분포")
            theme_summary = filtered_df.groupby('theme').agg(
                marketSum_total=('marketSum', 'sum'),
                item_count=('itemcode', 'count')
            ).reset_index().sort_values('marketSum_total', ascending=True)

            fig_theme = px.bar(
                theme_summary,
                y='theme',
                x='marketSum_total',
                orientation='h',
                color='marketSum_total',
                color_continuous_scale='Viridis',
                text_auto=',.0f',
                labels={'marketSum_total': '시가총액(억원)', 'theme': '테마'}
            )
            fig_theme.update_layout(margin=dict(t=20, l=10, r=10, b=10))
            st.plotly_chart(fig_theme, use_container_width=True)

        st.markdown("---")

        row2_col1, row2_col2 = st.columns(2)

        # 등락률 분포 (Histogram + Box)
        with row2_col1:
            st.markdown("##### 📈 당일 등락률(%) 분포")
            fig_dist = px.histogram(
                filtered_df,
                x='changeRate',
                nbins=40,
                marginal='box',
                color_discrete_sequence=['#1E88E5'],
                labels={'changeRate': '등락률 (%)'}
            )
            fig_dist.add_vline(x=0, line_dash="dash", line_color="red")
            fig_dist.update_layout(margin=dict(t=20, l=10, r=10, b=10))
            st.plotly_chart(fig_dist, use_container_width=True)

        # 시가총액 Top 15 종목 Bar Chart
        with row2_col2:
            st.markdown("##### 🏆 시가총액 상위 15개 종목")
            top15_mkt = filtered_df.sort_values('marketSum', ascending=False).head(15)
            fig_top15 = px.bar(
                top15_mkt,
                x='marketSum',
                y='itemname',
                orientation='h',
                color='changeRate',
                color_continuous_scale='RdBu_r',
                color_continuous_midpoint=0,
                hover_data=['nowVal', 'changeRate', 'brand'],
                labels={'marketSum': '시가총액(억원)', 'itemname': '종목명', 'changeRate': '등락률(%)'}
            )
            fig_top15.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=20, l=10, r=10, b=10))
            st.plotly_chart(fig_top15, use_container_width=True)

    # ---------------------------------------------------------
    # TAB 2: 상관관계 & NAV 괴리율 분석
    # ---------------------------------------------------------
    with tab2:
        st.subheader("📈 상관관계 및 NAV 괴리율 탐색")

        col_control1, col_control2 = st.columns([1, 4])
        with col_control1:
            use_log_scale = st.checkbox("🔍 Log Scale 적용 (시총/거래대금)", value=True)

        # 산점도: 시가총액 vs 거래대금 (색상: 등락률, 크기: 거래량)
        st.markdown("##### 🌌 시가총액 vs 당일 거래대금 상관관계 산점도")
        fig_scatter = px.scatter(
            filtered_df,
            x='marketSum',
            y='amount_uk',
            size='quant',
            color='changeRate',
            hover_name='itemname',
            hover_data=['itemcode', 'brand', 'theme', 'nowVal', 'nav_gap_rate'],
            color_continuous_scale='Turbo',
            color_continuous_midpoint=0,
            log_x=use_log_scale,
            log_y=use_log_scale,
            labels={
                'marketSum': '시가총액 (억원)',
                'amount_uk': '거래대금 (억원)',
                'changeRate': '등락률 (%)',
                'quant': '거래량(주)'
            }
        )
        fig_scatter.update_layout(height=500, margin=dict(t=20, l=10, r=10, b=10))
        st.plotly_chart(fig_scatter, use_container_width=True)

        st.markdown("---")

        row3_col1, row3_col2 = st.columns(2)

        # NAV 괴리율 분포
        with row3_col1:
            st.markdown("##### ⚖️ NAV 괴리율 (%) 분포")
            fig_gap_dist = px.histogram(
                filtered_df,
                x='nav_gap_rate',
                nbins=50,
                color_discrete_sequence=['#43A047'],
                marginal='rug',
                labels={'nav_gap_rate': 'NAV 괴리율 (%)'}
            )
            fig_gap_dist.add_vline(x=0, line_dash="dash", line_color="black")
            fig_gap_dist.update_layout(margin=dict(t=20, l=10, r=10, b=10))
            st.plotly_chart(fig_gap_dist, use_container_width=True)

        # 3개월 수익률 vs 당일 등락률
        with row3_col2:
            st.markdown("##### 📅 3개월 수익률 vs 당일 등락률 교차 분석")
            fig_earn = px.scatter(
                filtered_df,
                x='threeMonthEarnRate',
                y='changeRate',
                color='brand',
                hover_name='itemname',
                labels={
                    'threeMonthEarnRate': '3개월 수익률 (%)',
                    'changeRate': '당일 등락률 (%)',
                    'brand': '브랜드'
                }
            )
            fig_earn.add_hline(y=0, line_dash="dot", line_color="gray")
            fig_earn.add_vline(x=0, line_dash="dot", line_color="gray")
            fig_earn.update_layout(margin=dict(t=20, l=10, r=10, b=10))
            st.plotly_chart(fig_earn, use_container_width=True)

    # ---------------------------------------------------------
    # TAB 3: 랭킹 & 심층 EDA
    # ---------------------------------------------------------
    with tab3:
        st.subheader("🏆 주요 항목별 랭킹 & Top 10 순위 분석")

        rank_tab1, rank_tab2, rank_tab3 = st.tabs(["🚀 등락률 랭킹", "💸 거래대금 / 거래량 랭킹", "💎 NAV 괴리율 극단 종목"])

        # 등락률 Top 10 / Bottom 10
        with rank_tab1:
            r1_c1, r1_c2 = st.columns(2)
            with r1_c1:
                st.markdown("##### 🔥 당일 상승률 Top 10")
                top_rise = filtered_df.sort_values('changeRate', ascending=False).head(10)
                st.dataframe(
                    top_rise[['itemcode', 'itemname', 'nowVal', 'changeRate', 'marketSum', 'brand']],
                    column_config={
                        'itemcode': '종목코드',
                        'itemname': '종목명',
                        'nowVal': st.column_config.NumberColumn('현재가(원)', format="%d 원"),
                        'changeRate': st.column_config.NumberColumn('등락률(%)', format="%.2f %%"),
                        'marketSum': st.column_config.NumberColumn('시가총액(억원)', format="%d 억"),
                        'brand': '브랜드'
                    },
                    use_container_width=True,
                    hide_index=True
                )
            with r1_c2:
                st.markdown("##### 🔻 당일 하락률 Top 10")
                top_fall = filtered_df.sort_values('changeRate', ascending=True).head(10)
                st.dataframe(
                    top_fall[['itemcode', 'itemname', 'nowVal', 'changeRate', 'marketSum', 'brand']],
                    column_config={
                        'itemcode': '종목코드',
                        'itemname': '종목명',
                        'nowVal': st.column_config.NumberColumn('현재가(원)', format="%d 원"),
                        'changeRate': st.column_config.NumberColumn('등락률(%)', format="%.2f %%"),
                        'marketSum': st.column_config.NumberColumn('시가총액(억원)', format="%d 억"),
                        'brand': '브랜드'
                    },
                    use_container_width=True,
                    hide_index=True
                )

        # 거래대금 / 거래량 Top 10
        with rank_tab2:
            r2_c1, r2_c2 = st.columns(2)
            with r2_c1:
                st.markdown("##### 💸 당일 거래대금 Top 10")
                top_amount = filtered_df.sort_values('amount_uk', ascending=False).head(10)
                st.dataframe(
                    top_amount[['itemcode', 'itemname', 'nowVal', 'amount_uk', 'quant', 'brand']],
                    column_config={
                        'itemcode': '종목코드',
                        'itemname': '종목명',
                        'nowVal': st.column_config.NumberColumn('현재가(원)', format="%d 원"),
                        'amount_uk': st.column_config.NumberColumn('거래대금(억원)', format="%.1f 억"),
                        'quant': st.column_config.NumberColumn('거래량(주)', format="%d 주"),
                        'brand': '브랜드'
                    },
                    use_container_width=True,
                    hide_index=True
                )
            with r2_c2:
                st.markdown("##### 📊 당일 거래량 Top 10")
                top_quant = filtered_df.sort_values('quant', ascending=False).head(10)
                st.dataframe(
                    top_quant[['itemcode', 'itemname', 'nowVal', 'quant', 'amount_uk', 'brand']],
                    column_config={
                        'itemcode': '종목코드',
                        'itemname': '종목명',
                        'nowVal': st.column_config.NumberColumn('현재가(원)', format="%d 원"),
                        'quant': st.column_config.NumberColumn('거래량(주)', format="%d 주"),
                        'amount_uk': st.column_config.NumberColumn('거래대금(억원)', format="%.1f 억"),
                        'brand': '브랜드'
                    },
                    use_container_width=True,
                    hide_index=True
                )

        # NAV 괴리율 극단 종목
        with rank_tab3:
            r3_c1, r3_c2 = st.columns(2)
            with r3_c1:
                st.markdown("##### 🔺 NAV 대비 고평가(Overpriced) Top 10 (괴리율 > 0)")
                top_over = filtered_df[filtered_df['nav'] > 0].sort_values('nav_gap_rate', ascending=False).head(10)
                st.dataframe(
                    top_over[['itemcode', 'itemname', 'nowVal', 'nav', 'nav_gap_rate', 'brand']],
                    column_config={
                        'itemcode': '종목코드',
                        'itemname': '종목명',
                        'nowVal': st.column_config.NumberColumn('현재가(원)', format="%d 원"),
                        'nav': st.column_config.NumberColumn('NAV(원)', format="%.2f 원"),
                        'nav_gap_rate': st.column_config.NumberColumn('괴리율(%)', format="%.2f %%"),
                        'brand': '브랜드'
                    },
                    use_container_width=True,
                    hide_index=True
                )
            with r3_c2:
                st.markdown("##### 🔻 NAV 대비 저평가(Discounted) Top 10 (괴리율 < 0)")
                top_under = filtered_df[filtered_df['nav'] > 0].sort_values('nav_gap_rate', ascending=True).head(10)
                st.dataframe(
                    top_under[['itemcode', 'itemname', 'nowVal', 'nav', 'nav_gap_rate', 'brand']],
                    column_config={
                        'itemcode': '종목코드',
                        'itemname': '종목명',
                        'nowVal': st.column_config.NumberColumn('현재가(원)', format="%d 원"),
                        'nav': st.column_config.NumberColumn('NAV(원)', format="%.2f 원"),
                        'nav_gap_rate': st.column_config.NumberColumn('괴리율(%)', format="%.2f %%"),
                        'brand': '브랜드'
                    },
                    use_container_width=True,
                    hide_index=True
                )

    # ---------------------------------------------------------
    # TAB 4: 실시간 원본 데이터
    # ---------------------------------------------------------
    with tab4:
        st.subheader("📋 실시간 메모리 원본 데이터 테이블")
        st.caption("ℹ️ 아래 데이터는 로컬 저장 없이 네이버 금융 API에서 실시간 메모리로 수집된 전체 파생변수 포함 데이터셋입니다.")

        # 표출용 DataFrame 정돈
        display_cols = [
            'itemcode', 'itemname', 'brand', 'theme', 'nowVal', 'changeVal',
            'changeRate', 'nav', 'nav_gap_rate', 'threeMonthEarnRate',
            'quant', 'amount_uk', 'marketSum', 'risefall_name'
        ]

        st.dataframe(
            filtered_df[display_cols],
            column_config={
                'itemcode': '종목코드',
                'itemname': '종목명',
                'brand': '운용사 브랜드',
                'theme': '자산/테마',
                'nowVal': st.column_config.NumberColumn('현재가(원)', format="%d 원"),
                'changeVal': st.column_config.NumberColumn('대비(원)', format="%+d 원"),
                'changeRate': st.column_config.NumberColumn('등락률(%)', format="%+.2f %%"),
                'nav': st.column_config.NumberColumn('NAV(원)', format="%.2f 원"),
                'nav_gap_rate': st.column_config.NumberColumn('NAV 괴리율(%)', format="%+.2f %%"),
                'threeMonthEarnRate': st.column_config.NumberColumn('3개월 수익률(%)', format="%+.2f %%"),
                'quant': st.column_config.NumberColumn('거래량(주)', format="%d 주"),
                'amount_uk': st.column_config.NumberColumn('거래대금(억원)', format="%.2f 억"),
                'marketSum': st.column_config.NumberColumn('시가총액(억원)', format="%d 억"),
                'risefall_name': '등락구분'
            },
            use_container_width=True,
            height=600
        )


if __name__ == "__main__":
    main()
