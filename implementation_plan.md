# Kế hoạch chuyển đổi giao diện sang React

Chào bạn! Việc chuyển giao diện từ Streamlit sang React là hoàn toàn khả thi và là một quyết định tuyệt vời để cải thiện đáng kể UI/UX, tốc độ phản hồi, hiệu ứng chuyển động mượt mà và khả năng tùy biến cao hơn rất nhiều.

Dưới đây là kế hoạch chi tiết để chuyển đổi giao diện hiện tại của hệ thống **Stock AI** sang **React** (sử dụng **Vite** + **TypeScript** + **Vanilla CSS** cao cấp).

---

## User Review Required

> [!WARNING]
> Việc chuyển đổi này sẽ xây dựng một dự án frontend độc lập trong thư mục `frontend-react` và không làm ảnh hưởng đến mã nguồn backend hiện tại. Tuy nhiên, để React hoạt động bình thường, chúng ta sẽ cần:
> 1. **Cấu hình CORS** trên backend FastAPI (`api/api_service.py`) để cho phép React (chạy ở cổng 5173 hoặc 3000) gửi request đến.
> 2. **Chuyển đổi các trang hiện tại** (Tổng quan, Phân tích AI, So sánh) và tính năng Login/Register sang giao diện React.

---

## Open Questions

> [!IMPORTANT]
> 1. **Framework Khởi Tạo:** Tôi đề xuất sử dụng **Vite** kết hợp với **TypeScript** để ứng dụng nhẹ, chạy cực nhanh và dễ quản lý. Bạn có đồng ý không, hay bạn muốn dùng **Next.js**?
> 2. **Thư viện Vẽ Biểu đồ:** Streamlit hiện đang dùng Plotly. Với React, chúng ta có thể dùng `react-plotly.js` (đồng bộ 100% với backend hiện tại trả về dữ liệu Plotly JSON) hoặc chuyển sang `Recharts` / `ApexCharts` để có biểu đồ mượt mà và tương thích tốt hơn với React. Bạn muốn sử dụng thư viện nào?
> 3. **Cơ chế Xác thực (Auth):** Giao diện cũ đang lưu user đăng ký vào file `users.json` ở phía server. Khi chuyển sang React (chạy ở trình duyệt của user), việc đăng nhập/đăng ký nên được xử lý qua các API endpoint mới trên FastAPI để đảm bảo an toàn bảo mật. Tôi có thể tự động viết thêm API đăng nhập/đăng ký trên backend FastAPI cho bạn, bạn thấy thế nào?

---

## Proposed Changes

Để thực hiện quá trình này, các bước dự kiến như sau:

### 1. Khởi tạo dự án React (Mới)
#### [NEW] [frontend-react](file:///d:/code/Cloud/frontend-react)
Tạo thư mục frontend mới chứa ứng dụng React:
- Cấu hình file `vite.config.ts`, `tsconfig.json`.
- Thiết lập hệ thống thư mục:
  - `src/components/` (Sidebar, Navbar, GlassCard, MetricCard...)
  - `src/pages/` (Login, Register, Dashboard, Analysis, MarketCompare)
  - `src/api/` (Axios client kết nối với backend)
  - `src/styles/` (CSS file chứa Glassmorphism style, dark-mode gradients)

### 2. Cập nhật Backend FastAPI (Nếu cần)
#### [MODIFY] [api_service.py](file:///d:/code/Cloud/api/api_service.py)
- Thêm middleware CORS (`CORSMiddleware`) để cho phép frontend React kết nối.
- (Tùy chọn) Thêm endpoint `/api/auth/register` và `/api/auth/login` để hỗ trợ tính năng đăng nhập/đăng ký cho React.

### 3. Thiết kế Giao diện (Premium Glassmorphism)
- Tận dụng phong cách màu tối hiện đại (`#0f172a`, `#1e1b4b`).
- Sử dụng các hiệu ứng chuyển động mượt mà khi đổi trang, hover chuột vào các thẻ cổ phiếu.
- Sidebar lớn, cỡ chữ rõ ràng, nút bấm nổi bật, loại bỏ các emoji không cần thiết.

---

## Verification Plan

### Automated & Manual Tests
1. **Khởi chạy đồng thời:**
   - Chạy backend: `python run_all.py` hoặc `uvicorn api.api_service:app --reload`
   - Chạy frontend: `cd frontend-react && npm run dev`
2. **Kiểm tra chức năng:**
   - Truy cập `http://localhost:5173` để thử đăng ký tài khoản mới và đăng nhập.
   - Thử chuyển đổi giữa 3 tab chính: *Tổng quan*, *AI Phân Tích*, *Thị trường & So sánh*.
   - Kiểm tra tính tương tác của các biểu đồ chứng khoán và bảng dữ liệu.
