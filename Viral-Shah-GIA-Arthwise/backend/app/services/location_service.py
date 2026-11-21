from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.models import MasterLocation

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry"
]

PRESEEDED_CITIES = [
    # Gujarat
    {"city": "Ahmedabad", "state": "Gujarat", "tier": "tier1"},
    {"city": "Surat", "state": "Gujarat", "tier": "tier1"},
    {"city": "Vadodara", "state": "Gujarat", "tier": "tier2"},
    {"city": "Rajkot", "state": "Gujarat", "tier": "tier2"},
    {"city": "Gandhinagar", "state": "Gujarat", "tier": "tier2"},
    {"city": "Bhavnagar", "state": "Gujarat", "tier": "tier2"},
    {"city": "Jamnagar", "state": "Gujarat", "tier": "tier2"},
    {"city": "Anand", "state": "Gujarat", "tier": "tier3"},
    {"city": "Bharuch", "state": "Gujarat", "tier": "tier3"},
    {"city": "Vapi", "state": "Gujarat", "tier": "tier3"},
    {"city": "Navsari", "state": "Gujarat", "tier": "tier3"},
    {"city": "Morbi", "state": "Gujarat", "tier": "tier3"},
    {"city": "Mehsana", "state": "Gujarat", "tier": "tier3"},
    {"city": "Valsad", "state": "Gujarat", "tier": "tier3"},
    {"city": "Porbandar", "state": "Gujarat", "tier": "tier3"},

    # Maharashtra
    {"city": "Mumbai", "state": "Maharashtra", "tier": "tier1"},
    {"city": "Pune", "state": "Maharashtra", "tier": "tier1"},
    {"city": "Nagpur", "state": "Maharashtra", "tier": "tier2"},
    {"city": "Thane", "state": "Maharashtra", "tier": "tier1"},
    {"city": "Nashik", "state": "Maharashtra", "tier": "tier2"},
    {"city": "Aurangabad (Chhatrapati Sambhajinagar)", "state": "Maharashtra", "tier": "tier2"},
    {"city": "Solapur", "state": "Maharashtra", "tier": "tier2"},
    {"city": "Kolhapur", "state": "Maharashtra", "tier": "tier2"},
    {"city": "Amravati", "state": "Maharashtra", "tier": "tier3"},
    {"city": "Navi Mumbai", "state": "Maharashtra", "tier": "tier1"},

    # Karnataka
    {"city": "Bengaluru", "state": "Karnataka", "tier": "tier1"},
    {"city": "Mysuru", "state": "Karnataka", "tier": "tier2"},
    {"city": "Hubballi-Dharwad", "state": "Karnataka", "tier": "tier2"},
    {"city": "Mangaluru", "state": "Karnataka", "tier": "tier2"},
    {"city": "Belagavi", "state": "Karnataka", "tier": "tier2"},

    # Tamil Nadu
    {"city": "Chennai", "state": "Tamil Nadu", "tier": "tier1"},
    {"city": "Coimbatore", "state": "Tamil Nadu", "tier": "tier2"},
    {"city": "Madurai", "state": "Tamil Nadu", "tier": "tier2"},
    {"city": "Tiruchirappalli", "state": "Tamil Nadu", "tier": "tier2"},
    {"city": "Salem", "state": "Tamil Nadu", "tier": "tier2"},
    {"city": "Tiruppur", "state": "Tamil Nadu", "tier": "tier2"},

    # Delhi NCR & Haryana
    {"city": "New Delhi", "state": "Delhi", "tier": "tier1"},
    {"city": "Gurugram", "state": "Haryana", "tier": "tier1"},
    {"city": "Faridabad", "state": "Haryana", "tier": "tier2"},
    {"city": "Panipat", "state": "Haryana", "tier": "tier3"},
    {"city": "Ambala", "state": "Haryana", "tier": "tier3"},
    {"city": "Karnal", "state": "Haryana", "tier": "tier3"},

    # Uttar Pradesh
    {"city": "Noida", "state": "Uttar Pradesh", "tier": "tier1"},
    {"city": "Greater Noida", "state": "Uttar Pradesh", "tier": "tier1"},
    {"city": "Ghaziabad", "state": "Uttar Pradesh", "tier": "tier2"},
    {"city": "Lucknow", "state": "Uttar Pradesh", "tier": "tier2"},
    {"city": "Kanpur", "state": "Uttar Pradesh", "tier": "tier2"},
    {"city": "Agra", "state": "Uttar Pradesh", "tier": "tier2"},
    {"city": "Varanasi", "state": "Uttar Pradesh", "tier": "tier2"},
    {"city": "Meerut", "state": "Uttar Pradesh", "tier": "tier2"},
    {"city": "Prayagraj", "state": "Uttar Pradesh", "tier": "tier2"},

    # Telangana & Andhra Pradesh
    {"city": "Hyderabad", "state": "Telangana", "tier": "tier1"},
    {"city": "Warangal", "state": "Telangana", "tier": "tier2"},
    {"city": "Visakhapatnam", "state": "Andhra Pradesh", "tier": "tier2"},
    {"city": "Vijayawada", "state": "Andhra Pradesh", "tier": "tier2"},
    {"city": "Guntur", "state": "Andhra Pradesh", "tier": "tier2"},

    # Rajasthan
    {"city": "Jaipur", "state": "Rajasthan", "tier": "tier1"},
    {"city": "Jodhpur", "state": "Rajasthan", "tier": "tier2"},
    {"city": "Kota", "state": "Rajasthan", "tier": "tier2"},
    {"city": "Udaipur", "state": "Rajasthan", "tier": "tier2"},
    {"city": "Bhiwadi", "state": "Rajasthan", "tier": "tier3"},

    # West Bengal
    {"city": "Kolkata", "state": "West Bengal", "tier": "tier1"},
    {"city": "Howrah", "state": "West Bengal", "tier": "tier2"},
    {"city": "Durgapur", "state": "West Bengal", "tier": "tier2"},
    {"city": "Asansol", "state": "West Bengal", "tier": "tier2"},
    {"city": "Siliguri", "state": "West Bengal", "tier": "tier3"},

    # Madhya Pradesh
    {"city": "Indore", "state": "Madhya Pradesh", "tier": "tier2"},
    {"city": "Bhopal", "state": "Madhya Pradesh", "tier": "tier2"},
    {"city": "Gwalior", "state": "Madhya Pradesh", "tier": "tier2"},
    {"city": "Jabalpur", "state": "Madhya Pradesh", "tier": "tier2"},

    # Punjab & Chandigarh
    {"city": "Chandigarh", "state": "Chandigarh", "tier": "tier2"},
    {"city": "Ludhiana", "state": "Punjab", "tier": "tier2"},
    {"city": "Amritsar", "state": "Punjab", "tier": "tier2"},
    {"city": "Jalandhar", "state": "Punjab", "tier": "tier2"},
    {"city": "Mohali", "state": "Punjab", "tier": "tier2"},

    # Kerala
    {"city": "Kochi", "state": "Kerala", "tier": "tier2"},
    {"city": "Thiruvananthapuram", "state": "Kerala", "tier": "tier2"},
    {"city": "Kozhikode", "state": "Kerala", "tier": "tier2"},
    {"city": "Thrissur", "state": "Kerala", "tier": "tier3"},

    # Others
    {"city": "Patna", "state": "Bihar", "tier": "tier2"},
    {"city": "Bhubaneswar", "state": "Odisha", "tier": "tier2"},
    {"city": "Cuttack", "state": "Odisha", "tier": "tier2"},
    {"city": "Guwahati", "state": "Assam", "tier": "tier2"},
    {"city": "Ranchi", "state": "Jharkhand", "tier": "tier2"},
    {"city": "Jamshedpur", "state": "Jharkhand", "tier": "tier2"},
    {"city": "Raipur", "state": "Chhattisgarh", "tier": "tier2"},
    {"city": "Dehradun", "state": "Uttarakhand", "tier": "tier2"},
    {"city": "Panaji", "state": "Goa", "tier": "tier3"},
    {"city": "Shimla", "state": "Himachal Pradesh", "tier": "tier3"},
    {"city": "Srinagar", "state": "Jammu and Kashmir", "tier": "tier2"},
    {"city": "Jammu", "state": "Jammu and Kashmir", "tier": "tier2"},
]

def seed_locations_if_empty(db: Session):
    count = db.query(MasterLocation).count()
    if count == 0:
        for item in PRESEEDED_CITIES:
            loc = MasterLocation(
                city=item["city"],
                state=item["state"],
                tier=item["tier"],
                is_custom=False
            )
            db.add(loc)
        db.commit()
