# ====================================================================
# Streamlit Web Frontend - Stock Prediction Platform v2.0
# ====================================================================
# Module: dashboard/dashboard.py
#
# Giao diện Premium kết nối FastAPI Backend.
# Giai đoạn 1: Chọn thị trường, chọn mã, vẽ biểu đồ, train model
# Giai đoạn 2: So sánh nhiều mã, heatmap return, top tăng/giảm, watchlist
# Giai đoạn 3: Chỉ làm frontend, gọi API lấy data/predict/train
# Giai đoạn 4: Lưu model theo mã, auto-update, Docker
#
# Khởi chạy: streamlit run dashboard/dashboard.py
# ====================================================================

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime

# ── Cấu hình URL Backend ─────────────────────────────────────────────
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ── Phải là lệnh đầu tiên trong script ───────────────────────────────
st.set_page_config(
    page_title="Stock AI – Dự báo Giá Cổ phiếu",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom Premium CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

/* Dark gradient background */
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
}

/* Cards */
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

/* Metric heading */
.metric-label { color: #94a3b8; font-size: 13px; font-weight: 600; margin: 0; }
.metric-value { color: #f1f5f9; font-size: 30px; font-weight: 800; margin: 4px 0 0 0; }
.metric-value.green  { color: #22c55e !important; }
.metric-value.red    { color: #ef4444 !important; }
.metric-value.yellow { color: #f59e0b !important; }
.metric-value.blue   { color: #38bdf8 !important; }

/* Section headings */
h1, h2, h3 { color: #f1f5f9 !important; font-weight: 800 !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: rgba(15,23,42,0.95);
    border-right: 1px solid rgba(148,163,184,0.12);
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0f172a; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }

/* Reco box shadow */
.reco-box {
    padding: 24px;
    border-radius: 16px;
    margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  HELPER: GỌI API
# ═══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=30)
def api_tickers():
    try:
        r = requests.get(f"{BACKEND_URL}/api/tickers", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        st.sidebar.error(f"⚠️ Không kết nối được Backend!\n\n`{e}`")
    return {"US": ["AAPL", "TSLA", "MSFT", "AMZN", "GOOGL"],
            "VN": ["FPT.VN", "HPG.VN", "VNM.VN", "VIC.VN", "TCB.VN"]}


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


# ═══════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════

col_h1, col_h2 = st.columns([5, 1])
with col_h1:
    st.markdown("""
    <h1 style='margin-bottom:0'>📈 Stock AI — Hệ thống Dự báo Giá Cổ phiếu</h1>
    <p style='color:#94a3b8; margin-top:4px'>
        Phân tích kỹ thuật & Trí tuệ nhân tạo cho thị trường <b>Mỹ</b> 🇺🇸 và <b>Việt Nam</b> 🇻🇳
    </p>
    """, unsafe_allow_html=True)
with col_h2:
    now_str = datetime.now().strftime("%H:%M:%S — %d/%m/%Y")
    st.markdown(f"""
    <div style='text-align:right; padding-top:14px;'>
        <code style='background:rgba(30,41,59,0.8); padding:6px 12px;
        border-radius:8px; border:1px solid rgba(255,255,255,0.1); font-size:12px'>
        🕐 {now_str}
        </code>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════

st.sidebar.markdown("<h2 style='text-align:center'>🎛️ Bảng Điều Khiển</h2>", unsafe_allow_html=True)

tickers_data = api_tickers()

# 1. Chọn thị trường
market = st.sidebar.selectbox(
    "1️⃣  Chọn Thị Trường",
    ["🇺🇸 Mỹ (US)", "🇻🇳 Việt Nam (VN)"]
)
ticker_list = tickers_data.get("US") if "Mỹ" in market else tickers_data.get("VN")
ticker_list = ticker_list or []

# 2. Chọn mã
default_idx = 0
selected_ticker = st.sidebar.selectbox("2️⃣  Chọn Mã Chứng Khoán", ticker_list, index=default_idx)

# 3. Chế độ xem
view = st.sidebar.radio(
    "3️⃣  Chế Độ Hiển Thị",
    ["📈 Phân Tích & AI Dự Báo", "🔗 Thị Trường & So Sánh"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ Hành Động Nhanh")

# Nút train model
if st.sidebar.button(f"🤖 Train Model AI cho **{selected_ticker}**", use_container_width=True):
    with st.sidebar.spinner("Đang cào dữ liệu & huấn luyện AI…"):
        try:
            r = requests.post(f"{BACKEND_URL}/api/train/{selected_ticker}", timeout=120)
            if r.status_code == 200:
                res = r.json()
                st.sidebar.success(
                    f"✅ Huấn luyện xong!\n"
                    f"Thuật toán: **{res['best_model']}**\n"
                    f"RMSE: `{res['test_rmse']:.5f}`"
                )
                st.cache_data.clear()
            else:
                st.sidebar.error(f"❌ Lỗi: {r.text[:200]}")
        except Exception as e:
            st.sidebar.error(f"❌ Không kết nối API: {e}")

# Nút cập nhật toàn hệ thống
if st.sidebar.button("🔄 Cập nhật dữ liệu toàn hệ thống", use_container_width=True):
    try:
        r = requests.post(f"{BACKEND_URL}/api/update-data", timeout=5)
        if r.status_code == 200:
            st.sidebar.info("📡 Đã kích hoạt cập nhật ngầm. Hoàn tất sau ~60 giây.")
    except Exception as e:
        st.sidebar.error(f"❌ {e}")

st.sidebar.markdown("""
<br>
<div style='text-align:center;color:#475569;font-size:11px'>
    Stock AI Platform v2.0<br>
    FastAPI + Streamlit + ML
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  VIEW 1: PHÂN TÍCH & AI DỰ BÁO
# ═══════════════════════════════════════════════════════════════════════

if view == "📈 Phân Tích & AI Dự Báo":

    with st.spinner(f"Đang tải dữ liệu {selected_ticker}…"):
        df = api_historical(selected_ticker, days=150)

    if df.empty:
        st.warning(
            f"⚠️ Không có dữ liệu cho **{selected_ticker}**. "
            "Vui lòng nhấn **'Train Model AI'** ở thanh bên để tải dữ liệu."
        )
        st.stop()

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").set_index("date")

    last = df.iloc[-1]
    daily_chg = float(last.get("daily_return", 0)) * 100
    vol = float(last.get("volatility", 0)) * 100
    rsi_val = float(last.get("rsi", 50))

    # ── Metric Cards ─────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    def metric_card(col, label, value_html, extra=""):
        col.markdown(f"""
        <div class='glass-card'>
            <p class='metric-label'>{label}</p>
            <p class='metric-value {extra}'>{value_html}</p>
        </div>
        """, unsafe_allow_html=True)

    metric_card(c1, "Giá Chốt Phiên", f"${float(last['close']):,.2f}")
    chg_cls = "green" if daily_chg >= 0 else "red"
    chg_arrow = "▲" if daily_chg >= 0 else "▼"
    metric_card(c2, "Biến Động 24h", f"{chg_arrow} {daily_chg:+.2f}%", chg_cls)
    metric_card(c3, "Dao Động (Volatility)", f"{vol:.2f}%", "yellow")
    rsi_cls = "red" if rsi_val >= 70 else ("green" if rsi_val <= 30 else "blue")
    metric_card(c4, "Chỉ Báo RSI(14)", f"{rsi_val:.1f}", rsi_cls)

    # ── Biểu đồ giá ─────────────────────────────────────────────────
    st.subheader(f"📊 Phân Tích Kỹ Thuật — {selected_ticker}")

    ma_col1, ma_col2, ma_col3 = st.columns(3)
    show_ma10 = ma_col1.checkbox("MA10", value=True)
    show_ma20 = ma_col2.checkbox("MA20", value=True)
    show_ma50 = ma_col3.checkbox("MA50", value=False)

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name="OHLC",
        increasing_line_color="#22c55e", decreasing_line_color="#ef4444"
    ))

    ma_cfg = [("ma10", show_ma10, "#f59e0b"),
              ("ma20", show_ma20, "#ef4444"),
              ("ma50", show_ma50, "#38bdf8")]
    for col_name, show, color in ma_cfg:
        if show and col_name in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_name],
                name=col_name.upper(), mode="lines",
                line=dict(color=color, width=1.5)
            ))

    fig.update_layout(
        template="plotly_dark",
        height=430,
        xaxis_rangeslider_visible=False,
        margin=dict(l=30, r=30, t=30, b=30),
        legend=dict(bgcolor="rgba(0,0,0,0)")
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── RSI & Volatility ─────────────────────────────────────────────
    ri1, ri2 = st.columns(2)

    with ri1:
        fig_rsi = go.Figure()
        fig_rsi.add_trace(go.Scatter(
            x=df.index, y=df["rsi"], name="RSI(14)",
            line=dict(color="#8b5cf6", width=2)
        ))
        fig_rsi.add_hline(y=70, line_dash="dash", line_color="#ef4444",
                          annotation_text="Quá mua (70)", annotation_position="top right")
        fig_rsi.add_hline(y=30, line_dash="dash", line_color="#22c55e",
                          annotation_text="Quá bán (30)", annotation_position="bottom right")
        fig_rsi.update_layout(
            template="plotly_dark", height=260,
            yaxis=dict(range=[0, 100]),
            margin=dict(l=30, r=30, t=30, b=30),
            title="Relative Strength Index (RSI)"
        )
        st.plotly_chart(fig_rsi, use_container_width=True)

    with ri2:
        fig_vol = go.Figure()
        fig_vol.add_trace(go.Scatter(
            x=df.index, y=df["volatility"] * 100,
            name="Volatility", fill="tozeroy",
            line=dict(color="#f59e0b", width=2)
        ))
        fig_vol.update_layout(
            template="plotly_dark", height=260,
            margin=dict(l=30, r=30, t=30, b=30),
            title="Dao Động Giá Rolling (%)"
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    # ── AI Dự Báo ────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🧠 Dự Báo Trí Tuệ Nhân Tạo & Khuyến Nghị Đầu Tư")

    with st.spinner("Đang chạy mô hình AI…"):
        pred, err = api_predict(selected_ticker)

    if err and pred is None:
        # Chưa có model hoặc lỗi
        st.markdown(f"""
        <div class='reco-box' style='background:rgba(239,68,68,0.12);
             border-left:6px solid #ef4444'>
            <h3 style='color:#ef4444;margin:0'>⚠️ Chưa có mô hình AI cho {selected_ticker}</h3>
            <p style='color:#cbd5e1;margin-top:10px;font-size:15px'>
                {err}
            </p>
            <p style='color:#f1f5f9;font-weight:600;margin-top:12px'>
                👉 Nhấn nút <b>"🤖 Train Model AI"</b> ở thanh bên trái để AI tự học từ dữ liệu lịch sử.
            </p>
        </div>
        """, unsafe_allow_html=True)
    elif pred:
        box_col = pred["box_color"]
        txt_col = pred["text_color"]
        reco = pred["recommendation"]
        desc = pred["reco_desc"]
        latest_c = pred["latest_close"]
        next_c = pred["predicted_next_close"]
        ret_pct = pred["predicted_return"] * 100
        pred_dt = pred["prediction_date"]
        model_name = pred["model_used"]
        m = pred.get("metrics", {})

        box1, box2 = st.columns([3, 2])

        with box1:
            st.markdown(f"""
            <div class='reco-box' style='background:{box_col};
                 border-left:6px solid {txt_col}'>
                <h2 style='color:{txt_col};margin:0;font-size:28px'>{reco}</h2>
                <p style='color:#1e293b;font-size:15px;line-height:1.6;margin:12px 0 20px'>{desc}</p>
                <div style='display:flex;flex-wrap:wrap;gap:20px;
                     background:rgba(255,255,255,0.65);
                     padding:14px;border-radius:12px'>
                    <div>
                        <p style='margin:0;color:#475569;font-size:12px;font-weight:700'>
                            Giá Hiện Tại
                        </p>
                        <p style='margin:4px 0 0;font-size:22px;font-weight:800;color:#0f172a'>
                            ${latest_c:,.2f}
                        </p>
                    </div>
                    <div>
                        <p style='margin:0;color:#475569;font-size:12px;font-weight:700'>
                            Dự Báo ({pred_dt})
                        </p>
                        <p style='margin:4px 0 0;font-size:22px;font-weight:800;color:{txt_col}'>
                            ${next_c:,.2f}
                        </p>
                    </div>
                    <div>
                        <p style='margin:0;color:#475569;font-size:12px;font-weight:700'>
                            Biến Động Dự Kiến
                        </p>
                        <p style='margin:4px 0 0;font-size:22px;font-weight:800;color:{txt_col}'>
                            {ret_pct:+.2f}%
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with box2:
            st.markdown(f"#### 📊 Hiệu Năng Mô Hình AI")
            st.markdown(f"🧠 Thuật toán: **{model_name}**")
            met_df = pd.DataFrame({
                "Chỉ Số": ["MAE (Lỗi Tuyệt Đối)", "RMSE (Lỗi Bình Phương)", "R² Score"],
                "Giá Trị": [
                    f"{m.get('mae', 0):.5f}",
                    f"{m.get('rmse', 0):.5f}",
                    f"{m.get('r2', 0)*100:.2f}%"
                ]
            })
            st.dataframe(met_df, hide_index=True, use_container_width=True)
            st.caption("💡 RMSE càng thấp = mô hình càng chính xác. R² gần 100% = khớp xu hướng cao.")


# ═══════════════════════════════════════════════════════════════════════
#  VIEW 2: THỊ TRƯỜNG & SO SÁNH
# ═══════════════════════════════════════════════════════════════════════

elif view == "🔗 Thị Trường & So Sánh":

    st.subheader("🌏 Tổng Hợp Thị Trường Thời Gian Thực")

    with st.spinner("Đang tải dữ liệu thị trường…"):
        summary = api_market_summary()

    if not summary:
        st.error("❌ Không lấy được dữ liệu thị trường. Kiểm tra Backend API đang chạy chưa?")
        st.stop()

    # ── Top Gainers & Losers ─────────────────────────────────────────
    col_g, col_l = st.columns(2)

    with col_g:
        st.markdown("### 🟢 Top Tăng Giá Tốt Nhất")
        gainers = summary.get("top_gainers", [])
        if gainers:
            gdf = pd.DataFrame(gainers)[["ticker", "close", "change_pct", "signal", "market"]]
            gdf.columns = ["Mã", "Giá ($)", "Biến Động (%)", "Tín Hiệu AI", "Thị Trường"]
            st.dataframe(
                gdf.style.format({"Giá ($)": "${:.2f}", "Biến Động (%)": "{:+.2f}%"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Không có dữ liệu.")

    with col_l:
        st.markdown("### 🔴 Top Giảm Giá Sâu Nhất")
        losers = summary.get("top_losers", [])
        if losers:
            ldf = pd.DataFrame(losers)[["ticker", "close", "change_pct", "signal", "market"]]
            ldf.columns = ["Mã", "Giá ($)", "Biến Động (%)", "Tín Hiệu AI", "Thị Trường"]
            st.dataframe(
                ldf.style.format({"Giá ($)": "${:.2f}", "Biến Động (%)": "{:+.2f}%"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Không có dữ liệu.")

    # ── Watchlist ────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📌 Bảng Watchlist — Theo Dõi Tất Cả Mã")

    wl_add1, wl_add2 = st.columns([3, 1])
    with wl_add1:
        new_ticker = st.text_input(
            "➕ Thêm mã mới vào watchlist (VD: NVDA, META, VHM.VN):",
            placeholder="Nhập mã và nhấn nút →"
        ).strip().upper()
    with wl_add2:
        st.markdown("<div style='padding-top:26px'></div>", unsafe_allow_html=True)
        if st.button("Thêm & Huấn luyện AI", use_container_width=True) and new_ticker:
            with st.spinner(f"Đang xử lý mã {new_ticker}…"):
                try:
                    r = requests.post(f"{BACKEND_URL}/api/train/{new_ticker}", timeout=120)
                    if r.status_code == 200:
                        st.success(f"🎉 Đã thêm {new_ticker} thành công!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ {r.text[:200]}")
                except Exception as e:
                    st.error(f"❌ {e}")

    watchlist = summary.get("watchlist", [])
    if watchlist:
        wdf = pd.DataFrame(watchlist)
        wdf = wdf[["ticker", "market", "close", "change_pct", "signal"]]
        wdf.columns = ["Mã", "Thị Trường", "Giá Chốt ($)", "Thay Đổi (%)", "AI Khuyến Nghị"]
        st.dataframe(
            wdf.style.format({"Giá Chốt ($)": "${:.2f}", "Thay Đổi (%)": "{:+.2f}%"}),
            use_container_width=True, hide_index=True, height=280
        )

    # ── Multi-Stock Comparison ───────────────────────────────────────
    st.markdown("---")
    st.subheader("🔗 So Sánh Tăng Trưởng Lũy Kế (Chuẩn hoá về mốc 100)")
    st.caption("Giá tất cả các mã được quy về mốc 100 tại phiên đầu tiên để so sánh tốc độ tăng trưởng.")

    all_tickers = [item["ticker"] for item in watchlist]
    if all_tickers:
        chosen = st.multiselect(
            "Chọn các mã muốn so sánh:",
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
                    template="plotly_dark",
                    height=420,
                    labels={"norm": "Giá trị chuẩn hoá (mốc=100)", "date": "Thời gian"}
                )
                fig_cmp.update_layout(
                    hovermode="x unified",
                    margin=dict(l=30, r=30, t=30, b=30),
                    legend=dict(bgcolor="rgba(0,0,0,0)")
                )
                st.plotly_chart(fig_cmp, use_container_width=True)

    # ── Correlation Heatmap ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔥 Heatmap Tương Quan Tỷ Suất Sinh Lời (120 phiên)")

    heat_c1, heat_c2 = st.columns([2, 3])
    with heat_c1:
        st.markdown("""
        <div class='glass-card'>
            <p style='color:#94a3b8;font-size:14px;line-height:1.7'>
            Biểu đồ thể hiện hệ số tương quan tỷ suất sinh lời hàng ngày giữa các mã:
            </p>
            <ul style='color:#cbd5e1;font-size:13px'>
                <li><b style='color:#22c55e'>+1</b>: Biến động cùng chiều rất mạnh</li>
                <li><b style='color:#94a3b8'>0</b>: Không tương quan — tốt để đa dạng hoá danh mục</li>
                <li><b style='color:#ef4444'>-1</b>: Biến động ngược chiều hoàn toàn</li>
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
            st.plotly_chart(fig_h, use_container_width=True)
        else:
            st.info("Không có đủ dữ liệu để vẽ Heatmap.")
