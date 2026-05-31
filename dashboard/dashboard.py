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

try:
    from chat_assistant import render_chat_assistant, check_ollama_alive, get_installed_ollama_models
    CHAT_MODULE_OK = True
except Exception as _chat_err:
    CHAT_MODULE_OK = False
    _CHAT_ERR_MSG = str(_chat_err)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Stock AI",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =======================================================================
#  AUTH — ĐĂNG NHẬP / ĐĂNG KÝ
# =======================================================================

import json
import hashlib

USERS_FILE = os.path.join(os.path.dirname(__file__), "..", ".streamlit", "users.json")

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _load_local_users() -> dict:
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_local_users(users: dict):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def check_login(username: str, password: str) -> bool:
    # Kiểm tra secrets.toml (plain text)
    try:
        valid_users = st.secrets.get("users", {})
        if valid_users.get(username) == password:
            return True
    except Exception:
        if username == "admin" and password == "admin123":
            return True
    # Kiểm tra users.json (hashed)
    local_users = _load_local_users()
    entry = local_users.get(username)
    if entry and entry.get("password_hash") == _hash(password):
        return True
    return False

def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    if len(username) < 3:
        return False, "Tên đăng nhập phải có ít nhất 3 ký tự."
    if len(password) < 6:
        return False, "Mật khẩu phải có ít nhất 6 ký tự."
    # Kiểm tra trùng với secrets
    try:
        if username in st.secrets.get("users", {}):
            return False, "Tên đăng nhập đã tồn tại."
    except Exception:
        if username == "admin":
            return False, "Tên đăng nhập đã tồn tại."
    # Kiểm tra trùng với local
    local_users = _load_local_users()
    if username in local_users:
        return False, "Tên đăng nhập đã tồn tại."
    local_users[username] = {
        "email": email,
        "password_hash": _hash(password),
    }
    _save_local_users(local_users)
    return True, "Đăng ký thành công!"

def render_auth_page():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); }

    .auth-card {
        background: rgba(30, 41, 59, 0.88);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 24px;
        padding: 40px 48px 48px 48px;
        backdrop-filter: blur(16px);
        box-shadow: 0 24px 64px rgba(0,0,0,0.45);
        margin: auto;
    }
    .auth-logo { font-size: 52px; text-align: center; margin-bottom: 6px; }
    .auth-title { font-size: 28px; font-weight: 800; color: #f1f5f9; text-align: center; margin: 0 0 2px 0; }
    .auth-sub   { font-size: 13px; color: #64748b; text-align: center; margin-bottom: 28px; }

    [data-testid="stTextInput"] input {
        background: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(148, 163, 184, 0.2) !important;
        border-radius: 10px !important;
        color: #f1f5f9 !important;
        font-size: 15px !important;
        padding: 12px 16px !important;
    }
    [data-testid="stTextInput"] input:focus {
        border-color: rgba(99, 102, 241, 0.6) !important;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
    }
    [data-testid="stTextInput"] label {
        color: #94a3b8 !important; font-size: 13px !important; font-weight: 600 !important;
    }
    [data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        border: none !important; border-radius: 10px !important;
        color: white !important; font-size: 16px !important; font-weight: 700 !important;
        padding: 13px !important; width: 100% !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4) !important;
        margin-top: 8px !important;
    }
    [data-testid="stFormSubmitButton"] button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(99, 102, 241, 0.55) !important;
    }
    /* Tab styling */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        background: rgba(15,23,42,0.5) !important;
        border-radius: 12px !important;
        padding: 4px !important;
        gap: 4px !important;
        margin-bottom: 24px !important;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        border-radius: 9px !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        color: #94a3b8 !important;
        padding: 10px 0 !important;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: white !important;
    }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class='auth-logo'>Stock AI System  </div>
        <p class='auth-sub'>Nền tảng phân tích & dự báo cổ phiếu thông minh</p>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["Đăng Nhập", "Đăng Ký"])

        # ── TAB ĐĂNG NHẬP ──────────────────────────────────────
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Tên đăng nhập", placeholder="Nhập username...", key="li_user")
                password = st.text_input("Mật khẩu", type="password", placeholder="Nhập mật khẩu...", key="li_pass")
                submitted = st.form_submit_button("Đăng Nhập", use_container_width=True)

            if submitted:
                if check_login(username.strip(), password):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username.strip()
                    if "chat_messages" in st.session_state:
                        del st.session_state["chat_messages"]
                    st.rerun()
                else:
                    st.error("❌ Sai tên đăng nhập hoặc mật khẩu!")

        # ── TAB ĐĂNG KÝ ────────────────────────────────────────
        with tab_register:
            with st.form("register_form"):
                reg_user  = st.text_input("Tên đăng nhập", placeholder="Tối thiểu 3 ký tự...", key="rg_user")
                reg_email = st.text_input("Email", placeholder="example@email.com", key="rg_email")
                reg_pass  = st.text_input("Mật khẩu", type="password", placeholder="Tối thiểu 6 ký tự...", key="rg_pass")
                reg_pass2 = st.text_input("Xác nhận mật khẩu", type="password", placeholder="Nhập lại mật khẩu...", key="rg_pass2")
                reg_submitted = st.form_submit_button("Tạo Tài Khoản", use_container_width=True)

            if reg_submitted:
                if not reg_user.strip() or not reg_pass:
                    st.error("⚠️ Vui lòng điền đầy đủ thông tin.")
                elif reg_pass != reg_pass2:
                    st.error("❌ Mật khẩu xác nhận không khớp!")
                else:
                    ok, msg = register_user(reg_user.strip(), reg_email.strip(), reg_pass)
                    if ok:
                        st.success(f"✅ {msg} Hãy chuyển sang tab Đăng Nhập.")
                    else:
                        st.error(f"❌ {msg}")

if not st.session_state.get("authenticated", False):
    render_auth_page()
    st.stop()


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

# Hiển thị user đang đăng nhập
current_user = st.session_state.get("username", "")
st.sidebar.markdown(f"""
<div style='
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 10px;
    padding: 10px 14px;
    text-align: center;
    margin-bottom: 4px;
'>
    <span style='color:#94a3b8; font-size:12px;'>đăng nhập với</span><br>
    <span style='color:#a5b4fc; font-size:16px; font-weight:700;'>{current_user}</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

# Navigation buttons
if "current_view" not in st.session_state:
    st.session_state["current_view"] = "Tổng quan"

view_options = [
    "Tổng quan",
    "Phân Tích & AI Dự Báo",
    "Thị Trường & So Sánh",
    "Trợ Lý AI Chat",
]

for opt in view_options:
    is_active = "active" if st.session_state["current_view"] == opt else ""
    if st.sidebar.button(opt, key=f"nav_{opt}", use_container_width=True):
        st.session_state["current_view"] = opt
        st.rerun()

# Cấu hình thân thiện cho AI Chat trong Sidebar
if st.session_state["current_view"] == "Trợ Lý AI Chat":
    st.sidebar.markdown("---")
    st.sidebar.markdown("<p style='font-size:16px; font-weight:700; color:#cbd5e1; margin-bottom:12px;'>Cài đặt AI Chat</p>", unsafe_allow_html=True)
    
    # 1. Bộ chọn chế độ phân tích thân thiện
    analysis_mode_friendly = st.sidebar.radio(
        "Chế độ phân tích:",
        ["Phân tích nhanh", "Phân tích thông minh"],
        index=0,
        help="Chọn chế độ phân tích tài chính phù hợp với nhu cầu của bạn."
    )
    analysis_mode = "Nhanh" if "Nhanh" in analysis_mode_friendly else "Thông minh"
    st.session_state["chat_analysis_mode"] = analysis_mode
    
    # 2. Thu gọn thông tin kỹ thuật trong expander nâng cao
    with st.sidebar.expander("Cấu hình nâng cao"):
        st.markdown("<p style='font-size:12px; font-weight:600; margin:0; color:#94a3b8;'>Trạng thái trợ lý cục bộ:</p>", unsafe_allow_html=True)
        is_ollama_ready = check_ollama_alive() if CHAT_MODULE_OK else False
        if is_ollama_ready:
            st.markdown("<p style='font-size:14px; color:#22c55e; font-weight:700; margin:0 0 10px 0;'>Sẵn sàng</p>", unsafe_allow_html=True)
            installed_models = get_installed_ollama_models() if CHAT_MODULE_OK else []
            selected_model = st.selectbox(
                "Mô hình AI cục bộ:",
                installed_models,
                index=0 if "qwen2.5:1.5b" not in installed_models else installed_models.index("qwen2.5:1.5b")
            )
            st.session_state["chat_selected_model"] = selected_model
        else:
            st.markdown("<p style='font-size:14px; color:#ef4444; font-weight:700; margin:0 0 10px 0;'>Chưa sẵn sàng</p>", unsafe_allow_html=True)
            st.session_state["chat_selected_model"] = "qwen2.5:1.5b"
            st.markdown("""
            <p style='font-size:11px; color:#94a3b8; line-height:1.5; margin:0;'>
                Chế độ <b>Phân tích thông minh</b> yêu cầu trợ lý AI cục bộ chạy trên máy của bạn.<br><br>
                <b>Cách kích hoạt trợ lý:</b><br>
                1. Khởi động ứng dụng <b>Ollama</b>.<br>
                2. Chạy lệnh CMD tải mô hình:<br>
                <code style='background:rgba(255,255,255,0.08); padding:2px 4px; border-radius:3px; color:#fca5a5;'>ollama run qwen2.5:1.5b</code>
            </p>
            """, unsafe_allow_html=True)
else:
    # Thiết lập mặc định khi đang ở tab khác
    if "chat_analysis_mode" not in st.session_state:
        st.session_state["chat_analysis_mode"] = "Nhanh"
    if "chat_selected_model" not in st.session_state:
        st.session_state["chat_selected_model"] = "qwen2.5:1.5b"

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

# Nút đăng xuất
st.sidebar.markdown("""
<style>
[data-testid="stSidebar"] [data-testid="stBaseButton-logout_btn"] button,
[data-testid="stSidebar"] div[data-testid$="logout_btn"] button {
    background: rgba(239,68,68,0.15) !important;
    border: 1px solid rgba(239,68,68,0.35) !important;
    color: #fca5a5 !important;
}
[data-testid="stSidebar"] div[data-testid$="logout_btn"] button:hover {
    background: rgba(239,68,68,0.3) !important;
    border-color: rgba(239,68,68,0.6) !important;
    color: #fee2e2 !important;
}
</style>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Đăng xuất", use_container_width=True, key="logout_btn"):
    st.session_state["authenticated"] = False
    st.session_state["username"] = ""
    if "chat_messages" in st.session_state:
        del st.session_state["chat_messages"]
    st.rerun()



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


# =======================================================================
#  VIEW 4: TRỢ LÝ AI CHAT
# =======================================================================

elif view == "Trợ Lý AI Chat":
    if not CHAT_MODULE_OK:
        st.error(f"Không tải được module Trợ Lý AI Chat: {_CHAT_ERR_MSG}")
    else:
        # Lấy cấu hình từ session
        analysis_mode = st.session_state.get("chat_analysis_mode", "Nhanh")
        selected_model = st.session_state.get("chat_selected_model", "qwen2.5:1.5b")
        
        # Render Chat Assistant
        render_chat_assistant(analysis_mode, selected_model)
