"""Read-only endpoint check. No access-control workarounds or stored market payloads."""
import json
from pathlib import Path
import sys
import urllib.request
import xml.etree.ElementTree as ET

URLS={
    "sebi":"https://www.sebi.gov.in/sebirss.xml",
    "rbi_press":"https://rbi.org.in/pressreleases_rss.xml",
    "rbi_notifications":"https://rbi.org.in/notifications_rss.xml",
    "nse_announcements":"https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml",
    "nse_circulars":"https://nsearchives.nseindia.com/content/RSS/Circulars.xml",
}
results=[]
for name,url in URLS.items():
    row={"source":name,"url":url}
    try:
        request=urllib.request.Request(url,headers={"User-Agent":"FinstockEventScope/1.0 (RSS reader; endpoint verification)"})
        with urllib.request.urlopen(request,timeout=25) as response:
            body=response.read(5_000_001)
            root=ET.fromstring(body)
            items=root.findall(".//item")
            row.update(status=response.status,content_type=response.headers.get("Content-Type"),items=len(items),item_fields=sorted({child.tag for item in items[:3] for child in item}))
    except Exception as exc:
        row["error"]=str(exc)
    results.append(row)
    print(json.dumps(row),flush=True)
if len(sys.argv)>1:
    Path(sys.argv[1]).parent.mkdir(parents=True,exist_ok=True)
    Path(sys.argv[1]).write_text(json.dumps(results,indent=2),encoding="utf-8")

