import requests, json

# Test schedules
r = requests.get("http://127.0.0.1:8000/api/schedules/1")
d = r.json()
print("Schedules keys:", list(d.keys()))
print("AR count:", len(d.get("ar", [])))
if d.get("ar"):
    print("AR first row keys:", list(d["ar"][0].keys()))
    print("AR first row:", json.dumps(d["ar"][0], indent=2))

print()

# Test notes
r2 = requests.get("http://127.0.0.1:8000/api/notes/1")
notes = r2.json()
print("Notes count:", len(notes))
for n in notes[:3]:
    tj = n.get("table_json")
    print(f"  Note {n['note_number']}: table_json={'YES len=' + str(len(tj)) if tj else 'NULL'}")
