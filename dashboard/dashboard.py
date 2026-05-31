# ====================================================================
# Streamlit Web Frontend - Stock Prediction Platform v2.0
# Khởi chạy: streamlit run dashboard/dashboard.py
# ====================================================================

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import requests
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
try:
    from ai_analysis import render_ai_analysis_section
    AI_MODULE_OK = True
except Exception as _ai_err:
    AI_MODULE_OK = False
    _AI_ERR_MSG = str(_ai_err)

try:
    from market_overview import render_market_overview
    MARKET_MODULE_OK = True
except Exception as _mk_err:
    MARKET_MODULE_OK = False
    _MK_ERR_MSG = str(_mk_err)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Stock AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
}

.glass-card {
    background: rgba(30, 41, 59, 0.75);
    border: 1px solid rgba(148, 163, 184, 0.15);
    padding: 22px 26px;
    border-radius: 16px;
    backdrop-filter: blur(12px);
    margin-bottom: 18px;
    transition: transform .2s, border-color .2s;
}
.glass-card:hover {
    transform: translateY(-4px);
    border-color: rgba(148, 163, 184, 0.35);
}

.metric-label { color: #94a3b8; font-size: 13px; font-weight: 600; margin: 0; }
.metric-value { color: #f1f5f9; font-size: 30px; font-weight: 800; margin: 4px 0 0 0; }
.metric-value.green  { color: #22c55e !important; }
.metric-value.red    { color: #ef4444 !important; }
.metric-value.yellow { color: #f59e0b !important; }
.metric-value.blue   { color: #38bdf8 !important; }

h1, h2, h3 { color: #f1f5f9 !important; font-weight: 800 !important; }

[data-testid="stSidebar"] {
    background: rgba(15,23,42,0.95);
    border-right: 1px solid rgba(148,163,184,0.12);
}

[data-testid="stSidebar"] * {
    font-size: 17px !important;
}

[data-testid="stSidebar"] h2 {
    font-size: 22px !important;
    font-weight: 800 !important;
}

.nav-btn {
    display: block;
    width: 100%;
    padding: 14px 20px;
    margin-bottom: 10px;
    border-radius: 12px;
    border: 1px solid rgba(148,163,184,0.2);
    background: rgba(30,41,59,0.6);
    color: #cbd5e1;
    font-size: 17px;
    font-weight: 600;
    font-family: 'Outfit', sans-serif;
    cursor: pointer;
    text-align: left;
    transition: all 0.2s ease;
    letter-spacing: 0.3px;
}

.nav-btn:hover {
    background: rgba(99,102,241,0.25);
    border-color: rgba(99,102,241,0.5);
    color: #f1f5f9;
    transform: translateX(4px);
}

.nav-btn.active {
    background: linear-gradient(135deg, rgba(99,102,241,0.4), rgba(168,85,247,0.3));
    border-color: rgba(99,102,241,0.7);
    color: #f1f5f9;
    box-shadow: 0 4px 16px rgba(99,102,241,0.2);
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }

.reco-box {
    padding: 24px;
    border-radius: 16px;
    margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
</style>
""", unsafe_allow_html=True)


# =======================================================================
#  HELPER: GỌI API BACKEND
# =======================================================================

@st.cache_data(ttl=30)
def api_tickers():
    try:
        r = requests.get(f"{BACKEND_URL}/api/tickers", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {
        "US": [
            "AAPL", "TSLA", "MSFT", "AMZN", "GOOGL",
            "NVDA", "META", "NFLX", "BTC-USD", "ETH-USD"
        ],
        "VN": [
            "FPT.VN", "HPG.VN", "VNM.VN", "VIC.VN", "TCB.VN",
            "VHM.VN", "VCB.VN", "MWG.VN", "BID.VN", "SSI.VN"
        ]
    }


@st.cache_data(ttl=20, show_spinner=False)
def api_historical(ticker: str, days: int = 150):
    try:
        r = requests.get(f"{BACKEND_URL}/api/data/{ticker}?days={days}", timeout=8)
        if r.status_code == 200:
            return pd.DataFrame(r.json())
    except Exception:
        pass
    return pd.DataFrame()


@st.cache_data(ttl=15, show_spinner=False)
def api_predict(ticker: str):
    try:
        r = requests.get(f"{BACKEND_URL}/api/predict/{ticker}", timeout=8)
        if r.status_code == 200:
            return r.json(), None
        return None, r.json().get("detail", "Lỗi không xác định")
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=20, show_spinner=False)
def api_market_summary():
    try:
        r = requests.get(f"{BACKEND_URL}/api/market-summary", timeout=12)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


# =======================================================================
#  HEADER
# =======================================================================

col_h1, col_h2 = st.columns([5, 1])
with col_h1:
    st.markdown("""
    <h1 style='margin-bottom:0'>Stock AI System</h1>
    """, unsafe_allow_html=True)
with col_h2:
    now_str = datetime.now().strftime("%H:%M:%S — %d/%m/%Y")
    st.markdown(f"""
    <div style='text-align:right; padding-top:14px;'>
        <code style='background:rgba(30,41,59,0.8); padding:6px 12px;
        border-radius:8px; border:1px solid rgba(255,255,255,0.1); font-size:12px'>
        {now_str}
        </code>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")


# =======================================================================
#  SIDEBAR
# =======================================================================

st.sidebar.markdown("<h2 style='text-align:center'>Bảng Điều Khiển</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# Navigation buttons
if "current_view" not in st.session_state:
    st.session_state["current_view"] = "Tổng quan"

view_options = [
    "Tổng quan",
    "Phân Tích & AI Dự Báo",
    "Thị Trường & So Sánh",
]

for opt in view_options:
    is_active = "active" if st.session_state["current_view"] == opt else ""
    if st.sidebar.button(opt, key=f"nav_{opt}", use_container_width=True):
        st.session_state["current_view"] = opt
        st.rerun()

# Apply button styles
st.sidebar.markdown("""
<style>
[data-testid="stSidebar"] [data-testid^="stBaseButton"] button {
    background: rgba(30,41,59,0.6) !important;
    border: 1px solid rgba(148,163,184,0.2) !important;
    color: #cbd5e1 !important;
    font-size: 17px !important;
    font-weight: 600 !important;
    padding: 14px 20px !important;
    border-radius: 12px !important;
    text-align: left !important;
    justify-content: flex-start !important;
    transition: all 0.2s ease !important;
    margin-bottom: 6px !important;
    letter-spacing: 0.3px !important;
    width: 100% !important;
}
[data-testid="stSidebar"] [data-testid^="stBaseButton"] button:hover {
    background: rgba(99,102,241,0.25) !important;
    border-color: rgba(99,102,241,0.5) !important;
    color: #f1f5f9 !important;
    transform: translateX(4px) !important;
}
</style>
""", unsafe_allow_html=True)

view = st.session_state["current_view"]

st.sidebar.markdown("---")

if st.sidebar.button("Cập nhật dữ liệu toàn hệ thống", use_container_width=True, key="update_data_btn"):
    try:
        r = requests.post(f"{BACKEND_URL}/api/update-data", timeout=5)
        if r.status_code == 200:
            st.sidebar.info("Đã kích hoạt cập nhật. Hoàn tất sau ~60 giây.")
    except Exception as e:
        st.sidebar.error(f"Lỗi: {e}")



# =======================================================================
#  VIEW 1: PHÂN TÍCH & AI DỰ BÁO
# =======================================================================

if view == "Tổng quan":
    if not MARKET_MODULE_OK:
        st.error(f"Không tải được module thị trường: {_MK_ERR_MSG}")
    else:
        render_market_overview()


# =======================================================================
#  VIEW 2: PHÂN TÍCH & AI DỰ BÁO
# =======================================================================

elif view == "Phân Tích & AI Dự Báo":
    if not AI_MODULE_OK:
        st.error(f"Không tải được module AI: {_AI_ERR_MSG}")
    else:
        render_ai_analysis_section()


# =======================================================================
#  VIEW 3: THỊ TRƯỜNG & SO SÁNH
# =======================================================================

elif view == "Thị Trường & So Sánh":

    st.subheader("Tổng Hợp Thị Trường")

    with st.spinner("Đang tải dữ liệu thị trường…"):
        summary = api_market_summary()

    if not summary:
        st.warning(
            "Không kết nối được Backend API. "
            "Trang Thị Trường & So Sánh cần Backend đang chạy để hiển thị dữ liệu live."
        )
        st.info("Chạy lệnh: uvicorn api.api_service:app --reload để khởi động backend.")
        st.stop()

    # Top Tăng & Giảm
    col_g, col_l = st.columns(2)
    with col_g:
        st.markdown("### Top Tăng Giá")
        gainers = summary.get("top_gainers", [])
        if gainers:
            gdf = pd.DataFrame(gainers)[["ticker", "close", "change_pct", "signal", "market"]]
            gdf.columns = ["Ticker", "Price ($)", "Change (%)", "Signal", "Market"]
            st.dataframe(
                gdf.style.format({"Price ($)": "${:.2f}", "Change (%)": "{:+.2f}%"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Không có dữ liệu.")

    with col_l:
        st.markdown("### Top Giảm Giá")
        losers = summary.get("top_losers", [])
        if losers:
            ldf = pd.DataFrame(losers)[["ticker", "close", "change_pct", "signal", "market"]]
            ldf.columns = ["Ticker", "Price ($)", "Change (%)", "Signal", "Market"]
            st.dataframe(
                ldf.style.format({"Price ($)": "${:.2f}", "Change (%)": "{:+.2f}%"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Không có dữ liệu.")

    # Watchlist
    st.markdown("---")
    st.markdown("### Watchlist — 20 Mã Theo Dõi")

    wl_add1, wl_add2 = st.columns([3, 1])
    with wl_add1:
        new_ticker = st.text_input(
            "Thêm ticker vào watchlist (VD: NVDA, META, VHM.VN):",
            placeholder="Nhập ticker và nhấn nút Train"
        ).strip().upper()
    with wl_add2:
        st.markdown("<div style='padding-top:26px'></div>", unsafe_allow_html=True)
        if st.button("Thêm & Train Model", use_container_width=True) and new_ticker:
            with st.spinner(f"Đang xử lý {new_ticker}…"):
                try:
                    r = requests.post(f"{BACKEND_URL}/api/train/{new_ticker}", timeout=120)
                    if r.status_code == 200:
                        st.success(f"Đã thêm {new_ticker} thành công!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {r.text[:200]}")
                except Exception as e:
                    st.error(f"Lỗi: {e}")

    watchlist = summary.get("watchlist", [])
    if watchlist:
        wdf = pd.DataFrame(watchlist)
        wdf = wdf[["ticker", "market", "close", "change_pct", "signal"]]
        wdf.columns = ["Ticker", "Market", "Close Price ($)", "Change (%)", "AI Signal"]
        st.dataframe(
            wdf.style.format({"Close Price ($)": "${:.2f}", "Change (%)": "{:+.2f}%"}),
            use_container_width=True, hide_index=True, height=360
        )

    # So Sánh Normalized
    st.markdown("---")
    st.subheader("So Sánh Normalized Return (Base = 100)")
    st.caption("Giá được chuẩn hoá về mốc 100 tại phiên đầu tiên để so sánh tốc độ tăng trưởng giữa các ticker.")

    all_tickers = [item["ticker"] for item in watchlist]
    if all_tickers:
        chosen = st.multiselect(
            "Chọn ticker muốn so sánh:",
            all_tickers,
            default=all_tickers[:min(5, len(all_tickers))]
        )
        if chosen:
            frames = []
            for t in chosen:
                d = api_historical(t, days=120)
                if not d.empty:
                    d["date"] = pd.to_datetime(d["date"])
                    d = d.sort_values("date")
                    first = d["close"].iloc[0]
                    d["norm"] = d["close"] / first * 100
                    d["ticker"] = t
                    frames.append(d[["date", "norm", "ticker"]])
            if frames:
                df_all = pd.concat(frames)
                fig_cmp = px.line(
                    df_all, x="date", y="norm", color="ticker",
                    template="plotly_dark", height=420,
                    labels={"norm": "Normalized Price (Base=100)", "date": "Date"}
                )
                fig_cmp.update_layout(
                    hovermode="x unified",
                    margin=dict(l=30, r=30, t=30, b=30),
                    legend=dict(bgcolor="rgba(0,0,0,0)")
                )
                st.plotly_chart(fig_cmp, width="stretch")

    # Correlation Heatmap
    st.markdown("---")
    st.subheader("Correlation Heatmap — Daily Return (120 phiên)")

    heat_c1, heat_c2 = st.columns([2, 3])
    with heat_c1:
        st.markdown("""
        <div class='glass-card'>
            <p style='color:#94a3b8;font-size:14px;line-height:1.8'>
                Hệ số Correlation của Daily Return giữa các ticker:
            </p>
            <ul style='color:#cbd5e1;font-size:13px;line-height:2'>
                <li><b style='color:#22c55e'>+1</b>: Tương quan dương hoàn toàn</li>
                <li><b style='color:#94a3b8'>0</b>: Không tương quan</li>
                <li><b style='color:#ef4444'>-1</b>: Tương quan âm hoàn toàn</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with heat_c2:
        corr = summary.get("correlation", {})
        if corr and corr.get("z"):
            fig_h = px.imshow(
                corr["z"], x=corr["x"], y=corr["y"],
                color_continuous_scale="RdBu",
                zmin=-1, zmax=1,
                template="plotly_dark",
                height=370
            )
            fig_h.update_layout(margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_h, width="stretch")
        else:
            st.info("Không đủ dữ liệu để vẽ Correlation Heatmap.")
