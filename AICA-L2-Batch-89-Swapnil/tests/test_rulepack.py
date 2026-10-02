"""Rule-pack validation: the app must refuse to start on an invalid pack and
say which row failed; a law change is a YAML edit (close row, open row)."""
import shutil
from datetime import date

import pytest
import yaml

from engine import RulePackError, generate, load
from engine.rulepack import DEFAULT_DIR


@pytest.fixture()
def pack(tmp_path):
    d = tmp_path / "rulepack"
    shutil.copytree(DEFAULT_DIR, d)
    return d


def edit(path, fn):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_real_pack_loads(rp):
    assert rp.version and len(rp.rules) > 50
    assert rp.rule("DIR3KYC_ANNUAL").effective_to == date(2026, 3, 30)
    assert rp.rule("DIR3KYC_TRIENNIAL").effective_from == date(2026, 3, 31)
    assert all(not r.verified for r in rp.rules)
    assert len(rp.content_hash) == 64


def test_unknown_predicate_named(pack):
    edit(pack / "companies_annual.yaml", lambda d: d["rules"][3].update(applicability=["eval('1')"]))
    with pytest.raises(RulePackError, match=r"companies_annual.yaml: rule AOC4: unknown predicate"):
        load(pack)


def test_bad_field_names_row(pack):
    edit(pack / "llp.yaml", lambda d: d["rules"][1].update(anchor="SOMETIME"))
    with pytest.raises(RulePackError) as e:
        load(pack)
    assert "llp.yaml" in str(e.value) and "code=LLP_FORM11" in str(e.value)


@pytest.mark.parametrize("mutate,msg", [
    (lambda r: r.update(entity_types=["TRUST"]), "unknown entity type"),
    (lambda r: r.update(effective_to="2000-01-01"), "effective_to is before"),
    (lambda r: r.update(anchor="CALENDAR_FIXED"), "needs 'fixed"),
    (lambda r: r.update(recurrence="event"), "needs event_types"),
    (lambda r: r.update(variant="guess_variant"), "unknown variant"),
    (lambda r: r.update(surprise=1), "Extra inputs"),
])
def test_rule_validations(pack, mutate, msg):
    edit(pack / "companies_onetime.yaml", lambda d: mutate(d["rules"][0]))
    with pytest.raises(RulePackError, match=msg):
        load(pack)


def test_duplicate_codes(pack):
    edit(pack / "llp.yaml", lambda d: d["rules"].append(dict(d["rules"][0])))
    with pytest.raises(RulePackError, match="Duplicate rule codes"):
        load(pack)


def test_missing_files_and_yaml_errors(pack):
    (pack / "schemes.yaml").write_text("schemes: [unclosed", encoding="utf-8")
    with pytest.raises(RulePackError, match="YAML syntax error"):
        load(pack)
    (pack / "schemes.yaml").unlink()
    with pytest.raises(RulePackError, match="missing: schemes.yaml"):
        load(pack)
    (pack / "VERSION").unlink()
    with pytest.raises(RulePackError, match="VERSION"):
        load(pack)


def test_fee_and_scheme_validation(pack):
    edit(pack / "schemes.yaml", lambda d: d["schemes"][0].update(rule_codes=["NOPE"]))
    with pytest.raises(RulePackError, match="unknown rule codes"):
        load(pack)


def test_fee_file_validation(pack):
    edit(pack / "fees.yaml", lambda d: d["tables"].pop(0))
    with pytest.raises(RulePackError, match="missing fee tables"):
        load(pack)
    edit(pack / "fees.yaml", lambda d: d.update(domain="other"))
    with pytest.raises(RulePackError, match="fees.yaml"):
        load(pack)


def test_scheme_file_validation(pack):
    edit(pack / "schemes.yaml", lambda d: d["schemes"][0].update(kind="AMNESTY"))
    with pytest.raises(RulePackError, match="schemes.yaml"):
        load(pack)


def test_lookup_errors(rp):
    with pytest.raises(RulePackError):
        rp.rule("NOPE")
    with pytest.raises(RulePackError):
        rp.threshold("SMALL_COMPANY", date(2000, 1, 1))
    with pytest.raises(RulePackError):
        rp.fee_table("LLP_MATRIX", date(2020, 1, 1))


def test_law_change_is_a_yaml_edit(pack, demo):
    """Demonstrates §6.2: publishing a changed rule moves the due date with no code change."""
    alpha = demo["alpha"]
    before = {s.key: s for s in generate(alpha["entity"], alpha["facts"], [], [], load(pack), date(2026, 9, 25),
                                         period_flags=alpha["flags"])}
    edit(pack / "companies_onetime.yaml", lambda d: next(r for r in d["rules"] if r["code"] == "INC20A")
         .update(offset={"days": 90}))
    (pack / "VERSION").write_text("test-2", encoding="utf-8")
    rp2 = load(pack)
    after = {s.key: s for s in generate(alpha["entity"], alpha["facts"], [], [], rp2, date(2026, 9, 25),
                                        period_flags=alpha["flags"])}
    k = "1:INC20A:ONCE"
    assert before[k].due_date == date(2026, 7, 19) and after[k].due_date == date(2026, 4, 20)
    assert after[k].rule_version == "test-2" and after[k].rule_hash != before[k].rule_hash
