"""Trang "Gửi ảnh": tải ảnh lên, chọn prompt, gửi sang OCR service và theo dõi trạng thái."""
import streamlit as st

from .api_client import OcrServiceClient, ServiceError


def _prompt_label(p: dict) -> str:
    return f"{p['name']} v{p['version']}" + (" (đang dùng)" if p["is_active"] else "")


def _choose_prompt(client: OcrServiceClient) -> int | None:
    """Selectbox chọn prompt, mặc định là prompt đang kích hoạt. Trả về prompt_id (None = dùng prompt active)."""
    try:
        prompts = client.list_prompts()
    except ServiceError as e:
        st.error(f"{e.code}: {e.message}")
        return None
    if not prompts:
        st.warning("Service chưa có prompt nào.")
        return None
    active_idx = next((i for i, p in enumerate(prompts) if p["is_active"]), 0)
    chosen = st.selectbox("Prompt", prompts, index=active_idx, format_func=_prompt_label)
    return None if chosen["is_active"] else chosen["id"]


def _submit(client: OcrServiceClient, uploads: list, prompt_id: int | None) -> None:
    """Gửi ảnh theo thứ tự tải lên, rồi ghi id vào session_state."""
    files = [(f.name, f.getvalue(), f.type or "application/octet-stream") for f in uploads]
    try:
        created = client.create_extraction(files, prompt_id)
    except ServiceError as e:
        st.error(f"{e.code}: {e.message}")
        return
    new_id = str(created["id"])
    recent = st.session_state["recent_ids"]
    if new_id in recent:
        recent.remove(new_id)
    recent.insert(0, new_id)
    st.session_state["current_id"] = new_id
    st.success(f"Đã gửi, mã extraction: {new_id}")


def _render_current(client: OcrServiceClient) -> None:
    """Hiện trạng thái của current_id kèm nút "Làm mới" (không tự polling)."""
    current_id = st.session_state["current_id"]
    if not current_id:
        return
    st.divider()
    st.subheader("Trạng thái")
    st.caption(f"Extraction: {current_id}")
    st.button("Làm mới")  # bấm sẽ rerun trang, phần dưới gọi lại get_extraction
    try:
        info = client.get_extraction(current_id)
    except ServiceError as e:
        st.error(f"{e.code}: {e.message}")
        return
    status = info.get("status")
    st.write(f"Trạng thái: **{status}**")
    if status == "succeeded":
        st.success("Đã xử lý xong. Chuyển sang trang Duyệt để xem kết quả.")
    elif status == "failed":
        err = info.get("error")
        st.error(str(err) if err else "Xử lý thất bại.")
    else:
        st.info("Đang xử lý, bấm Làm mới để cập nhật.")


def render(client: OcrServiceClient) -> None:
    st.session_state.setdefault("recent_ids", [])
    st.session_state.setdefault("current_id", None)

    st.header("Gửi ảnh")
    uploads = st.file_uploader("Chọn ảnh (jpg, jpeg, png, webp)", type=["jpg", "jpeg", "png", "webp"],
                               accept_multiple_files=True)
    if uploads:
        st.caption("Thứ tự tải lên cũng là thứ tự ghép văn bản:")
        for i, f in enumerate(uploads, 1):
            st.write(f"{i}. {f.name}")

    prompt_id = _choose_prompt(client)

    if st.button("Gửi", type="primary", disabled=not uploads):
        _submit(client, uploads, prompt_id)

    _render_current(client)
