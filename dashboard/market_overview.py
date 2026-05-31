# ====================================================================
# Market Overview — dashboard/market_overview.py
# Trang tổng quan thị trường: biểu đồ chỉ số + bảng hiệu suất
# Bấm vào tên CP bên phải → cập nhật biểu đồ bên trái
# ====================================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, datetime
import warnings
warnings.filterwarnings("ignore")


# ── CẤU HÌNH CÁC MÃ THEO VÙNG ───────────────────────────────────────
# Lưu ý: Yahoo Finance không hỗ trợ các chỉ số VN (^VNINDEX, ^HNX...)
# → dùng cổ phiếu VN30 với hậu tố .VN thay thế

REGIONS = {
    "Việt Nam": {
        "chart_ticker": "FPT.VN",
        "chart_name":   "FPT",
        "indices": [
            {"name": "FPT",  "ticker": "FPT.VN"},
            {"name": "VIC",  "ticker": "VIC.VN"},
            {"name": "HPG",  "ticker": "HPG.VN"},
            {"name": "VHM",  "ticker": "VHM.VN"},
            {"name": "VCB",  "ticker": "VCB.VN"},
            {"name": "TCB",  "ticker": "TCB.VN"},
            {"name": "VNM",  "ticker": "VNM.VN"},
            {"name": "MWG",  "ticker": "MWG.VN"},
            {"name": "CTG",  "ticker": "CTG.VN"},
            {"name": "HDB",  "ticker": "HDB.VN"},
            {"name": "MSN",  "ticker": "MSN.VN"},
            {"name": "VPB",  "ticker": "VPB.VN"},
            {"name": "BID",  "ticker": "BID.VN"},
            {"name": "GAS",  "ticker": "GAS.VN"},
            {"name": "SAB",  "ticker": "SAB.VN"},
            {"name": "SSI",  "ticker": "SSI.VN"},
            {"name": "PLX",  "ticker": "PLX.VN"},
            {"name": "MBB",  "ticker": "MBB.VN"},
            {"name": "POW",  "ticker": "POW.VN"},
            {"name": "PNJ",  "ticker": "PNJ.VN"},
        ],
    },
    "Mỹ": {
        "chart_ticker": "^GSPC",
        "chart_name":   "S&P 500",
        "indices": [
            {"name": "S&P 500",      "ticker": "^GSPC"},
            {"name": "Dow Jones",    "ticker": "^DJI"},
            {"name": "NASDAQ",       "ticker": "^IXIC"},
            {"name": "Russell 2000", "ticker": "^RUT"},
            {"name": "VIX",          "ticker": "^VIX"},
            {"name": "S&P 400",      "ticker": "^MID"},
            {"name": "NYSE",         "ticker": "^NYA"},
            {"name": "S&P 600",      "ticker": "^SML"},
            {"name": "AAPL",         "ticker": "AAPL"},
            {"name": "MSFT",         "ticker": "MSFT"},
            {"name": "AMZN",         "ticker": "AMZN"},
            {"name": "GOOGL",        "ticker": "GOOGL"},
            {"name": "TSLA",         "ticker": "TSLA"},
            {"name": "NVDA",         "ticker": "NVDA"},
            {"name": "META",         "ticker": "META"},
            {"name": "NFLX",         "ticker": "NFLX"},
            {"name": "BRK-B",        "ticker": "BRK-B"},
            {"name": "JPM",          "ticker": "JPM"},
            {"name": "V",            "ticker": "V"},
            {"name": "UNH",          "ticker": "UNH"},
        ],
    },
    "Châu Âu": {
        "chart_ticker": "^STOXX50E",
        "chart_name":   "Euro Stoxx 50",
        "indices": [
            {"name": "Euro Stoxx 50", "ticker": "^STOXX50E"},
            {"name": "FTSE 100",      "ticker": "^FTSE"},
            {"name": "DAX",           "ticker": "^GDAXI"},
            {"name": "CAC 40",        "ticker": "^FCHI"},
            {"name": "IBEX 35",       "ticker": "^IBEX"},
            {"name": "AEX",           "ticker": "^AEX"},
            {"name": "SMI",           "ticker": "^SSMI"},
            {"name": "BEL 20",        "ticker": "^BFX"},
            {"name": "OMX 30",        "ticker": "^OMX"},
            {"name": "LVMH",          "ticker": "MC.PA"},
            {"name": "SAP",           "ticker": "SAP"},
            {"name": "ASML",          "ticker": "ASML"},
            {"name": "Nestlé",        "ticker": "NESN.SW"},
            {"name": "Siemens",       "ticker": "SIE.DE"},
            {"name": "Volkswagen",    "ticker": "VOW3.DE"},
        ],
    },
    "Châu Á": {
        "chart_ticker": "^N225",
        "chart_name":   "Nikkei 225",
        "indices": [
            {"name": "Nikkei 225",    "ticker": "^N225"},
            {"name": "Hang Seng",     "ticker": "^HSI"},
            {"name": "Shanghai",      "ticker": "000001.SS"},
            {"name": "Kospi",         "ticker": "^KS11"},
            {"name": "STI",           "ticker": "^STI"},
            {"name": "ASX 200",       "ticker": "^AXJO"},
            {"name": "Nifty 50",      "ticker": "^NSEI"},
            {"name": "Sensex",        "ticker": "^BSESN"},
            {"name": "Toyota",        "ticker": "7203.T"},
            {"name": "Sony",          "ticker": "6758.T"},
            {"name": "Samsung",       "ticker": "005930.KS"},
            {"name": "Alibaba",       "ticker": "9988.HK"},
            {"name": "Tencent",       "ticker": "0700.HK"},
            {"name": "Meituan",       "ticker": "3690.HK"},
            {"name": "BYD",           "ticker": "1211.HK"},
        ],
    },
}

CHART_PERIODS = {
    "1D":  {"period": "1d",  "interval": "5m"},
    "5D":  {"period": "5d",  "interval": "15m"},
    "1M":  {"period": "1mo", "interval": "1h"},
    "3M":  {"period": "3mo", "interval": "1d"},
    "6M":  {"period": "6mo", "interval": "1d"},
    "YTD": {"period": "ytd", "interval": "1d"},
    "1Y":  {"period": "1y",  "interval": "1d"},
    "ALL": {"period": "max", "interval": "1wk"},
}

MAX_INDICES = 20


# ── DATA FETCHING ────────────────────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def fetch_chart_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_index_summary(ticker: str) -> dict:
    try:
        df = yf.download(ticker, period="1y", interval="1d",
                         auto_adjust=True, progress=False)
        if df is None or df.empty:
            return {}
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if "Close" not in df.columns:
            return {}

        close = df["Close"].dropna()
        if len(close) < 2:
            return {}

        price = float(close.iloc[-1])

        def pct(n):
            if len(close) > n:
                return float((close.iloc[-1] - close.iloc[-n]) / close.iloc[-n] * 100)
            return None

        ytd_start = date(date.today().year, 1, 1)
        ytd_mask  = df.index.date >= ytd_start
        ytd_close = close[ytd_mask]
        ytd = float((ytd_close.iloc[-1] - ytd_close.iloc[0]) / ytd_close.iloc[0] * 100) \
              if len(ytd_close) > 1 else None

        return {"price": price, "D": pct(2), "W": pct(6),
                "M": pct(22), "Q": pct(66), "YTD": ytd}
    except Exception:
        return {}


# ── HELPERS ──────────────────────────────────────────────────────────

def fmt_pct(val):
    if val is None:
        return "—"
    return f"{'+'if val>=0 else ''}{val:.2f}%"

def pct_color(val):
    if val is None:
        return "#475569"
    return "#22c55e" if val >= 0 else "#ef4444"


# ── CHART ────────────────────────────────────────────────────────────

def _render_chart():
    ticker   = st.session_state.mo_chart_ticker
    name     = st.session_state.mo_chart_name
    period_k = st.session_state.mo_period
    params   = CHART_PERIODS[period_k]

    df = fetch_chart_data(ticker, params["period"], params["interval"])

    if df.empty or "Close" not in df.columns:
        st.warning(f"Không lấy được dữ liệu **{name}** ({ticker}) từ Yahoo Finance.")
        return

    close = df["Close"].dropna()
    if len(close) < 2:
        st.warning("Dữ liệu không đủ để vẽ biểu đồ.")
        return

    latest     = float(close.iloc[-1])
    first      = float(close.iloc[0])
    change     = latest - first
    change_pct = change / first * 100
    is_up      = change >= 0
    line_color = "#22c55e" if is_up else "#ef4444"
    fill_color = "rgba(34,197,94,0.08)" if is_up else "rgba(239,68,68,0.08)"
    arrow      = "▲" if is_up else "▼"

    st.markdown(f"""
    <div style='padding:2px 0 10px 0'>
        <span style='font-size:15px;color:#94a3b8;font-weight:600'>{name}</span>
        <span style='font-size:11px;color:#475569;margin-left:6px'>({ticker})</span><br>
        <span style='font-size:32px;font-weight:900;color:#f1f5f9;letter-spacing:-1px'>
            {latest:,.2f}
        </span>&nbsp;
        <span style='font-size:13px;font-weight:700;color:{line_color}'>
            {arrow} {abs(change):.2f} ({change_pct:+.2f}%)
        </span>
    </div>
    """, unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=close.index,
        y=close.values,
        mode="lines",
        line=dict(color=line_color, width=2),
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate="<b>%{y:,.2f}</b><br>%{x}<extra></extra>",
    ))
    fig.update_layout(
        height=320,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=4, t=0, b=0),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   zeroline=False, showline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                   zeroline=False, side="right", showline=False),
        showlegend=False,
        hovermode="x unified",
    )
    # Dùng width='stretch' thay use_container_width (deprecated sau 2025-12-31)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.markdown(
        f"<div style='color:#475569;font-size:11px;text-align:right;margin-top:-10px'>"
        f"🕐 {datetime.now().strftime('%d/%m/%Y — %H:%M:%S')}</div>",
        unsafe_allow_html=True,
    )


# ── BẢNG CP (CLICKABLE) ──────────────────────────────────────────────

def _render_indices_table():
    region  = st.session_state.mo_region
    indices = REGIONS[region]["indices"][:MAX_INDICES]

    st.markdown("""
    <style>
    .mo-header {
        color:#64748b; font-size:11.5px; font-weight:600;
        padding:4px 2px; border-bottom:1px solid rgba(148,163,184,0.15);
        margin-bottom:2px;
    }
    .mo-cell {
        font-size:12.5px; padding:1px 2px;
        text-align:right; font-weight:600;
    }
    .mo-divider {
        border-bottom:1px solid rgba(148,163,184,0.07);
        margin:1px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    COL_W = [2.6, 1.3, 0.85, 0.85, 0.85, 0.85, 0.85]

    # Header
    hcols = st.columns(COL_W)
    for col, label in zip(hcols, ["", "Giá", "D", "W", "M", "Q", "YTD"]):
        col.markdown(
            f"<div class='mo-header' style='text-align:{'left' if label=='' else 'right'}'>{label}</div>",
            unsafe_allow_html=True,
        )

    # Rows
    for idx in indices:
        data      = fetch_index_summary(idx["ticker"])
        price_str = f"{data['price']:,.2f}" if data.get("price") else "—"
        is_sel    = (st.session_state.mo_chart_ticker == idx["ticker"])

        row = st.columns(COL_W)

        # Tên — nút bấm clickable
        with row[0]:
            if st.button(
                idx["name"],
                key=f"idx_btn_{idx['ticker']}",
                use_container_width=True,
                type="primary" if is_sel else "secondary",
            ):
                st.session_state.mo_chart_ticker = idx["ticker"]
                st.session_state.mo_chart_name   = idx["name"]
                st.rerun()

        # Giá
        row[1].markdown(
            f"<div class='mo-cell' style='color:#cbd5e1'>{price_str}</div>",
            unsafe_allow_html=True,
        )

        # D / W / M / Q / YTD
        for col, key in zip(row[2:], ["D", "W", "M", "Q", "YTD"]):
            v  = data.get(key)
            col.markdown(
                f"<div class='mo-cell' style='color:{pct_color(v)}'>{fmt_pct(v)}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div class='mo-divider'></div>", unsafe_allow_html=True)


# ── MAIN RENDER ──────────────────────────────────────────────────────

def render_market_overview():
    # Session state defaults
    if "mo_region" not in st.session_state:
        st.session_state.mo_region = "Việt Nam"
    if "mo_period" not in st.session_state:
        st.session_state.mo_period = "1D"
    if "mo_category" not in st.session_state:
        st.session_state.mo_category = "Chứng khoán"
    if "mo_chart_ticker" not in st.session_state:
        st.session_state.mo_chart_ticker = REGIONS["Việt Nam"]["chart_ticker"]
    if "mo_chart_name" not in st.session_state:
        st.session_state.mo_chart_name = REGIONS["Việt Nam"]["chart_name"]

    # Xóa ticker cũ không hợp lệ còn sót trong session (^VNINDEX, ^HNX...)
    _invalid = {
        "^VNINDEX", "^HNX", "^UPCOM", "^VN30", "^HNX30",
        "^VNMIDCAP", "^VN100", "^VNSMALL", "^VNALL", "^VS100", "VN30F1M.VN",
    }
    if st.session_state.get("mo_chart_ticker") in _invalid:
        region = st.session_state.get("mo_region", "Việt Nam")
        cfg    = REGIONS.get(region, REGIONS["Việt Nam"])
        st.session_state.mo_chart_ticker = cfg["chart_ticker"]
        st.session_state.mo_chart_name   = cfg["chart_name"]

    # Tiêu đề
    st.markdown("""
    <h2 style='color:#f1f5f9;font-weight:900;margin:0 0 8px 0;font-size:28px'>
        Thị trường
    </h2>""", unsafe_allow_html=True)

    # Tabs danh mục
    categories = ["Chứng khoán", "Hàng hóa", "Tiền tệ", "Tiền ảo"]
    cat_cols   = st.columns([1.1, 1.1, 1.1, 1.1, 5])
    for i, cat in enumerate(categories):
        with cat_cols[i]:
            is_active = (st.session_state.mo_category == cat)
            if st.button(cat, key=f"cat_{cat}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state.mo_category = cat
                st.rerun()

    if st.session_state.mo_category != "Chứng khoán":
        st.info(f"Tính năng **{st.session_state.mo_category}** đang được phát triển — sắp ra mắt.")
        return

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Layout chính
    col_chart, col_table = st.columns([3, 2], gap="large")

    # ════ BIỂU ĐỒ ════
    with col_chart:
        period_cols = st.columns(len(CHART_PERIODS))
        for col, pk in zip(period_cols, CHART_PERIODS):
            is_sel = (st.session_state.mo_period == pk)
            with col:
                if st.button(pk, key=f"period_{pk}", use_container_width=True,
                             type="primary" if is_sel else "secondary"):
                    st.session_state.mo_period = pk
                    st.rerun()

        _render_chart()

    # ════ BẢNG CLICKABLE ════
    with col_table:
        region_keys = list(REGIONS.keys())
        r_cols      = st.columns(len(region_keys))
        for col, rk in zip(r_cols, region_keys):
            is_sel = (st.session_state.mo_region == rk)
            with col:
                if st.button(rk, key=f"region_{rk}", use_container_width=True,
                             type="primary" if is_sel else "secondary"):
                    st.session_state.mo_region       = rk
                    st.session_state.mo_chart_ticker = REGIONS[rk]["chart_ticker"]
                    st.session_state.mo_chart_name   = REGIONS[rk]["chart_name"]
                    st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

        with st.spinner("Đang tải…"):
            _render_indices_table()
