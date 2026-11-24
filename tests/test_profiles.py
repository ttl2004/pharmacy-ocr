import pytest

from ocr_baseline.profiles import PROFILES, get_profile


def test_drug_fields_are_text():
    drug = get_profile("drug")
    result = drug.normalize({"ten_thuoc": "Methocarbamol", "chi_dinh": ["Đau cơ", "Co thắt"]})
    assert result["ten_thuoc"] == "Methocarbamol"
    assert result["chi_dinh"] == "Đau cơ\nCo thắt"
    assert len(result) == 16


def test_every_profile_title_field_exists():
    for profile in PROFILES.values():
        assert profile.title_field in profile.field_keys()


def test_unknown_profile():
    with pytest.raises(ValueError):
        get_profile("khong_ton_tai")
