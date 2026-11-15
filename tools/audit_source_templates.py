"""Read-only template audit. No VBA execution; no literal identities/caches exported."""
import hashlib,json,re,sys
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.utils.cell import column_index_from_string

def audit(path):
    wb=load_workbook(path,keep_vba=True,data_only=False);cached=load_workbook(path,keep_vba=True,data_only=True)
    result=dict(filename=Path(path).name,sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),named_ranges=list(wb.defined_names),sheets=[])
    try:
        for sh in wb:
            areas=[]
            for a,r,b,s in re.findall(r'\$([A-Z]+)\$(\d+):\$([A-Z]+)\$(\d+)',str(sh.print_area)):
                areas.append((column_index_from_string(a),int(r),column_index_from_string(b),int(s)))
            cells=[c for row in sh for c in row if c.value is not None]
            outside=[c.coordinate for c in cells if areas and not any(a<=c.column<=b and r<=c.row<=s for a,r,b,s in areas)]
            formulas={}
            for c in cells:
                if c.data_type!='f':continue
                formula=c.value
                # A source-specific income expression contains private financial
                # constants. Keep its structure, not source amounts, in this audit.
                if re.fullmatch(r'=\d+(?:\.\d+)?(?:[+*/-]\d+(?:\.\d+)?)+',formula):formula='=[SOURCE_AMOUNT]+[SOURCE_AMOUNT] (literal financial inputs redacted)'
                formulas[c.coordinate]=formula
            result['sheets'].append(dict(name=sh.title,state=sh.sheet_state,dimensions=sh.calculate_dimension(),print_area=str(sh.print_area),merged=list(map(str,sh.merged_cells.ranges)),populated=len(cells),styled_empty_cells={c.coordinate:dict(bold=bool(c.font.bold),style_id=c.style_id,number_format=c.number_format) for row in sh for c in row if c.value is None and c.has_style},row_heights={i:d.height for i,d in sh.row_dimensions.items() if d.height},column_widths={i:d.width for i,d in sh.column_dimensions.items()},cell_inventory={c.coordinate:dict(type=c.data_type,bold=bool(c.font.bold),number_format=c.number_format) for c in cells},formulas=formulas,cache_types={c.coordinate:type(cached[sh.title][c.coordinate].value).__name__ for c in cells if c.data_type=='f'},bold_cells=[c.coordinate for c in cells if c.font.bold],outside_print_cells=outside,hidden_rows=[i for i,d in sh.row_dimensions.items() if d.hidden],hidden_columns=[i for i,d in sh.column_dimensions.items() if d.hidden],broken_ref_formulas=[c.coordinate for c in cells if c.data_type=='f' and '#REF!' in c.value]))
    finally:wb.close();cached.close()
    return result

if __name__=='__main__':
    if len(sys.argv)<3:raise SystemExit('Usage: audit_source_templates.py output.json source1.xlsm [source2.xlsm ...]')
    Path(sys.argv[1]).write_text(json.dumps([audit(Path(p)) for p in sys.argv[2:]],indent=2),encoding='utf-8')
