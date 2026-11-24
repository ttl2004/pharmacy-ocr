"""Hàm dùng chung cho các route."""
from .errors import api_error


def resolve_prompt(state, prompt_id: int | None):
    """Id không tồn tại thì báo not_found; None thì dùng prompt đang kích hoạt."""
    if prompt_id is None:
        return state.prompts.get_active()
    prompt = state.prompts.get(prompt_id)
    if prompt is None:
        raise api_error("not_found", f"Không tìm thấy prompt {prompt_id}")
    return prompt
