"""Công cụ nội bộ giả lập backend: gọi OCR service qua HTTP.

Chạy:  streamlit run app.py
File này chỉ chọn trang; nội dung từng trang nằm trong thư mục ui/.
Không import gói xử lý (ocr_baseline), chỉ nói chuyện với service qua ui/api_client.py.
"""
import streamlit as st

from ui import page_prompts, page_review, page_stats, page_submit
from ui.api_client import get_client

st.set_page_config(page_title="OCR service - công cụ nội bộ", layout="wide")

PAGES = {
    "Gửi ảnh": page_submit,
    "Duyệt": page_review,
    "Thống kê": page_stats,
    "Prompt": page_prompts,
}

st.sidebar.title("OCR service")
page = st.sidebar.radio("Trang", list(PAGES), label_visibility="collapsed")

PAGES[page].render(get_client())
