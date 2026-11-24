"""Bật hiển thị màu ANSI cho cửa sổ console Windows rồi chạy một module Python.

Dùng trong run.bat: console Windows 10 (cmd, PowerShell 5.1) mặc định không hiểu mã màu
nên uvicorn và Streamlit in ra ký tự lạ như "←[32m".

Cách dùng: python tools/run-with-ansi-colors.py <module> [tham số...]
Ví dụ:    python tools/run-with-ansi-colors.py uvicorn app:create_app --factory
"""

import os
import runpy
import sys

if os.name == "nt":
    # Mẹo quen thuộc: gọi cmd.exe rỗng sẽ bật ENABLE_VIRTUAL_TERMINAL_PROCESSING
    # cho console hiện tại, chế độ này giữ nguyên cho phần còn lại của tiến trình.
    os.system("")

if len(sys.argv) < 2:
    sys.exit("Thiếu tên module, ví dụ: uvicorn hoặc streamlit")

module = sys.argv[1]
sys.argv = [module] + sys.argv[2:]
runpy.run_module(module, run_name="__main__", alter_sys=True)
