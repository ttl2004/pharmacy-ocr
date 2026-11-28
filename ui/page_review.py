"""Trang "Duyệt": xem một extraction, sửa 16 trường, chấm sao, xem độ lệch, chạy lại, xoá."""
import streamlit as st

from .api_client import OcrServiceClient, ServiceError
from .review_form import go_to, remember, render_delete, render_rerun, render_review_form

_IMAGE_COLS = 4


def _on_pick() -> None:
    """Selectbox đổi: lựa chọn thành current_id."""
    picked = st.session_state.get("picked_id")
    if picked:
        st.session_state["current_id"] = picked


def _on_type() -> None:
    """Text_input đổi: chỉ nhận khi không rỗng sau strip."""
    typed = (st.session_state.get("typed_id") or "").strip()
    if typed:
        st.session_state["current_id"] = typed


def _choose_id() -> str | None:
    """current_id là nguồn duy nhất; selectbox và text_input cập nhật nó qua callback (lần đổi sau cùng thắng)."""
    recent = st.session_state["recent_ids"]
    current = st.session_state["current_id"]
    st.session_state.setdefault("picked_id", current if current in recent else None)
    st.session_state.setdefault("typed_id", "")
    col1, col2 = st.columns(2)
    col1.selectbox("Extraction gần đây", list(recent), index=None, key="picked_id",
                   placeholder="Chọn một mã", on_change=_on_pick)
    col2.text_input("Hoặc nhập mã", key="typed_id", on_change=_on_type)
    return st.session_state["current_id"]


def _render_header(info: dict) -> None:
    c = st.columns(4)
    c[0].metric("Trạng thái", info.get("status") or "-")
    c[1].metric("Engine", info.get("engine") or "-")
    c[2].metric("LLM", info.get("llm_model") or "-")
    c[3].metric("Prompt", str(info.get("prompt_version") or "-"))
    status = info.get("status")
    if info.get("superseded_by"):
        st.warning(f"Bản này đã bị thay thế bởi {info['superseded_by']}.")
        st.button("Mở bản mới", on_click=go_to, args=(str(info["superseded_by"]),))
    if status in ("queued", "running"):
        st.info("Đang xử lý, bấm Làm mới để cập nhật.")
        st.button("Làm mới")
    elif status == "failed":
        st.error(str(info.get("error") or "Xử lý thất bại."))


def _render_images(client: OcrServiceClient, info: dict) -> None:
    images = info.get("images") or []
    for start in range(0, len(images), _IMAGE_COLS):
        cols = st.columns(_IMAGE_COLS)
        for col, img in zip(cols, images[start:start + _IMAGE_COLS]):
            try:
                col.image(client.get_image(info["id"], img["index"]), caption=f"Ảnh {img['index']}")
            except ServiceError as e:
                col.error(f"{e.code}: {e.message}")


def _render_ocr(info: dict) -> None:
    ocr = info.get("ocr")
    if not ocr:
        return
    with st.expander("OCR thô (raw)"):
        st.text(ocr.get("raw") or "")
    with st.expander("OCR đã làm sạch (clean)"):
        st.text(ocr.get("clean") or "")


def render(client: OcrServiceClient) -> None:
    st.session_state.setdefault("recent_ids", [])
    st.session_state.setdefault("current_id", None)

    st.header("Duyệt")
    flash = st.session_state.pop("flash_error", None)
    if flash:
        st.error(flash)
    eid = _choose_id()
    if not eid:
        st.info("Chọn hoặc nhập mã extraction để bắt đầu.")
        return
    try:
        info = client.get_extraction(eid)
    except ServiceError as e:
        st.error(f"{e.code}: {e.message}")
        return
    # Id nhập tay tải được thì nhớ lại (không đụng key widget trong script chính)
    if eid not in st.session_state["recent_ids"]:
        remember(eid)

    _render_header(info)
    _render_images(client, info)
    _render_ocr(info)
    status = info.get("status")
    superseded = bool(info.get("superseded_by"))
    if status == "succeeded" and not superseded and info.get("result"):
        render_review_form(client, info)
    if status in ("queued", "running"):
        return  # đang xử lý: ẩn chạy lại và xoá
    st.divider()
    if not superseded:
        render_rerun(client, str(info["id"]))
        st.divider()
    render_delete(client, str(info["id"]))
