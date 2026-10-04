# test_run.py
import os
import sys
from datetime import datetime, timedelta

# Fix console encoding for Windows cp1252
sys.stdout.reconfigure(encoding='utf-8')

from travel_tails import (
    resolve_transit_details,
    resolve_destination_circuit,
    download_destination_photos,
    build_package_pdf,
    DESTINATION_CIRCUITS,
    DESTINATION_REAL_PHOTOS
)

print("=" * 75)
print("TEST 1: Bhutan 5-Day Circuit (Ex-Bangalore)")
print("=" * 75)

circuit_5d = resolve_destination_circuit("Bhutan", 5, "2026-12-20", "Bangalore")
print(f"Destination: {circuit_5d['country']}")
print(f"Circuit Title: {circuit_5d['circuit_title']}")
print(f"Transit Mode: {circuit_5d['transit_mode']}")
print(f"Stay Summary: {circuit_5d['stay_summary_str']}")
print(f"\nFamous Towns Included ({len(circuit_5d['cities'])}):")
for c in circuit_5d['cities']:
    h = c['hotels']['value']
    print(f"  * Town: {c['city_name']} ({c['nights']}N) [{c['checkin_str']} to {c['checkout_str']}]")
    print(f"    Hotel: {h['name']} | Address: {h['address']}")

print(f"\nDay-by-Day Authentic Schedule ({len(circuit_5d['day_plan'])} Days):")
for d in circuit_5d['day_plan']:
    print(f"  Day {d['num']} ({d['date_str']}) [{d['city_hub']}]: {d['title']}")
    print(f"    Attractions: {', '.join(d['major_attractions'])}")

print(f"\nFlight Sectors ({len(circuit_5d['flights'])} Sectors):")
for s in circuit_5d['flights']:
    print(f"  [{s.get('transit_type').upper()}] {s.get('carrier')} ({s.get('service_num')}):")
    print(f"    From: {s.get('from_name')} - {s.get('from_details')}")
    print(f"    To:   {s.get('to_name')} - {s.get('to_details')}")

print("\n" + "=" * 75)
print("TEST 2: Bhutan 7-Day Circuit (Ex-Bangalore)")
print("=" * 75)

circuit_7d = resolve_destination_circuit("Bhutan", 7, "2026-12-20", "Bangalore")
print(f"Stay Summary: {circuit_7d['stay_summary_str']}")
print(f"\nDay-by-Day Authentic Schedule ({len(circuit_7d['day_plan'])} Days):")
for d in circuit_7d['day_plan']:
    print(f"  Day {d['num']} ({d['date_str']}) [{d['city_hub']}]: {d['title']}")
    print(f"    Attractions: {', '.join(d['major_attractions'])}")

print("\n" + "=" * 75)
print("TEST 3: Photo Acquisition for Bhutan (Verifying Exact Image Correlation)")
print("=" * 75)

save_dir = os.path.abspath("test_bhutan_output")
os.makedirs(save_dir, exist_ok=True)
photos = download_destination_photos("Bhutan", circuit_5d['day_plan'], circuit_5d['cities'], save_dir, lambda m: print(f"  {m}"))

print(f"\nHero Banner Photo: {photos['banner_path']} (Size: {os.path.getsize(photos['banner_path'])} bytes)")
print(f"Day Thumbnails ({len(photos['day_thumbs'])}):")
for idx, p in enumerate(photos['day_thumbs']):
    d = circuit_5d['day_plan'][idx]
    print(f"  * Day {d['num']} ({d['photo_caption']}): {os.path.basename(p)} ({os.path.getsize(p)} bytes)")
print(f"Hotel Thumbnails ({len(photos['hotel_thumbs'])}):")
for idx, p in enumerate(photos['hotel_thumbs']):
    c = circuit_5d['cities'][idx]
    h = c['hotels']['value']['name']
    print(f"  * Hotel {idx+1} ({c['city_name']} - {h}): {os.path.basename(p)} ({os.path.getsize(p)} bytes)")

print("\n" + "=" * 75)
print("TEST 4: Generating Executive PDF Itinerary for Bhutan (5 Days)")
print("=" * 75)

package_data = {
    "tier_key": "value",
    "tier_name": "Premium Cultural Heritage",
    "tier_badge": "⭐ Most Recommended",
    "tagline": "4-Star & 5-Star Heritage Resorts, Paro Taktsang Special Permits & Private SUV Transfers",
    "destination": "Bhutan",
    "source": "Bangalore",
    "circuit_title": circuit_5d["circuit_title"],
    "overview": circuit_5d["overview"],
    "tour_highlights": circuit_5d["tour_highlights"],
    "stay_summary_str": circuit_5d["stay_summary_str"],
    "cities": circuit_5d["cities"],
    "day_plan": circuit_5d["day_plan"],
    "flights": circuit_5d["flights"],
    "transit_mode": circuit_5d["transit_mode"],
    "days": 5,
    "dep_date": "20 Dec 2026",
    "ret_date": "24 Dec 2026",
    "traveller_name": "Dr. Ananya & Family",
    "adults": 2,
    "children": 0,
    "pax": 2,
    "rooms": 1,
    "adult_per_pax": 68500,
    "child_per_pax": 0,
    "net_per_pax": 68500,
    "num_rooms": 1,
    "total_cost": 137000
}

pdf_path = os.path.join(save_dir, "Travel_Tails_Bhutan_5Days_Executive.pdf")
build_package_pdf(package_data, pdf_path, photos, save_dir)

print(f"\n🎉 Successfully compiled PDF: {pdf_path}")
print(f"File Size: {os.path.getsize(pdf_path)} bytes")
print("=" * 75)
