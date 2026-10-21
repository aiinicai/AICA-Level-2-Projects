"""HSN / SAC helpers: suggested descriptions and the per-client memory of HSN -> description / unit / rate.

The built-in descriptions are the standard HS chapter / heading titles and the SAC service groups. They are
SUGGESTIONS to save typing - staff can overwrite them, and anything approved for a client is remembered for that
client and takes priority over the built-in text.
"""
from typing import Dict, Optional

CHAPTERS = {
    "01": "Live animals", "02": "Meat and edible meat offal", "03": "Fish and crustaceans, molluscs and other aquatic invertebrates",
    "04": "Dairy produce; birds' eggs; natural honey", "05": "Products of animal origin, not elsewhere specified",
    "06": "Live trees and other plants; bulbs, roots; cut flowers", "07": "Edible vegetables and certain roots and tubers",
    "08": "Edible fruit and nuts; peel of citrus fruit or melons", "09": "Coffee, tea, mate and spices", "10": "Cereals",
    "11": "Products of the milling industry; malt; starches", "12": "Oil seeds and oleaginous fruits; miscellaneous grains, seeds and fruit",
    "13": "Lac; gums, resins and other vegetable saps and extracts", "14": "Vegetable plaiting materials",
    "15": "Animal or vegetable fats and oils", "16": "Preparations of meat, fish or crustaceans",
    "17": "Sugars and sugar confectionery", "18": "Cocoa and cocoa preparations",
    "19": "Preparations of cereals, flour, starch or milk; bakers' wares", "20": "Preparations of vegetables, fruit, nuts",
    "21": "Miscellaneous edible preparations", "22": "Beverages, spirits and vinegar",
    "23": "Residues and waste from the food industries; prepared animal fodder", "24": "Tobacco and manufactured tobacco substitutes",
    "25": "Salt; sulphur; earths and stone; plastering materials, lime and cement", "26": "Ores, slag and ash",
    "27": "Mineral fuels, mineral oils and products of their distillation", "28": "Inorganic chemicals",
    "29": "Organic chemicals", "30": "Pharmaceutical products", "31": "Fertilisers",
    "32": "Tanning or dyeing extracts; paints and varnishes; putty", "33": "Essential oils and resinoids; perfumery, cosmetic or toilet preparations",
    "34": "Soap, washing preparations, lubricating preparations, waxes", "35": "Albuminoidal substances; modified starches; glues; enzymes",
    "36": "Explosives; pyrotechnic products; matches", "37": "Photographic or cinematographic goods",
    "38": "Miscellaneous chemical products", "39": "Plastics and articles thereof", "40": "Rubber and articles thereof",
    "41": "Raw hides and skins and leather", "42": "Articles of leather; saddlery and harness; travel goods, handbags",
    "43": "Furskins and artificial fur", "44": "Wood and articles of wood; wood charcoal", "45": "Cork and articles of cork",
    "46": "Manufactures of straw, esparto or other plaiting materials", "47": "Pulp of wood or other fibrous cellulosic material",
    "48": "Paper and paperboard; articles of paper pulp, paper or paperboard", "49": "Printed books, newspapers, pictures",
    "50": "Silk", "51": "Wool, fine or coarse animal hair", "52": "Cotton", "53": "Other vegetable textile fibres; paper yarn",
    "54": "Man-made filaments", "55": "Man-made staple fibres", "56": "Wadding, felt and nonwovens; twine, cordage, ropes and cables",
    "57": "Carpets and other textile floor coverings", "58": "Special woven fabrics; tufted textile fabrics; lace",
    "59": "Impregnated, coated, covered or laminated textile fabrics", "60": "Knitted or crocheted fabrics",
    "61": "Articles of apparel and clothing accessories, knitted or crocheted",
    "62": "Articles of apparel and clothing accessories, not knitted or crocheted", "63": "Other made up textile articles; worn clothing",
    "64": "Footwear, gaiters and the like", "65": "Headgear and parts thereof", "66": "Umbrellas, walking-sticks, whips",
    "67": "Prepared feathers and down; artificial flowers", "68": "Articles of stone, plaster, cement, asbestos, mica",
    "69": "Ceramic products", "70": "Glass and glassware", "71": "Pearls, precious stones, precious metals; imitation jewellery; coin",
    "72": "Iron and steel", "73": "Articles of iron or steel", "74": "Copper and articles thereof", "75": "Nickel and articles thereof",
    "76": "Aluminium and articles thereof", "78": "Lead and articles thereof", "79": "Zinc and articles thereof",
    "80": "Tin and articles thereof", "81": "Other base metals; cermets", "82": "Tools, implements, cutlery of base metal",
    "83": "Miscellaneous articles of base metal", "84": "Nuclear reactors, boilers, machinery and mechanical appliances",
    "85": "Electrical machinery and equipment; sound and television apparatus", "86": "Railway or tramway locomotives and rolling-stock",
    "87": "Vehicles other than railway or tramway rolling-stock, and parts and accessories thereof",
    "88": "Aircraft, spacecraft, and parts thereof", "89": "Ships, boats and floating structures",
    "90": "Optical, photographic, measuring, checking, medical or surgical instruments", "91": "Clocks and watches and parts thereof",
    "92": "Musical instruments; parts and accessories", "93": "Arms and ammunition; parts and accessories thereof",
    "94": "Furniture; bedding, mattresses; lamps and lighting fittings; prefabricated buildings", "95": "Toys, games and sports requisites",
    "96": "Miscellaneous manufactured articles", "97": "Works of art, collectors' pieces and antiques",
}

HEADINGS = {
    "0402": "Milk and cream, concentrated or containing added sugar", "1001": "Wheat and meslin", "1006": "Rice",
    "1701": "Cane or beet sugar and chemically pure sucrose, in solid form", "2106": "Food preparations not elsewhere specified",
    "2710": "Petroleum oils and oils from bituminous minerals (other than crude); preparations", "3004": "Medicaments put up in measured doses or for retail sale",
    "4011": "New pneumatic tyres, of rubber", "6109": "T-shirts, singlets and other vests, knitted or crocheted",
    "7308": "Structures and parts of structures, of iron or steel", "8471": "Automatic data processing machines (computers) and units thereof",
    "8473": "Parts and accessories for office machines and computers", "8481": "Taps, cocks, valves and similar appliances",
    "8517": "Telephone sets, smartphones and other apparatus for transmission of voice, images or data",
    "8536": "Electrical apparatus for switching or protecting electrical circuits", "8703": "Motor cars and other motor vehicles for the transport of persons",
    "8704": "Motor vehicles for the transport of goods", "8708": "Parts and accessories of motor vehicles", "9403": "Other furniture and parts thereof",
    # services (SAC)
    "9954": "Construction services", "9961": "Services in wholesale trade", "9962": "Services in retail trade",
    "9963": "Accommodation, food and beverage services", "9964": "Passenger transport services", "9965": "Goods transport services",
    "9966": "Rental services of transport vehicles with operator", "9967": "Supporting services in transport",
    "9968": "Postal and courier services", "9969": "Electricity, gas, water and other distribution services",
    "9971": "Financial and related services", "9972": "Real estate services", "9973": "Leasing or rental services without operator",
    "9981": "Research and development services", "9982": "Legal and accounting services",
    "9983": "Other professional, technical and business services", "9984": "Telecommunications, broadcasting and information supply services",
    "9985": "Support services", "9986": "Support services to agriculture, hunting, forestry, fishing, mining and utilities",
    "9987": "Maintenance, repair and installation (except construction) services", "9988": "Manufacturing services on physical inputs owned by others",
    "9989": "Other manufacturing services; publishing, printing and reproduction services", "9991": "Public administration and other services to the community",
    "9992": "Education services", "9993": "Human health and social care services", "9994": "Sewage and waste collection, treatment and disposal services",
    "9995": "Services of membership organisations", "9996": "Recreational, cultural and sporting services", "9997": "Other services",
    "9998": "Domestic services", "9999": "Services provided by extraterritorial organisations",
}

MAX_LEN = 30           # the Offline Tool accepts up to 30 characters for the HSN description


def describe(hsn: str, master: Optional[Dict[str, dict]] = None) -> str:
    """Best description for an HSN / SAC: the client's own remembered text, else the built-in heading / chapter."""
    h = (hsn or "").strip()
    if not h:
        return ""
    if master and h in master and master[h].get("description"):
        return master[h]["description"]
    for n in (len(h), 6, 4):
        if n <= len(h) and h[:n] in HEADINGS:
            return HEADINGS[h[:n]]
    if h[:2] in CHAPTERS:
        return CHAPTERS[h[:2]]
    return ""


def short(text: str) -> str:
    return (text or "")[:MAX_LEN]


def apply_to_lines(lines, master: Dict[str, dict]) -> int:
    """Fill blank description / unit / rate of lines from the client's remembered HSNs, then the built-in descriptions.
    The rate is only filled when the line has none and no tax amount to infer it from. Returns lines changed."""
    n = 0
    for l in lines:
        if not l.hsn:
            continue
        m = master.get(l.hsn, {})
        ch = False
        if not l.description:
            d = describe(l.hsn, master)
            if d:
                l.description, ch = d, True
        if not l.uqc and m.get("uqc"):
            l.uqc, ch = m["uqc"], True
        if not l.rate and not l.tax_total and m.get("rate") not in (None, ""):
            from .utils import D
            l.rate, ch = D(m["rate"]), True
            l.note = (l.note + "; " if l.note else "") + f"Rate {l.rate}% remembered for HSN {l.hsn}"
        n += ch
    return n
