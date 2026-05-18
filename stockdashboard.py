import streamlit as st
import yfinance as yf
import FinanceDataReader as fdr
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 1. 페이지 기본 설정 (브라우저 탭 타이틀 수정)
st.set_page_config(page_title="명수 투자 대시보드", layout="wide")

# --- 데이터 수집 함수 ---
@st.cache_data(ttl=1800) # 30분 단위 업데이트 설정 (30분 = 1800초)
def load_data(start_date, end_date):
    us_tickers = {
        'SPY': 'S&P 500 (시총가중)', 
        'RSP': 'S&P 500 (동일가중 - 시장체력)',
        'QQQ': '나스닥 100 (기술주)', 
        'SMH': '미 반도체 (AI/장비)', 
        'XLU': '미 유틸리티 (AI 전력망)',
        'PAVE': '미 인프라 (물리적 건설)',
        'XLK': '미 기술 (소프트웨어/IT)',
        'XLF': '미 금융 (은행/보험)',
        'XLE': '미 에너지 (화석연료)',
        'XBI': '미 바이오텍 (혁신신약)'
    }
    
    kr_tickers = {
        'KS11': '코스피 지수 (종합)',
        'KQ11': '코스닥 지수 (중소형)',
        '396690': '국내 반도체 (대형 TOP10)',
        '455850': '국내 반도체 소부장 (첨단패키징/장비)',
        '315930': '국내 스마트팩토리 (로봇/자동화)',
        '315990': '국내 스마트그리드 (전력기기/ESS)',
        '368590': '국내 신재생 (해상풍력/태양광)',
        '305540': '국내 2차전지 (TIGER)',
        '093240': '국내 자동차 (완성차/부품)',
        '266160': '국내 필수소비재 (내수방어)',
        '282820': '국내 경기소비재 (내수민감)',
        '264900': '국내 우주항공방산',
        '244580': '국내 바이오'
    }

    commo_tickers = {
        'GLD': '금 (안전자산)', 
        'SLV': '은 (귀금속/산업재)', 
        'CPER': '구리 (경기선행)', 
        'USO': '원유 (인플레이션)',
        'URA': '우라늄 (원전)',
        'LIT': '리튬 (2차전지 소재)'
    }

    crypto_tickers = {
        'BTC-USD': '비트코인 (BTC)',
        'ETH-USD': '이더리움 (ETH)'
    }
    
    macro_tickers = {
        '^TNX': '미국채 10년물 금리 (%)',
        'KRW=X': '원/달러 환율 (원)',
        'DX-Y.NYB': '달러 인덱스 (글로벌 유동성)'
    }

    sentiment_tickers = {
        '^VIX': 'VIX 지수 (S&P500 공포지수)',
        '^VXN': 'VXN 지수 (나스닥 공포지수)',
        'HYG': '하이일드 채권 (신용경색 리스크)'
    }

    yf_dict = {**us_tickers, **commo_tickers, **crypto_tickers, **macro_tickers, **sentiment_tickers}
    
    df_yf = yf.download(list(yf_dict.keys()), start=start_date, end=end_date)['Close']
    if isinstance(df_yf, pd.Series): df_yf = df_yf.to_frame(name=list(yf_dict.keys())[0])
    df_yf.rename(columns=yf_dict, inplace=True)

    kr_data = {}
    for code, name in kr_tickers.items():
        try:
            kr_df = fdr.DataReader(code, start=start_date, end=end_date)
            if not kr_df.empty:
                kr_data[name] = kr_df['Close']
        except Exception:
            pass
    df_kr = pd.DataFrame(kr_data)

    df_all = pd.concat([df_yf, df_kr], axis=1)
    df_all.index = pd.to_datetime(df_all.index).tz_localize(None)
    df_all.ffill(inplace=True)
    df_all.dropna(inplace=True)
    
    return df_all, us_tickers, kr_tickers, commo_tickers, crypto_tickers, macro_tickers, sentiment_tickers

def draw_sparkline(series, title, chart_type="asset"):
    fig = go.Figure()
    diff = series.iloc[-1] - series.iloc[0]
    
    if chart_type == "macro":
        color = "#f97316"
    elif chart_type == "sentiment":
        if "공포" in title:
            color = "#ef4444" if diff >= 0 else "#10b981"
        else:
            color = "#10b981" if diff >= 0 else "#ef4444"
    else: 
        color = "#10b981" if diff >= 0 else "#ef4444"
        
    fig.add_trace(go.Scatter(x=series.index, y=series.values, mode='lines', line=dict(color=color, width=2.5)))
    fig.add_trace(go.Scatter(x=[series.index[-1]], y=[series.iloc[-1]], mode='markers', marker=dict(color=color, size=8)))

    fig.update_layout(
        showlegend=False, height=130, margin=dict(l=5, r=5, t=35, b=5),
        title=dict(text=f"<b>{title}</b>", font=dict(size=12), x=0.0, y=0.9),
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig, diff

# --- 메인 화면 타이틀 수정 ---
st.title("📊 명수 투자 대시보드")
st.markdown("거시 경제 흐름부터 첨단 밸류체인(전력망, 소부장, 스마트팩토리)까지 시장 자금의 이동을 추적합니다.")

# 📱 모바일 최적화: 사이드바에서 메인 영역(제목 바로 및)으로 이동 및 가로 정렬(horizontal=True) 적용
period_option = st.radio("조회 기간 선택", ["1개월", "3개월", "6개월", "1년", "3년"], index=1, horizontal=True)

end_dt = datetime.today()
if period_option == "1개월": start_dt = end_dt - timedelta(days=30)
elif period_option == "3개월": start_dt = end_dt - timedelta(days=90)
elif period_option == "6개월": start_dt = end_dt - timedelta(days=180)
elif period_option == "1년": start_dt = end_dt - timedelta(days=365)
else: start_dt = end_dt - timedelta(days=365*3)

with st.spinner('다양한 섹터와 거시 지표 데이터를 동기화하는 중입니다...'):
    df, us_dict, kr_dict, commo_dict, crypto_dict, macro_dict, sentiment_dict = load_data(start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d'))

if not df.empty:
    absolute_names = list(macro_dict.values()) + list(sentiment_dict.values())
    asset_names = [col for col in df.columns if col not in absolute_names]
    
    df_return = (df[asset_names] / df[asset_names].iloc[0] - 1) * 100

    st.subheader("🎯 섹터 융합 정밀 비교 차트 (수익률)")
    
    desired_defaults = ["S&P 500 (시총가중)", "국내 스마트그리드 (전력기기/ESS)", "국내 스마트팩토리 (로봇/자동화)"]
    valid_defaults = [asset for asset in desired_defaults if asset in asset_names]
    
    selected_assets = st.multiselect(
        "다양한 자산들을 섞어서 겹쳐 보세요:",
        options=asset_names,
        default=valid_defaults
    )
    
    if selected_assets:
        fig_main = px.line(df_return, x=df_return.index, y=selected_assets, 
                           labels={'value': '누적 수익률 (%)', 'index': '날짜', 'variable': '자산명'})
        fig_main.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="기준점(0%)")
        fig_main.update_layout(hovermode="x unified", height=500, 
                               legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_main, use_container_width=True)

    st.divider()

    categories = {
        "🇺🇸 미국 지수 및 주도 섹터": us_dict,
        "🇰🇷 국내 지수 및 주도 섹터 (밸류체인/소비)": kr_dict,
        "🛢️ 원자재 및 에너지": commo_dict,
        "🪙 가상자산 (Crypto)": crypto_dict
    }

    for cat_name, ticker_dict in categories.items():
        st.subheader(cat_name)
        cols = st.columns(4)
        valid_cols = [name for name in ticker_dict.values() if name in df_return.columns]
        
        for idx, col_name in enumerate(valid_cols):
            with cols[idx % 4]:
                fig, diff = draw_sparkline(df_return[col_name], col_name, chart_type="asset")
                card = st.container(border=True)
                card.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                color_css = "color: #10b981;" if diff >= 0 else "color: #ef4444;"
                arrow = "▲" if diff >= 0 else "▼"
                card.markdown(f"<h4 style='text-align: center; margin-top:-20px; {color_css}'>{arrow} {df_return[col_name].iloc[-1]:.2f}%</h4>", unsafe_allow_html=True)
        st.write("") 

    st.divider()

    cols_bottom = st.columns(2)
    
    with cols_bottom[0]:
        st.subheader("🏦 거시경제 (유동성 및 금리)")
        valid_macro = [name for name in macro_dict.values() if name in df.columns]
        grid_macro = st.columns(2)
        
        for idx, col_name in enumerate(valid_macro):
            with grid_macro[idx % 2]:
                fig, diff = draw_sparkline(df[col_name], col_name, chart_type="macro")
                card = st.container(border=True)
                card.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                arrow = "▲" if diff >= 0 else "▼"
                unit = "원" if "환율" in col_name else ("pt" if "인덱스" in col_name else "%")
                card.markdown(f"<h4 style='text-align: center; margin-top:-20px; color: #f97316;'>{arrow} {df[col_name].iloc[-1]:,.2f}{unit}</h4>", unsafe_allow_html=True)

    with cols_bottom[1]:
        st.subheader("🚨 시장 심리 (공포 및 신용경색)")
        valid_sentiment = [name for name in sentiment_dict.values() if name in df.columns]
        grid_sent = st.columns(2)
        
        for idx, col_name in enumerate(valid_sentiment):
            with grid_sent[idx % 2]:
                fig, diff = draw_sparkline(df[col_name], col_name, chart_type="sentiment")
                card = st.container(border=True)
                card.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                
                if "공포" in col_name:
                    color_css = "color: #ef4444;" if diff >= 0 else "color: #10b981;" 
                else:
                    color_css = "color: #10b981;" if diff >= 0 else "color: #ef4444;" 
                arrow = "▲" if diff >= 0 else "▼"
                
                unit = "pt" if "공포" in col_name else "%"
                if "하이일드" in col_name:
                    card.markdown(f"<h4 style='text-align: center; margin-top:-20px; {color_css}'>{arrow} {df[col_name].iloc[-1]:.2f}% (수익률)</h4>", unsafe_allow_html=True)
                else:
                    card.markdown(f"<h4 style='text-align: center; margin-top:-20px; {color_css}'>{arrow} {df[col_name].iloc[-1]:.2f}{unit}</h4>", unsafe_allow_html=True)

else:
    st.error("데이터 동기화에 실패했습니다.")ss