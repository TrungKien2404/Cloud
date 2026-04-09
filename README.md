# 📈 Hệ Thống Dự Đoán Giá Cổ Phiếu AI (Stock Prediction System)

Dự án này là một hệ thống Machine Learning End-to-End hoàn chỉnh, dự báo biến động giá cổ phiếu trên thị trường dựa trên lịch sử giao dịch và các chỉ báo phân tích kỹ thuật chuyên sâu.

---

## 1. SƠ ĐỒ KIẾN TRÚC HỆ THỐNG TỔNG QUAN

```text
╔════════════════════════════════════════════════════════════════════════════╗
║                    STOCK PRICE PREDICTION SYSTEM ARCHITECTURE              ║
╚════════════════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────────────────────────────────────────┐
│ TIER 1: KÉO DỮ LIỆU TỪ YAHOO FINANCE (Ingestion Layer)                     │
└────────────────────────────────────────────────────────────────────────────┘
        │
┌───────▼────────────────────────────────────────────────────────────────────┐
│ TIER 2: XỬ LÝ ETL VÀ PHÂN TÍCH CHỈ BÁO (Processing Layer)                  │
│       ├─ Điền khuyết dữ liệu thị trường (Data Cleaning)                    │
│       ├─ Tính toán RSI, MA10, MA50, Biến động (Volatility)                 │
│       └─ Chuẩn hóa (Scaling) và Chia tập Train/Test                        │
└────────────────────────────────────────────────────────────────────────────┘
        │
┌───────▼────────────────────────────────────────────────────────────────────┐
│ TIER 3: HUẤN LUYỆN MACHINE LEARNING (Model Layer)                          │
│       ├─ Random Forest Regressor & Gradient Boosting                       │
│       ├─ Tính điểm RMSE, R2 Score và Chọn Thuật toán tốt nhất              │
│       └─ Kết xuất mô hình (.pkl files)                                     │
└────────────────────────────────────────────────────────────────────────────┘
        │
┌───────▼────────────────────────────────────────────────────────────────────┐
│ TIER 4: TRÌNH DIỄN & TƯ VẤN (Web & API Layer)                              │
│       ├─ Fast API: Luồng trả Json tự động dưới dạng Server backend         │
│       ├─ Streamlit: Trực quan hóa đồ thị thị trường lên Web Dashboard      │
│       └─ 🧠 AI Recommendation: Dịch ngôn ngữ máy sang ngôn ngữ MUA/BÁN     │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. CÁCH CHẠY DỰ ÁN (CHUẨN CHỈ, KHÔNG LỖI)

### Cách 1: Chạy hoàn toàn trên máy cá nhân (Local)
Đây là cách nhanh nhất để thấy kết quả hệ thống chạy mượt mà trên máy tính của bạn.

1. **Khởi tạo môi trường & cài thư viện:**
   Mở Terminal trong thư mục dự án: `pip install -r requirements.txt`
   
2. **Chạy Trí Tuệ Nhân Tạo (Kéo Data + Huấn Luyện Máy Học):**
   *(Nếu bạn không dùng notebook Databricks mà chạy trực tiếp file python)*
   Bật Terminal gõ:
   - `python run_etl.py` (Để làm sạch dữ liệu)
   - `python run_training.py` (Chờ khoảng 1-2 phút cho thẻ học máy xong mô hình)

3. **Mở Bảng Điều Khiển (Dashboard Giao thức):**
   Mở một Terminal khác:
   - `streamlit run dashboard/dashboard.py`
   *(Trình duyệt sẽ lập tức mở đồ thị lên và đánh giá đầu tư trực tiếp)*

4. **Khởi động API chạy ngầm (Dành cho việc liên kết Mobile APP nếu muốn):**
   - `uvicorn api.api_service:app --reload`
   Truy cập `http://localhost:8000/docs` để test việc lấy dữ liệu tự động.

### Cách 2: Chạy trực tiếp trên Đám mây (Databricks Community Edition)
1. Kết nối kho lưu trữ với GitHub thông qua tính năng **Git Folders** của Databricks.
2. Khởi tạo một Cluster Serverless hoặc Cluster bình thường (có mũi tên xanh lá là bật).
3. Vào thư mục `notebooks` trên repo Databricks được kéo về, mở file `01_etl_pipeline.py`.
4. Bấm **Run All** (hoặc `Shift + Enter` ở từng cell). Databricks sẽ tự chẻ các dòng mã `# COMMAND ----------` làm nhiều đốt (cell). 
*Lưu ý: Nếu dùng bản Databricks Miễn phí, code trong thư mục notebook đã được tối ưu để lưu và luân chuyển Dataframe gốc đứt quãng trên CPU luôn để né lỗi cấm đọc Write Table Unity Catalog.*

---

## 3. GIẢI THÍCH CHI TIẾT CÁC ĐOẠN CODE QUAN TRỌNG NHẤT

### A. Quá trình Nhào Nặn Dữ Liệu (ETL Pipeline / Feature Engineering)
Nằm tại: `notebooks/01_etl_pipeline.py` (hoặc `etl/data_processor.py`).
Đây là "trái tim" của hệ thống vì AI chỉ thông minh nếu như được ăn loại dữ liệu "sạch".
* **Lọc nhiễu / Điền khuyết (Data Cleaning):** Do thị trường có những ngày đóng cửa cuối tuần làm dữ liệu trên biểu đồ thường hay có lỗ trống. Chúng tôi dùng hàm `ffill()` và `bfill()` để "trám" ngay dữ liệu của phiên chốt liền trước đó vào lỗ hổng để máy học giữ được guồng.
* **Chỉ báo Kỹ thuật (Technical Indicators):** Trong chứng khoán, giá không tự sinh ra. Dự án đã tự động phân tích thêm các cột phụ như **MA10, MA20** (Giá Trung bình), **RSI** (Chỉ số sức mạnh nội tại) và **Volatility** (Dao động biên) để mô phỏng "tâm lý sợ hãi hay hưng phấn" của đám đông.
* **Mục tiêu đích (Target Variable):** Máy học sẽ học biến số `Biến động Ngày Mai` = `(Giá đóng cửa Ngày Mai / Giá đóng cửa Hôm nay) - 1`. Đây là công thức đếm bước thực dụng nhất, tránh tình trạng ép Machine Learning phải đoán mò một con số chênh hẳn 50 Đô-la. Nó dự đoán theo %. 

### B. Chọn Mặt Gửi Vàng (Machine Learning Models)
Nằm tại: `model/model_training.py` hoặc `run_training.py`.
* Hệ thống không bảo thủ xài 1 loại thuật toán, mà nó đẩy dữ liệu cùng một lúc chạy đua vào 3 thuật toán: `Linear Regression` (Đường thẳng cơ bản), `Random Forest` (Rừng quyết định), và `Gradient Boosting` (Dồn trọng số).
* Sau khi cả 3 chạy xong tập Dữ Liệu Thi (Test Set), nó tự đối chiếu bằng thước đo **RMSE** (Lỗi phân cấp tuyệt đối). 
* Thằng nào cắm thấp nhất = Lỗi ít nhất, hệ thống sẽ `pkl.dump` đóng gói não của nó lại thành file trong mục `models/...pkl` để xài vĩnh viễn không cần huấn luyện lại.

### C. Khuyến Nghị Tư Vấn Thông Minh trên Dashboard
Nằm tại: `dashboard/dashboard.py` (Khu vực New Feature AI Recommendation).
* Ứng dụng lọc trích xuất 1 nhịp chót của Index Thời Gian (Dữ liệu ngày hôm nay) làm "Mẫu thử trực tiếp". Đẩy nhanh vào mô hình `.predict()` để cho ra cái % tăng trưởng của chính phiên tiếp theo chưa xảy ra trong thực tế.
* Đưa vào cây Logic quy đổi: 
   - **Tăng trên > 1%** (Dự báo vút nắp: MUA MẠNH).
   - **Tăng từ 0 - 1%** (Dự tính sideway hoặc tăng hờ: Cân nhắc GIỮ hoặc mua dò).
   - **Giảm < 0%** (Rủi ro: Hạ tỉ trọng hoặc cắt lỗ GẤP).
Mô hình sẽ tô màu rất rõ Xanh Đỏ để loại trừ hoàn toàn việc quyết định cảm tính của con người khi xem bảng điện.
