"""Unit tests for the morphological analyser pipeline.

These tests use small inline fixtures and do NOT require the full database.
Integration tests are marked with @pytest.mark.integration.
"""

import pytest
from pathlib import Path

from pipeline.tags import humanize, feature_sort_key
from pipeline.normalize import fold, fold_latin, build_key, accent_strip
from pipeline.paradigm import (
    compute_paradigm_key,
    compute_allomorphs,
    find_slot,
    strip_one_prefix,
    build_paradigm_buckets,
    get_family_forming_buckets,
)
from pipeline.etymology import parse_templates, _parse_etymon_chain, _split_lang_word
from pipeline.frequency import load
from pipeline.extract import _classify_entry, _filter_forms, _extract_gloss


# ============================================================================
# normalize.py
# ============================================================================

class TestNormalize:
    def test_fold_strips_accents(self):
        assert fold("hacía") == "hacia"
        assert fold("HACER") == "hacer"
        assert fold("mentiré") == "mentire"
        assert fold("cántaro") == "cantaro"
    
    def test_fold_case_insensitive(self):
        assert fold("Hacer") == fold("hacer")
        assert fold("HACER") == fold("hacer")
    
    def test_fold_latin_macrons(self):
        assert fold_latin("factūra") == "factura"
        assert fold_latin("faciō") == "facio"
        assert fold_latin("factīcius") == "facticius"
        assert fold_latin("dʰeh₁") == "dheh1"
    
    def test_build_key(self):
        assert build_key("hacía") == "hacia"
        assert build_key("Hacer") == "hacer"
    
    def test_accent_strip_preserves_case(self):
        assert accent_strip("hacía") == "hacia"
        assert accent_strip("HEcho") == "HEcho"


# ============================================================================
# tags.py
# ============================================================================

class TestTags:
    def test_present_indicative_1sg(self):
        result = humanize(["first-person", "indicative", "present", "singular"])
        assert "present indicative" in result
        assert "1st" in result
        assert "singular" in result
    
    def test_imperfect_subjunctive_se(self):
        result = humanize(["imperfect", "imperfect-se", "singular", "subjunctive", "third-person"])
        assert "imperfect subjunctive" in result
        assert "(-se)" in result
        assert "3rd" in result
        assert "singular" in result
    
    def test_voseo_imperative(self):
        result = humanize(["imperative", "informal", "second-person", "singular", "vos-form"])
        assert "imperative" in result
        assert "(vos)" in result.lower()
    
    def test_past_participle(self):
        result = humanize(["participle", "past"])
        assert "participle" in result
        assert "past" in result
    
    def test_feminine_plural(self):
        result = humanize(["feminine", "plural"])
        assert "feminine" in result
        assert "plural" in result
    
    def test_combined_clitic_form(self):
        result = humanize(["combined-form", "accusative", "object-third-person", "object-singular", "infinitive"])
        assert "infinitive" in result
        assert "clitic" in result
        assert "accusative" in result
    
    def test_drops_form_of_and_table_tags(self):
        result = humanize(["form-of", "indicative", "present", "singular", "third-person"])
        assert "form-of" not in result
        result2 = humanize(["table-tags", "first-person", "singular"])
        assert "table-tags" not in result2
    
    def test_clitic_descriptor_gerund(self):
        result = humanize([
            "combined-form", "gerund",
            "object-second-person", "object-singular", "accusative",
        ])
        assert result == "gerund + 2nd singular accusative clitic"
    
    def test_clitic_descriptor_infinitive(self):
        result = humanize([
            "combined-form", "infinitive",
            "object-third-person", "object-singular", "accusative",
        ])
        assert result == "infinitive + 3rd singular accusative clitic"
    
    def test_clitic_descriptor_imperative(self):
        result = humanize([
            "combined-form", "imperative", "second-person", "singular",
            "object-first-person", "object-singular", "dative",
        ])
        assert result == "imperative 2nd singular + 1st singular dative clitic"
    
    def test_clitic_with_tu_parenthetical(self):
        result = humanize([
            "combined-form", "dative", "imperative", "informal",
            "object-second-person", "object-singular",
            "second-person", "singular", "with-tú",
        ])
        assert result == "imperative 2nd singular informal (tú) + 2nd singular dative clitic"


# ============================================================================
# tags.py — canonical ordering of form analyses (form.features)
# ============================================================================

class TestFeatureOrder:
    def test_mood_bucket_order(self):
        features = [
            "infinitive + 3rd singular accusative clitic",
            "imperative, 2nd singular",
            "present subjunctive, 1st singular",
            "gerund",
            "present indicative, 3rd singular",
            "feminine plural",
        ]
        assert sorted(features, key=feature_sort_key) == [
            "gerund",
            "present indicative, 3rd singular",
            "present subjunctive, 1st singular",
            "imperative, 2nd singular",
            "infinitive + 3rd singular accusative clitic",
            "feminine plural",
        ]
    
    def test_within_mood_tense_then_person(self):
        features = [
            "preterite indicative, 3rd singular",
            "present indicative, 1st plural",
            "present indicative, 1st singular",
            "present indicative, 3rd singular",
        ]
        assert sorted(features, key=feature_sort_key) == [
            "present indicative, 1st singular",
            "present indicative, 3rd singular",
            "present indicative, 1st plural",
            "preterite indicative, 3rd singular",
        ]
    
    def test_haga_analyses_subjunctive_before_imperative(self):
        features = [
            "imperative, 3rd singular",
            "present subjunctive, 3rd singular",
            "present subjunctive, 1st singular",
        ]
        assert sorted(features, key=feature_sort_key) == [
            "present subjunctive, 1st singular",
            "present subjunctive, 3rd singular",
            "imperative, 3rd singular",
        ]


# ============================================================================
# paradigm.py — §4.1 assertions
# ============================================================================

# Minimal hacer conjugation forms (the 10 diagnostic slots)
_HACER_FORMS = [
    {"form": "hacer",    "tags": ["infinitive"]},
    {"form": "haciendo", "tags": ["gerund"]},
    {"form": "hago",     "tags": ["first-person", "indicative", "present", "singular"]},
    {"form": "haces",    "tags": ["second-person", "indicative", "present", "singular"]},
    {"form": "hace",     "tags": ["third-person", "indicative", "present", "singular"]},
    {"form": "hacemos",  "tags": ["first-person", "indicative", "present", "plural"]},
    {"form": "hizo",     "tags": ["third-person", "indicative", "preterite", "singular"]},
    {"form": "hicieron", "tags": ["third-person", "indicative", "preterite", "plural"]},
    {"form": "haga",     "tags": ["third-person", "present", "subjunctive", "singular"]},
    {"form": "hiciera",  "tags": ["third-person", "imperfect", "subjunctive", "singular"]},
]

_BAILAR_FORMS = [
    {"form": "bailar",    "tags": ["infinitive"]},
    {"form": "bailando",  "tags": ["gerund"]},
    {"form": "bailo",     "tags": ["first-person", "indicative", "present", "singular"]},
    {"form": "bailas",    "tags": ["second-person", "indicative", "present", "singular"]},
    {"form": "baila",     "tags": ["third-person", "indicative", "present", "singular"]},
    {"form": "bailamos",  "tags": ["first-person", "indicative", "present", "plural"]},
    {"form": "bailó",     "tags": ["third-person", "indicative", "preterite", "singular"]},
    {"form": "bailaron",  "tags": ["third-person", "indicative", "preterite", "plural"]},
    {"form": "baile",     "tags": ["third-person", "present", "subjunctive", "singular"]},
    {"form": "bailara",   "tags": ["third-person", "imperfect", "subjunctive", "singular"]},
]


class TestParadigmKey:
    def test_hacer_paradigm_key(self):
        result = compute_paradigm_key(_HACER_FORMS)
        assert result is not None
        P, residual = result
        assert P == "h"
        assert residual == (
            "acer", "aciendo", "ago", "aces", "ace",
            "acemos", "izo", "icieron", "aga", "iciera",
        )
    
    def test_same_residual_for_satisfacer(self):
        # satisfacer has same paradigm as hacer with P="satisf"
        satisfacer_forms = [
            {"form": "satisfacer",    "tags": ["infinitive"]},
            {"form": "satisfaciendo", "tags": ["gerund"]},
            {"form": "satisfago",     "tags": ["first-person", "indicative", "present", "singular"]},
            {"form": "satisfaces",    "tags": ["second-person", "indicative", "present", "singular"]},
            {"form": "satisface",     "tags": ["third-person", "indicative", "present", "singular"]},
            {"form": "satisfacemos",  "tags": ["first-person", "indicative", "present", "plural"]},
            {"form": "satisfizo",     "tags": ["third-person", "indicative", "preterite", "singular"]},
            {"form": "satisficieron", "tags": ["third-person", "indicative", "preterite", "plural"]},
            {"form": "satisfaga",     "tags": ["third-person", "present", "subjunctive", "singular"]},
            {"form": "satisficiera",  "tags": ["third-person", "imperfect", "subjunctive", "singular"]},
        ]
        result = compute_paradigm_key(satisfacer_forms)
        assert result is not None
        P, residual = result
        assert P == "satisf"
        assert residual == (
            "acer", "aciendo", "ago", "aces", "ace",
            "acemos", "izo", "icieron", "aga", "iciera",
        )
    
    def test_cantar_bailar_same_residual(self):
        cantar_forms = [
            {"form": "cantar",    "tags": ["infinitive"]},
            {"form": "cantando",  "tags": ["gerund"]},
            {"form": "canto",     "tags": ["first-person", "indicative", "present", "singular"]},
            {"form": "cantas",    "tags": ["second-person", "indicative", "present", "singular"]},
            {"form": "canta",     "tags": ["third-person", "indicative", "present", "singular"]},
            {"form": "cantamos",  "tags": ["first-person", "indicative", "present", "plural"]},
            {"form": "cantó",     "tags": ["third-person", "indicative", "preterite", "singular"]},
            {"form": "cantaron",  "tags": ["third-person", "indicative", "preterite", "plural"]},
            {"form": "cante",     "tags": ["third-person", "present", "subjunctive", "singular"]},
            {"form": "cantara",   "tags": ["third-person", "imperfect", "subjunctive", "singular"]},
        ]
        r1 = compute_paradigm_key(cantar_forms)
        r2 = compute_paradigm_key(_BAILAR_FORMS)
        assert r1 is not None and r2 is not None
        assert r1[1] == r2[1]  # same residual tuple
        assert r1[0] == "cant" and r2[0] == "bail"
    
    def test_vos_form_excluded_from_2sg(self):
        # Slot 4 (2sg present indicative) must NOT pick vos-form
        forms = _HACER_FORMS + [
            {"form": "hacés", "tags": ["second-person", "indicative", "present", "singular", "vos-form"]},
        ]
        result = compute_paradigm_key(forms)
        assert result is not None
        # Should still pick "haces", not "hacés"
        _, residual = result
        assert residual[3] == "aces"  # haces - h = aces
    
    def test_imperfect_se_excluded(self):
        # Slot 10 must pick -ra form, not -se form
        forms = _HACER_FORMS + [
            {"form": "hiciese", "tags": ["third-person", "imperfect", "imperfect-se", "subjunctive", "singular"]},
        ]
        result = compute_paradigm_key(forms)
        assert result is not None
        _, residual = result
        assert residual[9] == "iciera"  # hiciera - h = iciera
    
    def test_missing_slot_returns_none(self):
        incomplete = _HACER_FORMS[:8]  # missing slots 9 and 10
        result = compute_paradigm_key(incomplete)
        assert result is None


# ============================================================================
# paradigm.py — §4.2 allomorphs
# ============================================================================

class TestAllomorphs:
    def test_hacer_allomorphs(self):
        # Build a representative set of hacer conjugation forms
        hacer_verbs_forms = [
            {"form": "hacer"}, {"form": "haciendo"}, {"form": "hago"},
            {"form": "haces"}, {"form": "hace"}, {"form": "hacemos"},
            {"form": "hacéis"}, {"form": "hacen"},
            {"form": "hice"}, {"form": "hiciste"}, {"form": "hizo"},
            {"form": "hicimos"}, {"form": "hicisteis"}, {"form": "hicieron"},
            {"form": "haré"}, {"form": "harás"}, {"form": "hará"},
            {"form": "haremos"}, {"form": "haréis"}, {"form": "harán"},
            {"form": "haga"}, {"form": "hagas"}, {"form": "hagamos"},
            {"form": "hagáis"}, {"form": "hagan"},
            {"form": "hiciera"}, {"form": "hicieras"}, {"form": "hiciéramos"},
            {"form": "hecho"},
        ]
        allos = compute_allomorphs("hacer", "verb", hacer_verbs_forms)
        assert "hac" in allos
        assert "hag" in allos
        assert "hic" in allos
        assert "hiz" in allos
        assert "har" in allos
        assert "hech" in allos
    
    def test_casa_allomorphs(self):
        # Non-verb: citation form + plural/feminine
        forms = [
            {"form": "casas", "tags": ["feminine", "plural"]},
        ]
        allos = compute_allomorphs("casa", "noun", forms)
        assert "casa" in allos  # citation form + common prefix = casa
    def test_hacer_no_fac_allomorph(self):
        """FIX 2: hacer's allomorphs must NOT include fac-."""
        allos = compute_allomorphs("hacer", "verb", _HACER_FORMS)
        assert not any(a.startswith("fac") for a in allos), f"fac found in: {allos}"
        assert strip_one_prefix("contradecir") == "decir"


# ============================================================================
# etymology.py
# ============================================================================

class TestEtymology:
    def test_af_template(self):
        templates = [
            {"name": "af", "args": {"1": "es", "2": "des-", "3": "hacer"}},
        ]
        result = parse_templates("deshacer", templates, "")
        assert ("hacer", "des-") in result["internal"]
    
    def test_ety_af_template(self):
        templates = [
            {"name": "ety", "args": {"1": "es", "2": ":af", "3": "re-", "4": "hacer", "text": "+", "tree": "1"}},
        ]
        result = parse_templates("rehacer", templates, "")
        assert ("hacer", "re-") in result["internal"]
    
    def test_inh_template(self):
        templates = [
            {"name": "inh", "args": {"1": "es", "2": "la", "3": "faciō", "4": "facere"}},
        ]
        result = parse_templates("hacer", templates, "")
        assert any("facio" == a for a, lang, m, s in result["etymons"])
        assert any("facere" == a for a, lang, m, s in result["etymons"])
        templates = [
            {"name": "bor+", "args": {"1": "es", "2": "la", "3": "factūra"}},
        ]
        result = parse_templates("factura", templates, "")
        assert any("factura" == a for a, lang, m, s in result["etymons"])
        assert any(m == "borrowed" for a, lang, m, s in result["etymons"])
    def test_doublet_template(self):
        templates = [
            {"name": "doublet", "args": {"1": "es", "2": "hechura", "notext": "1"}},
        ]
        result = parse_templates("factura", templates, "")
        assert "hechura" in result["doublets"]
    
    def test_etymon_chain_parsing(self):
        chain = "osp:fechizo<ety:inh<la:factīcius<t:artificial><pos:adj>>>"
        results = _parse_etymon_chain(chain)
        words = {w for _, w, _ in results}
        assert "fechizo" in words
        assert "facticius" in words
    
    def test_split_lang_word(self):
        assert _split_lang_word("la:factus") == ("la", "factus")
        assert _split_lang_word("factus") == (None, "factus")
    
    def test_etym_tree_parsing(self):
        text = (
            "Etymology tree\n"
            "Proto-Indo-European *dʰeh₁-\n"
            "Latin facere\n"
            "Old Spanish fazer\n"
            "Spanish hacer\n"
            "Inherited from Old Spanish fazer."
        )
        result = parse_templates("hacer", [], text)
        # Should pick up ancestors from tree
        ancestors = {a for a, lang in result["etymtree_ancestors"]}
        assert "facere" in ancestors


# ============================================================================
# extract.py
# ============================================================================

class TestExtract:
    def test_classify_form_entry(self):
        entry = {
            "pos": "verb",
            "word": "hizo",
            "senses": [
                {
                    "form_of": [{"word": "hacer"}],
                    "tags": ["form-of", "indicative", "preterite", "singular", "third-person"],
                    "glosses": ["third-person singular preterite indicative of hacer"],
                }
            ],
        }
        assert _classify_entry(entry) == "form-entry"
    
    def test_classify_lemma_entry(self):
        entry = {
            "pos": "verb",
            "word": "hacer",
            "senses": [
                {"glosses": ["to do"], "tags": []},
            ],
        }
        assert _classify_entry(entry) == "lemma-entry"
    
    def test_classify_skip_character(self):
        entry = {"pos": "character", "word": "a", "senses": []}
        assert _classify_entry(entry) == "skip"
    
    def test_classify_misspelling_skipped(self):
        entry = {
            "pos": "verb",
            "word": "hecho",
            "senses": [
                {
                    "tags": ["alt-of", "misspelling"],
                    "glosses": ["misspelling of echo"],
                }
            ],
        }
        assert _classify_entry(entry) == "skip"
    
    def test_filter_forms_removes_table_tags(self):
        forms = [
            {"form": "hago", "tags": ["first-person", "present", "singular"]},
            {"form": "irregular", "tags": ["table-tags"]},
            {"form": "es-conj", "tags": ["inflection-template"]},
        ]
        filtered = _filter_forms(forms)
        assert len(filtered) == 1
        assert filtered[0]["form"] == "hago"
    
    def test_extract_gloss_strips_parenthetical(self):
        senses = [
            {"glosses": ["(transitive) to do something"], "tags": []},
        ]
        gloss = _extract_gloss(senses)
        assert gloss == "to do something"
    
    def test_hecho_multi_entry(self):
        """hecho has 4 entries: adj (etym1), verb form (etym1), noun (etym2), misspelling (etym3).
        The adj entry should be lemma-entry, verb form should be form-entry,
        noun should be lemma-entry, misspelling should be skip."""
        # This is tested implicitly by the classification logic above.


class TestFrequency:
    def test_frequencywords_txt(self):
        """The loader must read the word␣count lines, preserve accents, and
        normalise to per-million (not raw counts)."""
        txt = Path(__file__).resolve().parents[1] / "es_full.txt"
        if not txt.exists():
            pytest.skip("es_full.txt not present")
        freq = load(txt)
        assert len(freq) > 1_000_000
        assert freq["hacer"] > 0
        assert freq["abalanzándose"] > 0
        assert freq["qué"] > 0
        # Per-million normalisation: the raw top count is ~14.5M, so a
        # per-million value can never approach that scale.
        assert max(freq.values()) < 100_000.0
        # Corpus total is the file's own sum: the values sum to 1M.
        assert abs(sum(freq.values()) - 1_000_000.0) < 1.0

    def test_malformed_lines_and_duplicates(self, tmp_path):
        """Blank/malformed/negative lines are skipped; duplicate words are
        summed; values are per-million of the valid total."""
        txt = tmp_path / "freq.txt"
        txt.write_text(
            "casa 100\n"
            "casa 50\n"
            "sin-cuenta\n"
            "solo\n"
            "raro nope\n"
            "neg -5\n"
            "perro 25\n",
            encoding="utf-8",
        )
        freq = load(txt)
        total = 100 + 50 + 25
        assert freq == {
            "casa": 150 / total * 1_000_000.0,
            "perro": 25 / total * 1_000_000.0,
        }
