# Pharmacy OCR service

Service HTTP (FastAPI) trích xuất thông tin từ ảnh tờ hướng dẫn sử dụng thuốc:
**OCR** (lấy văn bản từ ảnh) → **LLM** (tách văn bản thành 16 trường dữ liệu) → **JSON** trả về cho backend.
Người dùng cuối kiểm tra, chấm sao kết quả và gửi lại qua API (feedback).

Repo gồm hai phần:
- **Service** (`src/ocr_baseline/`): API cho backend gọi.
- **Công cụ nội bộ** (`app.py`, `ui/`): giao diện Streamlit giả lập backend, chỉ gọi service qua HTTP.

## Mô hình và API sử dụng

| Thành phần | Công nghệ | Ghi chú |
|---|---|---|
| Service HTTP | **FastAPI** + uvicorn | Xác thực bằng header `X-API-Key` |
| OCR qua API | **Google Cloud Vision API** (`DOCUMENT_TEXT_DETECTION`) | Engine mặc định, cần mạng |
| OCR cục bộ: phát hiện vùng chữ | **PaddleOCR** `PP-OCRv5_server_det` | Chạy trên CPU, không cần GPU |
| OCR cục bộ: nhận dạng chữ | **VietOCR** `vgg_transformer` | Hỗ trợ đầy đủ tiếng Việt có dấu |
| OCR cục bộ: tự xoay ảnh | PaddleOCR `PP-LCNet_x1_0_doc_ori` | Nhận biết ảnh xoay 0/90/180/270° |
| Tách thông tin | **DeepSeek** (`deepseek-chat`, API tương thích OpenAI) | Chế độ JSON, temperature 0 |
| Công cụ nội bộ | Streamlit + requests | Chỉ là client HTTP |
| Lưu trữ | SQLite + file ảnh WebP | |

## Kiến trúc

```
 FE ───► Backend ───► OCR service (FastAPI) ───► hàng đợi job (worker trong tiến trình)
                          │
                          ▼
      ┌─────────────────────────────────────────────┐
 Ảnh ►│ OCR: Google Cloud Vision (mặc định)         │──► Văn bản
      │      hoặc OCR cục bộ (PaddleOCR + VietOCR)  │
      └─────────────────────────────────────────────┘
                          │
                          ▼
      ┌─────────────────────────────────────────────┐
      │ LLM (DeepSeek) + prompt có phiên bản        │──► 16 trường (JSON)
      │ + kiểm tra con số không có trong văn bản OCR│
      └─────────────────────────────────────────────┘
                          │
                          ▼
              SQLite + data/extractions/
```

- Gửi ảnh nhận ngay `202` kèm `id`; job chạy nền, client hỏi lại `GET /extractions/{id}` tới khi `status` là `succeeded` hoặc `failed`.
- Nhiều ảnh trong một extraction được ghép văn bản theo đúng thứ tự gửi lên.
- Mọi engine OCR có cùng giao diện `run(ảnh) -> văn bản`, nên đổi engine không ảnh hưởng bước LLM và lưu trữ.
- Chạy lại (`rerun`) tạo extraction mới, bản cũ bị đánh dấu `superseded_by`. Chế độ `llm_only` dùng lại văn bản OCR cũ, chỉ gọi lại LLM (có thể đổi prompt).
- Prompt quản lý theo **phiên bản**: mỗi lần sửa tạo phiên bản mới, không sửa đè. Mỗi extraction ghi rõ prompt, engine và model đã dùng.

## API

Tất cả endpoint nằm dưới prefix `/api/v1` và cần header `X-API-Key`.

| Method | Đường dẫn | Chức năng |
|---|---|---|
| POST | `/extractions` | Gửi ảnh (multipart, field `images[]`, tuỳ chọn `prompt_id`), trả `202` |
| GET | `/extractions/{id}` | Trạng thái, ảnh, văn bản OCR, kết quả, bản duyệt |
| GET | `/extractions/{id}/images/{index}` | Tải ảnh WebP đã tối ưu |
| POST | `/extractions/{id}/rerun` | Chạy lại (`mode`: `full` hoặc `llm_only`, tuỳ chọn `prompt_id`), trả `202` |
| PUT | `/extractions/{id}/feedback` | Lưu `rating` 1-5 và `final_fields`, trả bảng độ lệch so với đề xuất |
| DELETE | `/extractions/{id}` | Xoá extraction và ảnh (`409` khi đang chạy) |
| GET | `/stats?group_by=prompt\|engine\|model\|source` | Thống kê điểm sao và tỉ lệ chỉnh sửa theo nhóm |
| POST | `/parse` | Parse thử các trường dạng text |
| GET | `/prompts` | Danh sách phiên bản prompt |
| POST | `/prompts` | Tạo phiên bản prompt mới |
| POST | `/prompts/{id}/activate` | Đặt prompt làm bản đang dùng |

Lỗi luôn có dạng `{"error": {"code": "...", "message": "..."}}`. Các mã lỗi:

| code | HTTP |
|---|---|
| `too_many_images` | 400 |
| `unauthorized` | 401 |
| `not_found` | 404 |
| `invalid_state` | 409 |
| `image_too_large` | 413 |
| `unsupported_format` | 415 |
| `invalid_request` | 422 |
| `internal_error` | 500 |

Hợp đồng JSON đầy đủ (request, response từng endpoint) nằm trong Linear issue **PHA-8**.

## Quyết định cần biết khi vận hành

- **Vision tự dự phòng bằng OCR cục bộ**: Google Cloud Vision lỗi (mất mạng, sai key, hết quota) thì service tự làm lại toàn bộ ảnh bằng OCR cục bộ, không cần can thiệp. Kết quả ghi rõ engine đã dùng.
- **Tách đoạn theo tiêu đề tắt mặc định**: bật bằng `SECTION_SPLIT_ENABLED=true`.
- **Dữ liệu giữ vĩnh viễn**: service không tự xoá extraction nào. Xoá thủ công bằng `DELETE /extractions/{id}`.
- **Sao lưu do người vận hành tự làm**: cần sao lưu `data/ocr_service.db` (SQLite) và thư mục `data/extractions/` (ảnh). Hai thứ này đi cùng nhau, nên sao lưu cùng thời điểm.
- Thiếu `OCR_SERVICE_API_KEY` thì service không khởi động (tránh vô tình mở API không xác thực).
- Google Cloud Vision gửi ảnh lên máy chủ Google và cần mạng. OCR cục bộ chạy hoàn toàn trên máy.
- Thông tin do hệ thống trích xuất cần được người dùng kiểm tra trước khi sử dụng.

## Biến môi trường (`.env`)

Sao chép `.env.example` thành `.env`. Các biến chính (mặc định trong ngoặc):

| Nhóm | Biến |
|---|---|
| API | `OCR_SERVICE_API_KEY` (bắt buộc với service), `OCR_SERVICE_URL` (`http://127.0.0.1:8000`, dùng cho Streamlit) |
| LLM | `DEEPSEEK_API_KEY` (bắt buộc), `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` (`deepseek-chat`), `LLM_TIMEOUT` (180) |
| Google Vision | `GOOGLE_VISION_API_KEY`, `VISION_TIMEOUT` (60) |
| OCR cục bộ | `OCR_THREADS` (0 = tự chọn), `OCR_ENABLE_MKLDNN` (true), `OCR_DET_LIMIT_SIDE` (1600), `MODELS_DIR` (thư mục `models/`) |
| Engine mặc định | `OCR_ENGINE` (`vision` hoặc `local`, mặc định `vision`) |
| Worker | `WORKER_COUNT` (1), `WORKER_POLL_SECONDS` (1.0) |
| Ảnh tải lên | `MAX_IMAGES` (20), `MAX_IMAGE_MB` (5), `IMAGE_MAX_SIDE` (2400), `IMAGE_QUALITY` (85) |
| Tách đoạn | `SECTION_SPLIT_ENABLED` (false), `SECTION_MIN_FOUND` (3) |
| Feedback | `MINOR_EDIT_THRESHOLD` (0.9): độ tương đồng tối thiểu để coi là sửa nhẹ |
| Dữ liệu | `DATA_DIR` (`data/`), `DB_PATH` (`DATA_DIR/ocr_service.db`), `STORAGE_DIR` (`DATA_DIR/extractions`) |

## Cấu trúc thư mục

```
app.py                       Điểm vào Streamlit (chỉ chọn trang)
ui/                          Công cụ nội bộ, client HTTP (không import ocr_baseline)
  api_client.py              Client gọi service, đọc OCR_SERVICE_URL / OCR_SERVICE_API_KEY
  field_labels.py            Nhãn 16 trường (phải khớp profiles/drug.py)
  page_submit.py             Gửi ảnh
  page_review.py, review_form.py   Duyệt, chấm sao, chạy lại, xoá
  page_stats.py              Thống kê
  page_prompts.py            Quản lý prompt
src/ocr_baseline/            Service
  config.py                  Đọc cấu hình từ .env
  constants.py               Mã engine, trạng thái, chế độ chạy lại
  pipeline.py                Các bước dùng chung: OCR ảnh (Vision, dự phòng local), ghép văn bản, trích xuất
  prompts.py                 Prompt có phiên bản
  stats.py                   Thống kê
  api/                       FastAPI: app, xác thực, lỗi, các route, schema
  jobs/                      Hàng đợi và worker xử lý extraction
  images/                    Kiểm tra, tối ưu WebP, lưu ảnh
  ocr/
    vision.py                Google Cloud Vision
    local/                   OCR cục bộ: tiền xử lý, PaddleOCR, VietOCR, thứ tự đọc
  profiles/                  Danh sách 16 trường + prompt gốc (drug.py)
  extraction/                Gọi LLM, kiểm tra con số
  text/                      Làm sạch, tách đoạn, parse, so sánh trường
  storage/                   SQLite: định nghĩa bảng, repository
data/                        ocr_service.db và extractions/ (tạo khi chạy)
tests/                       Kiểm thử tự động (không gọi API)
```

## Cài đặt và chạy

```bash
python3 -m venv .venv
.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install --no-deps vietocr==0.3.13
.venv/bin/pip install -e ".[dev]"
cp .env.example .env          # điền OCR_SERVICE_API_KEY, DEEPSEEK_API_KEY, GOOGLE_VISION_API_KEY

# Service (không có biến module `app`, phải dùng --factory)
.venv/bin/uvicorn ocr_baseline.api.app:create_app --factory --port 8000

# Công cụ nội bộ (cần service đang chạy)
.venv/bin/streamlit run app.py

# Kiểm thử
.venv/bin/python -m pytest
```

- Lần đầu dùng OCR cục bộ, hệ thống tự tải model (PaddleOCR vào `~/.paddlex/`, VietOCR vào `MODELS_DIR`).
- Streamlit dùng chung `OCR_SERVICE_API_KEY` trong `.env` để gọi service.
- Tài liệu API tự sinh của FastAPI có ở `http://127.0.0.1:8000/docs`.

## Mở rộng

| Muốn | Sửa ở |
|---|---|
| Sửa quy ước tách trường | Tạo phiên bản prompt mới qua `POST /prompts` hoặc trang **Prompt** (không cần sửa code) |
| Thêm / bớt trường | `src/ocr_baseline/profiles/drug.py` và `ui/field_labels.py` |
| Thêm engine OCR | Class có `run(ảnh) -> OcrResult` trong `ocr/`, thêm mã vào `constants.py` và `ocr/__init__.py` |
