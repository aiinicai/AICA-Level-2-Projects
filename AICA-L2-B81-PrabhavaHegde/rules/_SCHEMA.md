# Control Catalogue Schema

One YAML file per DPDP Rule, or per group of Act sections that no single Rule covers
(`s04_consent.yaml`, rule_id `S4`). Each file holds a `rule` block and a `controls` list.

## File-level keys

| Key | Type | Meaning |
|---|---|---|
| `rule_id` | str | Short code, e.g. `R6` or `S4`; one capital letter followed by digits |
| `rule_ref` | str | Full citation printed in the report |
| `rule_title` | str | Plain-language heading |
| `citation_status` | str | Required. `verified` or `pending`; see Citation status below |
| `controls` | list | The controls under this rule |

## Control keys

| Key | Type | Required | Meaning |
|---|---|---|---|
| `id` | str | yes | Unique across all files, e.g. `R6.5` |
| `title` | str | yes | One-line control name |
| `question` | str | yes | Asked in the assessment UI |
| `guidance` | str | yes | Shown on hover; tells the assessor what "Present" looks like |
| `evidence_required` | list[str] | yes | Artefacts the assessor must attach |
| `weight` | int 1-5 | yes | Contribution to score |
| `severity_if_absent` | enum | yes | `low` / `medium` / `high` / `critical` |
| `applies_when` | dict | yes | Gating conditions, see below |
| `observation` | str | yes | Offline fallback text when status is Absent |
| `impact` | str | yes | Offline fallback consequence text |
| `action` | str | yes | Offline fallback remediation text |
| `citation_status` | str | no | `verified` or `pending`; overrides the file's value for this control |

## Citation status

- `verified` means the citation was checked against the gazette text, and the check is
  recorded in a comment above the key. `pending` means it was not.
- A reference that cites both a Rule and a section of the Act is `verified` only when both
  were checked against their gazette texts.
- Every rule file must declare `citation_status`. A file without it, or with any other
  value, fails to load, and the error names the file.
- The ledger shows "Citation pending verification" beside each control whose status is
  `pending`. Which controls carry the marker is decided only here, never in code.
- `rule_id` is one capital letter followed by digits: `R` for a DPDP Rule, `S` for a
  section of the Act. The digits order the groups. A malformed
  `rule_id` fails to load.

## Scoring rules

- Status is one of `Present` (1.0), `Partial` (0.5), `Absent` (0.0).
- **Evidence gate:** any control with `weight >= 4` scores 0.0 unless at least one
  evidence file is attached, whatever status the assessor selected.
- Score = sum(weight x factor) / sum(weight of applicable controls) x 100.
- Controls excluded by `applies_when` are dropped from both numerator and denominator.

## applies_when

```yaml
applies_when:
  role: [fiduciary, processor]   # engagement role determined in role.py
  condition: processes_children  # optional; a named flag on the client profile
```

Omit `condition` when the control always applies to the listed roles.

## Report mapping

The three template fields feed the Word report columns directly:

`observation` -> Observation
`impact` -> Impact
`action` -> Further Actions
(Management Response is captured in the UI, not in the catalogue.)

When an AI provider is configured, these three fields are replaced by generated text
and the catalogue values become the fallback. The AI receives only `id`, `title`,
`status` and `weight`. It never receives client data or evidence content.
