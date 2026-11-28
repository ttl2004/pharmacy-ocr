"""Trang "Thống kê": số lượng, điểm đánh giá, tỉ lệ sửa theo nhóm, và quan hệ rating - số trường bị sửa."""
import streamlit as st

from .api_client import OcrServiceClient, ServiceError
from .field_labels import FIELD_LABELS

_GROUP_BY = ["prompt", "engine", "model", "source"]
_LABELS = dict(FIELD_LABELS)


def _group_rows(groups: list[dict]) -> list[dict]:
    """Mỗi nhóm một dòng: key, count, avg_rating, kèm status_counts tách thành cột."""
    rows = []
    for g in groups:
        row = {"key": g.get("key"), "count": g.get("count"), "avg_rating": g.get("avg_rating")}
        for status, n in (g.get("status_counts") or {}).items():
            row[status] = n
        rows.append(row)
    return rows


def _render_edit_rates(groups: list[dict]) -> None:
    """Mỗi nhóm một expander liệt kê tỉ lệ sửa theo từng trường."""
    for g in groups:
        rates = g.get("edit_rate") or {}
        with st.expander(f"Tỉ lệ sửa - {g.get('key')}"):
            if not rates:
                st.caption("Chưa có dữ liệu.")
                continue
            st.dataframe([{"Trường": _LABELS.get(k, k), "Tỉ lệ sửa": v} for k, v in rates.items()])


def render(client: OcrServiceClient) -> None:
    st.header("Thống kê")
    group_by = st.selectbox("Nhóm theo", _GROUP_BY)
    try:
        data = client.stats(group_by)
    except ServiceError as e:
        st.error(f"{e.code}: {e.message}")
        return

    groups = data.get("groups") or []
    if not groups:
        st.info("Chưa có dữ liệu thống kê.")
    else:
        st.subheader("Theo nhóm")
        st.dataframe(_group_rows(groups))
        _render_edit_rates(groups)

    st.subheader("Rating và số trường bị sửa")
    rating_rows = data.get("rating_vs_edits") or []
    if rating_rows:
        st.dataframe(rating_rows)
    else:
        st.caption("Chưa có đánh giá nào.")
