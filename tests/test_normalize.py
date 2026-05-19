import pytest

from research_collect.normalize import bib_key, normalize_record


class TestBibKey:
    def test_basic(self):
        assert bib_key(["Zhang Wei"], 2024, "Coupling Beam Behavior") == "wei2024coupling"

    def test_ascii_fold_diacritics(self):
        assert bib_key(["Müller, Hans"], 2023, "X-ray Methods") == "muller2023xray"

    def test_strip_punctuation_in_title(self):
        assert bib_key(["Smith Jane"], 2024, "(Re-)examining X") == "jane2024reexamining"


class TestNormalizeRecord:
    def test_authors_string_coerced_to_list(self):
        rec = normalize_record({"title": "T", "authors": "Zhang", "year": 2024})
        assert rec["authors"] == ["Zhang"]

    def test_optional_fields_default_to_empty(self):
        rec = normalize_record({"title": "T", "authors": ["A"], "year": 2024})
        assert rec["doi"] == ""
        assert rec["abstract"] == ""

    def test_missing_year_raises(self):
        with pytest.raises(ValueError, match="year"):
            normalize_record({"title": "T", "authors": ["A"]})

    def test_missing_authors_raises(self):
        with pytest.raises(ValueError, match="authors"):
            normalize_record({"title": "T", "year": 2024})

    def test_attaches_bibkey(self):
        rec = normalize_record({
            "title": "Coupling Beam", "authors": ["Zhang Wei"], "year": 2024,
        })
        assert rec["key"] == "wei2024coupling"

    def test_does_not_mutate_input(self):
        original = {"title": "T", "authors": "A", "year": 2024}
        normalize_record(original)
        assert original["authors"] == "A"
        assert "key" not in original
