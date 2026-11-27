"""Apply cell-level changes without round-tripping the company's native Excel model."""
import ast
import io
import os
import posixpath
import re
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree as ET
from openpyxl import load_workbook
from openpyxl.utils import coordinate_to_tuple, get_column_letter
from openpyxl.utils.datetime import to_excel
from sources import InputError

NS="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
def tag(name):
    return f"{{{NS}}}{name}"

def xml(data):
    return ET.fromstring(data,parser=ET.XMLParser(resolve_entities=False,no_network=True))

def encoded(root):
    return ET.tostring(root,encoding="UTF-8",xml_declaration=True,standalone=True)

def number(value):
    if isinstance(value, date):
        return Decimal(str(to_excel(value)))
    if isinstance(value,(int,float,Decimal)):
        return Decimal(str(value))
    if value is None or isinstance(value,str) and not value.startswith(("#","=")):
        return Decimal(0)
    raise InputError(f"Missing or invalid numeric dependency: {value!r}")

CELL=re.compile(r"(?:(?:'([^']+)'|(\[\d+\][\w-]+))!)?(\$?[A-Z]{1,3}\$?\d+)(?::(\$?[A-Z]{1,3}\$?\d+))?")


class NativeBook:
    def __init__(self, data, name):
        self.name=name
        with ZipFile(io.BytesIO(data)) as z:
            self.parts={n:z.read(n) for n in z.namelist()}
        self.values={}
        self.formulas={}
        self.edits=set()
        self.cache={}
        self.busy=set()
        self.links={}
        self.ext={}
        self.ext_updates={}
        self.link_files={}
        self.initial={}
        for formulas in (False,True):
            book=load_workbook(io.BytesIO(data),read_only=True,data_only=not formulas,keep_links=False)
            try:
                if name not in book.sheetnames:
                    raise InputError(f"The prior workbook needs the working sheet {name}.")
                for s in (book[name],) if formulas else book.worksheets:
                    target=self.values.setdefault(s.title,{})
                    for row in s.iter_rows():
                        for c in row:
                            if c.value is None:
                                continue
                            if formulas:
                                if c.data_type=="f":
                                    self.formulas[c.coordinate]=c.value
                            else:
                                target[c.coordinate]=c.value
            finally:
                book.close()
        self.initial=dict(self.values[name])
        self.original_formulas = frozenset(self.formulas)
        wb=xml(self.parts["xl/workbook.xml"])
        rid=next(s.get(f"{{{REL}}}id") for s in wb.find(tag("sheets")) if s.get("name")==name)
        rels={r.get("Id"):r.get("Target") for r in xml(self.parts["xl/_rels/workbook.xml.rels"])}
        def internal(target):
            return target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/"+target)
        self.sheet_part=internal(rels[rid])
        for i,e in enumerate(wb.findall(".//"+tag("externalReference")),1):
            part=internal(rels[e.get(f"{{{REL}}}id")])
            tree=xml(self.parts[part])
            book=tree.find(tag("externalBook"))
            if book is None:
                continue
            names=[s.get("val") for s in book.findall(".//"+tag("sheetName"))]
            self.links[i]=(part,names)
            for s in book.findall(".//"+tag("sheetData")):
                tab=names[int(s.get("sheetId"))]
                for c in s.iter(tag("cell")):
                    val=c.findtext(tag("v"))
                    if val is not None:
                        self.ext[(i,tab,c.get("r"))]=val

    def set(self, coord, value, formula=None):
        self.values[self.name][coord]=value
        self.formulas.pop(coord,None)
        if formula:
            self.formulas[coord]=formula
        self.edits.add(coord)

    def ext_value(self, link, sheet, coord, value):
        self.ext[(link,sheet,coord)]=value
        self.ext_updates.setdefault((link,sheet),{})[coord]=value

    def value(self, coord, sheet=None):
        sheet=sheet or self.name
        coord=coord.replace("$","")
        if sheet.startswith("["):
            num,tab=sheet[1:].split("]",1)
            key=(int(num),tab,coord)
            if key not in self.ext:
                raise InputError(f"Missing cached workbook dependency {sheet}!{coord}.")
            return Decimal(str(self.ext[key]))
        if sheet!=self.name or coord not in self.formulas:
            return number(self.values.get(sheet,{}).get(coord))
        if coord in self.cache:
            return self.cache[coord]
        f=self.formulas[coord]
        if "SUMIF(" in f and re.search(r"\[\d+\].*\$B:\$B",f):
            if coord not in self.initial:
                raise InputError(f"{coord} is missing its linked billable value.")
            return number(self.initial[coord])
        if coord in self.busy:
            raise InputError(f"Circular reference at {coord}.")
        self.busy.add(coord)
        def sub(match):
            target=match[1] or match[2] or sheet
            a=match[3].replace("$","")
            if not match[4]:
                return str(self.value(a,target))
            r1,c1=coordinate_to_tuple(a)
            r2,c2=coordinate_to_tuple(match[4].replace("$",""))
            return str(sum(self.value(f"{get_column_letter(c)}{r}",target)
                           for r in range(r1,r2+1) for c in range(c1,c2+1)))
        expr=CELL.sub(sub,f[1:])
        expr=re.sub(r"(\d+(?:\.\d+)?)%",r"(\1/100)",expr)
        def evaluate(node):
            if isinstance(node,ast.Constant) and type(node.value) in (int,float):
                return Decimal(str(node.value))
            if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
                val=evaluate(node.operand)
                return -val if isinstance(node.op,ast.USub) else val
            if isinstance(node,ast.BinOp):
                a,b=evaluate(node.left),evaluate(node.right)
                if isinstance(node.op,ast.Add):return a+b
                if isinstance(node.op,ast.Sub):return a-b
                if isinstance(node.op,ast.Mult):return a*b
                if isinstance(node.op,ast.Div):return a/b
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="SUM":
                return sum(evaluate(arg) for arg in node.args)
            raise InputError(f"Unsupported formula in {sheet}!{coord}: {f}")
        try:
            self.cache[coord]=evaluate(ast.parse(expr,mode="eval").body)
        finally:
            self.busy.remove(coord)
        return self.cache[coord]

    def export(self, out):
        out=Path(out).resolve()
        if out.suffix.lower()!=".xlsx" or out.exists():
            raise InputError("Choose a new .xlsx filename. The source and previous exports are protected.")
        parts=self.parts.copy()
        root=xml(parts[self.sheet_part])
        data=root.find(tag("sheetData"))
        rows={int(r.get("r")):r for r in data.findall(tag("row"))}
        cells={c.get("r"):c for c in data.iter(tag("c"))}
        def child(parent, name, **attrs):
            return ET.SubElement(parent,tag(name),**attrs)
        for a in sorted(self.edits|self.formulas.keys(),key=coordinate_to_tuple):
            c=cells.get(a)
            if c is None:
                r,col=coordinate_to_tuple(a)
                row=rows[r]
                c=ET.Element(tag("c"),r=a)
                pos=next((i for i,x in enumerate(row) if x.tag==tag("c") and coordinate_to_tuple(x.get("r"))[1]>col),len(row))
                row.insert(pos,c)
            for entry in list(c):
                if entry.tag in (tag("v"),tag("is"),tag("f")):
                    c.remove(entry)
            c.attrib.pop("t",None)
            if a in self.formulas:
                child(c,"f").text=self.formulas[a][1:]
                value=self.value(a)
            else:
                value=self.values[self.name][a]
            if isinstance(value,str):
                c.set("t","inlineStr")
                child(child(c,"is"),"t").text=value
            elif value is not None:
                child(c,"v").text=str(value)
        parts[self.sheet_part]=encoded(root)
        for (link,sheet),updates in self.ext_updates.items():
            part,names=self.links[link]
            root=xml(parts[part])
            node=next(s for s in root.iter(tag("sheetData")) if s.get("sheetId")==str(names.index(sheet)))
            for entry in list(node):
                node.remove(entry)
            extrows={}
            for a,v in sorted(updates.items(),key=lambda x:coordinate_to_tuple(x[0])):
                row,_=coordinate_to_tuple(a)
                if row not in extrows:
                    extrows[row]=child(node,"row",r=str(row))
                child(child(extrows[row],"cell",r=a),"v").text=str(v)
            parts[part]=encoded(root)
        for link,(part,names) in self.links.items():
            relpath=posixpath.join(posixpath.dirname(part),"_rels",posixpath.basename(part)+".rels")
            if relpath not in parts:
                continue
            rels=xml(parts[relpath])
            changed=False
            for rel in rels:
                target=rel.get("Target","")
                targetpath=self.link_files.get(link)
                if targetpath:
                    if rel.get("Id")=="rId1":
                        try: target=quote(os.path.relpath(targetpath,out.parent).replace("\\","/"),safe="/:")
                        except ValueError: target=targetpath.as_uri()
                    else: target=targetpath.as_uri()
                elif not urlsplit(target).scheme and not target.startswith(("\\","/")):
                    target=(self.baseline_path.parent/unquote(target)).resolve().as_uri()
                if target != rel.get("Target"):
                    changed=True
                    rel.set("Target",target)
            if changed:parts[relpath]=encoded(rels)
        self.write_audit(parts)
        fd,x=tempfile.mkstemp(prefix=".cf-",suffix=".xlsx",dir=out.parent)
        os.close(fd)
        try:
            with ZipFile(x,"w",ZIP_DEFLATED) as z:
                for name,content in parts.items():
                    z.writestr(name,content)
            with ZipFile(x) as z:
                if z.testzip():
                    raise InputError("Excel package verification failed.")
            if os.name=="nt":os.rename(x,out)
            else:os.link(x,out)
        finally:
            Path(x).unlink(missing_ok=True)
        return out

    def write_audit(self,parts):
        wb=xml(parts["xl/workbook.xml"])
        sheets=wb.find(tag("sheets"))
        relpath="xl/_rels/workbook.xml.rels"
        rels=xml(parts[relpath])
        types=xml(parts["[Content_Types].xml"])
        title="Refresh review"
        existing=next((s for s in sheets if s.get("name")==title),None)
        if existing is None:
            i=max(int(s.get("sheetId")) for s in sheets)+1
            j=i
            while f"xl/worksheets/sheet{j}.xml" in parts:j+=1
            part=f"xl/worksheets/sheet{j}.xml"
            ident="rIdCashFlowReview"
            while any(r.get("Id")==ident for r in rels):ident+="X"
            ET.SubElement(sheets,tag("sheet"),name=title,sheetId=str(i),attrib={f"{{{REL}}}id":ident})
            ET.SubElement(rels,rels[0].tag,Id=ident,Target=part[3:],Type=REL+"/worksheet")
            ET.SubElement(types,"{http://schemas.openxmlformats.org/package/2006/content-types}Override",
                          PartName="/"+part,ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml")
            parts["xl/workbook.xml"]=encoded(wb)
            parts[relpath]=encoded(rels)
            parts["[Content_Types].xml"]=encoded(types)
        else:
            rid=existing.get(f"{{{REL}}}id")
            target=next(r.get("Target") for r in rels if r.get("Id")==rid)
            part=target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/"+target)
        sheet=ET.Element(tag("worksheet"),nsmap={None:NS})
        view=ET.SubElement(ET.SubElement(sheet,tag("sheetViews")),tag("sheetView"),workbookViewId="0")
        ET.SubElement(view,tag("pane"),ySplit="1",topLeftCell="A2",activePane="bottomLeft",state="frozen")
        cols=ET.SubElement(sheet,tag("cols"))
        for n,width in ((1,50),(2,110)):
            ET.SubElement(cols,tag("col"),min=str(n),max=str(n),width=str(width),customWidth="1")
        data=ET.SubElement(sheet,tag("sheetData"))
        for i,values in enumerate(self.audit_rows,1):
            row=ET.SubElement(data,tag("row"),r=str(i))
            for j,value in enumerate(values,1):
                cell=ET.SubElement(row,tag("c"),r=f"{get_column_letter(j)}{i}",t="inlineStr")
                ET.SubElement(ET.SubElement(cell,tag("is")),tag("t")).text=str(value)
        parts[part]=encoded(sheet)
