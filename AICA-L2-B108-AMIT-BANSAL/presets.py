"""
Preset scenarios for Netcrafty financial model.
Allows one-click scenario testing for e-commerce and D2C brands.
"""

from typing import Dict, Any

PRESETS: Dict[str, Dict[str, Any]] = {
    "Default Baseline (Seed)": {
        "description": "The default starting point from the Netcrafty dashboard: 50 website leads, zero WhatsApp leads, high shared overhead.",
        "web_leads": 50.0,
        "web_prepaid_pct": 0.0,
        "wa_leads": 0.0,
        "wa_prepaid_pct": 0.0,
        "wc": {"confirm": 90.0, "delivery": 50.0, "ad": 300.0, "product": 200.0, "packing": 30.0, "postage": 75.0, "price": 1400.0, "salary": 10000.0, "capacity": 50.0, "uplift": 30.0},
        "wp": {"delivery": 90.0, "price": 1400.0},
        "ac": {"confirm": 30.0, "delivery": 50.0, "ad": 15.0, "product": 200.0, "packing": 30.0, "postage": 75.0, "price": 1400.0, "salary": 10000.0, "capacity": 100.0, "uplift": 30.0},
        "ap": {"delivery": 90.0, "price": 1400.0},
        "shared": {"agency": 150000.0, "server": 20000.0, "influencer": 40000.0}
    },
    "Profitable D2C Scale Engine": {
        "description": "High volume e-commerce operation: 3,000 Website leads (35% prepaid) + 2,500 WhatsApp leads (25% prepaid). Optimized ad spend & strong positive cash flow.",
        "web_leads": 3000.0,
        "web_prepaid_pct": 35.0,
        "wa_leads": 2500.0,
        "wa_prepaid_pct": 25.0,
        "wc": {"confirm": 85.0, "delivery": 65.0, "ad": 180.0, "product": 220.0, "packing": 25.0, "postage": 70.0, "price": 1599.0, "salary": 18000.0, "capacity": 250.0, "uplift": 15.0},
        "wp": {"delivery": 94.0, "price": 1599.0},
        "ac": {"confirm": 45.0, "delivery": 65.0, "ad": 25.0, "product": 220.0, "packing": 25.0, "postage": 70.0, "price": 1599.0, "salary": 15000.0, "capacity": 350.0, "uplift": 15.0},
        "ap": {"delivery": 92.0, "price": 1599.0},
        "shared": {"agency": 120000.0, "server": 25000.0, "influencer": 50000.0}
    },
    "High COD / RTO Crisis (Cash Bleed)": {
        "description": "Warning scenario showing the dangerous COD cash trap: low 38% delivery rate, high transit uplift (35%), expensive ads, heavy agency fees.",
        "web_leads": 1200.0,
        "web_prepaid_pct": 5.0,
        "wa_leads": 800.0,
        "wa_prepaid_pct": 5.0,
        "wc": {"confirm": 80.0, "delivery": 38.0, "ad": 380.0, "product": 250.0, "packing": 35.0, "postage": 90.0, "price": 1299.0, "salary": 14000.0, "capacity": 60.0, "uplift": 35.0},
        "wp": {"delivery": 88.0, "price": 1299.0},
        "ac": {"confirm": 25.0, "delivery": 40.0, "ad": 35.0, "product": 250.0, "packing": 35.0, "postage": 90.0, "price": 1299.0, "salary": 14000.0, "capacity": 100.0, "uplift": 35.0},
        "ap": {"delivery": 88.0, "price": 1299.0},
        "shared": {"agency": 180000.0, "server": 25000.0, "influencer": 60000.0}
    },
    "Prepaid-First Hyper-Profit Engine": {
        "description": "Aggressive prepaid push (70% prepaid share), 92% successful deliveries, controlled transit buffer, high operating margins and rapid cash turnaround.",
        "web_leads": 4000.0,
        "web_prepaid_pct": 70.0,
        "wa_leads": 3000.0,
        "wa_prepaid_pct": 60.0,
        "wc": {"confirm": 90.0, "delivery": 68.0, "ad": 140.0, "product": 180.0, "packing": 20.0, "postage": 60.0, "price": 1650.0, "salary": 20000.0, "capacity": 300.0, "uplift": 10.0},
        "wp": {"delivery": 96.0, "price": 1650.0},
        "ac": {"confirm": 55.0, "delivery": 70.0, "ad": 20.0, "product": 180.0, "packing": 20.0, "postage": 60.0, "price": 1650.0, "salary": 18000.0, "capacity": 400.0, "uplift": 10.0},
        "ap": {"delivery": 95.0, "price": 1650.0},
        "shared": {"agency": 90000.0, "server": 30000.0, "influencer": 40000.0}
    }
}


def apply_preset(model, preset_key: str):
    """Apply a preset to Month 1 of model and cascade to all months."""
    if preset_key not in PRESETS:
        return
    p = PRESETS[preset_key]
    
    # Month 1 splits
    model.months[0].splits["web"]["total"] = p["web_leads"]
    model.months[0].splits["web"]["prepaid"] = p["web_prepaid_pct"]
    model.months[0].splits["wa"]["total"] = p["wa_leads"]
    model.months[0].splits["wa"]["prepaid"] = p["wa_prepaid_pct"]
    
    # COD assumptions
    for k, v in p["wc"].items():
        model.months[0].channels["wc"][k] = v
    for k, v in p["wp"].items():
        model.months[0].channels["wp"][k] = v
    for k, v in p["ac"].items():
        model.months[0].channels["ac"][k] = v
    for k, v in p["ap"].items():
        model.months[0].channels["ap"][k] = v
        
    # Shared
    for k, v in p["shared"].items():
        model.months[0].shared[k] = v
        
    model.cascade_month1_to_all()
