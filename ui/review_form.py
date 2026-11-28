"""Form duyệt, bảng độ lệch, chạy lại và xoá của trang "Duyệt"."""
import streamlit as st

from .api_client import OcrServiceClient, ServiceError
from .field_labels import FIELD_LABELS


def _show_error(e: ServiceError) -> None:
    st.error(f"{e.code}: {e.message}")


def remember(extraction_id: str) -> None:
    """Đưa id lên đầu recent_ids (không trùng). Không đụng key widget nên dùng được trong script chính."""
    recent = st.session_state["recent_ids"]
    if extraction_id in recent:
        recent.remove(extraction_id)
    recent.insert(0, extraction_id)


def go_to(extraction_id: str) -> None:
    """Chuyển trang sang một extraction. CHỈ gọi trong callback on_click/on_change (được phép sửa key widget)."""
    remember(extraction_id)
    st.session_state["current_id"] = extraction_id
    st.session_state["picked_id"] = extraction_id
    st.session_state["typed_id"] = ""


def _render_diff(diff: dict) -> None:
    """Bảng độ lệch giữa kết quả của máy và bản người duyệt đã sửa."""
    st.subheader("Độ lệch so với kết quả gốc")
    labels = dict(FIELD_LABELS)
    rows = [{"trường": labels.get(k, k), "status": v.get("status"), "similarity": v.get("similarity")}
            for k, v in (diff.get("fields") or {}).items()]
    st.dataframe(rows)
    if diff.get("summary") is not None:
        st.write("Tóm tắt:")
        st.json(diff["summary"])


def render_review_form(client: OcrServiceClient, info: dict) -> None:
    """16 text_area điền sẵn, rating 1-5, nút "Lưu" gọi put_feedback."""
    eid = str(info["id"])
    result = info["result"]
    fields = result.get("fields") or {}
    feedback = info.get("feedback") or {}
    saved = feedback.get("final_fields") or {}

    st.subheader("Duyệt kết quả")
    with st.form(f"review_form_{eid}"):
        for key, label in FIELD_LABELS:
            f = fields.get(key) or {}
            default = saved.get(key, f.get("value") or "")
            st.text_area(label, value=default, key=f"{key}_{eid}")
            warnings = f.get("warnings") or []
            cap = f"source: {f.get('source')}"
            if warnings:
                cap += " | cảnh báo: " + "; ".join(str(w) for w in warnings)
            st.caption(cap)
        st.write("Dữ liệu cấu trúc:")
        st.json(result.get("structured"))
        rating = st.radio("Đánh giá (1-5 sao)", [1, 2, 3, 4, 5], horizontal=True,
                          index=(feedback.get("rating") or 3) - 1, key=f"rating_{eid}")
        submitted = st.form_submit_button("Lưu", type="primary")

    if submitted:
        final_fields = {key: st.session_state.get(f"{key}_{eid}", "") for key, _ in FIELD_LABELS}
        try:
            st.session_state[f"diff_{eid}"] = client.put_feedback(eid, rating, final_fields)
            st.success("Đã lưu đánh giá.")
        except ServiceError as e:
            _show_error(e)
    diff = st.session_state.get(f"diff_{eid}")
    if diff:
        _render_diff(diff)


def _do_rerun(client: OcrServiceClient, eid: str) -> None:
    """Callback nút "Chạy lại": đọc mode và prompt từ key widget, thành công thì chuyển sang id mới."""
    mode = st.session_state[f"rerun_mode_{eid}"]
    prompt = st.session_state.get(f"rerun_prompt_{eid}")
    try:
        created = client.rerun(eid, mode, prompt["id"] if prompt else None)
    except ServiceError as e:
        st.session_state["flash_error"] = f"{e.code}: {e.message}"
        return
    go_to(str(created["id"]))


def render_rerun(client: OcrServiceClient, eid: str) -> None:
    """Chạy lại với mode và prompt chọn tay; id mới thành current_id."""
    st.subheader("Chạy lại")
    st.radio("Chế độ", ["full", "llm_only"], horizontal=True, key=f"rerun_mode_{eid}")
    try:
        prompts = client.list_prompts()
    except ServiceError as e:
        _show_error(e)
        return
    if prompts:
        active_idx = next((i for i, p in enumerate(prompts) if p["is_active"]), 0)
        st.selectbox("Prompt", prompts, index=active_idx, key=f"rerun_prompt_{eid}",
                     format_func=lambda p: f"{p['name']} v{p['version']}"
                     + (" (đang dùng)" if p["is_active"] else ""))
    st.button("Chạy lại", key=f"rerun_btn_{eid}", on_click=_do_rerun, args=(client, eid))


def _do_delete(client: OcrServiceClient, eid: str) -> None:
    """Callback nút "Xoá": gỡ id khỏi recent_ids và bỏ chọn."""
    try:
        client.delete(eid)
    except ServiceError as e:
        st.session_state["flash_error"] = f"{e.code}: {e.message}"
        return
    recent = st.session_state["recent_ids"]
    if eid in recent:
        recent.remove(eid)
    st.session_state["current_id"] = None
    st.session_state["picked_id"] = None
    st.session_state["typed_id"] = ""


def render_delete(client: OcrServiceClient, eid: str) -> None:
    """Xoá extraction sau khi người dùng tick xác nhận."""
    st.subheader("Xoá")
    sure = st.checkbox("Tôi chắc chắn", key=f"del_sure_{eid}")
    st.button("Xoá", disabled=not sure, key=f"del_btn_{eid}", on_click=_do_delete, args=(client, eid))
