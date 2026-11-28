# Hướng dẫn chạy (Windows)

## Cách nhanh: bấm đúp `run.bat`

`run.bat` nằm ở thư mục gốc project. Bấm đúp vào nó sẽ:

1. Kiểm tra đã có `.venv` và `.env`. Thiếu một trong hai thì báo lỗi và dừng.
2. Mở cửa sổ terminal **"OCR service :8000"** chạy FastAPI.
3. Đợi 4 giây rồi mở cửa sổ **"OCR Streamlit :8501"** chạy công cụ nội bộ.
4. Mở trình duyệt ở `http://localhost:8501`.

Tắt: đóng cửa sổ terminal tương ứng, hoặc bấm `Ctrl+C` trong cửa sổ đó.

Đổi cổng: sửa `SERVICE_PORT` / `UI_PORT` ở đầu `run.bat`. Nếu đổi `SERVICE_PORT` thì phải sửa `OCR_SERVICE_URL` trong `.env` cho khớp, vì Streamlit gọi service qua địa chỉ này.

## Cài đặt lần đầu

Chạy trong PowerShell, tại thư mục `projects/pharmacy-ocr`.

### Bản nhẹ (chỉ dùng Google Vision, không có OCR cục bộ)

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
```

Bản này không có torch, PaddleOCR, VietOCR. Khi Vision lỗi (sai key, hết quota, mất mạng), service chuyển sang OCR cục bộ và job sẽ `failed` với lỗi `No module named 'torch'`.

`.venv` hiện có trong project là bản nhẹ này.

### Bản đầy đủ (có OCR cục bộ làm dự phòng)

```powershell
python -m venv .venv
.\.venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\pip install --no-deps vietocr==0.3.13
.\.venv\Scripts\pip install -e ".[dev]"
```

Lần đầu chạy OCR cục bộ, model tự tải về (PaddleOCR vào `~/.paddlex/`, VietOCR vào `MODELS_DIR`).

## File `.env`

Sao chép `.env.example` thành `.env`, rồi điền tối thiểu 3 biến:

| Biến | Vai trò |
|---|---|
| `OCR_SERVICE_API_KEY` | Khoá tự đặt, chuỗi bất kỳ. Thiếu thì service không khởi động. Streamlit dùng chung khoá này. |
| `DEEPSEEK_API_KEY` | Gọi LLM tách 16 trường. Thiếu thì job báo lỗi. |
| `GOOGLE_VISION_API_KEY` | OCR qua Google Vision. Thiếu thì service dùng OCR cục bộ. |

Các biến khác xem bảng trong `README.md`.

## Chạy tay (không dùng `run.bat`)

Mở 2 cửa sổ PowerShell tại thư mục project.

Cửa sổ 1, service:

```powershell
.\.venv\Scripts\python.exe -m uvicorn ocr_baseline.api.app:create_app --factory --port 8000
```

Cửa sổ 2, công cụ nội bộ (cần service đang chạy):

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

`--server.address 127.0.0.1` giữ công cụ nội bộ chỉ mở trên máy này. Bỏ cờ này thì Streamlit mở cho cả mạng LAN và in thêm "Network URL", "External URL".

## Sau khi chạy

- Công cụ nội bộ: `http://localhost:8501`. Có 4 trang: Gửi ảnh, Duyệt, Thống kê, Prompt.
- Tài liệu API tự sinh: `http://127.0.0.1:8000/docs`. Mọi endpoint cần header `X-API-Key` bằng `OCR_SERVICE_API_KEY`.
- Dữ liệu lưu ở `data/ocr_service.db` và `data/extractions/`.

## Lỗi thường gặp

| Hiện tượng | Nguyên nhân và cách xử lý |
|---|---|
| Cửa sổ service tắt ngay, báo `Thiếu OCR_SERVICE_API_KEY` | Điền `OCR_SERVICE_API_KEY` trong `.env`. |
| Service báo cổng đang bị dùng | Có chương trình khác giữ cổng 8000. Đổi `SERVICE_PORT` trong `run.bat` và `OCR_SERVICE_URL` trong `.env`. |
| Terminal hiện ký tự lạ như `←[0m`, `←[34m` | Đó là mã màu ANSI mà console Windows 10 (cả `cmd` lẫn PowerShell 5.1) không hiển thị được. `run.bat` chạy qua `tools/run-with-ansi-colors.py` để bật chế độ màu. Nếu chạy tay thì thay `-m uvicorn` / `-m streamlit` bằng `tools\run-with-ansi-colors.py uvicorn` / `tools\run-with-ansi-colors.py streamlit`, hoặc dùng Windows Terminal. |
| Streamlit báo `connection_error` | Service chưa chạy hoặc `OCR_SERVICE_URL` sai cổng. |
| Streamlit báo `unauthorized` | Streamlit và service đọc khác khoá. Kiểm tra không có biến môi trường `OCR_SERVICE_API_KEY` đặt sẵn trong hệ thống ghi đè `.env`. |
| Job `failed` với lỗi `No module named 'torch'` | Vision lỗi nên service chuyển sang OCR cục bộ, nhưng `.venv` là bản nhẹ. Kiểm tra `GOOGLE_VISION_API_KEY`, hoặc cài bản đầy đủ. |
