"""End-to-end smoke test for the schema-free pipeline using the sample files."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ingestion import FileIngestSpec, compile_divisions, detect_file_header
from core.summaries import classify_columns, group_summary, cross_tab_matrix, overall_totals
from core.query_engine import evaluate_filters, FilterRow
from core.export_engine import export_as_excel_table, export_as_csv, export_filtered_list_to_excel, suggested_filename

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
OUT_DIR = Path(__file__).parent.parent / "test_outputs"
OUT_DIR.mkdir(exist_ok=True)

print("=" * 70)
print("STEP 1: Header detection (row 1 or row 2 only, schema-free)")
print("=" * 70)
for f in sorted(SAMPLE_DIR.glob("*.xlsx")):
    row, conf, headers = detect_file_header(str(f))
    print(f"{f.name:45s} -> header row {row}  (confidence: {conf:6s})  headers: {headers[:4]}...")

print()
print("=" * 70)
print("STEP 2: Compile files AS-IS (no schema, no required fields)")
print("=" * 70)

specs = [FileIngestSpec(file_path=str(f), division=f.stem) for f in sorted(SAMPLE_DIR.glob("*.xlsx"))]
result = compile_divisions(specs)

print(f"Compiled at: {result.compiled_at}")
print(f"Total divisions: {result.total_divisions}")
print(f"Total rows read: {result.total_rows_read}")
print(f"Total rows rejected: {result.total_rows_rejected}  (should be 0 -- schema-free never rejects for missing columns)")
print(f"Compiled DataFrame shape: {result.compiled_df.shape}")
print()
for log in result.load_logs:
    print(f"  [{log.division}] file={log.file_name}")
    print(f"      header_row={log.header_row_detected} confidence={log.header_confidence}")
    print(f"      rows_read={log.rows_read}  columns={len(log.detected_columns)}  warnings={len(log.errors)}")
    print(f"      notes: {log.notes}")

df = result.compiled_df
print()
print("Compiled columns:", list(df.columns))

print()
print("=" * 70)
print("STEP 3: Dynamic summaries (auto-detected columns, no hard-coded fields)")
print("=" * 70)
numeric_cols, categorical_cols = classify_columns(df)
print("Numeric columns detected:", numeric_cols)
print("Categorical columns detected:", categorical_cols)

if categorical_cols:
    summ = group_summary(df, categorical_cols[0], numeric_cols[:2] if numeric_cols else None)
    print(f"\nGroup summary by '{categorical_cols[0]}':")
    print(summ.to_string(index=False))

totals = overall_totals(df, numeric_cols[:3] if numeric_cols else None)
print("\nOverall totals (first 3 numeric cols):", totals)

print()
print("=" * 70)
print("STEP 4: Query / Filter engine (arbitrary column names)")
print("=" * 70)
if categorical_cols:
    filters = [FilterRow(field=categorical_cols[0], operator="contains", value="Div")]
    filtered = evaluate_filters(df, filters)
    print(f"Filter ({categorical_cols[0]} contains 'Div'): {len(filtered)} matching rows out of {len(df)}")

print()
print("=" * 70)
print("STEP 5: Export")
print("=" * 70)
xlsx_path = export_as_excel_table(df, str(OUT_DIR / suggested_filename("August", 2026)))
print(f"Excel Table export: {xlsx_path}")

csv_path = export_as_csv(df, str(OUT_DIR / suggested_filename("August", 2026, "csv")))
print(f"CSV export: {csv_path}")

print()
print("ALL STEPS COMPLETED SUCCESSFULLY")
