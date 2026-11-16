import requests,feedparser,xml.etree.ElementTree as ET
url="https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
response=requests.get(url,timeout=25,headers={"User-Agent":"FinstockEventScope/1.0 (authorized API / RSS client)"})
feed=feedparser.parse(response.content)
print("bozo",feed.bozo,"error",str(feed.get("bozo_exception","")))
count=0
for entry in feed.entries:
    if not entry.get("link"):
        print("missing_link_entry",repr(dict(entry))[:1500]);count+=1
        if count==2:break
root=ET.fromstring(response.content)
count=0
for item in root.findall(".//item"):
    if not item.findtext("link"):
        print("missing_xml_link",ET.tostring(item,encoding="unicode")[:1500]);count+=1
        if count==2:break
