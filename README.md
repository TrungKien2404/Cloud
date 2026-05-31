# 📈 Stock AI — Hệ Thống Dự Báo Giá Cổ Phiếu

Hệ thống Machine Learning End-to-End, dự báo giá cổ phiếu toàn cầu dựa trên lịch sử giao dịch và các chỉ báo kỹ thuật. Hỗ trợ thị trường Mỹ 🇺🇸, Việt Nam 🇻🇳, Crypto và hơn 50.000 mã trên Yahoo Finance.

---

## 1. KIẾN TRÚC HỆ THỐNG

```text
┌──────────────────────────────────────────────────────────────┐
│ Streamlit Dashboard  (dashboard/dashboard.py)                │
│  ├─ Tab "Phân Tích Từ Hệ Thống"  ← gọi FastAPI Backend      │
│  └─ Tab "AI Dự Báo — Nhập Mã Bất Kỳ"  ← yfinance trực tiếp │
├──────────────────────────────────────────────────────────────┤
│ FastAPI Backend  (api/api_service.py)                        │
│  └─ /api/data, /api/predict, /api/train, /api/market-summary │
├──────────────────────────────────────────────────────────────┤
│ ML Models  (model/)  + ETL Pipeline  (etl/)                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. CÀI ĐẶT THƯ VIỆN

```bash
pip install -r requirements.txt
```

Các thư viện chính:
- `streamlit` — giao diện web
- `yfinance` — lấy dữ liệu Yahoo Finance
- `scikit-learn` — các mô hình ML
- `plotly` — biểu đồ tương tác
- `pandas`, `numpy` — xử lý dữ liệu
- `fastapi`, `uvicorn` — backend API

---

## 3. CÁCH CHẠY APP

### Chạy nhanh (chỉ cần Streamlit — không cần backend):

```bash
streamlit run dashboard/dashboard.py
```

Tab **"🤖 AI Dự Báo — Nhập Mã Bất Kỳ"** hoạt động hoàn toàn độc lập, không cần backend.

### Chạy đầy đủ (có backend API):

```bash
# Terminal 1 — ETL + Train
python run_etl.py
python run_training.py

# Terminal 2 — FastAPI Backend
uvicorn api.api_service:app --reload

# Terminal 3 — Streamlit Dashboard
streamlit run dashboard/dashboard.py
```

---

## 4. CÁCH DÙNG PHẦN "AI DỰ BÁO — NHẬP MÃ BẤT KỲ"

1. Vào menu bên trái → chọn **"📈 Phân Tích & AI Dự Báo"**
2. Chọn tab **"🤖 AI Dự Báo — Nhập Mã Bất Kỳ"**
3. Nhập mã cổ phiếu vào ô nhập liệu, ví dụ:
   - `AAPL` — Apple (Mỹ)
   - `TSLA` — Tesla (Mỹ)
   - `NVDA` — NVIDIA (Mỹ)
   - `BTC-USD` — Bitcoin
   - `ETH-USD` — Ethereum
   - `FPT.VN` — FPT (Việt Nam)
   - `VNM.VN` — Vinamilk (Việt Nam)
4. Chọn **Khoảng thời gian**: 6mo / 1y / 2y / 5y
5. Chọn **Chu kỳ**: 1d / 1wk / 1mo
6. Nhấn **"🔍 Phân Tích & Dự Báo"**

Kết quả bao gồm:
- Biểu đồ nến (Candlestick) + MA20 + MA50 + Volume
- RSI (14) và MACD
- Bảng so sánh 3 mô hình ML
- Biểu đồ Actual vs Predicted
- Dự đoán giá phiên tiếp theo
- Khuyến nghị AI: MUA MẠNH / MUA / THEO DÕI / BÁN / BÁN MẠNH

---

## 5. CÁC MÔ HÌNH VÀ CHỈ SỐ

### Mô hình ML

| Mô hình | Mô tả |
|---|---|
| **Linear Regression** | Hồi quy tuyến tính — đơn giản, diễn giải dễ |
| **Random Forest** | Tập hợp nhiều cây quyết định — mạnh với dữ liệu phi tuyến |
| **Gradient Boosting** | Tăng cường gradient — thường cho kết quả tốt nhất |

Mô hình tốt nhất được chọn theo **RMSE thấp nhất**.

### Chỉ số đánh giá

| Chỉ số | Ý nghĩa | Tốt khi |
|---|---|---|
| **MAE** (Mean Absolute Error) | Sai số tuyệt đối trung bình | Càng thấp càng tốt |
| **RMSE** (Root Mean Square Error) | Căn bậc hai sai số bình phương trung bình — phạt nặng outlier | Càng thấp càng tốt |
| **R²** (R-squared) | Tỷ lệ phương sai được giải thích | Càng gần 1.0 càng tốt |
| **MAPE** (Mean Absolute Percentage Error) | Sai số % trung bình | Càng thấp càng tốt |

### Chỉ báo kỹ thuật

| Chỉ báo | Mô tả |
|---|---|
| **MA20 / MA50** | Trung bình động 20 / 50 phiên |
| **RSI (14)** | Chỉ số sức mạnh tương đối — >70: quá mua, <30: quá bán |
| **MACD** | Hội tụ / phân kỳ đường trung bình động |
| **Volatility** | Độ dao động giá rolling 20 phiên |

---

## 6. CẤU TRÚC THƯ MỤC

```
Cloud/
├── dashboard/
│   ├── dashboard.py       # Giao diện chính Streamlit
│   └── ai_analysis.py     # Module AI Dự Báo độc lập (yfinance)
├── api/                   # FastAPI Backend
├── model/                 # Huấn luyện ML
├── etl/                   # ETL Pipeline
├── data/                  # Dữ liệu local
├── notebooks/             # Databricks notebooks
└── requirements.txt
```

---

## 7. ⚠️ CẢNH BÁO QUAN TRỌNG

> **Kết quả phân tích và dự báo chỉ phục vụ mục đích học tập / nghiên cứu, KHÔNG phải lời khuyên đầu tư.**
>
> Thị trường tài chính có rủi ro rất cao. Mọi quyết định đầu tư cần được tham khảo từ chuyên gia tài chính có chuyên môn. Nhóm phát triển không chịu trách nhiệm về bất kỳ tổn thất tài chính nào.
