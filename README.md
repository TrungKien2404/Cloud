# 📈 Stock AI — Unified E2E Stock Prediction & AI Chatbot System

<div align="center">
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white" alt="TypeScript" />
  <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Ollama-black?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" />
  <img src="https://img.shields.io/badge/scikit_learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white" alt="Scikit-Learn" />
  <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" />
</div>

---

**Stock AI** là một hệ thống **End-to-End Machine Learning & Offline AI Chatbot** đỉnh cao, hỗ trợ phân tích kỹ thuật, dự báo giá cổ phiếu và tư vấn đầu tư tự động. Hệ thống kết hợp sức mạnh của các mô hình học máy truyền thống (**Scikit-Learn, XGBoost, LightGBM**) và Trí tuệ Nhân tạo thế hệ mới chạy **Offline hoàn toàn (Ollama & Qwen)** để cung cấp những phân tích tài chính chuyên sâu cấp độ tổ chức.

Hệ thống hỗ trợ toàn bộ các thị trường tài chính toàn cầu bao gồm Cổ phiếu Mỹ (US), Cổ phiếu Việt Nam (VN), Hàng hóa (Gold, Oil, Agriculture), Ngoại hối (Forex) và Tiền điện tử (Crypto) với hơn 100.000+ mã giao dịch từ Yahoo Finance.

---

## 🌟 TÍNH NĂNG NỔI BẬT

### 1. 📊 Dashboard Thị Trường & So Sánh (React + Vite)
- **Watchlist cá nhân hóa**: Lưu trữ danh sách theo dõi động, bảo toàn dữ liệu lịch sử và tự động sắp xếp các mã vừa thêm lên **đầu bảng** (`data/watchlist_order.json`).
- **AI Trading Signals**: Đưa ra tín hiệu giao dịch thông minh tức thì (`MUA MẠNH`, `MUA/GIỮ`, `GIỮ/BÁN`, `BÁN MẠNH`) được sinh ra từ các mô hình Machine Learning riêng biệt đã tối ưu hóa cho từng mã.
- **Top Gainers & Losers**: Tự động lọc và hiển thị danh sách biến động mạnh nhất thị trường trong ngày.
- **Ma trận Tương quan Tỷ suất Sinh lời (Correlation Heatmap)**: Tính toán sự tương quan biến động giữa các cổ phiếu trong 120 phiên gần nhất giúp tối ưu hóa danh mục đầu tư và phân tán rủi ro.
- **So sánh Tăng trưởng Chuẩn hóa (Normalized Return)**: Chuẩn hóa giá đóng cửa về mốc gốc 100 để so sánh trực quan tốc độ tăng trưởng giữa các tài sản khác nhau trên biểu đồ Plotly tương tác.

### 2. 🤖 Trợ Lý AI Chatbot Offline (RAG - Retrieval-Augmented Generation)
- **Local LLM Integration**: Kết nối trực tiếp với **Ollama** sử dụng mô hình tối ưu siêu nhẹ **Qwen 2.5 (1.5B)** chạy 100% Offline trên máy tính cá nhân, bảo mật dữ liệu tuyệt đối và không phát sinh chi phí API.
- **2 Chế độ Phân tích Chuyên nghiệp**:
  - ⚡ **Phân tích nhanh (Quick)**: Sử dụng hệ thống quy tắc kỹ thuật nghiêm ngặt phân tích trực tiếp dữ liệu RSI, MACD, Bollinger Bands để sinh báo cáo Markdown trực quan chỉ trong 1 giây.
  - 🧠 **Phân tích thông minh (Smart AI)**: Áp dụng cơ chế **RAG**, tự động truy xuất dữ liệu giá lịch sử, các chỉ số kỹ thuật hiện tại và dự đoán tương lai từ hệ thống dữ liệu Parquet để làm ngữ cảnh (Context), cung cấp cho mô hình Qwen phân tích chuyên sâu và đưa ra lời khuyên đầu tư chi tiết.

### 3. 📈 Biểu Đồ Kỹ Thuật Live Candlestick & Indicators
- Biểu đồ nến Nhật tương tác trực quan thời gian thực (Live Candlestick Charts).
- Tích hợp các đường trung bình động phổ biến (**MA20**, **MA50**).
- Biểu đồ phụ hiển thị chỉ số sức mạnh tương đối **RSI (14)**, hội tụ phân kỳ trung bình động **MACD**, khối lượng giao dịch (**Volume**) và độ biến động lịch sử (**Volatility**).

### 4. ⚙️ Pipeline Machine Learning Tự Động & Đa Mô Hình
Mỗi khi bạn thêm một mã cổ phiếu mới, hệ thống sẽ tự động chạy pipeline huấn luyện khép kín:
1. **Data Ingestion**: Tải 5 năm dữ liệu lịch sử chất lượng cao từ Yahoo Finance lưu trữ dưới dạng Parquet hiệu năng cao.
2. **ETL Pipeline**: Làm sạch dữ liệu, xử lý nhiễu (outliers) bằng Z-score, và trích xuất các kỹ trưng quan trọng (MA, Lags, RSI, Returns, Volatility, Target Variable).
3. **Model Training & Selection**: Huấn luyện đồng thời **5 mô hình học máy** khác nhau:
   - *Linear Regression*
   - *Random Forest Regressor*
   - *Gradient Boosting Regressor*
   - *XGBoost Regressor*
   - *LightGBM Regressor*
4. **Validation & Registry**: Đánh giá hiệu năng dựa trên các chỉ số **RMSE, MAE, R²**, tự động lưu lại mô hình đạt **RMSE thấp nhất** để làm mô hình dự báo chính thức.

### 5. ⚡ Unified System Runner (`run_all.py`)
Trình khởi chạy 1-Click thông minh:
- Tự động kiểm tra cài đặt của Ollama, nếu chưa có sẽ tự động tải và cài đặt ở chế độ im lặng (Silent Setup).
- Tự động kiểm tra và tải mô hình `qwen2.5:1.5b` từ thư viện Ollama nếu hệ thống của bạn chưa có.
- Tự động kiểm tra tính hợp lệ của tệp dữ liệu Parquet cục bộ và các mô hình đã lưu.
- Khởi chạy song song FastAPI Backend và React Frontend với luồng log đồng bộ trực quan trên 1 terminal duy nhất.

---

## 🛠️ CÔNG NGHỆ SỬ DỤNG

### Frontend Stack:
- **React 18** & **TypeScript**
- **Vite** (Công cụ đóng gói và khởi chạy siêu tốc)
- **Lucide React** (Bộ icon hiện đại và sang trọng)
- **Plotly.js** (Biểu đồ tương tác cao cấp dành cho khoa học dữ liệu)
- **Vanilla CSS / Custom Glassmorphism Theme** (Giao diện tối huyền bí, sang trọng)

### Backend Stack:
- **FastAPI** (Web framework hiệu năng cao bằng Python)
- **Uvicorn** (ASGI web server)
- **Ollama API** (Kết nối và điều khiển mô hình ngôn ngữ lớn Offline)
- **Pandas** & **Numpy** & **PyArrow / FastParquet** (Xử lý tệp dữ liệu Parquet)
- **Joblib** (Serialize và lưu trữ mô hình học máy đã huấn luyện)

### ML Stack:
- **Scikit-Learn**
- **XGBoost** (eXtreme Gradient Boosting)
- **LightGBM** (Light Gradient Boosting Machine)
- **YFinance** (Thư viện lấy dữ liệu tài chính Yahoo Finance)

---

## 📐 KIẾN TRÚC HỆ THỐNG

```text
┌────────────────────────────────────────────────────────────────────────┐
│                    REACT FRONTEND (Vite on Port 5173)                   │
│          Giao diện tối Glassmorphic, Plotly Charts, AI Chatbox         │
└──────────────────┬──────────────────────────────────▲──────────────────┘
                   │ HTTP Request                      │ JSON Response
                   ▼                                   │
┌──────────────────────────────────────────────────────┴─────────────────┐
│                    FASTAPI BACKEND (Uvicorn on Port 8000)               │
│                                                                        │
│  ┌──────────────────┐    ┌────────────────────┐    ┌─────────────────┐ │
│  │   Auth Service   │    │  yfinance Engine   │    │ Ollama LLM RAG  │ │
│  └──────────────────┘    └─────────┬──────────┘    └────────▲────────┘ │
└────────────────────────────────────│────────────────────────│──────────┘
                                     │ Downloads              │ Offline Inference
                                     ▼                        ▼
                       ┌─────────────┴──────────┐    ┌────────┴────────┐
                       │  Parquet Data Lake     │    │   Ollama Engine │
                       │  ├─ raw_data.parquet   │◄───┤  qwen2.5:1.5b   │
                       │  └─ processed.parquet  │    └─────────────────┘
                       └─────────────┬──────────┘
                                     │ Read/Write
                                     ▼
                       ┌─────────────┴──────────┐
                       │  ML Pipelines (Scikit) │
                       │  ├─ Ingestion & ETL    │
                       │  └─ Auto-Train Models  │
                       └────────────────────────┘
```

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT & CHẠY

### Yêu cầu hệ thống:
- **Python 3.10** trở lên (Khuyến nghị Python 3.13)
- **Node.js** v18 trở lên & **npm**
- Hệ điều hành Windows, macOS hoặc Linux

### Bước 1: Clone dự án về máy tính của bạn
```bash
git clone https://github.com/TrungKien2404/Cloud.git
cd Cloud
```

### Bước 2: Cài đặt các thư viện Python
Khởi tạo và kích hoạt môi trường ảo (Khuyến nghị):
```bash
python -m venv .venv
# Trên Windows:
.venv\Scripts\activate
# Trên macOS/Linux:
source .venv/bin/activate
```

Cài đặt các gói phụ thuộc:
```bash
pip install -r requirements.txt
```

### Bước 3: Cài đặt các gói phụ thuộc của Frontend
```bash
cd frontend-react
npm install
cd ..
```

### Bước 4: Khởi chạy toàn bộ hệ thống bằng 1 câu lệnh duy nhất
Tại thư mục gốc của dự án, bạn chỉ cần chạy lệnh sau:
```bash
python run_all.py
```

**Hệ thống thông minh sẽ tự động:**
1. Kiểm tra môi trường cục bộ và tự cài đặt **Ollama** ngầm nếu thiếu.
2. Kích hoạt Ollama phục vụ và tải mô hình `qwen2.5:1.5b`.
3. Kiểm tra các tệp dữ liệu Parquet và mô hình đã được huấn luyện sẵn trong thư mục `models/`.
4. Chạy đồng thời **FastAPI Backend (Port 8000)** và **React Frontend (Port 5173)**.

*Sau khi log hiển thị thành công, bạn chỉ cần mở trình duyệt và truy cập **[http://localhost:5173](http://localhost:5173)** để bắt đầu trải nghiệm!*

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN

```text
Cloud/
├── api/
│   ├── __init__.py
│   └── api_service.py       # FastAPI Backend, endpoints & RAG chatbot
├── configs/
│   ├── config.py            # Python Config Loader
│   └── config.yaml          # Tệp cấu hình các mã, chu kỳ, tham số ML
├── data/
│   ├── processed/           # Tệp Parquet đã qua xử lý và trích xuất chỉ báo
│   ├── raw/                 # Tệp Parquet thô lấy từ yfinance
│   └── watchlist_order.json # Tệp cấu trúc lưu trữ thứ tự của Watchlist
├── etl/
│   ├── __init__.py
│   └── etl_pipeline.py      # Module xử lý dữ liệu và tạo đặc trưng kỹ thuật
├── frontend-react/
│   ├── src/
│   │   ├── components/      # MetricCard, Sidebar, PlotlyWrapper
│   │   ├── pages/
│   │   │   ├── Overview.tsx      # Tổng quan thị trường Hàng hóa, Forex, Crypto
│   │   │   ├── MarketCompare.tsx # Watchlist, Biểu đồ so sánh, Tín hiệu AI
│   │   │   ├── AiAnalysis.tsx    # Biểu đồ nến Nhật kỹ thuật chuyên sâu
│   │   │   ├── ChatAssistant.tsx # Trợ lý AI Chatbot Offline RAG
│   │   │   └── LoginRegister.tsx # Đăng ký, Đăng nhập bảo mật
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── ingestion/
│   ├── __init__.py
│   └── data_ingestion.py    # Tải và cập nhật dữ liệu thông minh từ yfinance
├── model/
│   ├── __init__.py
│   └── model_training.py    # Pipeline huấn luyện 5 mô hình ML và chọn RMSE tốt nhất
├── models/                  # Nơi lưu trữ các mô hình .pkl đã tối ưu
├── run_all.py               # Runner hợp nhất 1-click khởi chạy toàn bộ hệ thống
├── run_etl.py               # Chạy thủ công ETL Pipeline
├── run_ingestion.py         # Chạy thủ công Data Ingestion
├── run_training.py          # Chạy thủ công Pipeline huấn luyện
└── requirements.txt         # Các thư viện Python yêu cầu
```

---

## 📊 KẾT QUẢ NGHIỆM THU MÔ HÌNH HỌC MÁY (VÍ DỤ VỚI VFS)

Khi chạy huấn luyện mô hình cho mã `VFS`, hệ thống tự động kiểm tra chéo 5 thuật toán và đưa ra thống kê sai số để chọn ra mô hình tối ưu nhất:

```text
================================================================================
MODEL COMPARISON RESULTS
================================================================================
Model Name           |         RMSE |          MAE |     R² Score
--------------------------------------------------------------------------------
Linear Regression    |     0.034956 |     0.026417 |    -0.019053
Random Forest        |     0.040914 |     0.031730 |    -0.684124
Gradient Boosting    |     0.058642 |     0.047432 |    -2.459835
XGBoost              |     0.109999 |     0.071073 |   -11.173475
LightGBM             |     0.067724 |     0.056330 |    -3.614372
================================================================================
-> Best Model Selected: Linear Regression (lowest RMSE: 0.034956)
================================================================================
```

---

## ⚠️ TUYÊN BỐ MIỄN TRỪ TRÁCH NHIỆM

> **Thông tin và dự báo được cung cấp bởi hệ thống Stock AI chỉ mang tính chất tham khảo, phục vụ cho mục đích học tập và nghiên cứu khoa học dữ liệu. Đây KHÔNG phải là lời khuyên đầu tư tài chính.**
> 
> Thị trường tài chính và cổ phiếu luôn tiềm ẩn rủi ro rất cao và không thể đoán trước chính xác 100%. Nhóm phát triển không chịu bất kỳ trách nhiệm nào đối với mọi tổn thất tài chính trực tiếp hoặc gián tiếp phát sinh từ việc sử dụng hệ thống này để giao dịch thực tế. Hãy luôn tham khảo ý kiến của các chuyên gia tư vấn tài chính được cấp phép trước khi thực hiện các quyết định đầu tư.
