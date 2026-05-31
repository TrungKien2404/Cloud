# ====================================================================
# User-Friendly AI Chat Assistant - dashboard/chat_assistant.py
# Chế độ: Phân tích nhanh (Offline Rules) & Phân tích thông minh (Local SLM RAG)
# ====================================================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
import re
import time
import json
from datetime import datetime

# Import các hàm tính toán từ module phân tích sẵn có
try:
    from ai_analysis import fetch_data, compute_features, train_and_evaluate, build_recommendation
    AI_ANALYTICS_OK = True
except Exception as e:
    AI_ANALYTICS_OK = False
    st.error(f"Lỗi import từ ai_analysis.py: {str(e)}")

OLLAMA_HOST = "http://localhost:11434"

# Danh sách Tickers mặc định của hệ thống để quét nhanh
SYSTEM_TICKERS = [
    "AAPL", "TSLA", "MSFT", "AMZN", "GOOGL", "NVDA", "META", "NFLX", "BTC-USD", "ETH-USD",
    "FPT.VN", "HPG.VN", "VNM.VN", "VIC.VN", "TCB.VN", "VHM.VN", "VCB.VN", "MWG.VN", "BID.VN", "SSI.VN"
]

def check_ollama_alive() -> bool:
    """Kiểm tra ngầm xem phần mềm Ollama (Trợ lý AI cục bộ) có đang chạy không."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=1.5)
        return response.status_code == 200
    except Exception:
        return False

def get_installed_ollama_models() -> list:
    """Lấy danh sách các mô hình ngôn ngữ đã tải trong Ollama."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=1.5)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            return [m.get("name") for m in models_data]
    except Exception:
        pass
    return ["qwen2.5:1.5b", "gemma2:2b", "llama3:latest"]

def detect_ticker(text: str) -> str:
    """Quét văn bản để tự động phát hiện mã cổ phiếu trong câu hỏi."""
    text_upper = text.upper()
    
    # 0. Hỗ trợ mapping viết tắt cho các lớp tài sản mới
    # a. Tiền ảo (Cryptocurrencies)
    crypto_map = {
        r'\bBTC\b': 'BTC-USD',
        r'\bETH\b': 'ETH-USD',
        r'\bBNB\b': 'BNB-USD',
        r'\bSOL\b': 'SOL-USD',
        r'\bXRP\b': 'XRP-USD',
        r'\bADA\b': 'ADA-USD',
        r'\bDOGE\b': 'DOGE-USD',
        r'\bDOT\b': 'DOT-USD',
        r'\bLTC\b': 'LTC-USD',
    }
    for pattern, target in crypto_map.items():
        if re.search(pattern, text_upper):
            return target
            
    # b. Hàng hóa (Commodities)
    commodity_map = {
        r'\b(VANG|GOLD|GC)\b': 'GC=F',
        r'\b(DAU|OIL|CL|DUTHOT)\b': 'CL=F',
        r'\b(BAC|SILVER|SI)\b': 'SI=F',
        r'\b(DONG|COPPER|HG)\b': 'HG=F',
        r'\b(GAS|NG)\b': 'NG=F',
    }
    for pattern, target in commodity_map.items():
        if re.search(pattern, text_upper):
            return target
            
    # c. Tiền tệ / Ngoại hối (Currencies/Forex)
    forex_map = {
        r'\b(USDVND|USD-VND|USD/VND)\b': 'USDVND=X',
        r'\b(EURUSD|EUR-USD|EUR/USD)\b': 'EURUSD=X',
        r'\b(GBPUSD|GBP-USD|GBP/USD)\b': 'GBPUSD=X',
        r'\b(USDJPY|USD-JPY|USD/JPY)\b': 'USDJPY=X',
        r'\b(AUDUSD|AUD-USD|AUD/USD)\b': 'AUDUSD=X',
        r'\b(USDCAD|USD-CAD|USDCAD)\b': 'USDCAD=X',
    }
    for pattern, target in forex_map.items():
        if re.search(pattern, text_upper):
            return target

    # 1. Quét theo danh sách hệ thống trước (không phân biệt hoa thường)
    for ticker in SYSTEM_TICKERS:
        if ticker in text_upper:
            return ticker
            
    # 2. Quét theo Regex cho mã Việt Nam (VD: FPT.VN) hoặc Crypto (BTC-USD)
    match_vn = re.search(r'\b([A-Za-z]{3,5}\.VN)\b', text)
    if match_vn:
        return match_vn.group(1).upper()
        
    match_crypto = re.search(r'\b([A-Za-z]{3,5}-USD)\b', text)
    if match_crypto:
        return match_crypto.group(1).upper()
        
    match_futures = re.search(r'\b([A-Za-z]{1,4}=F)\b', text)
    if match_futures:
        return match_futures.group(1).upper()
        
    match_forex = re.search(r'\b([A-Za-z]{3,6}=X)\b', text)
    if match_forex:
        return match_forex.group(1).upper()
        
    # 3. Quét các từ viết hoa 3-4 ký tự (VD: AAPL, HPG) đứng độc lập để đoán mã US/VN
    match_us = re.search(r'\b([A-Z]{3,5})\b', text)
    if match_us:
        potential = match_us.group(1)
        # Bỏ qua một số từ tiếng Anh/Việt viết hoa thông thường dễ nhầm lẫn
        ignored_words = ["BUY", "SELL", "HOLD", "RSI", "MACD", "MA20", "MA50", "USD", "VND", "EUR", "BTC", "ETH", "GOLD", "VANG", "OIL", "DAU"]
        if potential not in ignored_words:
            return potential
            
    return ""

def query_ticker_metrics(ticker: str) -> dict:
    """Lấy dữ liệu chỉ báo kỹ thuật thực tế và kết quả dự báo ML của mã cổ phiếu."""
    if not AI_ANALYTICS_OK:
        return {}
        
    try:
        # Tải dữ liệu 1 năm lịch sử
        df_raw = fetch_data(ticker, period="1y", interval="1d")
        if df_raw.empty:
            return {}
            
        df_feat = compute_features(df_raw)
        if len(df_feat) < 40:
            return {}
            
        latest = df_feat.iloc[-1]
        current_price = float(latest["Close"])
        previous_close = float(df_feat.iloc[-2]["Close"]) if len(df_feat) > 1 else current_price
        rsi_val = float(latest.get("RSI", 50))
        ma20_val = float(latest.get("MA20", current_price))
        ma50_val = float(latest.get("MA50", current_price))
        macd_val = float(latest.get("MACD", 0))
        macd_sig = float(latest.get("MACD_Signal", 0))
        vol_val = float(latest.get("Volatility", 0)) * 100
        latest_data_date = str(latest["Date"])[:10]
        
        # Huấn luyện nhanh mô hình ML để dự đoán ngày mai
        results_df, best_name, best_model, scaler, feat_df = train_and_evaluate(df_feat)
        
        next_price = current_price
        diff_pct = 0.0
        best_rmse = 0.0
        best_r2 = 0.0
        
        if results_df is not None:
            # Dự đoán giá ngày mai
            last_feat = df_feat[["Return", "MA20", "MA50", "Volatility", "RSI", "MACD", "MACD_Signal"]].dropna().iloc[-1:].values
            last_s = scaler.transform(last_feat)
            next_price = float(best_model.predict(last_s)[0])
            diff_pct = (next_price - current_price) / current_price * 100
            
            best_rmse = float(results_df.loc[results_df["Model"] == best_name, "RMSE"].values[0])
            best_r2 = float(results_df.loc[results_df["Model"] == best_name, "R²"].values[0])
            
        # Lập khuyến nghị
        reco = build_recommendation(
            current_price, next_price, rsi_val, ma20_val, ma50_val,
            macd_val, macd_sig, best_rmse, best_r2
        )
        
        reco_name = reco["reco"]
        reco_color = reco["color"]
        reco_reasons = list(reco["reasons"])
        reco_explanation = reco["explanation"]
        
        # Điều chỉnh khuyến nghị khi RSI quá mua (>70) nhưng xu thế vẫn Bullish
        if rsi_val > 70 and reco_name in ["STRONG BUY", "BUY"]:
            reco_name = "HOLD / WATCH"
            reco_color = "#f59e0b"  # Màu vàng cam hổ phách
            reco_explanation = "Mac dẫu xu thế dòng tiền và động lượng ngắn hạn (MA & MACD) vẫn tích cực, nhưng chỉ số RSI hiện đã đi sâu vào vùng Quá Mua (>70). Việc giải ngân mua mới ở vùng giá này tiềm ẩn rủi ro điều chỉnh kỹ thuật rất cao. Khuyến nghị NẮM GIỮ / THEO DÕI sát sao để tối ưu lợi nhuận, dừng việc mua đuổi."
            reco_reasons.append("Chỉ số RSI > 70 báo hiệu Quá Mua — khuyến nghị chuyển sang Theo Dõi / Nắm Giữ, dừng vị thế mua mới để tránh rủi ro nhịp chỉnh ngắn hạn")

        # Phân tách rủi ro (Xóa icon)
        # 1. Rủi ro biến động
        vol_risk = "THAP"
        if vol_val > 3.0:
            vol_risk = "CAO (Bien do dao dong rat lon)"
        elif vol_val > 1.5:
            vol_risk = "TRUNG BINH"
        else:
            vol_risk = "THAP"
            
        # 2. Rủi ro điều chỉnh kỹ thuật
        tech_risk = "THAP"
        if rsi_val > 70:
            tech_risk = "CAO (Qua mua, ap luc chot loi gia tang)"
        elif rsi_val < 30:
            tech_risk = "THAP (Qua ban, co the xuat hien nhip hoi ky thuat)"
        elif 60 <= rsi_val <= 70:
            tech_risk = "TRUNG BINH (Ap luc dieu chinh nhe)"
        else:
            tech_risk = "THAP"
            
        # Dọn dẹp emoji/icon khỏi reco_name
        reco_name = reco_name.replace("🟢", "").replace("🟡", "").replace("🟠", "").replace("🔴", "").replace("⚠️", "").strip()
            
        return {
            "ticker": ticker,
            "current_price": current_price,
            "previous_close": previous_close,
            "predicted_next_price": next_price,
            "predicted_change_pct": diff_pct,
            "rsi": rsi_val,
            "ma20": ma20_val,
            "ma50": ma50_val,
            "macd": macd_val,
            "macd_signal": macd_sig,
            "volatility": vol_val,
            "vol_risk": vol_risk,
            "tech_risk": tech_risk,
            "recommendation": reco_name,
            "reco_color": reco_color,
            "reco_reasons": reco_reasons,
            "reco_explanation": reco_explanation,
            "model_name": best_name,
            "best_rmse": best_rmse,
            "best_r2": best_r2,
            "latest_data_date": latest_data_date
        }
    except Exception as err:
        st.warning(f"Không thể tính toán số liệu cho {ticker}: {str(err)}")
        return {}

def render_fast_analysis_report(metrics: dict) -> str:
    """Tạo báo cáo HTML phân tích kỹ thuật nhanh chuyên nghiệp, không chứa icon."""
    ticker = metrics["ticker"]
    curr = metrics["current_price"]
    prev_close = metrics.get("previous_close", curr)
    hist_change_pct = ((curr - prev_close) / prev_close * 100) if prev_close else 0.0
    
    pred = metrics["predicted_next_price"]
    change = metrics["predicted_change_pct"]
    rsi = metrics["rsi"]
    vol = metrics["volatility"]
    vol_risk = metrics["vol_risk"]
    tech_risk = metrics["tech_risk"]
    reco_name = metrics["recommendation"]
    reco_color = metrics["reco_color"]
    reco_explanation = metrics["reco_explanation"]
    last_date = metrics["latest_data_date"]
    best_model_name = metrics["model_name"]
    best_rmse = metrics.get("best_rmse", 0.23)
    best_r2 = metrics.get("best_r2", 0.0)
    
    if ticker.endswith(".VN") or ticker == "USDVND=X":
        currency = "VND"
    elif ticker.endswith("=X"):
        currency = ""
    else:
        currency = "$"
    
    rsi_nhan_dinh = 'Qua Mua (Canh bao dao chieu giam)' if rsi > 70 else ('Qua Ban (Co hoi tao day di len)' if rsi < 30 else 'Trung tinh (Xu huong tiep tuc tich luy)')
    trend_nhan_dinh = 'Xu huong tang (Uptrend)' if change > 0.5 else ('Xu huong giam (Downtrend)' if change < -0.5 else 'Xu huong di ngang (Neutral)')
    
    # Map signal
    final_reco = "WATCH / HOLD"
    final_reco_color = "#f59e0b"
    if reco_name in ["STRONG BUY", "BUY"]:
        final_reco = "BUY"
        final_reco_color = "#22c55e"
    elif reco_name in ["STRONG SELL", "SELL"]:
        final_reco = "SELL / AVOID"
        final_reco_color = "#ef4444"

    # 2-4 sentence bullet points for each section:
    # Price Movement (Diễn biến giá)
    price_trend = "tăng" if hist_change_pct > 0 else "giảm"
    price_ma = "nằm trên" if curr > metrics["ma20"] else "nằm dưới"
    price_ma_status = "tích cực trong ngắn hạn" if curr > metrics["ma20"] else "tiêu cực trong ngắn hạn"
    
    # Technical Signals (Tín hiệu kỹ thuật)
    tech_ma_cross = "Crossover tăng giá (Bullish)" if metrics["ma20"] > metrics["ma50"] else "Crossover giảm giá (Bearish)"
    tech_macd = "nằm trên (Bullish momentum)" if metrics["macd"] > metrics["macd_signal"] else "nằm dưới (Bearish momentum)"
    
    # Model Forecast (Dự báo mô hình)
    model_confidence = "Độ tin cậy của mô hình ở mức cao dựa trên chỉ số R² tốt." if best_r2 > 0.5 else "Mô hình có sai số trung bình, khuyến nghị sử dụng để tham khảo và kết hợp quản trị vốn."
    
    # Risk (Rủi ro)
    vol_risk_desc = "biến động cao" if vol > 3.0 else ("biến động trung bình" if vol > 1.5 else "biến động thấp")
    tech_risk_desc = "áp lực điều chỉnh kỹ thuật lớn do đi sâu vào vùng quá mua" if rsi > 70 else ("cơ hội phục hồi kỹ thuật do ở vùng quá bán" if rsi < 30 else "trạng thái kỹ thuật ổn định, chưa có dấu hiệu cực đoan")

    report = f"""
<div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #cbd5e1;">
  <h3 style="color: #ffffff; margin-top: 0; margin-bottom: 12px; font-weight: 800; font-size: 18px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">
    Phân tích nhanh {ticker}
  </h3>
  
  <p style="margin: 4px 0 12px 0; font-size: 12px; color: #94a3b8;">
    Thời điểm tạo báo cáo: <strong>{datetime.now().strftime('%H:%M:%S — %d/%m/%Y')}</strong><br />
    Dữ liệu thị trường gần nhất: <strong>{last_date}</strong>
  </p>
  
  <!-- Box tóm tắt đầu -->
  <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(148, 163, 184, 0.15); border-radius: 8px; padding: 14px; margin-bottom: 20px; display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; font-size: 13px;">
    <div>
      <span style="color: #94a3b8; display: block; margin-bottom: 2px;">Giá hiện tại:</span>
      <strong style="font-size: 16px; color: #ffffff;">{curr:,.2f} {currency}</strong>
    </div>
    <div>
      <span style="color: #94a3b8; display: block; margin-bottom: 2px;">Giá phiên trước:</span>
      <strong style="font-size: 16px; color: #ffffff;">{prev_close:,.2f} {currency}</strong>
    </div>
    <div>
      <span style="color: #94a3b8; display: block; margin-bottom: 2px;">% thay đổi:</span>
      <strong style="font-size: 16px; color: {final_reco_color};">{hist_change_pct:+.2f}%</strong>
    </div>
    <div>
      <span style="color: #94a3b8; display: block; margin-bottom: 2px;">Khuyến nghị:</span>
      <strong style="font-size: 16px; color: {reco_color};">{reco_name}</strong>
    </div>
  </div>
  
  <!-- Các mục riêng -->
  <div style="margin-bottom: 16px;">
    <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px;">Diễn biến giá</h4>
    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
      <li style="margin-bottom: 4px;">Giá đóng cửa phiên gần nhất đạt <strong>{curr:,.2f} {currency}</strong>, thể hiện xu hướng <strong>{price_trend}</strong> ở mức <strong>{hist_change_pct:+.2f}%</strong> so với phiên trước.</li>
      <li style="margin-bottom: 4px;">Giá hiện tại đang <strong>{price_ma}</strong> đường trung bình động MA20 ngắn hạn (<strong>{metrics['ma20']:,.2f} {currency}</strong>), cho thấy tín hiệu xu hướng <strong>{price_ma_status}</strong>.</li>
    </ul>
  </div>
  
  <div style="margin-bottom: 16px;">
    <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px;">Tín hiệu kỹ thuật</h4>
    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
      <li style="margin-bottom: 4px;">Chỉ số RSI (14) đang ở mức <strong>{rsi:.2f}</strong>, cho thấy trạng thái <strong>{rsi_nhan_dinh}</strong>.</li>
      <li style="margin-bottom: 4px;">Động lượng MACD (<strong>{metrics['macd']:.4f}</strong>) đang <strong>{tech_macd}</strong> so với Signal Line (<strong>{metrics['macd_signal']:.4f}</strong>).</li>
      <li style="margin-bottom: 4px;">Hệ thống xác định trạng thái trung bình động là <strong>{tech_ma_cross}</strong> với đường MA20 ở mức <strong>{metrics['ma20']:,.2f}</strong> và đường MA50 ở mức <strong>{metrics['ma50']:,.2f}</strong>.</li>
    </ul>
  </div>
  
  <div style="margin-bottom: 16px;">
    <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px;">Dự báo mô hình</h4>
    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
      <li style="margin-bottom: 4px;">Mô hình học máy tốt nhất <strong>{best_model_name}</strong> dự báo giá đóng cửa phiên tiếp theo sẽ đạt <strong>{pred:,.2f} {currency}</strong>, tương ứng tỷ lệ thay đổi dự kiến <strong>{change:+.2f}%</strong>.</li>
      <li style="margin-bottom: 4px;">{model_confidence} Sai số đánh giá RMSE tối ưu đạt <strong>{best_rmse:.2f}</strong> trên tập dữ liệu kiểm nghiệm.</li>
    </ul>
  </div>
  
  <div style="margin-bottom: 16px;">
    <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px;">Rủi ro</h4>
    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
      <li style="margin-bottom: 4px;">Rủi ro biến động giá được đánh giá ở mức <strong>{vol_risk}</strong> với biên độ dao động lịch sử 20 phiên là <strong>{vol:.2f}%</strong>.</li>
      <li style="margin-bottom: 4px;">Rủi ro điều chỉnh kỹ thuật được xác định ở mức <strong>{tech_risk}</strong> do <strong>{tech_risk_desc}</strong>.</li>
    </ul>
  </div>
  
  <div style="margin-bottom: 20px;">
    <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 0 0 6px 0; text-transform: uppercase; letter-spacing: 0.5px;">Kết luận hệ thống</h4>
    <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
      <li style="margin-bottom: 4px;">Hệ thống tổng hợp các tín hiệu kỹ thuật và đưa ra nhận định: <strong>{reco_explanation}</strong></li>
    </ul>
  </div>
  
  <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 16px 0;" />
  
  <!-- Banner khuyến nghị cuối cùng cực kỳ rõ ràng -->
  <div style="background: rgba(15, 23, 42, 0.8); border: 2px solid {final_reco_color}; border-radius: 8px; padding: 16px; text-align: center; margin-top: 12px;">
    <span style="color: #94a3b8; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; display: block; margin-bottom: 4px;">KHUYẾN NGHỊ CUỐI CÙNG</span>
    <strong style="color: {final_reco_color}; font-size: 24px; font-weight: 900; letter-spacing: 0.5px;">{final_reco}</strong>
  </div>
  
  <!-- Nút print / save PDF -->
  <div style="margin-top: 20px; text-align: center;" class="no-print">
    <button onclick="window.print();" style="background: rgba(99, 102, 241, 0.2); border: 1px solid rgba(99, 102, 241, 0.4); border-radius: 6px; color: #a5b4fc; font-size: 13px; font-weight: 600; padding: 8px 16px; cursor: pointer; transition: all 0.2s;">
      In / Tải báo cáo PDF
    </button>
  </div>
  
</div>
"""
    return report

def stream_ollama_response(prompt: str, model: str):
    """Gọi API sinh văn bản cục bộ của Ollama dưới dạng stream để hiển thị chữ mượt mà."""
    try:
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "system": "Bạn là Stock AI Analyst - một trợ lý phân tích tài chính và chứng khoán thông minh, được tích hợp vào Hệ Thống Dự Báo Stock AI. Bạn phân tích dữ liệu vô cùng chính xác và chuyên nghiệp bằng tiếng Việt. Tuyệt đối trung thực với dữ liệu số được cung cấp, không tự bịa thông số. Câu trả lời của bạn cần cô đọng, đi thẳng vào vấn đề và chia bố cục rõ ràng.",
            "stream": True
        }
        
        response = requests.post(url, json=payload, stream=True, timeout=30)
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    chunk = line.decode('utf-8')
                    try:
                        chunk_json = json.loads(chunk) if 'json' in globals() else eval(chunk.replace("false", "False").replace("true", "True"))
                        # Xử lý an toàn trong trường hợp json chưa import
                        import json
                        chunk_json = json.loads(chunk)
                        yield chunk_json.get("response", "")
                    except Exception:
                        # Fallback parsing
                        match = re.search(r'"response"\s*:\s*"([^"]+)"', chunk)
                        if match:
                            yield match.group(1).encode().decode('unicode-escape')
        else:
            yield f"❌ Lỗi kết nối Ollama API: Mã lỗi {response.status_code}."
    except requests.exceptions.Timeout:
        yield "❌ Lỗi: Kết nối tới mô hình AI cục bộ bị quá thời gian chờ (Timeout). Vui lòng thử lại."
    except Exception as err:
        yield f"❌ Không thể giao tiếp với AI cục bộ: {str(err)}"

def render_chat_assistant(analysis_mode: str, selected_model: str):
    """Render toàn bộ khu vực làm việc của Trợ lý AI Chatbot."""
    
    # Khởi tạo lịch sử chat trong Session State nếu chưa có
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = [
            {"role": "assistant", "content": "Xin chào! Tôi là Trợ lý Stock AI hoạt động hoàn toàn cục bộ trên máy tính của bạn. Hôm nay tôi có thể giúp gì cho bạn? Bạn muốn phân tích nhanh hay trò chuyện chuyên sâu về mã cổ phiếu nào?"}
        ]
        
    # Hiển thị lịch sử trò chuyện
    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)
            
    # Nhận tin nhắn từ người dùng
    user_input = st.chat_input("Nhập câu hỏi của bạn tại đây...")
        
    if user_input:
        # Hiển thị tin nhắn của User
        st.session_state["chat_messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        # Xử lý phản hồi từ AI
        with st.chat_message("assistant"):
            # Phát hiện xem người dùng có nhắc đến mã cổ phiếu nào không
            ticker = detect_ticker(user_input)
            
            # --- CHẾ ĐỘ PHÂN TÍCH NHANH ---
            if analysis_mode == "Nhanh":
                with st.spinner("Đang truy xuất chỉ báo và tự động lập báo cáo phân tích..."):
                    if ticker:
                        metrics = query_ticker_metrics(ticker)
                        if metrics:
                            report_markdown = render_fast_analysis_report(metrics)
                            response_content = report_markdown
                        else:
                            response_content = f"""
<div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #cbd5e1;">
  <div style="background: rgba(239, 68, 68, 0.08); border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; color: #fca5a5;">
    Không tìm thấy dữ liệu thị trường cho mã <strong>{ticker}</strong>. Vui lòng kiểm tra lại kết nối internet hoặc đảm bảo mã này tồn tại trên Yahoo Finance.
  </div>
  
  <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 16px 0 8px 0;">Danh sách mã gợi ý hợp lệ:</h4>
  <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
    <li style="margin-bottom: 6px;"><strong>Cổ phiếu Mỹ:</strong> <code>AAPL</code> (Apple), <code>TSLA</code> (Tesla), <code>MSFT</code> (Microsoft), <code>NVDA</code> (Nvidia), <code>META</code> (Meta)</li>
    <li style="margin-bottom: 6px;"><strong>Cổ phiếu Việt Nam:</strong> <code>FPT.VN</code> (FPT), <code>HPG.VN</code> (Hòa Phát), <code>VNM.VN</code> (Vinamilk), <code>VIC.VN</code> (Vingroup)</li>
    <li style="margin-bottom: 6px;"><strong>Tiền ảo (Crypto):</strong> <code>BTC-USD</code> (Bitcoin), <code>ETH-USD</code> (Ethereum), <code>BNB-USD</code> (Binance Coin), <code>SOL-USD</code> (Solana)</li>
  </ul>
  
</div>
"""
                    else:
                        response_content = f"""
<div style="font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #cbd5e1;">
  <div style="background: rgba(99, 102, 241, 0.08); border-left: 4px solid #6366f1; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
    Bạn đang chọn chế độ <strong>Phân tích nhanh</strong>. Hãy nhập câu hỏi kèm theo tên mã cổ phiếu cụ thể (ví dụ: <em>'HPG.VN'</em>, <em>'FPT.VN'</em>, <em>'AAPL'</em>, <em>'BTC'</em>) để tôi tạo báo cáo chỉ báo kỹ thuật tức thì cho bạn.
  </div>
  
  <h4 style="color: #ffffff; font-size: 14px; font-weight: 700; margin: 16px 0 8px 0;">Danh sách mã gợi ý hợp lệ:</h4>
  <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #cbd5e1;">
    <li style="margin-bottom: 6px;"><strong>Cổ phiếu Mỹ:</strong> <code>AAPL</code>, <code>TSLA</code>, <code>MSFT</code>, <code>NVDA</code>, <code>META</code></li>
    <li style="margin-bottom: 6px;"><strong>Cổ phiếu Việt Nam:</strong> <code>FPT.VN</code>, <code>HPG.VN</code>, <code>VNM.VN</code>, <code>VIC.VN</code></li>
    <li style="margin-bottom: 6px;"><strong>Tiền ảo (Crypto):</strong> <code>BTC-USD</code> (hoặc <code>BTC</code>), <code>ETH-USD</code> (hoặc <code>ETH</code>), <code>BNB-USD</code>, <code>SOL-USD</code></li>
  </ul>
</div>
"""
                
                # Hiển thị kết quả ngay lập tức
                st.markdown(response_content, unsafe_allow_html=True)
                st.session_state["chat_messages"].append({"role": "assistant", "content": response_content})
                
            # --- CHẾ ĐỘ PHÂN TÍCH THÔNG MINH ---
            else:
                # 1. Kiểm tra xem Ollama có hoạt động không
                is_alive = check_ollama_alive()
                if not is_alive:
                    warning_msg = """
                    <div style='background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3);
                                border-radius: 8px; padding: 14px 18px; color: #fca5a5; font-size: 14px;'>
                        <b>Chế độ phân tích thông minh chưa sẵn sàng.</b><br>
                        Vui lòng bật trợ lý AI cục bộ trong phần cài đặt nâng cao ở Sidebar bên trái.
                    </div>
                    """
                    st.markdown(warning_msg, unsafe_allow_html=True)
                    st.session_state["chat_messages"].append({"role": "assistant", "content": warning_msg})
                else:
                    # 2. Có mã cổ phiếu -> Chạy RAG cục bộ
                    if ticker:
                        with st.spinner(f"Đang đọc dữ liệu kỹ thuật của {ticker} để chuẩn bị tài liệu tham khảo cho AI cục bộ..."):
                            metrics = query_ticker_metrics(ticker)
                            
                        if metrics:
                            # Nạp dữ liệu thật vào prompt ẩn để AI diễn giải
                            currency = "VND" if ticker.endswith(".VN") else "$"
                            prompt_context = f"""
[DỮ LIỆU CHỈ BÁO KỸ THUẬT THỰC TẾ]:
- Mã cổ phiếu: {metrics['ticker']}
- Giá đóng cửa phiên gần nhất: {metrics['current_price']:,.2f} {currency}
- Chỉ số Sức mạnh RSI (14): {metrics['rsi']:.2f}
- Biên độ biến động (Volatility 20 phiên): {metrics['volatility']:.2f}%
- Đánh giá Rủi ro hệ thống: {metrics['risk']}
- Khuyến nghị AI tổng hợp của hệ thống: {metrics['recommendation']}
- Lập luận khuyến nghị: {metrics['reco_explanation']}
- Dự báo của mô hình học máy: Giá ngày mai sẽ ở mức {metrics['predicted_next_price']:,.2f} {currency} (Thay đổi: {metrics['predicted_change_pct']:+.2f}%)

[YÊU CẦU CỦA NGƯỜI DÙNG]:
{user_input}

Hãy sử dụng chính xác dữ liệu kỹ thuật thực tế ở trên để phân tích chuyên nghiệp, giải thích ý nghĩa các chỉ số này một cách dễ hiểu và đưa ra lời khuyên thiết thực theo câu hỏi của người dùng. Không bịa số liệu khác. Trả lời bằng tiếng Việt, mạch lạc và chia bố cục rõ ràng.
"""
                        else:
                            prompt_context = f"Người dùng muốn hỏi về mã cổ phiếu {ticker} nhưng hệ thống không thể tải được dữ liệu chỉ báo kỹ thuật từ yfinance (có thể do sai tên mã hoặc mất internet). Hãy trả lời người dùng một cách lịch sự, hướng dẫn họ kiểm tra lại tên mã (ví dụ mã VN cần thêm đuôi .VN như FPT.VN) và giải thích các nguyên lý chung nếu họ hỏi lý thuyết. Câu hỏi của người dùng: {user_input}"
                    else:
                        # Câu hỏi lý thuyết chung
                        prompt_context = f"Người dùng hỏi câu hỏi lý thuyết hoặc trò chuyện thông thường: {user_input}. Hãy trả lời thông minh, chuyên nghiệp dưới góc độ tài chính bằng tiếng Việt."
                        
                    # 3. Stream phản hồi từ Ollama
                    with st.spinner("AI cục bộ đang suy luận và soạn câu trả lời chuyên sâu..."):
                        response_placeholder = st.empty()
                        complete_response = ""
                        
                        try:
                            # Khởi chạy bộ stream
                            for text_chunk in stream_ollama_response(prompt_context, selected_model):
                                complete_response += text_chunk
                                response_placeholder.markdown(complete_response + " ▌")
                            
                            # Hiển thị bản cuối không có con trỏ nhấp nháy
                            response_placeholder.markdown(complete_response)
                            st.session_state["chat_messages"].append({"role": "assistant", "content": complete_response})
                        except Exception as e:
                            err_msg = f"❌ Đã xảy ra sự cố trong quá trình giao tiếp với AI cục bộ: {str(e)}"
                            response_placeholder.markdown(err_msg)
                            st.session_state["chat_messages"].append({"role": "assistant", "content": err_msg})
                            
        # Buộc Streamlit cập nhật lại UI
        st.rerun()
        
    st.markdown("<div style='margin-top: 40px;'></div>", unsafe_allow_html=True)
