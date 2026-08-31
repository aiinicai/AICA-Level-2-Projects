"""
Main Orchestrator — resumable version, ONE CALL PER PROCESS.
Each process now covers all 5 COSO components in a single AI call,
drastically cutting total calls (and runtime) versus the old
process x component loop.
"""

import os
import json
from sop_reader import read_sop
from process_identifier import identify_processes
from racm_generator import generate_racm_for_process
from excel_writer import write_racm_to_excel, write_racm_to_csv

OUTPUT_FOLDER = "output"
PROGRESS_FILE = os.path.join(OUTPUT_FOLDER, "progress_v2.json")


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"completed_processes": [], "rows": []}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


def run_pipeline(sop_path):
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    excel_path = os.path.join(OUTPUT_FOLDER, "RACM_Output.xlsx")
    csv_path = os.path.join(OUTPUT_FOLDER, "RACM_Output.csv")

    progress = load_progress()
    all_rows = progress["rows"]
    completed_processes = set(progress["completed_processes"])

    if completed_processes:
        print(f"Resuming previous run — {len(completed_processes)} process(es) already completed.\n")

    print("Reading SOP file...")
    sop_text = read_sop(sop_path)
    print(f"  Extracted {len(sop_text)} characters.\n")

    print("Identifying distinct processes in the document...")
    processes = identify_processes(sop_text)
    print(f"  Found {len(processes)} process(es): {processes}\n")

    total_steps = len(processes)
    step = 0

    for process_name in processes:
        step += 1

        if process_name in completed_processes:
            print(f"[{step}/{total_steps}] SKIPPED (already done): '{process_name}'")
            continue

        print(f"[{step}/{total_steps}] Generating full RACM for process: '{process_name}' "
              f"(all 5 COSO components in one pass)...")

        try:
            rows = generate_racm_for_process(sop_text, process_name)
            print(f"  -> {len(rows)} row(s) generated.")
            all_rows.extend(rows)
            completed_processes.add(process_name)
        except Exception as e:
            print(f"  -> [Warning] Skipped due to error: {e}")

        progress["rows"] = all_rows
        progress["completed_processes"] = list(completed_processes)
        save_progress(progress)
        _finalize_and_save(all_rows, excel_path, csv_path)

    print(f"\nDONE. Total rows generated: {len(all_rows)}")
    print(f"Final files: {excel_path} and {csv_path}")


def _finalize_and_save(rows, excel_path, csv_path):
    for i, row in enumerate(rows, start=1):
        row["Sr. No."] = i
    write_racm_to_excel(rows, excel_path)
    write_racm_to_csv(rows, csv_path)


if __name__ == "__main__":
    test_path = input("Paste the full path to your SOP .docx file: ").strip().strip('"')
    print("\nStarting RACM generation (v2 — one call per process). This is resumable;")
    print("if interrupted, re-run this script with the same file to skip completed processes.\n")
    run_pipeline(test_path)