"""Resolve the dated reports, prior workbook and locally recorded decisions."""
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sources import InputError, discover

DATE = r"(\d{2}-\d{2}-\d{4})"


def parsed(text, pattern):
    match = re.fullmatch(pattern, text, re.I)
    if match:
        try:
            return datetime.strptime(match[1], "%d-%m-%Y").date()
        except ValueError:
            raise InputError(f"Invalid calendar date in '{text}'.") from None


def week_date(folder):
    return parsed(folder.name, r"(?:\d+\.\s*)?" + DATE)


def prior_folders(folder):
    if not week_date(folder):
        return []
    month = folder.parent
    if month.parent.name.isdigit() and len(month.parent.name) == 4:
        year = month.parent
        years = [year, year.parent / str(int(year.name)-1)]
        containers = [m for y in years if y.is_dir() and not y.is_symlink()
                      for m in y.iterdir() if m.is_dir() and not m.is_symlink() and re.match(r"^(0[1-9]|1[0-2])\.",m.name)]
    else:
        containers = [month]
    matches = [(week_date(p), p) for m in containers for p in m.iterdir()
               if p.is_dir() and not p.is_symlink() and week_date(p) and week_date(p)<week_date(folder)]
    return sorted(matches, key=lambda pair:pair[0], reverse=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_at(folder):
    path = folder / "cash-flow-refresh.json"
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError) as exc:
            raise InputError(f"{path.name} — could not read the refresh record: {exc}") from exc
    return {}


@dataclass
class WeeklyFiles:
    paths: dict
    baseline: Path
    snapshot: object
    record: dict
    prior_folder: object
    original: Path


def weekly_files(folder, chosen=None):
    folder=Path(folder).resolve()
    paths=discover(folder, require_demo_model=False)
    record=manifest_at(folder)
    stamps={parsed(p.stem, r".*?-\s*"+DATE) for p in paths.values()} - {None}
    if len(stamps)>1:
        raise InputError("Reports contain different snapshot dates. Select files from one reporting run.")
    stamp=next(iter(stamps),None) or week_date(folder)
    if not stamp and record.get("requestDate"):
        stamp=datetime.fromisoformat(record["requestDate"]).date()
    if not stamp:
        raise InputError("Use a dated weekly folder or date-stamped source reports to distinguish the output from the prior workbook.")
    def candidates(path):
        result=[]
        for f in path.iterdir():
            day=parsed(f.name,r"CF\s*-\s*"+DATE+r"\.xlsx")
            if f.is_file() and day and day < stamp:
                result.append((day,f))
        return sorted(result,key=lambda pair:pair[0],reverse=True)
    previous=prior_folders(folder)
    prior=None
    local=candidates(folder)
    target_name=f"CF-{stamp:%d-%m-%Y}.xlsx"
    if chosen:
        seed=Path(chosen).resolve()
        if not seed.is_file() or not parsed(seed.name,r"CF\s*-\s*"+DATE+r"\.xlsx") or parsed(seed.name,r"CF\s*-\s*"+DATE+r"\.xlsx")>=stamp:
            raise InputError("Choose a prior dated CF-DD-MM-YYYY.xlsx workbook.")
        prior=seed.parent if seed.parent!=folder else None
    elif local:
        if len(local)>1:
            raise InputError("Multiple prior CF workbooks in the selected folder. Use Choose baseline to select the intended one.")
        seed=local[0][1]
    elif previous:
        d,prior=previous[0]
        if len(previous)>1 and previous[1][0]==d:
            raise InputError("Two preceding weekly folders have the same date. Use Choose baseline.")
        eligible=candidates(prior)
        past=manifest_at(prior)
        if past.get("status")=="validated":
            fname=Path(past.get("finalOutputPath","")).name
            eligible=[pair for pair in eligible if pair[1].name.casefold()==fname.casefold()]
        if len(eligible)!=1:
            raise InputError(f"Cannot identify a single finalized workbook in {prior.name}. Use Choose baseline.")
        seed=eligible[0][1]
        if past.get("status")=="validated" and past.get("finalOutputHash","").lower()!=digest(seed):
            raise InputError(f"{seed.name} has changed since its recorded refresh. Use Choose baseline to confirm the intended version.")
    else:
        raise InputError("Previous workbook missing. Add the prior CF-DD-MM-YYYY.xlsx to this folder or use Choose baseline.")
    if not prior and previous:
        corresponding=previous[0][1]/seed.name
        if corresponding.is_file() and digest(corresponding)==digest(seed):
            prior=corresponding.parent
    return WeeklyFiles(paths,seed,stamp,record,prior,folder/target_name)
