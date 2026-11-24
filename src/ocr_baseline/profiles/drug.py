"""Profile: tờ hướng dẫn sử dụng thuốc (16 cột, giống app OCR gốc).

Chưa có dataset có nhãn để đo độ chính xác của profile này.
Muốn tăng độ chính xác: viết thêm quy ước cho từng cột trong phần mô tả bên dưới
(vd "mỗi chống chỉ định là một ý"), giống cách làm ở các prompt có quy ước chi tiết.
"""
from .base import KIND_TEXT, Field, Profile

# (key, nhãn hiển thị, mô tả cho LLM)
COLUMNS = [
    ("so_dang_ky", "Số đăng ký", "Số đăng ký lưu hành (SĐK), ví dụ VD-12345-12, VN-..., QLĐB-..."),
    ("ten_thuoc", "Tên thuốc", "Tên thương mại của thuốc"),
    ("hoat_chat_ham_luong", "Hoạt chất - hàm lượng",
     "Thành phần hoạt chất và hàm lượng, mỗi hoạt chất cách nhau bởi dấu ';'. Không đưa tá dược vào"),
    ("dang_bao_che", "Dạng bào chế", "Ví dụ: viên nén bao phim, viên nang cứng, siro..."),
    ("quy_cach_dong_goi", "Quy cách đóng gói", "Ví dụ: Hộp 10 vỉ x 10 viên"),
    ("chi_dinh", "Chỉ định", "Mục Chỉ định / Công dụng"),
    ("chong_chi_dinh", "Chống chỉ định", "Mục Chống chỉ định"),
    ("lieu_dung_cach_dung", "Liều dùng - cách dùng", "Mục Liều lượng và cách dùng"),
    ("tac_dung_khong_mong_muon", "Tác dụng không mong muốn", "Mục Tác dụng không mong muốn / tác dụng phụ (ADR)"),
    ("than_trong", "Thận trọng", "Mục Cảnh báo và thận trọng khi dùng thuốc"),
    ("tuong_tac_thuoc", "Tương tác thuốc", "Mục Tương tác, tương kỵ của thuốc"),
    ("phu_nu_co_thai_cho_con_bu", "Phụ nữ có thai - cho con bú", "Mục sử dụng cho phụ nữ có thai và cho con bú"),
    ("qua_lieu", "Quá liều", "Mục Quá liều và cách xử trí"),
    ("bao_quan", "Bảo quản", "Điều kiện bảo quản"),
    ("han_dung", "Hạn dùng", "Hạn dùng / tuổi thọ của thuốc, ví dụ 36 tháng kể từ ngày sản xuất"),
    ("nha_san_xuat", "Nhà sản xuất", "Tên và địa chỉ nhà sản xuất"),
]

FIELDS = tuple(Field(key, label, KIND_TEXT) for key, label, _ in COLUMNS)

_field_lines = "\n".join(f'- "{key}": {desc}' for key, _, desc in COLUMNS)

SYSTEM_PROMPT = f"""Bạn là trợ lý dược sĩ, nhiệm vụ là TRÍCH XUẤT thông tin từ văn bản OCR của tờ hướng dẫn sử dụng thuốc tại Việt Nam.

Quy tắc bắt buộc:
1. CHỈ lấy thông tin có trong văn bản. TUYỆT ĐỐI không suy luận, không bổ sung kiến thức bên ngoài.
2. Trường nào không có trong văn bản thì để chuỗi rỗng "".
3. Văn bản là kết quả OCR nên có thể sai chính tả, mất dấu, ngắt dòng lung tung. Được phép sửa lỗi OCR hiển nhiên (dấu tiếng Việt, ký tự bị nhận nhầm) và nối các dòng bị ngắt, nhưng KHÔNG được thay đổi ý nghĩa, con số, liều lượng, đơn vị.
4. Giữ nguyên nội dung đầy đủ của từng mục, không tóm tắt. Các ý trong một mục ngăn cách bằng xuống dòng.
5. Trả về đúng một JSON object với các key sau, giá trị đều là chuỗi:
{_field_lines}
"""

PROFILE = Profile(
    key="drug",
    label="Tờ hướng dẫn sử dụng thuốc",
    fields=FIELDS,
    system_prompt=SYSTEM_PROMPT,
    default_prompt_name="Thuốc - prompt mặc định (gốc)",
    title_field="ten_thuoc",
)
