# ====================================================================
# AI Analysis Module — dashboard/ai_analysis.py
# Phân tích kỹ thuật + Machine Learning + Khuyến nghị
# Hoàn toàn độc lập, dùng yfinance, không cần backend API
# ====================================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings("ignore")


# ── 1. LẤY DỮ LIỆU ──────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """Lấy dữ liệu từ Yahoo Finance."""
    try:
        raw = yf.download(ticker, period=period, interval=interval,
                          auto_adjust=True, progress=False)
        if raw is None or raw.empty:
            return pd.DataFrame()

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)
        raw = raw.loc[:, ~raw.columns.duplicated()]

        raw.reset_index(inplace=True)

        col_map = {}
        for c in raw.columns:
            cl = str(c).lower()
            if "date" in cl or "datetime" in cl or cl == "index":
                col_map[c] = "Date"
            elif cl == "open":
                col_map[c] = "Open"
            elif cl == "high":
                col_map[c] = "High"
            elif cl == "low":
                col_map[c] = "Low"
            elif cl in ("close", "adj close"):
                col_map[c] = "Close"
            elif cl == "volume":
                col_map[c] = "Volume"
        raw.rename(columns=col_map, inplace=True)

        required = ["Date", "Open", "High", "Low", "Close", "Volume"]
        for req in required:
            if req not in raw.columns:
                return pd.DataFrame()

        df = raw[required].copy()
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        df = df.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)

        for c in ["Open", "High", "Low", "Close", "Volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df.dropna(subset=["Close"])

        return df
    except Exception:
        return pd.DataFrame()


# ── 2. TÍNH CHỈ BÁO KỸ THUẬT ────────────────────────────────────────

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """Tính các Technical Indicators."""
    d = df.copy()

    d["Return"]     = d["Close"].pct_change()
    d["MA20"]       = d["Close"].rolling(20).mean()
    d["MA50"]       = d["Close"].rolling(50).mean()
    d["Volatility"] = d["Return"].rolling(20).std()

    # RSI(14)
    delta = d["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / (loss + 1e-9)
    d["RSI"] = 100 - 100 / (1 + rs)

    # MACD
    ema12 = d["Close"].ewm(span=12, adjust=False).mean()
    ema26 = d["Close"].ewm(span=26, adjust=False).mean()
    d["MACD"]        = ema12 - ema26
    d["MACD_Signal"] = d["MACD"].ewm(span=9, adjust=False).mean()

    # Target: Close ngày tiếp theo
    d["Target"] = d["Close"].shift(-1)

    return d


# ── 3. HUẤN LUYỆN MÔ HÌNH ───────────────────────────────────────────

FEATURE_COLS = ["Return", "MA20", "MA50", "Volatility", "RSI", "MACD", "MACD_Signal"]


def train_and_evaluate(df: pd.DataFrame):
    """Huấn luyện 3 model ML, so sánh metrics, trả về model tốt nhất."""
    feat = df[FEATURE_COLS + ["Target"]].dropna()
    if len(feat) < 40:
        return None, None, None, None, None

    X = feat[FEATURE_COLS].values
    y = feat["Target"].values

    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    models = {
        "Linear Regression":     LinearRegression(),
        "Random Forest":         RandomForestRegressor(n_estimators=100, random_state=42),
        "Gradient Boosting":     GradientBoostingRegressor(n_estimators=100, random_state=42),
    }

    rows = []
    trained = {}
    for name, m in models.items():
        m.fit(X_train_s, y_train)
        preds = m.predict(X_test_s)

        mae  = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2   = r2_score(y_test, preds)
        mask = y_test != 0
        mape = np.mean(np.abs((y_test[mask] - preds[mask]) / y_test[mask])) * 100 if mask.any() else np.nan

        rows.append({
            "Model":    name,
            "MAE":      round(mae, 4),
            "RMSE":     round(rmse, 4),
            "R²":       round(r2, 4),
            "MAPE (%)": round(mape, 2) if not np.isnan(mape) else "N/A",
        })
        trained[name] = m

    results_df = pd.DataFrame(rows)
    best_name  = results_df.loc[results_df["RMSE"].idxmin(), "Model"]
    best_model = trained[best_name]

    return results_df, best_name, best_model, scaler, feat


# ── 4. DỰ ĐOÁN GIÁ ──────────────────────────────────────────────────

def predict_next(df_feat: pd.DataFrame, model, scaler):
    """Dự đoán Close price phiên tiếp theo."""
    last = df_feat[FEATURE_COLS].dropna().iloc[-1:].values
    last_s = scaler.transform(last)
    return float(model.predict(last_s)[0])


# ── 5. XÂY DỰNG KHUYẾN NGHỊ ─────────────────────────────────────────

def build_recommendation(current_price, next_price, rsi, ma20, ma50,
                          macd, macd_signal, best_rmse, best_r2):
    """Tạo khuyến nghị dựa trên nhiều Technical Signals."""
    change_pct = (next_price - current_price) / current_price * 100

    score = 0
    reasons = []

    # 1. Predicted price change
    if change_pct > 2:
        score += 2
        reasons.append(f"Predicted price **tăng {change_pct:.2f}%** — tín hiệu tích cực mạnh")
    elif change_pct > 0.5:
        score += 1
        reasons.append(f"Predicted price **tăng {change_pct:.2f}%** — tín hiệu tích cực")
    elif change_pct < -2:
        score -= 2
        reasons.append(f"Predicted price **giảm {abs(change_pct):.2f}%** — tín hiệu tiêu cực mạnh")
    elif change_pct < -0.5:
        score -= 1
        reasons.append(f"Predicted price **giảm {abs(change_pct):.2f}%** — tín hiệu tiêu cực")
    else:
        reasons.append(f"Predicted price thay đổi nhẹ **{change_pct:+.2f}%** — Neutral")

    # 2. RSI
    if rsi < 30:
        score += 1
        reasons.append(f"RSI = {rsi:.1f} — vùng **Oversold**, cơ hội mua vào")
    elif rsi > 70:
        score -= 1
        reasons.append(f"RSI = {rsi:.1f} — vùng **Overbought**, cảnh báo điều chỉnh")
    else:
        reasons.append(f"RSI = {rsi:.1f} — vùng **Neutral**")

    # 3. MA Cross
    if ma20 > ma50:
        score += 1
        reasons.append("MA20 nằm trên MA50 — **Bullish crossover**, xu hướng tăng ngắn hạn")
    elif ma20 < ma50:
        score -= 1
        reasons.append("MA20 nằm dưới MA50 — **Bearish crossover**, xu hướng giảm ngắn hạn")
    else:
        reasons.append("MA20 và MA50 gần bằng nhau — chưa có Crossover rõ ràng")

    # 4. MACD Signal
    if macd > macd_signal:
        score += 1
        reasons.append("MACD vượt trên Signal Line — **Bullish momentum**")
    else:
        score -= 1
        reasons.append("MACD nằm dưới Signal Line — **Bearish momentum**")

    # 5. Model quality
    if best_rmse > current_price * 0.05:
        reasons.append(f"Model RMSE = {best_rmse:.2f} — sai số khá cao, nên thận trọng")
    else:
        reasons.append(f"Model accuracy tốt (RMSE = {best_rmse:.2f}, R² = {best_r2:.3f})")

    # Map score → Signal
    if score >= 3:
        reco  = "STRONG BUY"
        color = "#22c55e"
        bg    = "rgba(34,197,94,0.12)"
    elif score >= 1:
        reco  = "BUY"
        color = "#86efac"
        bg    = "rgba(134,239,172,0.10)"
    elif score == 0:
        reco  = "NEUTRAL / HOLD"
        color = "#f59e0b"
        bg    = "rgba(245,158,11,0.10)"
    elif score >= -2:
        reco  = "SELL"
        color = "#fb923c"
        bg    = "rgba(251,146,60,0.10)"
    else:
        reco  = "STRONG SELL"
        color = "#ef4444"
        bg    = "rgba(239,68,68,0.12)"

    trend = "Uptrend" if change_pct > 0.5 else ("Downtrend" if change_pct < -0.5 else "Sideways")
    explanation = ". ".join(r.replace("**", "") for r in reasons) + "."

    return {
        "reco": reco, "color": color, "bg": bg,
        "change_pct": change_pct, "trend": trend,
        "reasons": reasons, "explanation": explanation,
    }


# ── 6. BIỂU ĐỒ ──────────────────────────────────────────────────────

def chart_candle_ma(df: pd.DataFrame, ticker: str):
    """Candlestick chart với MA20, MA50 và Volume."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.7, 0.3],
        vertical_spacing=0.03,
        subplot_titles=[f"{ticker} — Price & Moving Averages", "Volume"]
    )

    fig.add_trace(go.Candlestick(
        x=df["Date"], open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="OHLC",
        increasing_line_color="#22c55e",
        decreasing_line_color="#ef4444"
    ), row=1, col=1)

    if "MA20" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["MA20"], name="MA20",
            line=dict(color="#f59e0b", width=1.5)
        ), row=1, col=1)

    if "MA50" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["Date"], y=df["MA50"], name="MA50",
            line=dict(color="#38bdf8", width=1.5)
        ), row=1, col=1)

    colors = ["#22c55e" if c >= o else "#ef4444"
              for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(go.Bar(
        x=df["Date"], y=df["Volume"], name="Volume",
        marker_color=colors, opacity=0.7
    ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark", height=560,
        xaxis_rangeslider_visible=False,
        margin=dict(l=30, r=30, t=40, b=30),
        legend=dict(bgcolor="rgba(0,0,0,0)")
    )
    return fig


def chart_rsi(df: pd.DataFrame):
    """RSI(14) chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["RSI"], name="RSI(14)",
        line=dict(color="#8b5cf6", width=2)
    ))
    fig.add_hrect(y0=70, y1=100, fillcolor="#ef4444", opacity=0.07, layer="below", line_width=0)
    fig.add_hrect(y0=0,  y1=30,  fillcolor="#22c55e", opacity=0.07, layer="below", line_width=0)
    fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", annotation_text="Overbought (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="#22c55e", annotation_text="Oversold (30)")
    fig.update_layout(
        template="plotly_dark", height=260,
        yaxis=dict(range=[0, 100]),
        margin=dict(l=30, r=30, t=40, b=30),
        title="RSI — Relative Strength Index (14)"
    )
    return fig


def chart_macd(df: pd.DataFrame):
    """MACD chart."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["MACD"], name="MACD",
        line=dict(color="#38bdf8", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["MACD_Signal"], name="Signal Line",
        line=dict(color="#f59e0b", width=1.5, dash="dash")
    ))
    hist = df["MACD"] - df["MACD_Signal"]
    fig.add_trace(go.Bar(
        x=df["Date"], y=hist, name="Histogram",
        marker_color=["#22c55e" if v >= 0 else "#ef4444" for v in hist],
        opacity=0.5
    ))
    fig.update_layout(
        template="plotly_dark", height=260,
        margin=dict(l=30, r=30, t=40, b=30),
        title="MACD — Moving Average Convergence Divergence"
    )
    return fig


def chart_actual_vs_pred(df_feat: pd.DataFrame, model, scaler, ticker: str):
    """Actual vs Predicted Price trên Test set."""
    feat = df_feat[FEATURE_COLS + ["Target", "Date"]].dropna()
    if len(feat) < 40:
        return None

    X = feat[FEATURE_COLS].values
    y = feat["Target"].values
    dates = feat["Date"].values

    split = int(len(X) * 0.8)
    X_test = scaler.transform(X[split:])
    y_test = y[split:]
    dates_test = dates[split:]

    preds = model.predict(X_test)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates_test, y=y_test, name="Actual Price",
        line=dict(color="#22c55e", width=2)
    ))
    fig.add_trace(go.Scatter(
        x=dates_test, y=preds, name="Predicted Price",
        line=dict(color="#f59e0b", width=2, dash="dot")
    ))
    fig.update_layout(
        template="plotly_dark", height=300,
        margin=dict(l=30, r=30, t=40, b=30),
        title=f"Actual vs Predicted — {ticker} (Test set 20%)",
        legend=dict(bgcolor="rgba(0,0,0,0)")
    )
    return fig


# ── 7. RENDER CHÍNH ──────────────────────────────────────────────────

def render_ai_analysis_section():
    """Render toàn bộ phần AI Dự Báo."""

    st.subheader("AI Dự Báo — Nhập Ticker Bất Kỳ")
    st.caption(
        "Hỗ trợ mọi ticker trên Yahoo Finance: US stocks, VN stocks (*.VN), "
        "Crypto (BTC-USD, ETH-USD), ETF, Futures và hơn 50.000 mã toàn cầu."
    )

    # ── Input ─────────────────────────────────────────────────────
    inp1, inp2, inp3, inp4 = st.columns([2, 1, 1, 1])

    with inp1:
        raw_ticker = st.text_input(
            "Ticker",
            value="AAPL",
            placeholder="VD: AAPL, TSLA, BTC-USD, FPT.VN",
            help="Nhập bất kỳ ticker hợp lệ trên Yahoo Finance",
            key="ai_ticker_input"
        ).strip().upper()
        
        # Smart mapping for commodities, currencies, and cryptocurrencies
        ticker_input = raw_ticker
        if raw_ticker:
            # Cryptocurrencies
            crypto_map = {
                "BTC": "BTC-USD", "ETH": "ETH-USD", "BNB": "BNB-USD", "SOL": "SOL-USD",
                "XRP": "XRP-USD", "ADA": "ADA-USD", "DOGE": "DOGE-USD", "DOT": "DOT-USD", "LTC": "LTC-USD"
            }
            # Commodities
            commodity_map = {
                "VANG": "GC=F", "GOLD": "GC=F", "GC": "GC=F",
                "DAU": "CL=F", "OIL": "CL=F", "CL": "CL=F", "DUTHOT": "CL=F",
                "BAC": "SI=F", "SILVER": "SI=F", "SI": "SI=F",
                "DONG": "HG=F", "COPPER": "HG=F", "HG": "HG=F",
                "GAS": "NG=F", "NG": "NG=F"
            }
            # Forex/Currencies
            forex_map = {
                "USDVND": "USDVND=X", "USD-VND": "USDVND=X", "USD/VND": "USDVND=X",
                "EURUSD": "EURUSD=X", "EUR-USD": "EURUSD=X", "EUR/USD": "EURUSD=X",
                "GBPUSD": "GBPUSD=X", "GBP-USD": "GBPUSD=X", "GBP/USD": "GBPUSD=X",
                "USDJPY": "USDJPY=X", "USD-JPY": "USDJPY=X", "USD/JPY": "USDJPY=X",
                "AUDUSD": "AUDUSD=X", "AUD-USD": "AUDUSD=X", "AUD/USD": "AUDUSD=X",
                "USDCAD": "USDCAD=X", "USD-CAD": "USDCAD=X", "USD/CAD": "USDCAD=X"
            }
            if raw_ticker in crypto_map:
                ticker_input = crypto_map[raw_ticker]
            elif raw_ticker in commodity_map:
                ticker_input = commodity_map[raw_ticker]
            elif raw_ticker in forex_map:
                ticker_input = forex_map[raw_ticker]

    with inp2:
        period = st.selectbox(
            "Period",
            ["6mo", "1y", "2y", "5y"],
            index=1,
            key="ai_period"
        )

    with inp3:
        interval = st.selectbox(
            "Interval",
            ["1d", "1wk", "1mo"],
            index=0,
            key="ai_interval"
        )

    with inp4:
        st.markdown("<div style='padding-top:26px'></div>", unsafe_allow_html=True)
        run_btn = st.button(
            "Phân Tích & Dự Báo",
            use_container_width=True,
            type="primary",
            key="ai_run_btn"
        )

    if not run_btn:
        st.info("Nhập ticker và nhấn Phân Tích & Dự Báo để bắt đầu.")
        return

    if not ticker_input:
        st.warning("Vui lòng nhập ticker.")
        return

    # ── Tải dữ liệu ───────────────────────────────────────────────
    with st.spinner(f"Đang tải dữ liệu {ticker_input} từ Yahoo Finance…"):
        df_raw = fetch_data(ticker_input, period=period, interval=interval)

    if df_raw.empty:
        st.error(
            f"Không tìm thấy dữ liệu cho ticker **{ticker_input}**. "
            "Kiểm tra lại ticker hoặc thử: AAPL, TSLA, BTC-USD, FPT.VN, VNM.VN"
        )
        return

    if len(df_raw) < 60:
        st.warning(
            f"Chỉ có {len(df_raw)} phiên dữ liệu — có thể ảnh hưởng accuracy. "
            "Thử chọn Period dài hơn hoặc Interval ngắn hơn."
        )

    st.success(f"Đã tải {len(df_raw):,} phiên dữ liệu — {ticker_input}")

    # ── Tính Technical Indicators ─────────────────────────────────
    df_feat = compute_features(df_raw)

    # ── Metric Cards ──────────────────────────────────────────────
    latest = df_feat.iloc[-1]
    current_price = float(latest["Close"])
    rsi_val  = float(latest.get("RSI", 50))
    ma20_val = float(latest.get("MA20", current_price))
    ma50_val = float(latest.get("MA50", current_price))
    macd_val = float(latest.get("MACD", 0))
    macd_sig = float(latest.get("MACD_Signal", 0))
    vol_val  = float(latest.get("Volatility", 0)) * 100

    m1, m2, m3, m4 = st.columns(4)

    def mk(col, label, val, cls=""):
        col.markdown(f"""
        <div class='glass-card'>
            <p class='metric-label'>{label}</p>
            <p class='metric-value {cls}'>{val}</p>
        </div>""", unsafe_allow_html=True)

    mk(m1, "Close Price", f"${current_price:,.2f}")
    rsi_cls = "red" if rsi_val >= 70 else ("green" if rsi_val <= 30 else "blue")
    mk(m2, "RSI (14)", f"{rsi_val:.1f}", rsi_cls)
    mk(m3, "Volatility (20-day)", f"{vol_val:.2f}%", "yellow")
    macd_cls = "green" if macd_val > macd_sig else "red"
    mk(m4, "MACD", f"{macd_val:.3f}", macd_cls)

    # ── Candlestick + Volume ───────────────────────────────────────
    st.markdown(f"### Biểu Đồ Kỹ Thuật — {ticker_input}")
    st.plotly_chart(chart_candle_ma(df_feat, ticker_input), width="stretch")

    # ── RSI & MACD ────────────────────────────────────────────────
    rc1, rc2 = st.columns(2)
    with rc1:
        st.plotly_chart(chart_rsi(df_feat), width="stretch")
    with rc2:
        st.plotly_chart(chart_macd(df_feat), width="stretch")

    # ── Model Training ────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### So Sánh Hiệu Năng Các Model ML")

    with st.spinner("Đang training 3 model, vui lòng chờ…"):
        results_df, best_name, best_model, scaler, feat_df = train_and_evaluate(df_feat)

    if results_df is None:
        st.warning("Không đủ dữ liệu để training model (tối thiểu 60 phiên).")
        return

    def highlight_best(row):
        if row["Model"] == best_name:
            return ["background-color: rgba(34,197,94,0.20)"] * len(row)
        return [""] * len(row)

    st.dataframe(
        results_df.style.apply(highlight_best, axis=1),
        use_container_width=True, hide_index=True
    )
    st.caption(f"Best model: **{best_name}** (RMSE thấp nhất — được highlight xanh)")

    # ── Actual vs Predicted ───────────────────────────────────────
    fig_avp = chart_actual_vs_pred(df_feat, best_model, scaler, ticker_input)
    if fig_avp:
        st.plotly_chart(fig_avp, width="stretch")

    # ── Next Price Prediction ─────────────────────────────────────
    st.markdown("---")
    st.markdown("### Dự Đoán Close Price Phiên Tiếp Theo")

    next_price = predict_next(df_feat, best_model, scaler)
    diff       = next_price - current_price
    diff_pct   = diff / current_price * 100

    trend_txt   = "Uptrend" if diff_pct > 0.5 else ("Downtrend" if diff_pct < -0.5 else "Sideways")
    trend_color = "#22c55e" if diff_pct > 0.5 else ("#ef4444" if diff_pct < -0.5 else "#f59e0b")

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Current Price", f"${current_price:,.2f}")
    p2.metric("Predicted Price", f"${next_price:,.2f}", f"{diff:+.2f}")
    p3.metric("Expected Change", f"{diff_pct:+.2f}%")
    p4.markdown(f"""
    <div class='glass-card' style='text-align:center;margin-top:8px'>
        <p class='metric-label'>Trend</p>
        <p class='metric-value' style='color:{trend_color};font-size:22px'>{trend_txt}</p>
    </div>""", unsafe_allow_html=True)

    # ── AI Signal / Khuyến nghị ───────────────────────────────────
    best_rmse = float(results_df.loc[results_df["Model"] == best_name, "RMSE"].values[0])
    best_r2   = float(results_df.loc[results_df["Model"] == best_name, "R²"].values[0])

    reco_data = build_recommendation(
        current_price, next_price, rsi_val,
        ma20_val, ma50_val, macd_val, macd_sig,
        best_rmse, best_r2
    )

    st.markdown("---")
    st.markdown("### AI Signal & Khuyến Nghị")

    rc_left, rc_right = st.columns([2, 3])

    with rc_left:
        st.markdown(f"""
        <div style='background:{reco_data["bg"]};border:2px solid {reco_data["color"]};
                    border-radius:16px;padding:28px;text-align:center'>
            <div style='font-size:36px;font-weight:900;color:{reco_data["color"]};
                        letter-spacing:2px'>
                {reco_data["reco"]}
            </div>
            <div style='color:#94a3b8;margin-top:14px;font-size:15px;line-height:2'>
                Trend dự báo:<br>
                <b style='color:{trend_color};font-size:18px'>{trend_txt}</b><br>
                Expected change:<br>
                <b style='color:{reco_data["color"]};font-size:18px'>{diff_pct:+.2f}%</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with rc_right:
        st.markdown("**Phân tích các Technical Signal:**")
        for r in reco_data["reasons"]:
            st.markdown(f"- {r}")

        st.markdown(f"""
        <div style='background:rgba(148,163,184,0.08);border-radius:10px;
                    padding:16px;margin-top:14px;border-left:3px solid #38bdf8'>
            <p style='color:#94a3b8;font-size:13px;margin:0;line-height:1.8'>
                <i>{reco_data["explanation"]}</i>
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.warning(
        "Lưu ý: Kết quả phân tích và dự báo chỉ phục vụ mục đích học tập / nghiên cứu, "
        "không phải lời khuyên đầu tư (Not financial advice). "
        "Thị trường tài chính có rủi ro cao, hãy tham khảo chuyên gia tài chính trước khi đầu tư."
    )
