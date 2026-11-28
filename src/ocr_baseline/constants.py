"""Các mã dùng chung trong toàn bộ project (lưu trong DB, trả qua API)."""

# Engine OCR
ENGINE_VISION = "vision"   # Google Cloud Vision + LLM
ENGINE_LOCAL = "local"     # OCR local (PaddleOCR + VietOCR, CPU) + LLM

# Trạng thái extraction
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"

# Chế độ chạy: full = OCR + LLM, llm_only = dùng lại text OCR có sẵn, chỉ chạy LLM
MODE_FULL = "full"
MODE_LLM_ONLY = "llm_only"

# Nguồn của một trường kết quả
SOURCE_SECTION = "section"
SOURCE_LLM = "llm"
SOURCE_NONE = "none"

# Loại chỉnh sửa của người dùng so với kết quả máy (feedback)
EDIT_UNCHANGED = "unchanged"
EDIT_MINOR = "minor_edit"
EDIT_MAJOR = "major_edit"
EDIT_FILLED = "filled"
EDIT_CLEARED = "cleared"

SCHEMA_VERSION = "1"
IMAGE_CONTENT_TYPE = "image/webp"

# Các trường văn bản dài, có thể tách theo tiêu đề đoạn
SECTION_FIELDS = (
    "chi_dinh",
    "chong_chi_dinh",
    "lieu_dung_cach_dung",
    "tac_dung_khong_mong_muon",
    "than_trong",
    "tuong_tac_thuoc",
    "phu_nu_co_thai_cho_con_bu",
    "qua_lieu",
    "bao_quan",
)

# Các trường có cấu trúc, luôn do LLM trích
STRUCTURED_FIELDS = ("hoat_chat_ham_luong", "quy_cach_dong_goi", "han_dung")
