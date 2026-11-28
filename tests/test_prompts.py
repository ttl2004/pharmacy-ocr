from ocr_baseline.profiles import DRUG_PROFILE
from ocr_baseline.prompts import builtin_prompt, missing_field_keys


def test_builtin_prompt_comes_from_drug_profile():
    name, content = builtin_prompt()
    assert name == DRUG_PROFILE.default_prompt_name
    assert content == DRUG_PROFILE.system_prompt


def test_missing_field_keys():
    assert missing_field_keys(DRUG_PROFILE.system_prompt) == []
    assert "chi_dinh" in missing_field_keys("chỉ có ten_thuoc")
