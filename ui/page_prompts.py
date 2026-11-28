"""Trang "Prompt": xem danh sách, kích hoạt, tạo phiên bản mới (gọi service qua HTTP)."""
import streamlit as st

from .api_client import OcrServiceClient, ServiceError

_FLASH = "prompts_flash"
_PICK_KEY = "prompts_pick"
_PENDING_PICK = "_prompts_pending_pick"


def _label(prompt: dict) -> str:
    """Nhãn trong selectbox: "{name} v{version}" kèm (đang dùng) nếu active."""
    text = f"{prompt['name']} v{prompt['version']}"
    return text + " (đang dùng)" if prompt.get("is_active") else text


def _activate(client: OcrServiceClient, prompt_id: int) -> None:
    """Callback nút Kích hoạt: thành công thì để lại thông báo cho lần chạy sau."""
    try:
        client.activate_prompt(prompt_id)
    except ServiceError as e:
        st.session_state[_FLASH] = ("error", f"{e.code}: {e.message}")
        return
    st.session_state[_FLASH] = ("success", "Đã kích hoạt prompt.")


def _show_flash() -> None:
    flash = st.session_state.pop(_FLASH, None)
    if flash:
        kind, text = flash
        (st.error if kind == "error" else st.success)(text)


def _render_table(prompts: list[dict]) -> None:
    st.dataframe([
        {"name": p["name"], "version": p["version"], "is_active": p["is_active"],
         "is_builtin": p["is_builtin"], "created_at": p["created_at"]}
        for p in prompts
    ])


def _render_create_form(client: OcrServiceClient, selected: dict) -> None:
    """Form tạo phiên bản mới; key chứa id prompt nên prefill đổi theo lựa chọn."""
    pid = selected["id"]
    with st.form(f"create_prompt_{pid}"):
        st.subheader("Tạo phiên bản mới")
        name = st.text_input("Tên", value=selected["name"], key=f"new_name_{pid}")
        content = st.text_area("Nội dung", value=selected["content"], height=300,
                               key=f"new_content_{pid}")
        note = st.text_input("Ghi chú", key=f"new_note_{pid}")
        submitted = st.form_submit_button("Tạo phiên bản")
    if not submitted:
        return
    try:
        created = client.create_prompt(name, content, note)
    except ServiceError as e:
        st.error(f"{e.code}: {e.message}")
        return
    st.session_state[_FLASH] = ("success", "Đã tạo phiên bản mới.")
    if isinstance(created, dict) and created.get("id") is not None:
        # Không gán thẳng key của selectbox đã tạo; chọn ở lần chạy sau
        st.session_state[_PENDING_PICK] = created["id"]
    st.rerun()


def render(client: OcrServiceClient) -> None:
    st.header("Prompt")
    _show_flash()
    try:
        prompts = client.list_prompts()
    except ServiceError as e:
        st.error(f"{e.code}: {e.message}")
        return
    if not prompts:
        st.info("Chưa có prompt nào.")
        return

    _render_table(prompts)
    by_id = {p["id"]: p for p in prompts}
    # Áp lựa chọn chờ (prompt vừa tạo) trước khi selectbox được tạo
    pending = st.session_state.pop(_PENDING_PICK, None)
    if pending is not None:
        st.session_state[_PICK_KEY] = pending
    if st.session_state.get(_PICK_KEY) not in by_id:
        st.session_state.pop(_PICK_KEY, None)
    picked = st.selectbox("Chọn prompt", list(by_id), key=_PICK_KEY,
                          format_func=lambda i: _label(by_id[i]))
    selected = by_id[picked]

    st.text_area("Nội dung prompt", value=selected["content"], height=300, disabled=True,
                 key=f"view_content_{picked}")
    if selected.get("note"):
        st.caption(f"Ghi chú: {selected['note']}")
    if not selected.get("is_active"):
        st.button("Kích hoạt", on_click=_activate, args=(client, picked))

    st.divider()
    _render_create_form(client, selected)
