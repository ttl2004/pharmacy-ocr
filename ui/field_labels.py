"""Nhãn 16 trường thuốc để hiển thị form duyệt.

Danh sách này PHẢI khớp với COLUMNS trong src/ocr_baseline/profiles/drug.py
(UI không import ocr_baseline nên phải chép tay, cùng thứ tự).
"""

FIELD_LABELS: list[tuple[str, str]] = [
    ("so_dang_ky", "Số đăng ký"),
    ("ten_thuoc", "Tên thuốc"),
    ("hoat_chat_ham_luong", "Hoạt chất - hàm lượng"),
    ("dang_bao_che", "Dạng bào chế"),
    ("quy_cach_dong_goi", "Quy cách đóng gói"),
    ("chi_dinh", "Chỉ định"),
    ("chong_chi_dinh", "Chống chỉ định"),
    ("lieu_dung_cach_dung", "Liều dùng - cách dùng"),
    ("tac_dung_khong_mong_muon", "Tác dụng không mong muốn"),
    ("than_trong", "Thận trọng"),
    ("tuong_tac_thuoc", "Tương tác thuốc"),
    ("phu_nu_co_thai_cho_con_bu", "Phụ nữ có thai - cho con bú"),
    ("qua_lieu", "Quá liều"),
    ("bao_quan", "Bảo quản"),
    ("han_dung", "Hạn dùng"),
    ("nha_san_xuat", "Nhà sản xuất"),
]
