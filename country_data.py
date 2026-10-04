"""
=============================================================================
TRAVEL TAILS - Global Destination Circuits & Country Intelligence Database
=============================================================================
Contains exhaustive, curated travel circuits for premier world destinations:
- Vietnam (Hanoi, Ha Long Bay, Da Nang & Hoi An, Ho Chi Minh City / Saigon)
- Japan (Tokyo, Mt. Fuji & Hakone, Kyoto, Osaka)
- Switzerland (Zurich, Lucerne & Mt. Titlis, Interlaken & Jungfraujoch, Geneva)
- France (Paris, Nice & French Riviera)
- Italy (Rome, Florence, Venice)
- United Arab Emirates / Dubai (Dubai, Abu Dhabi)
- Singapore (Marina Bay, Sentosa Island)
- Indonesia / Bali (Ubud, Seminyak & Kuta, Nusa Penida)
- United Kingdom (London, Edinburgh & Highlands)
- Spain (Barcelona, Madrid)

Plus GLOBAL_COUNTRY_DATABASE covering 30+ additional international destinations
with real constituent cities, exact airports, and authentic non-repetitive attractions.
=============================================================================
"""

DESTINATION_CIRCUITS_EXTENDED = {
    "vietnam": {
        "country": "Vietnam",
        "circuit_title": "Vietnam Grand Heritage & Scenic Wonder: Hanoi, Ha Long Bay, Hoi An & Saigon",
        "base_flight_fare": 18500,
        "overview": (
            "Vietnam is a captivating land of staggering natural beauty, 1,000-year imperial heritage, "
            "vibrant ancient towns, and pulsating modern metropolises. This curated multi-city circuit spans "
            "the historic 36 Guild Streets of Hanoi, the mystical emerald limestone towers of UNESCO World Heritage Ha Long Bay "
            "aboard a luxury overnight cruise ship, the world-renowned Golden Hand Bridge at Ba Na Hills, "
            "the romantic lantern-lit river canals of 16th-century Hoi An Ancient Town, and the dynamic southern "
            "energy of Ho Chi Minh City (Saigon) paired with the historic underground Cu Chi War Tunnels."
        ),
        "tour_highlights": [
            "Confirmed Round-Trip International & Domestic Flights Ex-{source} ({transit_station})",
            "Stay with Daily Buffet Breakfast Included across all 4-Star & 5-Star Heritage Hotels & Resorts",
            "5-Star Luxury Overnight Cruise on Ha Long Bay with all-inclusive full-board gourmet meals & sea kayaking",
            "VIP Private Transfers across Hanoi, Ha Long Bay, Da Nang, Hoi An, and Ho Chi Minh City",
            "Hanoi Heritage Tour: Hoan Kiem Lake, Ngoc Son Temple, Temple of Literature & Water Puppet Theatre",
            "Sun World Ba Na Hills Cable Car & Walk across the world-famous Golden Bridge held by giant stone hands",
            "UNESCO Hoi An Ancient Town Walking Tour with private Thu Bon River lantern boat cruise",
            "Historic Cu Chi Guerrilla Tunnels (250km underground network) guided excursion in Saigon",
            "Saigon Heritage Discovery: War Remnants Museum, Reunification Palace, Notre-Dame & Bitexco Skydeck"
        ],
        "cities": [
            {
                "city": "Hanoi",
                "display_name": "Hanoi (1,000-Year Capital & Old Quarter)",
                "nights": 2,
                "region_tag": "Northern Imperial Heritage",
                "transfer": "Noi Bai International Airport (HAN) to Hotel Included on private basis",
                "hotels": {
                    "budget": {"name": "Silk Path Hotel Hanoi", "stars": 4, "rate": 4500, "area": "Hang Bong, Hoan Kiem - Hanoi", "address": "195 Hang Bong, Hoan Kiem, Hanoi 100000, Vietnam", "room": "Deluxe Old Quarter Room", "meal": "Buffet Breakfast", "features": "Walking Distance to Hoan Kiem, Rooftop Bar, Free Wi-Fi"},
                    "value": {"name": "Apricot Hotel / Pan Pacific Hanoi", "stars": 4.5, "rate": 7800, "area": "Hang Trong, Hoan Kiem - Hanoi", "address": "136 Hang Trong, Hoan Kiem, Hanoi 100000, Vietnam", "room": "Lake View Superior Room", "meal": "Gourmet Breakfast", "features": "Overlooking Hoan Kiem Lake, Heated Pool, Luxury Spa"},
                    "luxury": {"name": "Sofitel Legend Metropole Hanoi", "stars": 5, "rate": 24500, "area": "Ngo Quyen, Hoan Kiem - Hanoi", "address": "15 Ngo Quyen, Hoan Kiem, Hanoi 100000, Vietnam", "room": "Historical Metropole French Colonial Suite", "meal": "Michelin Executive Chef Breakfast", "features": "French Colonial Heritage Since 1901, Le Spa, Heated Pool"}
                }
            },
            {
                "city": "Ha Long Bay",
                "display_name": "Ha Long Bay (UNESCO Natural Wonder Cruise)",
                "nights": 1,
                "region_tag": "Emerald Karsts & Secluded Lagoons",
                "transfer": "Scenic Red River Delta Private Limousine Hanoi to Tuan Chau Marina Included",
                "hotels": {
                    "budget": {"name": "Bhaya Classic Luxury Cruise", "stars": 4, "rate": 7200, "area": "Tuan Chau Marina, Ha Long Bay", "address": "Tuan Chau Island Marina, Ha Long City, Quang Ninh 200000, Vietnam", "room": "Oceanview Balcony Cabin", "meal": "All-Inclusive Full Board (Lunch, Dinner, Breakfast)", "features": "Traditional Wooden Junk, Kayaking, Squid Fishing"},
                    "value": {"name": "Paradise Elegance Luxury Cruise Ha Long", "stars": 5, "rate": 11500, "area": "Tuan Chau Marina, Ha Long Bay", "address": "Tuan Chau Marina, Ha Long City, Quang Ninh 200000, Vietnam", "room": "Executive Balcony Suite Cabin", "meal": "All-Inclusive Royal Gastronomy & Seafood", "features": "Private Terrace, Piano Bar, Floating Spa, Panoramic Sundeck"},
                    "luxury": {"name": "Orchid Classic / Heritage Cruise Lan Ha & Ha Long", "stars": 5, "rate": 28000, "area": "Pristine Lan Ha Bay & Ha Long", "address": "Got Pier, Ha Long Bay & Lan Ha Bay, Vietnam", "room": "Presidential Royal Balcony Suite with Jacuzzi", "meal": "Five-Course Michelin Chef Gourmet Experience", "features": "Exclusive Secluded Route, On-Deck Jacuzzi, Private Tender Boat"}
                }
            },
            {
                "city": "Da Nang & Hoi An",
                "display_name": "Da Nang & Hoi An Ancient Lantern Town",
                "nights": 2,
                "region_tag": "Golden Hand Bridge & 16th-Century Heritage",
                "transfer": "Noi Bai Airport to Da Nang (DAD) & Private Scenic Transfer to Hoi An Included",
                "hotels": {
                    "budget": {"name": "Hoi An Historic Hotel", "stars": 4, "rate": 4200, "area": "Tran Hung Dao, Hoi An", "address": "10 Tran Hung Dao, Hoi An 560000, Quang Nam, Vietnam", "room": "Heritage Deluxe Room", "meal": "Buffet Breakfast", "features": "Walking Distance to Ancient Town, Garden Pool"},
                    "value": {"name": "Anantara Hoi An Resort / Vinpearl Da Nang", "stars": 5, "rate": 8900, "area": "Thu Bon Riverfront, Hoi An", "address": "1 Pham Hong Thai, Cam Chau, Hoi An 560000, Vietnam", "room": "River View Deluxe Balcony Room", "meal": "Gourmet Riverside Breakfast", "features": "Thu Bon Riverfront, Luxury Anantara Spa, Infinity Pool"},
                    "luxury": {"name": "Four Seasons Resort The Nam Hai / InterContinental Da Nang", "stars": 5, "rate": 36000, "area": "Ha My Beach, Hoi An", "address": "Ha My Beach, Dien Ban, Hoi An 560000, Vietnam", "room": "One-Bedroom Beachfront Pool Villa", "meal": "Private Chef Breakfast & Champagne", "features": "Private Oceanfront Villa, 3 Tiered Beachfront Pools, Private Beach"}
                }
            },
            {
                "city": "Ho Chi Minh City",
                "display_name": "Ho Chi Minh City (Saigon & Cu Chi Tunnels)",
                "nights": 2,
                "region_tag": "Southern Metropolis & War History",
                "transfer": "Da Nang Airport to Saigon (SGN) & Private City Hotel Transfer Included",
                "hotels": {
                    "budget": {"name": "Liberty Central Saigon Citypoint", "stars": 4, "rate": 4500, "area": "District 1, Ho Chi Minh City", "address": "59 Pasteur, District 1, Ho Chi Minh City 700000, Vietnam", "room": "Deluxe City Room", "meal": "Buffet Breakfast", "features": "Rooftop Cinema & Pool, Near Ben Thanh Market"},
                    "value": {"name": "Caravelle Saigon / Hotel Majestic Saigon", "stars": 5, "rate": 7500, "area": "Lam Son Square, District 1, Saigon", "address": "19-23 Lam Son Square, District 1, Ho Chi Minh City 700000, Vietnam", "room": "Opera View Deluxe Room", "meal": "Buffet Breakfast", "features": "Historic Landmark Since 1959, Rooftop Bar, Signature Spa"},
                    "luxury": {"name": "The Reverie Saigon / Park Hyatt Saigon", "stars": 5, "rate": 29000, "area": "Nguyen Hue Boulevard, District 1", "address": "22-36 Nguyen Hue Boulevard, District 1, Ho Chi Minh City 700000, Vietnam", "room": "Grand Panoramic Saigon River Suite", "meal": "All-Inclusive Fine Dining", "features": "Italian Haute Couture Interior, Helipad, Luxury Rolls Royce Chauffeur"}
                }
            }
        ],
        "days": [
            {
                "day_num": 1,
                "min_days": 1,
                "title": "Arrival in Hanoi & Hoan Kiem Lake Heritage Walk",
                "desc": "-Arrival at Noi Bai International Airport (HAN) & private transfer across the Red River. -Check-in and refresh with Vietnamese jasmine tea. -Evening stroll around emerald Hoan Kiem Lake, Ngoc Son Temple & The Huc Bridge. -Thang Long Water Puppet Theatre show & egg coffee at Cafe Giang.",
                "meals": "Dinner Included",
                "transfer_type": "Private",
                "photo_caption": "Hanoi: Hoan Kiem Lake, Ngoc Son Temple & The Huc Bridge",
                "city_hub": "Hanoi",
                "region_tag": "Capital Gateway",
                "morning": "Arrival at Noi Bai International Airport (HAN). VIP airport reception and private transfer across the Red River into historic Hanoi Old Quarter. Hotel check-in and refresh.",
                "afternoon": "Leisure walk around iconic emerald Hoan Kiem Lake (Lake of the Restored Sword), crossing the iconic red-lacquered The Huc Bridge to visit sacred Ngoc Son Temple.",
                "evening": "Experience the world-famous traditional Thang Long Water Puppet Theatre performance. Authentic Old Quarter culinary walk tasting Michelin-featured Pho Gia Truyen and egg coffee at Cafe Giang (est. 1946).",
                "major_attractions": ["Hoan Kiem Lake & Ngoc Son Temple", "The Huc Scarlet Bridge", "Thang Long Water Puppet Theatre", "Hanoi Old Quarter 36 Guild Streets", "Cafe Giang Egg Coffee"],
                "inclusions": "Noi Bai Airport Pickup, Private AC Transfer, Water Puppet Show Tickets, Guide"
            },
            {
                "day_num": 2,
                "min_days": 7,
                "title": "Hanoi 1,000-Year Capital Heritage & Temple of Literature",
                "desc": "-Post Breakfast, visit Ba Dinh Square: Ho Chi Minh Mausoleum complex, Presidential Palace gardens & One Pillar Pagoda. -Explore monumental Temple of Literature (1070) & Vietnam Museum of Ethnology. -Evening cyclo ride through French Quarter & sunset over West Lake.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Hanoi: Temple of Literature (Van Mieu Quoc Tu Giam)",
                "city_hub": "Hanoi",
                "region_tag": "Imperial Heritage",
                "morning": "Guided morning visit to historic Ba Dinh Square: Ho Chi Minh Mausoleum complex, Presidential Palace gardens, Ho Chi Minh's Stilt House, and the 11th-century One Pillar Pagoda.",
                "afternoon": "Explore monumental Temple of Literature (Van Mieu - Quoc Tu Giam), founded in 1070 as Vietnam's first national university. Continue to the Vietnam Museum of Ethnology displaying tribal architecture.",
                "evening": "Scenic cyclo (pedicab) ride weaving through the bustling 36 Guild Streets of the French Quarter and Old Quarter. Sunset panoramic cocktail overlooking West Lake (Ho Tay) and Tran Quoc Pagoda.",
                "major_attractions": ["Temple of Literature (Van Mieu)", "Ho Chi Minh Mausoleum Complex", "One Pillar Pagoda", "Vietnam Museum of Ethnology", "Tran Quoc Pagoda West Lake"],
                "inclusions": "Full Day Private AC Van, English Speaking Heritage Guide, Entry Permits, Cyclo Ride"
            },
            {
                "day_num": 3,
                "min_days": 10,
                "title": "Ninh Binh UNESCO Trang An Grottoes, Bai Dinh & Mua Cave Dragon Summit",
                "desc": "-Post Breakfast, morning drive to Ninh Binh (Halong Bay on land). -Traditional sampan boat cruise through mystical Trang An water caves & limestone grottoes. -Climb 500 stone steps to Mua Cave dragon viewpoint overlooking Tam Coc rice valley. -Visit monumental Bai Dinh Pagoda complex. -Return to Hanoi.",
                "meals": "Breakfast, Lunch",
                "transfer_type": "Private",
                "photo_caption": "Ninh Binh: Trang An UNESCO Karst Grottoes & Mua Dragon Peak",
                "city_hub": "Ninh Binh & Hanoi",
                "region_tag": "UNESCO Karst Landscape",
                "morning": "Scenic morning drive south through the verdant Red River Delta to Ninh Binh. Board a traditional wooden sampan rowed by local boatmen through UNESCO Trang An Grottoes, passing beneath towering limestone karst tunnels and emerald subterranean caves.",
                "afternoon": "Hike the 500 carved stone steps to the jagged summit of Hang Mua (Mua Cave) for the world-famous panoramic dragon viewpoint overlooking the golden Tam Coc rice valleys and winding Ngo Dong river.",
                "evening": "Visit the sprawling Bai Dinh Buddhist Pagoda, admiring the corridor of 500 stone Arhat statues and Southeast Asia's largest bronze Buddha. Return to Hanoi for overnight stay.",
                "major_attractions": ["Trang An UNESCO Grottoes Boat Safari", "Mua Cave (Hang Mua) Dragon Viewpoint", "Bai Dinh Pagoda Giant Bronze Buddha", "Tam Coc Karst Valley Vistas"],
                "inclusions": "Private AC Limousine, Trang An Boat Tickets & Rowers, Hang Mua Summit Entry, English Guide"
            },
            {
                "day_num": 4,
                "min_days": 3,
                "title": "Scenic Red River Delta to Ha Long Bay UNESCO Luxury Overnight Cruise",
                "desc": "-Post Breakfast, private limousine transfer through Red River Delta to Tuan Chau Marina, Ha Long Bay. -Board 5-star luxury cruise ship. -Multi-course seafood lunch gliding past 1,600 towering limestone karsts. -Explore Sung Sot (Surprise) Cave & kayak through Luon Cave. -Sunset party & squid fishing.",
                "meals": "Breakfast, Lunch, Dinner",
                "transfer_type": "Private",
                "photo_caption": "Ha Long Bay: Luxury Overnight Cruise & Limestone Karsts",
                "city_hub": "Ha Long Bay",
                "region_tag": "UNESCO Natural Wonder",
                "morning": "Post buffet breakfast, board private luxury limousine van traveling through verdant rice paddies of the Red River Delta toward Tuan Chau Marina, Ha Long Bay.",
                "afternoon": "Board 5-star luxury cruise ship. Welcome cocktail and multi-course seafood lunch while gliding past thousands of limestone pillars (Fighting Cocks Islet, Incense Burner Islet).",
                "evening": "Guided excursion inside colossal Sung Sot Cave (Surprise Cave) with dramatic stalactites. Kayak through hidden lagoons at Luon Cave. Return to ship for sunset sundeck party, cooking class, and night squid fishing.",
                "major_attractions": ["Ha Long Bay UNESCO Karst Islands", "Sung Sot (Surprise) Cave", "Luon Cave Kayaking Lagoon", "Fighting Cocks & Incense Islets", "Overnight Cruise Sundeck"],
                "inclusions": "Limousine Transfer Hanoi - Ha Long, 5-Star Luxury Cruise Cabin, Full Board Meals, Kayaking, Cave Passes"
            },
            {
                "day_num": 5,
                "min_days": 5,
                "title": "Ti Top Island Sunrise, Flight to Da Nang & Dragon Bridge Fire Show",
                "desc": "-Sunrise Tai Chi on cruise sundeck. -Hike to Ti Top Island summit for 360-degree panoramic bay views. -Brunch cruising to pier. -Transfer to airport for express flight to Da Nang (DAD). -Witness spectacular Dragon Bridge breathing fire and water.",
                "meals": "Breakfast, Brunch",
                "transfer_type": "Private",
                "photo_caption": "Da Nang: Dragon Bridge (Cau Rong) & My Khe Coastline",
                "city_hub": "Ha Long Bay & Da Nang",
                "region_tag": "Coastal Gateway",
                "morning": "Sunrise Tai Chi session on open sundeck overlooking mist-shrouded karsts. Hike 400 steps to the summit of Ti Top Island for breathtaking 360-degree panoramic photos of Ha Long Bay.",
                "afternoon": "Hearty international brunch while cruising back to Tuan Chau Pier. Disembark and private transfer to airport for an express flight to Da Nang International Airport (DAD). Chauffeur meet & greet and check-in at resort.",
                "evening": "Stroll down the illuminated riverside promenade and witness the iconic Dragon Bridge (Cau Rong) spout fire and water jets into the night sky. Relax along the sands of My Khe Beach.",
                "major_attractions": ["Ti Top Island Panoramic Summit & Beach", "Halong Bay Sunrise Tai Chi", "Da Nang Dragon Bridge (Cau Rong)", "My Khe Beach Coastline"],
                "inclusions": "Cruise Excursion & Brunch, Flight Transfer, Da Nang Private Transfer, Dragon Bridge Experience"
            },
            {
                "day_num": 6,
                "min_days": 4,
                "title": "Sun World Ba Na Hills Cable Car & Golden Bridge Held by Giant Stone Hands",
                "desc": "-Ascend Truong Son mountains via world-record cable car to Sun World Ba Na Hills. -Walk along world-famous Golden Bridge held by colossal giant stone hands. -Explore French Village, Debay Wine Cellar & Linh Ung Pagoda Lady Buddha. -Scenic mountain descent.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Ba Na Hills: World-Famous Golden Bridge Held by Giant Stone Hands",
                "city_hub": "Da Nang",
                "region_tag": "Ba Na Hills Wonder",
                "morning": "Excursion ascending into Truong Son mountains via world's longest single-wire cable car to Sun World Ba Na Hills. Walk across world-famous Golden Bridge (Cau Vang) held aloft by gigantic stone hands emerging from cliffside.",
                "afternoon": "Explore the medieval French Village, historic 1923 Debay Wine Cellar carved deep into rock, and the Le Jardin D'Amour romantic flower gardens. Visit the monumental 27-meter white Buddha statue at Linh Ung Pagoda.",
                "evening": "Descend via cable car over lush waterfalls. Relax with oceanfront dining featuring fresh Da Nang sea prawns and Vietnamese banh mi.",
                "major_attractions": ["Golden Bridge (Giant Stone Hands)", "Ba Na Hills Cable Car (Guinness Record)", "French Village & Debay Wine Cellar", "Linh Ung Pagoda Lady Buddha", "Le Jardin D'Amour Flower Gardens"],
                "inclusions": "Ba Na Hills Cable Car Tickets, Golden Bridge Entry, Mountain Transfers, English Speaking Guide"
            },
            {
                "day_num": 7,
                "min_days": 4,
                "title": "Hoi An 16th-Century Ancient Lantern Town & Cam Thanh Coconut Basket Boat",
                "desc": "-Post Breakfast, morning visit to Cam Thanh Coconut Forest: spin in traditional bamboo basket boats (thung chai). -Afternoon guided walking tour of UNESCO Hoi An: Japanese Covered Bridge (1590), Phuc Kien Hall & Tan Ky Old House. -Twilight Thu Bon River lantern release.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Hoi An Ancient Town: Thu Bon River Illuminated Lanterns",
                "city_hub": "Hoi An",
                "region_tag": "UNESCO Ancient Port",
                "morning": "Head to Cam Thanh Coconut Village for an exhilarating ride in traditional round bamboo basket boats (thung chai), navigating dense nipa palm canals with master boatmen spinning and fishing.",
                "afternoon": "Guided walking tour through pedestrian-only UNESCO Hoi An Ancient Town: visit iconic Japanese Covered Bridge (built 1590), ornate Cantonese Assembly Hall (Phuc Kien), and 200-year-old Tan Ky Merchant House.",
                "evening": "As darkness falls and thousands of colorful silk lanterns illuminate the cobblestones, board a traditional wooden boat on Thu Bon River to release floating candlelit flower lanterns for health and happiness.",
                "major_attractions": ["Cam Thanh Coconut Forest Basket Boat", "Japanese Covered Bridge (1590)", "Phuc Kien Assembly Hall", "Tan Ky Historic Merchant House", "Thu Bon River Floating Lantern Release"],
                "inclusions": "Basket Boat Experience, Hoi An Heritage Walking Ticket, Private Lantern Boat Cruise, AC Transfer"
            },
            {
                "day_num": 8,
                "min_days": 13,
                "title": "UNESCO My Son Hindu-Buddhist Valley Sanctuary & An Bang Beach Leisure",
                "desc": "-Post Breakfast, morning excursion to UNESCO World Heritage My Son Sanctuary (4th-13th century Cham temple ruins). -Witness traditional Apsara dance performance. -Afternoon relaxation at golden An Bang Beach. -Evening Hoi An Memories cultural show.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "My Son Sanctuary: Ancient Red-Brick Cham Civilization Temples",
                "city_hub": "Hoi An & My Son",
                "region_tag": "Champa Civilization",
                "morning": "Excursion into a verdant circular valley dominated by Hon Quap (Cat's Tooth Mountain) to explore the UNESCO My Son Sanctuary, the ancient religious capital of the Champa Kingdom with intricately carved red-brick Shiva temples.",
                "afternoon": "Watch an authentic Cham Apsara musical performance with earthen drums and flutes. Continue to tranquil An Bang Beach for afternoon relaxation, refreshing ocean breezes, and coconut drinks.",
                "evening": "Attend the spectacular 'Hoi An Memories' outdoor live theatrical extravaganza featuring 500 performers on a 25,000 sqm water stage tracing Hoi An's 400-year history. Stroll vibrant night markets.",
                "major_attractions": ["My Son UNESCO Valley Sanctuary", "Cham Ancient Brick Temples & Sculptures", "Apsara Traditional Dance Performance", "An Bang Beach & Coastal Cafes", "Hoi An Memories Cultural Show"],
                "inclusions": "My Son Guided Tour & Electric Buggy, Apsara Show, Beach Transfer, Hoi An Memories Ticket"
            },
            {
                "day_num": 9,
                "min_days": 8,
                "title": "Scenic Hai Van Pass Drive, Hue Imperial Citadel & Thien Mu Pagoda",
                "desc": "-Post Breakfast, spectacular coastal drive over legendary Hai Van Pass (Ocean Cloud Pass) to Hue. -Tour UNESCO Complex of Hue Monuments & Forbidden Purple City. -Dragon boat cruise on Perfume River to 7-storey Thien Mu Pagoda. -Royal Hue gastronomy.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Hue Imperial Citadel: Forbidden Purple City & Ngo Mon Gate",
                "city_hub": "Hue",
                "region_tag": "Imperial Nguyen Dynasty",
                "morning": "Traverse the legendary winding Hai Van Pass ('Ocean Cloud Pass') offering breathtaking views over Lang Co beach and turquoise bays to imperial capital Hue, seat of the Nguyen Emperors from 1802 to 1945.",
                "afternoon": "Tour the colossal walled Imperial Citadel and Forbidden Purple City (Tu Cam Thanh), exploring the Throne Hall, Nine Dynastic Urns, and Royal Theatres restored to dynastic splendor.",
                "evening": "Board a painted royal dragon boat along the gentle Perfume River (Song Huong) to visit the iconic octagonal 7-storey Thien Mu Pagoda standing gracefully on the river bluff. Sample Hue royal imperial banquet delicacies.",
                "major_attractions": ["Hai Van Mountain Coastal Pass", "Complex of Hue Monuments (Imperial City)", "Forbidden Purple City & Ngo Mon Gate", "Thien Mu 7-Storey Pagoda", "Perfume River Dragon Boat Cruise"],
                "inclusions": "Private AC Coastal Transfer, Imperial Citadel Permits, Royal Dragon Boat Cruise, Heritage Historian Guide"
            },
            {
                "day_num": 10,
                "min_days": 11,
                "title": "Khai Dinh Royal Mosaic Tomb & Flight to Da Lat Highland Mountain Resort",
                "desc": "-Post Breakfast, explore elaborate royal tomb of Emperor Khai Dinh blending French Gothic and Vietnamese porcelain mosaic art. -Flight to cool pine highlands of Da Lat (The City of Eternal Spring). -Ride Datanla Waterfall alpine coaster. -Evening at Xuan Huong Lake.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Da Lat: Datanla Cascading Waterfall & Highland Pine Valleys",
                "city_hub": "Hue & Da Lat",
                "region_tag": "Highland Pine Valleys",
                "morning": "Visit the extraordinary hillside Tomb of Emperor Khai Dinh (Ung Lang), admiring its dark gothic stone facade and jaw-dropping interior decorated with millions of colorful porcelain and glass shards creating elaborate dragons and ceiling murals.",
                "afternoon": "Transfer to airport for domestic flight to Da Lat, the misty 'City of Eternal Spring' located at 1,500m elevation surrounded by pine hills, strawberry gardens, and French colonial villas.",
                "evening": "Experience the exhilarating motorized alpine coaster zipping through fragrant pine forests down to cascading Datanla Waterfall. Stroll along horseshoe-shaped Xuan Huong Lake.",
                "major_attractions": ["Tomb of King Khai Dinh (Porcelain Mosaic)", "Datanla Waterfall & Alpine Coaster", "Xuan Huong Lake Promenade", "Da Lat French Colonial Architecture", "Da Lat Highland Night Market"],
                "inclusions": "Khai Dinh Tomb Pass, Domestic Flight Hue/Da Nang to Da Lat, Alpine Coaster Pass, Private Transfer"
            },
            {
                "day_num": 11,
                "min_days": 14,
                "title": "Langbiang Mountain Summit, Truc Lam Monastery & Surreal Crazy House",
                "desc": "-Post Breakfast, 4x4 jeep safari up Langbiang Mountain summit for 360-degree highland views. -Scenic Robin Hill cable car to Truc Lam Zen Monastery overlooking Tuyen Lam Lake. -Explore surreal fairy-tale architecture of Crazy House (Hang Nga). -Artisan coffee tasting.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Da Lat: Truc Lam Zen Buddhist Monastery & Tuyen Lam Lake",
                "city_hub": "Da Lat",
                "region_tag": "Highland Adventures",
                "morning": "4x4 mountain jeep safari up the jagged granite slopes of Langbiang Peak (2,167m) for jaw-dropping vistas over Da Lat's golden valleys, silver streams, and pine-clad peaks. Visit Lat ethnic minority hamlet.",
                "afternoon": "Board the Robin Hill cable car gliding silently above pine forest canopies to Truc Lam Zen Monastery, surrounded by tranquil manicured bonsai gardens overlooking turquoise Tuyen Lam Lake.",
                "evening": "Explore the whimsical, surrealist architectural marvel known as 'Crazy House' (Hang Nga Guesthouse), designed like an organic tree trunk with twisting stairs and spider-web windows. Savor high-altitude Da Lat Arabica coffee.",
                "major_attractions": ["Langbiang Mountain Peak (2,167m) 4x4 Jeep", "Truc Lam Zen Monastery & Cable Car", "Tuyen Lam Pine Lake", "Crazy House (Hang Nga Surreal Architecture)", "Da Lat French Railway Station (1938)"],
                "inclusions": "4x4 Jeep Safari, Cable Car Tickets, Crazy House Entry, Private Van & Chauffeur"
            },
            {
                "day_num": 12,
                "min_days": 5,
                "title": "Flight to Ho Chi Minh City (Saigon Colonial Heritage & Bitexco Skydeck)",
                "desc": "-Morning flight from Da Lat to vibrant Ho Chi Minh City (Saigon). -Check-in at luxury hotel. -Guided colonial tour: War Remnants Museum, Reunification Palace, Notre-Dame Cathedral & Eiffel's Central Post Office. -Saigon Skydeck sunset cocktail.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Ho Chi Minh City (Saigon): Notre-Dame Cathedral & Bitexco Skydeck",
                "city_hub": "Ho Chi Minh City",
                "region_tag": "Metropolis & Colonial History",
                "morning": "Morning flight from Da Lat to vibrant Ho Chi Minh City (Tan Son Nhat Airport SGN). Private reception and transfer to luxury hotel in the heart of District 1.",
                "afternoon": "Comprehensive tour of historic Saigon: visit poignant War Remnants Museum, the landmark Independence (Reunification) Palace, French neo-Romanesque Notre-Dame Cathedral, and the majestic Central Post Office designed by Gustave Eiffel.",
                "evening": "Ascend to the 49th floor Saigon Skydeck at Bitexco Financial Tower for 360-degree sunset vistas over the glittering skyline and meandering Saigon River. Dinner cruise with traditional Southern live music.",
                "major_attractions": ["War Remnants Museum", "Reunification (Independence) Palace", "Notre-Dame Cathedral & Central Post Office", "Bitexco Financial Tower Skydeck", "Saigon River Sunset Promenade"],
                "inclusions": "Domestic Flight Da Lat to Saigon, Airport Transfers, Museum Entry Passes, Skydeck Pass"
            },
            {
                "day_num": 13,
                "min_days": 6,
                "title": "Historic Cu Chi Underground War Tunnels & Ben Thanh Artisan Market",
                "desc": "-Guided morning excursion into countryside to legendary Cu Chi Tunnels (250km underground guerrilla war network). -Explore command bunkers, secret trapdoors & hospital rooms. -Afternoon artisan shopping at Ben Thanh Market. -Evening walk down Nguyen Hue Boulevard.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Cu Chi Historic Underground Guerrilla War Tunnels (250km)",
                "city_hub": "Ho Chi Minh City",
                "region_tag": "Cu Chi War Network",
                "morning": "Guided excursion into the historic countryside to the legendary Cu Chi Tunnels. Crawl through a preserved section of the 250km multi-level underground guerrilla network used during the Vietnam War, featuring secret trapdoors, living quarters, weapon workshops, and command bunkers.",
                "afternoon": "Return to central Saigon. Tour the vibrant Ben Thanh Market and Binh Tay Market in Cho Lon (Chinatown) for authentic Trung Nguyen coffee beans, hand-embroidered textiles, lacquerware, and tailored silk.",
                "evening": "Stroll down the illuminated pedestrian boulevard of Nguyen Hue. Admire the illuminated French colonial Ho Chi Minh City Hall (People's Committee Building) and Municipal Opera House.",
                "major_attractions": ["Cu Chi Guerilla Tunnels (250km Network)", "Ben Thanh Market", "Cho Lon Chinatown & Thien Hau Pagoda", "Nguyen Hue Boulevard & City Hall", "Saigon Opera House"],
                "inclusions": "Cu Chi Tunnels Guided Excursion & Entry, Underground Tunnel Experience, Private AC Van, Market Guide"
            },
            {
                "day_num": 14,
                "min_days": 8,
                "title": "Deep Mekong Delta Safari: Cai Rang Floating Market & Nipa Palm Canals",
                "desc": "-Full day scenic expedition to the waterways of the Mekong Delta (My Tho & Ben Tre). -Cruising Tien River past Dragon, Unicorn & Phoenix islets. -Rowing sampan through narrow shaded nipa palm canals. -Visit honeybee farms, coconut candy workshops & enjoy Don Ca Tai Tu folk music.",
                "meals": "Breakfast, Lunch",
                "transfer_type": "Private",
                "photo_caption": "Mekong Delta: Traditional Hand-Rowed Sampan Coconut Canals",
                "city_hub": "Mekong Delta",
                "region_tag": "Mekong Delta Waterways",
                "morning": "Scenic morning drive south to My Tho, gateway to the lush Mekong Delta. Board a motorboat cruising along the mighty Tien River, taking in views of stilt houses, fish-farming cages, and the four sacred animal islets (Dragon, Unicorn, Phoenix, Turtle).",
                "afternoon": "Transfer to small wooden sampans, hand-rowed by local boatmen through tranquil, labyrinthine water-coconut canals. Visit an artisanal bee farm, taste warm honey tea, and watch traditional coconut candy making in Ben Tre.",
                "evening": "Listen to soulful UNESCO-recognized Don Ca Tai Tu traditional Southern Vietnamese folk singing while enjoying tropical seasonal fruits. Return to Saigon for evening leisure.",
                "major_attractions": ["Mekong Delta Riverboat Cruise", "Ben Tre Nipa Palm Hand-Rowed Sampan", "Artisanal Coconut Candy Workshop", "Tropical Fruit Orchards & Honeybee Farm", "Vinh Trang Historic Buddhist Pagoda"],
                "inclusions": "Private AC Van Saigon - Mekong, Private Riverboat & Sampan Rowers, Farm Visits & Tastings, Lunch"
            },
            {
                "day_num": 15,
                "min_days": 12,
                "title": "Tropical Paradise Excursion / Saigon River Yacht Cruise & Landmark 81",
                "desc": "-Morning luxury Saigon River speedboat cruise or visit historic Jade Emperor Pagoda. -Afternoon visit to the trendy Cafe Apartments on Nguyen Hue Boulevard. -Ascend Landmark 81 SkyView (Vietnam's tallest skyscraper at 461m) for farewell panoramic dinner.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Landmark 81 Saigon: Vietnam's Tallest 461m Skyscraper SkyView",
                "city_hub": "Ho Chi Minh City",
                "region_tag": "Modern Metropolis",
                "morning": "Board a luxury speedboat gliding along the peaceful bends of the Saigon River, admiring lush mangrove shores and glittering skyline villas. Visit the historic 1909 Jade Emperor Pagoda (Chua Ngoc Hoang).",
                "afternoon": "Explore the iconic 9-storey 'Cafe Apartments' at 42 Nguyen Hue, a quirky 1960s residential complex filled with bohemian coffee shops, vintage fashion boutiques, and artisanal tea houses.",
                "evening": "Ascend to the summit observation deck of Landmark 81 SkyView (461 meters), the tallest skyscraper in Vietnam, for breathtaking twilight city vistas. Enjoy a farewell gourmet Vietnamese dinner.",
                "major_attractions": ["Landmark 81 SkyView (461m Summit)", "Cafe Apartments on Nguyen Hue Boulevard", "Jade Emperor Pagoda (1909)", "Saigon River Luxury Speedboat Promenade"],
                "inclusions": "Landmark 81 SkyView Fast-Track Pass, Private AC Transport, Sightseeing Guide"
            },
            {
                "day_num": 16,
                "min_days": 1,
                "title": "Dong Khoi Shopping Boulevard, Souvenirs & Departure Home",
                "desc": "-Relaxed gourmet breakfast at hotel. -Morning souvenir and artisan shopping along historic Dong Khoi Boulevard. -Hotel check-out & private VIP transfer to Tan Son Nhat International Airport (SGN). -Board return international flight home.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Tan Son Nhat International Airport Saigon Departure",
                "city_hub": "Ho Chi Minh City / Departure",
                "region_tag": "Departure Hub",
                "morning": "Enjoy a relaxed buffet breakfast at hotel. Morning at leisure for last-minute souvenir shopping along French colonial Dong Khoi Boulevard, famous for high-end boutique silks, roasted civet coffee beans, and ceramic handicrafts.",
                "afternoon": "Hotel check-out. Chauffeur meet and assistance with luggage. Private transfer to Tan Son Nhat International Airport (SGN) for your return international flight to origin.",
                "evening": "Board return international flight to origin. Safe journey home with unforgettable memories of Vietnam!",
                "major_attractions": ["Dong Khoi Luxury Shopping Boulevard", "Saigon Central Post Office Souvenir Hall", "Tan Son Nhat International Airport (SGN)"],
                "inclusions": "Hotel Checkout Assistance, Private Airport Van Transfer, Luggage Assistance, Return Flight"
            }
        ]
    },

    "japan": {
        "country": "Japan",
        "circuit_title": "Japan Golden Route: Tokyo Metropolis, Mt. Fuji, Kyoto Temples & Osaka",
        "base_flight_fare": 32000,
        "overview": (
            "Japan harmoniously unites futuristic innovation with timeless samurai and geisha traditions. "
            "This Golden Route traverses the neon-lit crossing of Shibuya and historic Senso-ji Temple in Tokyo, "
            "the majestic snow-capped cone of Mount Fuji and Lake Ashi in Hakone, the 10,000 vermilion torii gates "
            "of Fushimi Inari and Arashiyama Bamboo Grove in Kyoto, culminating in the culinary neon capital of Osaka Dotonbori."
        ),
        "tour_highlights": [
            "Confirmed Round-Trip Flights Ex-{source} ({transit_station})",
            "Stay with Daily Buffet Breakfast Included across all 4-Star & 5-Star Hotels",
            "Shinkansen Bullet Train Experience connecting Tokyo to Kyoto at 300 km/h",
            "Tokyo Highlights: Shibuya Crossing, Senso-ji Asakusa, Meiji Shrine & Tokyo Skytree",
            "Full Day Mt. Fuji 5th Station & Lake Ashi Pirate Cruise in Hakone",
            "Kyoto Cultural Marvels: Fushimi Inari-taisha, Kinkaku-ji Golden Pavilion & Arashiyama Bamboo Forest",
            "Osaka Gastronomy & Heritage: Osaka Castle & Dotonbori Street Food Tour"
        ],
        "cities": [
            {
                "city": "Tokyo",
                "display_name": "Tokyo Metropolis",
                "nights": 3,
                "region_tag": "Kanto High-Tech Capital",
                "transfer": "Tokyo Haneda Airport (HND) to Hotel Included on private basis",
                "hotels": {
                    "budget": {"name": "Hotel Gracery Shinjuku", "stars": 4, "rate": 8500, "area": "Shinjuku, Tokyo", "address": "1-19-1 Kabukicho, Shinjuku, Tokyo 160-8466, Japan", "room": "Standard Double Room", "meal": "Buffet Breakfast", "features": "Near Shinjuku Station, Godzilla Road"},
                    "value": {"name": "Keio Plaza Hotel Tokyo", "stars": 4.5, "rate": 14500, "area": "Nishi-Shinjuku, Tokyo", "address": "2-2-1 Nishi-Shinjuku, Shinjuku, Tokyo 160-8330, Japan", "room": "Superior City View Room", "meal": "Gourmet Breakfast", "features": "Sky Lounge, Fitness Center, Near Metro"},
                    "luxury": {"name": "The Ritz-Carlton Tokyo / Aman Tokyo", "stars": 5, "rate": 45000, "area": "Roppongi, Tokyo", "address": "Tokyo Midtown, 9-7-1 Akasaka, Minato, Tokyo 107-6245, Japan", "room": "Club Deluxe Mount Fuji View Suite", "meal": "Michelin Star Executive Breakfast", "features": "53rd Floor Skyline Views, Luxury Spa, Club Lounge"}
                }
            },
            {
                "city": "Hakone & Mt. Fuji",
                "display_name": "Hakone & Mount Fuji",
                "nights": 1,
                "region_tag": "Volcanic Onsen & Alpine Lake",
                "transfer": "Tokyo - Hakone Private Scenic Mountain Transfer Included",
                "hotels": {
                    "budget": {"name": "Hakone Kowakien Ten-yu", "stars": 4, "rate": 11000, "area": "Ninotaira, Hakone", "address": "1297 Ninotaira, Hakone, Ashigarashimo, Kanagawa 250-0407, Japan", "room": "Open-Air Onsen Bath Room", "meal": "Traditional Kaiseki Dinner & Breakfast", "features": "Natural Hot Spring Onsen, Mountain Views"},
                    "value": {"name": "Hakone Kowakien Ten-yu", "stars": 4.5, "rate": 16000, "area": "Ninotaira, Hakone", "address": "1297 Ninotaira, Hakone, Ashigarashimo, Kanagawa 250-0407, Japan", "room": "Superior Japanese-Western Suite", "meal": "Kaiseki Multi-Course Dining", "features": "Private Forest Onsen, Japanese Garden"},
                    "luxury": {"name": "Gora Kadan Luxury Ryokan", "stars": 5, "rate": 55000, "area": "Gora, Hakone", "address": "1300 Gora, Hakone, Ashigarashimo, Kanagawa 250-0408, Japan", "room": "Imperial Villa Suite with Private Open-Air Onsen", "meal": "Royal Kaiseki Imperial Banquet", "features": "Former Imperial Family Villa, Private Mineral Onsen"}
                }
            },
            {
                "city": "Kyoto",
                "display_name": "Kyoto Ancient Imperial Capital",
                "nights": 2,
                "region_tag": "Kansai Zen Temples & Geishas",
                "transfer": "Shinkansen Bullet Train Hakone/Tokyo to Kyoto Included",
                "hotels": {
                    "budget": {"name": "Daiwa Roynet Hotel Kyoto Ekimae", "stars": 4, "rate": 7800, "area": "Shimogyo, Kyoto", "address": "7-1 Higashishiokojicho, Shimogyo, Kyoto 600-8216, Japan", "room": "Standard Double", "meal": "Buffet Breakfast", "features": "Direct Kyoto Station Access"},
                    "value": {"name": "Hotel Granvia Kyoto", "stars": 4.5, "rate": 13500, "area": "Kyoto Station Complex", "address": "Karasuma-dori, Shiokoji-sagaru, Shimogyo, Kyoto 600-8216, Japan", "room": "Deluxe Superior Room", "meal": "Buffet Breakfast", "features": "Indoor Pool, Fitness, Central Location"},
                    "luxury": {"name": "The Ritz-Carlton Kyoto / Four Seasons Kyoto", "stars": 5, "rate": 48000, "area": "Kamogawa River, Nakagyo, Kyoto", "address": "Kamogawa Nijo-Ohashi Hotori, Nakagyo, Kyoto 604-0902, Japan", "room": "Kamogawa River Luxury Suite", "meal": "Chef Curated Gastronomy", "features": "Overlooking Kamogawa River, Zen Garden, Michelin Dining"}
                }
            },
            {
                "city": "Osaka",
                "display_name": "Osaka Gastronomic Capital",
                "nights": 2,
                "region_tag": "Kansai Culinary & Castle Hub",
                "transfer": "Private Scenic Transfer Kyoto to Osaka Included",
                "hotels": {
                    "budget": {"name": "Cross Hotel Osaka", "stars": 4, "rate": 7200, "area": "Chuo, Dotonbori, Osaka", "address": "2-5-15 Shinsaibashisuji, Chuo, Osaka 542-0085, Japan", "room": "Standard Double", "meal": "Buffet Breakfast", "features": "Steps from Dotonbori Canal"},
                    "value": {"name": "Swissotel Nankai Osaka", "stars": 4.5, "rate": 12500, "area": "Namba, Osaka", "address": "5-1-60 Namba, Chuo, Osaka 542-0076, Japan", "room": "Premier Superior Room", "meal": "Buffet Breakfast", "features": "Above Namba Station, 6 Restaurants, Spa"},
                    "luxury": {"name": "Conrad Osaka / The St. Regis Osaka", "stars": 5, "rate": 42000, "area": "Kita, Nakanoshima, Osaka", "address": "3-2-4 Nakanoshima, Kita, Osaka 530-0005, Japan", "room": "Executive River View Sky Suite", "meal": "Gourmet All-Inclusive Breakfast", "features": "40th Floor Sky Lobby, Heated Pool, Spa"}
                }
            }
        ],
        "days": [
            {
                "day_num": 1,
                "title": "Arrival in Tokyo & Asakusa Senso-ji Heritage Walk",
                "desc": "-Arrival at Tokyo Haneda Airport (HND) & private transfer to hotel. -Check-in & refresh. -Visit historic Senso-ji Temple in Asakusa and stroll Nakamise Dori. -Tokyo Skytree evening panorama.",
                "meals": "Dinner Included",
                "transfer_type": "Private",
                "photo_caption": "Tokyo: Senso-ji Temple Asakusa & Tokyo Skytree",
                "city_hub": "Tokyo",
                "region_tag": "Metropolis Gateway",
                "morning": "Flight arrival at Tokyo Haneda Airport (HND). Airport meet & greet with private transfer to Tokyo hotel.",
                "afternoon": "Visit Tokyo's oldest and most sacred Buddhist temple, Senso-ji in Asakusa. Browse authentic craft and sweets stalls along Nakamise-dori.",
                "evening": "Ascend Tokyo Skytree (634m) for breathtaking 360-degree panoramic skyline views. Welcome Japanese Ramen and Yakitori dinner.",
                "major_attractions": ["Senso-ji Temple Asakusa", "Nakamise-dori", "Tokyo Skytree", "Sumida River Promenade"],
                "inclusions": "Airport Private Pickup, Skytree Pass, Temple Guide"
            },
            {
                "day_num": 2,
                "title": "Meiji Shrine, Shibuya Crossing & Akihabara Electric Town",
                "desc": "-Post Breakfast, walk through tranquil cedar forest to Meiji Jingu Shrine. -Witness world-famous Shibuya Scramble Crossing & Hachiko Statue. -Explore futuristic Akihabara Electric Town and Ginza luxury boulevard.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Tokyo: Shibuya Scramble Crossing & Meiji Shrine",
                "city_hub": "Tokyo",
                "region_tag": "Modern Culture",
                "morning": "Visit serene Meiji Jingu Shrine enveloped in a 170-acre forest in Harajuku. Stroll trendy Takeshita Street.",
                "afternoon": "Experience the famous Shibuya Scramble Crossing, the world's busiest pedestrian intersection, and pay tribute to Hachiko Statue.",
                "evening": "Explore the neon-drenched anime and tech wonderland of Akihabara Electric Town, followed by fine dining in Ginza.",
                "major_attractions": ["Meiji Jingu Shrine", "Shibuya Scramble Crossing & Hachiko", "Akihabara Electric Town", "Ginza District"],
                "inclusions": "Private AC Van, English Speaking Guide, Public Transit Experience"
            },
            {
                "day_num": 3,
                "title": "Mt. Fuji 5th Station & Lake Ashi Pirate Ship Cruise in Hakone",
                "desc": "-Post Breakfast, scenic drive ascending Mount Fuji to 5th Station (2,305m). -Pirate boat cruise across crater Lake Ashi in Hakone. -Hakone Ropeway over steaming Owakudani volcanic valley. -Overnight stay at hot spring onsen ryokan.",
                "meals": "Breakfast, Dinner",
                "transfer_type": "Private",
                "photo_caption": "Mount Fuji & Lake Ashi Pirate Cruise Hakone",
                "city_hub": "Hakone & Mt. Fuji",
                "region_tag": "Volcanic Alpine",
                "morning": "Scenic morning drive ascending winding slopes of Mount Fuji to 5th Station (2,305 meters) for breathtaking views above the cloud sea.",
                "afternoon": "Board a majestic pirate ship cruise across Lake Ashi, admiring red torii gate of Hakone Shrine rising from water. Ride Hakone Ropeway over volcanic Owakudani Valley.",
                "evening": "Check-in at traditional Japanese Onsen Ryokan. Relax in therapeutic mineral hot spring baths. Multi-course Kaiseki dinner.",
                "major_attractions": ["Mt. Fuji 5th Station", "Lake Ashi Pirate Cruise", "Hakone Ropeway & Owakudani Valley", "Hakone Shrine Torii Gate"],
                "inclusions": "Private AC Mountain Van, Lake Cruise Pass, Ropeway Tickets, Kaiseki Dinner"
            },
            {
                "day_num": 4,
                "title": "Shinkansen Bullet Train to Kyoto & Fushimi Inari 10,000 Torii Gates",
                "desc": "-Board world-famous Shinkansen Bullet Train speeding to Kyoto at 300 km/h. -Check-in at Kyoto hotel. -Afternoon pilgrimage through thousands of vermilion torii gates at Fushimi Inari-taisha. -Twilight stroll through historic Gion geisha district.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Kyoto: Fushimi Inari-taisha 10,000 Vermilion Torii Gates",
                "city_hub": "Kyoto",
                "region_tag": "Zen Heritage",
                "morning": "Board high-speed Shinkansen Bullet Train gliding smoothly through Japanese countryside to imperial capital of Kyoto.",
                "afternoon": "Visit iconic Fushimi Inari-taisha shrine, walking through mesmerizing mountain trails flanked by over 10,000 vibrant vermilion torii gates.",
                "evening": "Twilight walking tour through historic Gion preservation district with traditional wooden machiya merchant houses. Spot elegant geishas (geiko/maiko).",
                "major_attractions": ["Shinkansen Bullet Train", "Fushimi Inari-taisha 10,000 Torii Gates", "Gion Geisha District", "Shirakawa Canal"],
                "inclusions": "Shinkansen Bullet Train Ticket, Kyoto Private Transfer, Temple Guide"
            },
            {
                "day_num": 5,
                "title": "Kinkaku-ji (Golden Pavilion) & Arashiyama Bamboo Grove",
                "desc": "-Post Breakfast, marvel at gold-leaf Kinkaku-ji (Golden Pavilion) mirrored on Kyoko-chi pond. -Walk through enchanting Arashiyama Bamboo Grove & Tenryu-ji Zen temple. -Cross historic Togetsukyo Bridge.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Kyoto: Kinkaku-ji Golden Pavilion & Arashiyama Bamboo",
                "city_hub": "Kyoto",
                "region_tag": "Zen Architecture",
                "morning": "Visit world-famous Kinkaku-ji (Golden Pavilion), a Zen Buddhist temple covered in pure gold leaf reflecting brilliantly over mirror pond.",
                "afternoon": "Stroll through towering emerald Arashiyama Bamboo Grove, listening to wind rustling bamboo stalks. Visit UNESCO Tenryu-ji temple garden.",
                "evening": "Walk across historic wooden Togetsukyo Bridge (Moon Crossing Bridge) spanning Oi River. Authentic matcha green tea tasting.",
                "major_attractions": ["Kinkaku-ji (Golden Pavilion)", "Arashiyama Bamboo Grove", "Tenryu-ji Temple", "Togetsukyo Bridge"],
                "inclusions": "Private AC Van, Temple Passes, Matcha Tea Ceremony"
            },
            {
                "day_num": 6,
                "title": "Osaka Castle Heritage & Dotonbori Neon Culinary Street Tour",
                "desc": "-Scenic morning drive to Osaka. -Explore historic Osaka Castle & gardens. -Afternoon shopping in Shinsaibashi. -Evening Dotonbori neon canal cruise & tasting Takoyaki (octopus balls) and Okonomiyaki.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Osaka: Osaka Castle & Dotonbori Glico Man Neon",
                "city_hub": "Osaka",
                "region_tag": "Culinary Capital",
                "morning": "Private morning drive from Kyoto to Osaka. Tour imposing 16th-century Osaka Castle, its massive stone ramparts and surrounding moat.",
                "afternoon": "Explore Shinsaibashi-suji, Osaka's premier covered shopping avenue featuring hundreds of boutiques and Japanese craft shops.",
                "evening": "Night stroll through sensory wonderland of Dotonbori canal, iconic Glico Running Man neon sign, and tasting freshly grilled Takoyaki & Okonomiyaki.",
                "major_attractions": ["Osaka Castle & Park", "Dotonbori Canal & Glico Neon Sign", "Shinsaibashi Shopping Arcade", "Kuromon Ichiba Food Market"],
                "inclusions": "Inter-City Transfer, Castle Entry Pass, Dotonbori Food Walk"
            },
            {
                "day_num": 7,
                "title": "Kuromon Market Souvenirs & Departure from Kansai Airport",
                "desc": "-Post Breakfast, morning visit to Kuromon Ichiba Market for Japanese knives, ceramics & matcha snacks. -Private transfer to Kansai International Airport (KIX). -Board return flight home.",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Kansai International Airport (KIX) Departure",
                "city_hub": "Osaka / Departure",
                "region_tag": "Departure Hub",
                "morning": "Enjoy gourmet hotel breakfast. Last-minute Japanese artisan souvenir shopping at Kuromon Ichiba Market.",
                "afternoon": "Hotel check-out. Private transfer across scenic bay bridge to Kansai International Airport (KIX).",
                "evening": "Board return international flight. Safe journey home with memories of the Land of the Rising Sun!",
                "major_attractions": ["Kuromon Ichiba Market", "Kansai International Airport (KIX)"],
                "inclusions": "Airport Private Transfer, Luggage Assistance, Return Flight"
            }
        ]
    },
    "bhutan": {
        "country": "Bhutan",
        "circuit_title": "Bhutan Himalayan Kingdom of Happiness: Thimphu, Punakha & Paro Valley",
        "base_flight_fare": 18500,
        "overview": (
            "Bhutan, the mystical Land of the Thunder Dragon, is a pristine Himalayan kingdom nestled among snow-capped peaks, "
            "sacred ancient dzongs, fluttering prayer flags, and deep pine valleys. Measured by Gross National Happiness, "
            "this curated circuit journeys through the royal capital of Thimphu, crosses the scenic 3,100-meter Dochula Pass with panoramic "
            "views of the Eastern Himalayas, explores the dramatic riverside fortress of Punakha Dzong, and ascends to the awe-inspiring "
            "clifftop Tiger's Nest Monastery (Paro Taktsang) suspended 900 meters above the Paro Valley floor."
        ),
        "tour_highlights": [
            "Confirmed Flights Ex-{source} to Paro International Airport (PBH) via Drukair / Bhutan Airlines",
            "Stay with Daily Buffet Breakfast & Multi-Course Bhutanese Dinners at 4-Star & 5-Star Heritage Resorts",
            "Legendary Pilgrimage Hike to Clifftop Tiger's Nest Monastery (Paro Taktsang, 3,120m)",
            "Majestic Punakha Dzong (Palace of Great Happiness) & Pho Chhu Long Suspension Bridge",
            "Scenic Mountain Drive crossing Dochula Pass with 108 Druk Wangyal Chortens & Himalayan Panorama",
            "Giant Buddha Dordenma (169ft Gilded Bronze Statue overlooking Thimphu Valley)",
            "Tashichho Dzong Royal Fortress, National Memorial Chorten & Motithang Takin Preserve",
            "National Museum of Bhutan (Ta Dzong) & 15th-Century Rinpung Dzong in Paro",
            "Chimi Lhakhang (Temple of the Divine Madman) Paddy Field Walk & Traditional Hot Stone Bath"
        ],
        "cities": [
            {
                "city": "Thimphu",
                "display_name": "Thimphu (Royal Capital & Cultural Heart)",
                "nights": 2,
                "region_tag": "Himalayan Capital Valley",
                "transfer": "Paro International Airport (PBH) to Thimphu via Pa Chhu & Wang Chhu Valley Included",
                "hotels": {
                    "budget": {"name": "Hotel Norbuling Thimphu", "stars": 4, "rate": 4500, "area": "Chang Lam, Thimphu", "address": "Chang Lam, Post Box 1445, Thimphu, Bhutan", "room": "Deluxe Mountain View Room", "meal": "Buffet Breakfast & Dinner", "features": "Walking Distance to Clock Tower, Traditional Bhutanese Decor"},
                    "value": {"name": "Hotel Druk Thimphu / Kisa Villa", "stars": 4.5, "rate": 7800, "area": "Clock Tower Square, Thimphu", "address": "Wogzin Lam, Clock Tower Square, Thimphu, Bhutan", "room": "Superior Deluxe Valley Suite", "meal": "Buffet Breakfast & Dinner", "features": "Central Location, Multi-Cuisine Restaurant, Spa, Fitness Center"},
                    "luxury": {"name": "Le Méridien Thimphu / Pemako Thimphu", "stars": 5, "rate": 26000, "area": "Chorten Lam, Thimphu", "address": "Chorten Lam, Thimphu, Bhutan", "room": "Royal Classic Heritage Suite", "meal": "Five-Course Gourmet Breakfast & Dinner", "features": "Five-Star Luxury, Heated Indoor Pool, Explore Spa, Royal Hospitality"}
                }
            },
            {
                "city": "Punakha",
                "display_name": "Punakha Valley (Ancient Capital & Subtropical Dzongs)",
                "nights": 2,
                "region_tag": "Subtropical River Valley",
                "transfer": "Thimphu to Punakha via Dochula Pass (3,100m) Included on private basis",
                "hotels": {
                    "budget": {"name": "Hotel Pema Karpo Punakha", "stars": 4, "rate": 4200, "area": "Puna Tsang Chhu River, Punakha", "address": "Bajo Town, Punakha, Bhutan", "room": "Riverside Deluxe Room", "meal": "Buffet Breakfast & Dinner", "features": "River Views, Traditional Architecture, Mountain Backdrop"},
                    "value": {"name": "The Four Boutique Hotel / Zhingkham Resort", "stars": 4.5, "rate": 8200, "area": "Lobesa Valley, Punakha", "address": "Logodama, Punakha, Bhutan", "room": "Panoramic Valley Balcony Room", "meal": "Buffet Breakfast & Dinner", "features": "Overlooking Punakha Valley & Paddy Terraces, Spa, Organic Garden"},
                    "luxury": {"name": "Dhensa Boutique Resort / RKPO Green Resort", "stars": 5, "rate": 28500, "area": "Pine Forest Ridge, Punakha", "address": "Wolakha, Punakha, Bhutan", "room": "Deluxe Pine Forest Balcony Suite", "meal": "All-Inclusive Artisanal Himalayan Dining", "features": "Nestled in Pine Forests, Luxury Handcrafted Spa, Yoga Pavilion"}
                }
            },
            {
                "city": "Paro",
                "display_name": "Paro (Sacred Valley & Tiger's Nest Gateway)",
                "nights": 3,
                "region_tag": "Alpine Valley & Sacred Monasteries",
                "transfer": "Punakha to Paro Valley via scenic Himalayan highway Included on private basis",
                "hotels": {
                    "budget": {"name": "Hotel Olathang Paro", "stars": 4, "rate": 4500, "area": "Pine Hill, Paro", "address": "Olathang Pine Ridge, Paro, Bhutan", "room": "Heritage Cottage Room", "meal": "Buffet Breakfast & Dinner", "features": "Built for 1974 Royal Coronation, Traditional Fireplaces, Mountain Views"},
                    "value": {"name": "Tashi Namgay Resort / Metta Resort & Spa", "stars": 4.5, "rate": 7900, "area": "Pa Chhu Riverfront, Paro", "address": "Opposite Paro International Airport, Paro, Bhutan", "room": "Deluxe Riverfront Suite", "meal": "Buffet Breakfast & Dinner", "features": "Pa Chhu Riverfront, Herbal Hot Stone Bath, Traditional Archery Ground"},
                    "luxury": {"name": "Le Méridien Paro Riverfront / Zhiwa Ling Heritage", "stars": 5, "rate": 32000, "area": "Pa Chhu Riverfront, Paro", "address": "Paro Riverfront, Shaba, Paro, Bhutan", "room": "Grand Corner River & Himalayan Suite", "meal": "Michelin-Standard Himalayan Royal Gastronomy", "features": "Direct View of Pa Chhu River, World-Class Spa, Heated Swimming Pool"}
                }
            }
        ],
        "days": [
            {
                "day_num": 1,
                "min_days": 1,
                "title": "Arrival in Paro (PBH), Scenic Drive to Thimphu & National Memorial Chorten",
                "desc": "-Thrilling Himalayan arrival at Paro International Airport (PBH) with views of Mt. Everest and Kanchenjunga. -Private transfer along Pa Chhu & Wang Chhu rivers to capital city Thimphu (2,334m). -Hotel check-in & butter tea welcome. -Afternoon circumambulation of National Memorial Chorten with local elders. -Evening orientation walk around Clock Tower Square.",
                "meals": "Dinner Included",
                "transfer_type": "Private",
                "photo_caption": "Thimphu: National Memorial Chorten & Pa Chhu River Valley",
                "city_hub": "Thimphu",
                "region_tag": "Royal Gateway",
                "morning": "Fly into Paro International Airport (PBH), ranked among the world's most spectacular mountain descents. Traditional Tashi Khaddar scarf welcome by your private Bhutanese guide and chauffeur.",
                "afternoon": "Scenic 1.5-hour drive following the confluence of Pa Chhu and Wang Chhu rivers to the capital Thimphu. Check-in at your luxury hotel and refresh with traditional Suja (butter tea). Visit the revered National Memorial Chorten, built in 1974.",
                "evening": "Leisure evening stroll around Clock Tower Square and Norzin Lam boulevard, browsing authentic Bhutanese handicraft shops and observing traditional archers.",
                "major_attractions": ["Paro International Airport (PBH)", "Pa Chhu & Wang Chhu River Confluence", "National Memorial Chorten", "Clock Tower Square Thimphu"],
                "inclusions": "Paro Airport Meet & Greet, Private AC SUV Transfer, Entry Monument Permits, Welcome Dinner"
            },
            {
                "day_num": 2,
                "min_days": 2,
                "title": "Thimphu Valley Wonders: Giant Buddha Dordenma, Takin Preserve & Tashichho Dzong",
                "desc": "-Ascend Kuenselphodrang ridge to marvel at 169ft golden Buddha Dordenma overlooking Thimphu valley. -Visit Motithang Takin Preserve to observe Bhutan's unique national animal. -Explore National Institute for Zorig Chusum (13 Traditional Arts & Crafts). -Sunset visit to magnificent Tashichho Dzong (Fortress of the Glorious Religion).",
                "meals": "Breakfast & Dinner",
                "transfer_type": "Private",
                "photo_caption": "Thimphu: Giant Buddha Dordenma & Tashichho Dzong Fortress",
                "city_hub": "Thimphu",
                "region_tag": "Royal Citadel",
                "morning": "Morning drive to Kuenselphodrang Nature Park to stand before Buddha Dordenma, a colossal 51.5-meter bronze statue housing 125,000 smaller gilded Buddha statues with panoramic vistas across Thimphu Valley.",
                "afternoon": "Visit the Motithang Takin Preserve to witness Bhutan's mythological national animal, the Takin. Tour the National Institute for Zorig Chusum, observing master artisans and students painting thangkas, carving wood, and weaving textiles.",
                "evening": "Visit the monumental Tashichho Dzong, seat of the Bhutanese government and central monastic body. Witness the ceremonial lowering of the national flag and admire the whitewashed fortress against the twilight sky.",
                "major_attractions": ["Buddha Dordenma (Kuenselphodrang)", "Motithang Takin Preserve", "National Institute for Zorig Chusum", "Tashichho Dzong Royal Fortress"],
                "inclusions": "Private SUV & Guide, Takin Preserve Permit, Dzong Entry Access, Gourmet Dinner"
            },
            {
                "day_num": 3,
                "min_days": 7,
                "title": "Thimphu Living Culture: Centenary Farmers Market, Folk Heritage Museum & Jungshi Paper",
                "desc": "-Explore vibrant Centenary Farmers Market with local farmers selling organic Himalayan vegetables, yak cheese & spices. -Cross traditional wooden cantilever bridge to browse authentic handicraft stalls. -Visit Folk Heritage Museum & Jungshi Handmade Paper Factory. -Evening scenic drive to Sangaygang BBS Tower viewpoint.",
                "meals": "Breakfast & Dinner",
                "transfer_type": "Private",
                "photo_caption": "Thimphu: Folk Heritage Museum & Centenary Organic Market",
                "city_hub": "Thimphu",
                "region_tag": "Living Traditions",
                "morning": "Immerse in local life at the Centenary Farmers Market on the banks of Wang Chhu river. Stroll across the traditional wooden cantilever bridge to the handicraft market offering hand-woven silk kiras and wooden masks.",
                "afternoon": "Tour the Folk Heritage Museum, a restored 19th-century three-storey timber farmhouse displaying rural Bhutanese life. Visit the Jungshi Handmade Paper Factory to see traditional Deh-sho paper made from the daphne shrub.",
                "evening": "Drive up to Sangaygang (BBS Tower) at 2,685 meters for a sweeping twilight view of the entire Thimphu Valley draped in thousands of colorful prayer flags.",
                "major_attractions": ["Centenary Farmers Market", "Traditional Wooden Cantilever Bridge", "Folk Heritage Museum", "Jungshi Handmade Paper Factory", "Sangaygang Viewpoint"],
                "inclusions": "Private Transport, Museum Entry Fees, Craft Workshop Experience, Dinner"
            },
            {
                "day_num": 4,
                "min_days": 3,
                "title": "Scenic Mountain Pass Drive across Dochula Pass (3,100m) to Subtropical Punakha",
                "desc": "-Ascend through pine and rhododendron forests to Dochula Pass (3,100m). -Marvel at 108 Druk Wangyal Chortens with panoramic views of snow-capped Himalayan peaks. -Descend through lush valleys to fertile Punakha (1,242m). -Afternoon walk through green paddy fields to Chimi Lhakhang (Fertility Temple).",
                "meals": "Breakfast & Dinner",
                "transfer_type": "Private",
                "photo_caption": "Dochula Pass: 108 Druk Wangyal Chortens & Himalayan Panorama",
                "city_hub": "Punakha",
                "region_tag": "Mountain Passes",
                "morning": "Scenic morning drive climbing to Dochula Pass at 3,100 meters. On clear days, marvel at the jaw-dropping 360-degree panorama of snow-capped Himalayan peaks, including Gangkhar Puensum (7,570m), the world's highest unclimbed mountain. Walk around the 108 Druk Wangyal Chortens.",
                "afternoon": "Descend 1,800 meters through subtropical banana and cactus valleys into warmer Punakha. Enjoy a picturesque 30-minute walk through terraced rice fields in Sopsokha village to sacred Chimi Lhakhang, the 15th-century temple of Drukpa Kunley (the Divine Madman).",
                "evening": "Check-in at your valley resort overlooking the Puna Tsang Chhu river. Relax amidst tranquil subtropical gardens with dinner featuring organic local produce.",
                "major_attractions": ["Dochula Pass (3,100m)", "108 Druk Wangyal Memorial Chortens", "Chimi Lhakhang Fertility Temple", "Sopsokha Village Rice Terraces"],
                "inclusions": "Dochula Pass Excursion, Temple Entry Permits, Village Cultural Walk, Dinner"
            },
            {
                "day_num": 5,
                "min_days": 4,
                "title": "Punakha Imperial Grandeur: Punakha Dzong & Longest Pho Chhu Suspension Bridge",
                "desc": "-Visit majestic Punakha Dzong (Palace of Great Happiness), situated at the confluence of Pho Chhu (father) & Mo Chhu (mother) rivers. -Walk across Bhutan's longest Pho Chhu Suspension Bridge (160m). -Scenic hike to Khamsum Yulley Namgyal Chorten through pine terraces.",
                "meals": "Breakfast & Dinner",
                "transfer_type": "Private",
                "photo_caption": "Punakha: Punakha Dzong at River Confluence & Suspension Bridge",
                "city_hub": "Punakha",
                "region_tag": "Ancient Royal Citadel",
                "morning": "Explore the architectural masterpiece of Punakha Dzong, built in 1637 by Zhabdrung Ngawang Namgyal. Admire the golden spire, six-storey central utse tower, sacred coronation hall, and intricate murals depicting the life of Buddha.",
                "afternoon": "Walk across Bhutan's longest suspension bridge (160 meters) spanning the rushing turquoise waters of Pho Chhu river, festooned with colorful prayer flags. Hike up through terraced hillsides to the four-storey Khamsum Yulley Namgyal Chorten for breathtaking valley vistas.",
                "evening": "Peaceful riverbank stroll along the Mo Chhu river. Optional white-water rafting experience on gentle Class II-III rapids. Evening dinner at resort.",
                "major_attractions": ["Punakha Dzong (Pungtang Dechen Photrang)", "Pho Chhu Long Suspension Bridge", "Khamsum Yulley Namgyal Chorten", "Pho Chhu & Mo Chhu River Confluence"],
                "inclusions": "Dzong & Chorten Permits, Suspension Bridge Walk, Private Guide, Dinner"
            },
            {
                "day_num": 6,
                "min_days": 6,
                "title": "Punakha Excursion to Phobjikha Glacial Valley & 17th-Century Gangtey Monastery",
                "desc": "-Day trip ascending to the pristine U-shaped glacial valley of Phobjikha (3,000m). -Visit historic Gangtey Goenpa monastery perched on hill crest. -Walk the serene Gangtey Nature Trail through dwarf bamboo meadows. -Visit Black-Necked Crane Conservation Centre.",
                "meals": "Breakfast & Dinner",
                "transfer_type": "Private",
                "photo_caption": "Phobjikha Valley: Gangtey Monastery & Crane Sanctuary",
                "city_hub": "Punakha",
                "region_tag": "Glacial Wilderness",
                "morning": "Scenic drive winding over Pele La Pass (3,420m) into the breathtaking high-altitude valley of Phobjikha. Tour Gangtey Goenpa, the premier Nyingma monastery dating to 1613 with exquisite woodwork and sacred prayer halls.",
                "afternoon": "Embark on the gentle 1.5-hour Gangtey Nature Trail, meandering through tranquil pine forests, open meadows, and traditional stone farmhouses. Visit the Black-Necked Crane Information Centre to learn about the revered migratory birds that fly in from the Tibetan Plateau.",
                "evening": "Scenic return drive to Punakha valley. Savor hot Bhutanese butter tea and hearty dinner at hotel.",
                "major_attractions": ["Gangtey Goenpa Monastery", "Phobjikha Glacial Valley", "Gangtey Nature Trail", "Black-Necked Crane Information Centre", "Pele La Pass (3,420m)"],
                "inclusions": "Phobjikha Day Excursion, Crane Centre Entry, Nature Trail Guide, Dinner"
            },
            {
                "day_num": 7,
                "min_days": 5,
                "title": "Scenic Return to Paro Valley: National Museum (Ta Dzong) & Rinpung Dzong",
                "desc": "-Scenic return drive from Punakha to Paro Valley (2,200m). -Visit Ta Dzong, an ancient circular watchtower housing the National Museum of Bhutan. -Explore Rinpung Dzong (Fortress on a Heap of Jewels) & traditional Nyamai Zam wooden bridge. -Evening Paro town market stroll.",
                "meals": "Breakfast & Dinner",
                "transfer_type": "Private",
                "photo_caption": "Paro: Rinpung Dzong Fortress & Ta Dzong National Museum",
                "city_hub": "Paro",
                "region_tag": "Sacred Valley",
                "morning": "Scenic morning drive re-crossing Dochula Pass and descending into the lush willow-fringed Paro Valley. Check-in at your luxury riverfront resort in Paro.",
                "afternoon": "Visit Ta Dzong, a circular 17th-century fortress watchtower transformed into the National Museum of Bhutan, showcasing ancient weaponry, royal thangkas, and rare natural heritage exhibits. Walk down to Rinpung Dzong, one of Bhutan's finest fortresses, and cross the romantic roofed wooden cantilever bridge (Nyamai Zam).",
                "evening": "Stroll down Paro's quaint main street with wooden storefronts selling traditional silver jewellery, yak wool shawls, and handmade prayer wheels. Dinner at hotel.",
                "major_attractions": ["National Museum of Bhutan (Ta Dzong)", "Rinpung Dzong (Paro Dzong)", "Nyamai Zam Wooden Cantilever Bridge", "Paro Main Town Bazaar"],
                "inclusions": "Museum Entry Passes, Rinpung Dzong Entry, Private SUV, Guide, Dinner"
            },
            {
                "day_num": 8,
                "min_days": 1,
                "title": "The Ultimate Pilgrimage: Hike to Clifftop Tiger's Nest Monastery (Paro Taktsang)",
                "desc": "-Early morning ascent through blue pine forests festooned with Spanish moss to world-famous Tiger's Nest Monastery (Paro Taktsang, 3,120m). -Clifftop tea house break with breathtaking views. -Explore sacred cave temples where Guru Rinpoche meditated. -Evening herbal hot stone bath & celebration dinner.",
                "meals": "Breakfast & Dinner",
                "transfer_type": "Private",
                "photo_caption": "Paro: Tiger's Nest Monastery (Paro Taktsang, 3,120m)",
                "city_hub": "Paro",
                "region_tag": "Clifftop Pilgrimage",
                "morning": "Embark on Bhutan's most iconic pilgrimage hike to Paro Taktsang (Tiger's Nest), precariously clinging to a sheer granite cliff 900 meters above the valley floor. Ascend through pine forests to the Taktsang Cafeteria for panoramic photos and tea.",
                "afternoon": "Continue past sacred waterfalls and prayer flags across the chasm to enter the temple complex. Explore the sacred cave where Guru Padmasambhava meditated in the 8th century, the golden statues, and butter lamp halls. Descend back to the valley base.",
                "evening": "Relax weary muscles in a traditional Bhutanese Dotsho (Hot Stone Bath), heated by river stones baked in fire and infused with medicinal Artemisia leaves. Special farewell Bhutanese dinner.",
                "major_attractions": ["Paro Taktsang (Tiger's Nest Monastery)", "Taktsang Viewpoint Cafeteria", "Guru Rinpoche Meditation Cave", "Traditional Bhutanese Hot Stone Bath"],
                "inclusions": "Tiger's Nest Temple Special Permit, Experienced Trek Guide, Hot Stone Bath, Festive Dinner"
            },
            {
                "day_num": 9,
                "min_days": 8,
                "title": "Sacred Paro Heritage: 7th-Century Kyichu Lhakhang & Drukgyel Dzong Ramparts",
                "desc": "-Visit ancient Kyichu Lhakhang, one of Bhutan's oldest temples built in 659 AD by Tibetan King Songtsen Gampo. -Explore historic ruins and reconstructed ramparts of Drukgyel Dzong (Fortress of the Victorious Drukpas). -View Mt. Jomolhari (7,326m) on clear days.",
                "meals": "Breakfast & Dinner",
                "transfer_type": "Private",
                "photo_caption": "Paro: Kyichu Lhakhang Royal Temple & Drukgyel Dzong",
                "city_hub": "Paro",
                "region_tag": "Sacred Heritage",
                "morning": "Morning pilgrimage to Kyichu Lhakhang, one of the 108 border-taming temples built by Tibetan King Songtsen Gampo in 659 AD. Spin the ancient prayer wheels and admire the miraculous 7th-century statue of Jowo Jamba.",
                "afternoon": "Drive to the northern end of Paro Valley to visit Drukgyel Dzong, built in 1649 to commemorate victory over Tibetan invasion forces. On clear days, enjoy an imposing view of sacred snow-capped Mt. Jomolhari (7,326m).",
                "evening": "Visit a traditional local farmhouse for an authentic home-hosted dinner. Learn to prepare Ema Datshi (chilli and yak cheese), Bhutan's beloved national dish.",
                "major_attractions": ["Kyichu Lhakhang (659 AD)", "Drukgyel Dzong Victory Fortress", "Mt. Jomolhari Himalayan Viewpoint", "Traditional Farmhouse Cooking Experience"],
                "inclusions": "Kyichu Lhakhang Permits, Drukgyel Entry, Farmhouse Hospitality & Dinner"
            },
            {
                "day_num": 10,
                "min_days": 10,
                "title": "Himalayan Ridge Mountain Safari: Chele La Pass (3,988m) & Untouched Haa Valley",
                "desc": "-Early morning drive ascending winding alpine forests to Chele La Pass (3,988m), the highest motorable road in Bhutan. -Stunning views of Mt. Jomolhari and Jichu Drake. -Descend into pristine and culturally isolated Haa Valley. -Visit Lhakhang Karpo (White Temple) & Lhakhang Nagpo (Black Temple).",
                "meals": "Breakfast & Dinner",
                "transfer_type": "Private",
                "photo_caption": "Chele La Pass (3,988m): Prayer Flags & Himalayan Peaks",
                "city_hub": "Paro",
                "region_tag": "High Alpine Frontier",
                "morning": "Scenic 1.5-hour drive ascending through dense blue pine, oak, and rhododendron forests to Chele La Pass at 3,988 meters. Marvel at thousands of colorful prayer flags fluttering in the mountain wind against a backdrop of snow-capped peaks.",
                "afternoon": "Descend into the pristine and secluded Haa Valley, opened to tourism only in 2002. Visit the sacred twin temples of Lhakhang Karpo (White Temple) and Lhakhang Nagpo (Black Temple) at the foot of the sacred Meri Puensum hills.",
                "evening": "Return drive over the mountain pass back to Paro Valley. Enjoy a relaxed evening and multi-course dinner at your resort.",
                "major_attractions": ["Chele La Pass (3,988m)", "Mt. Jomolhari & Jichu Drake Panoramas", "Haa Valley Alpine Meadows", "Lhakhang Karpo & Lhakhang Nagpo Temples"],
                "inclusions": "High-Altitude 4WD SUV, Haa Valley Entry Permit, Private Guide, Dinner"
            },
            {
                "day_num": 11,
                "min_days": 11,
                "title": "Paro Artisanal Souvenirs, Traditional Archery & Valley Leisure Stroll",
                "desc": "-Post Breakfast, leisure morning along the willow-lined Pa Chhu riverbanks. -Try your hand at Bhutan's national sport of Archery (Dha) with traditional bamboo bows. -Browse local artisan craft shops for hand-carved masks, thangka scrolls, and cordyceps herbal tea. -Evening cultural dance showcase.",
                "meals": "Breakfast & Dinner",
                "transfer_type": "Private",
                "photo_caption": "Paro: Traditional Archery & Pa Chhu Willow Riverbanks",
                "city_hub": "Paro",
                "region_tag": "Artisanal Heritage",
                "morning": "Relaxed breakfast at resort with views of mist rising over pine ridges. Participate in an interactive Bhutanese national archery (Dha) experience with your guide at a traditional archery range.",
                "afternoon": "Last-minute souvenir shopping in Paro town for unique Himalayan treasures: authentic hand-woven yatra carpets, brass singing bowls, hand-carved wooden Phurba daggers, and Wild Himalayan honey.",
                "evening": "Enjoy a special cultural farewell evening at the resort featuring traditional Bhutanese Cham masked dances and folk songs celebrating Gross National Happiness.",
                "major_attractions": ["Traditional Bhutanese Archery Range", "Paro Handicraft & Thangka Studios", "Pa Chhu River Nature Walk", "Cultural Folk Music & Mask Dance Showcase"],
                "inclusions": "Archery Experience & Equipment, Guide, Cultural Dance Performance, Royal Dinner"
            },
            {
                "day_num": 12,
                "min_days": 1,
                "title": "Farewell to Bhutan: Departure from Paro International Airport (PBH)",
                "desc": "-Post Breakfast, hotel checkout and private transfer to Paro International Airport (PBH). -Board return international flight. -Safe journey home with unforgettable memories of the Kingdom of Happiness!",
                "meals": "Breakfast",
                "transfer_type": "Private",
                "photo_caption": "Paro International Airport (PBH) Runway & Alpine Valley",
                "city_hub": "Paro / Departure",
                "region_tag": "Departure Hub",
                "morning": "Enjoy your final Bhutanese buffet breakfast. Hotel check-out and private transfer to Paro International Airport (PBH), admired worldwide for its traditional pagodas and alpine setting.",
                "afternoon": "Board your return international flight on Drukair / Bhutan Airlines. Bid farewell to the Thunder Dragon kingdom as your aircraft soars above the Himalayan peaks.",
                "evening": "Safe arrival at your home destination. Cherish timeless memories of Bhutan!",
                "major_attractions": ["Paro Valley Viewpoint", "Paro International Airport (PBH)"],
                "inclusions": "Private Airport Transfer, Luggage Assistance, Return Flight"
            }
        ]
    }
}

# Real Destination Photographs Database
DESTINATION_REAL_PHOTOS_EXTENDED = {
    "vietnam": [
        ("banner_vietnam.jpg", "https://images.unsplash.com/photo-1528127269322-539801943592?w=1000&auto=format&fit=crop&q=80", "Ha Long Bay UNESCO World Heritage Emerald Karsts, Vietnam"),
        ("hanoi_hoankiem.jpg", "https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=600&auto=format&fit=crop&q=80", "Hanoi: Hoan Kiem Lake, Ngoc Son Temple & The Huc Bridge"),
        ("hanoi_literature.jpg", "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?w=600&auto=format&fit=crop&q=80", "Hanoi: Temple of Literature (Van Mieu Quoc Tu Giam)"),
        ("ninhbinh_trangan.jpg", "https://images.unsplash.com/photo-1576487248805-cf45f6bcc67f?w=600&auto=format&fit=crop&q=80", "Ninh Binh: Trang An UNESCO Karst Grottoes & Mua Dragon Peak"),
        ("halong_cruise.jpg", "https://images.unsplash.com/photo-1528127269322-539801943592?w=600&auto=format&fit=crop&q=80", "Ha Long Bay: Luxury Overnight Cruise & Limestone Karsts"),
        ("danang_dragonbridge.jpg", "https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?w=600&auto=format&fit=crop&q=80", "Da Nang: Dragon Bridge (Cau Rong) & My Khe Coastline"),
        ("danang_golden_bridge.jpg", "https://images.unsplash.com/photo-1583417319070-4a69db38a482?w=600&auto=format&fit=crop&q=80", "Ba Na Hills: World-Famous Golden Bridge Held by Giant Stone Hands"),
        ("hoian_lanterns.jpg", "https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?w=600&auto=format&fit=crop&q=80", "Hoi An Ancient Town: Thu Bon River Illuminated Lanterns"),
        ("myson_temples.jpg", "https://images.unsplash.com/photo-1583417319070-4a69db38a482?w=600&auto=format&fit=crop&q=80", "My Son Sanctuary: Ancient Red-Brick Cham Civilization Temples"),
        ("hue_citadel.jpg", "https://images.unsplash.com/photo-1576487248805-cf45f6bcc67f?w=600&auto=format&fit=crop&q=80", "Hue Imperial Citadel: Forbidden Purple City & Ngo Mon Gate"),
        ("dalat_waterfall.jpg", "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=600&auto=format&fit=crop&q=80", "Da Lat: Datanla Cascading Waterfall & Highland Pine Valleys"),
        ("dalat_truclam.jpg", "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=600&auto=format&fit=crop&q=80", "Da Lat: Truc Lam Zen Buddhist Monastery & Tuyen Lam Lake"),
        ("saigon_skyline.jpg", "https://images.unsplash.com/photo-1583417654171-995be1370bc7?w=600&auto=format&fit=crop&q=80", "Ho Chi Minh City (Saigon): Notre-Dame Cathedral & Bitexco Skydeck"),
        ("cuchi_tunnels.jpg", "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&auto=format&fit=crop&q=80", "Cu Chi Historic Underground Guerrilla War Tunnels (250km)"),
        ("mekong_delta.jpg", "https://images.unsplash.com/photo-1528127269322-539801943592?w=600&auto=format&fit=crop&q=80", "Mekong Delta: Traditional Hand-Rowed Sampan Coconut Canals"),
        ("landmark81.jpg", "https://images.unsplash.com/photo-1583417654171-995be1370bc7?w=600&auto=format&fit=crop&q=80", "Landmark 81 Saigon: Vietnam's Tallest 461m Skyscraper SkyView"),
        ("saigon_departure.jpg", "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=600&auto=format&fit=crop&q=80", "Tan Son Nhat International Airport Saigon Departure"),
        ("hotel_metropole.jpg", "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80", "Sofitel Legend Metropole Hanoi / Silk Path Hotel"),
        ("hotel_cruise.jpg", "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=600&auto=format&fit=crop&q=80", "Paradise Elegance / Orchid Classic Luxury Ha Long Cruise"),
        ("hotel_hoian.jpg", "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600&auto=format&fit=crop&q=80", "Anantara Hoi An Resort / Vinpearl Da Nang"),
        ("hotel_reverie.jpg", "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&auto=format&fit=crop&q=80", "The Reverie Saigon / Caravelle Saigon")
    ],
    "japan": [
        ("banner_japan.jpg", "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=1000&auto=format&fit=crop&q=80", "Mount Fuji & Chureito Pagoda, Japan"),
        ("tokyo_sensoji.jpg", "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=600&auto=format&fit=crop&q=80", "Tokyo: Senso-ji Temple Asakusa"),
        ("tokyo_shibuya.jpg", "https://images.unsplash.com/photo-1542051841857-5f90071e7989?w=600&auto=format&fit=crop&q=80", "Tokyo: Shibuya Scramble Crossing"),
        ("mt_fuji_lake.jpg", "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=600&auto=format&fit=crop&q=80", "Hakone: Lake Ashi & Mount Fuji"),
        ("kyoto_fushimi.jpg", "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=600&auto=format&fit=crop&q=80", "Kyoto: Fushimi Inari-taisha 10,000 Torii Gates"),
        ("kyoto_kinkaku.jpg", "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=600&auto=format&fit=crop&q=80", "Kyoto: Kinkaku-ji Golden Pavilion & Bamboo"),
        ("osaka_castle.jpg", "https://images.unsplash.com/photo-1590559899731-a382839e5549?w=600&auto=format&fit=crop&q=80", "Osaka: Osaka Castle & Dotonbori Neon"),
        ("osaka_departure.jpg", "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=600&auto=format&fit=crop&q=80", "Kansai Airport Departure"),
        ("hotel_gracery.jpg", "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600&auto=format&fit=crop&q=80", "Keio Plaza / Gracery Shinjuku Tokyo"),
        ("hotel_tenyu.jpg", "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=600&auto=format&fit=crop&q=80", "Hakone Kowakien Ten-yu Luxury Onsen"),
        ("hotel_granvia.jpg", "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600&auto=format&fit=crop&q=80", "Hotel Granvia Kyoto / The Ritz-Carlton"),
        ("hotel_swissotel.jpg", "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=600&auto=format&fit=crop&q=80", "Swissotel Nankai Osaka / Conrad Osaka")
    ],
    "bhutan": [
        ("banner_bhutan.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a6/Paro_Taktsang%2C_Bhutan_%28edited%29.jpg/1280px-Paro_Taktsang%2C_Bhutan_%28edited%29.jpg", "Tiger's Nest Monastery (Paro Taktsang) Cliffside Sanctuary, Bhutan"),
        ("thimphu_chorten.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3d/National_Memorial_Chorten%2C_Thimphu_01.jpg/1280px-National_Memorial_Chorten%2C_Thimphu_01.jpg", "Thimphu: National Memorial Chorten & Pa Chhu River"),
        ("thimphu_buddha.jpg", "https://thumb.wikimedia.org/wikipedia/en/thumb/4/4e/Buddha_Dordenma.jpg/1280px-Buddha_Dordenma.jpg", "Thimphu: Giant Buddha Dordenma Statue"),
        ("thimphu_tashichho.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/0/06/Tashichho_Dzong%2C_Bhutan_02.jpg/1280px-Tashichho_Dzong%2C_Bhutan_02.jpg", "Thimphu: Tashichho Dzong Royal Fortress"),
        ("dochula_pass.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c2/Druk_Wangyal_Chortens%2C_Bhutan_01.jpg/1280px-Druk_Wangyal_Chortens%2C_Bhutan_01.jpg", "Dochula Pass: 108 Druk Wangyal Chortens & Himalayan Panorama"),
        ("punakha_dzong.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5a/Punakha_Dzong%2C_Bhutan_02.jpg/1280px-Punakha_Dzong%2C_Bhutan_02.jpg", "Punakha Dzong at River Confluence & Pho Chhu Suspension Bridge"),
        ("phobjikha_valley.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5b/Gangteng_monastery_2019-08-23_b.jpg/1280px-Gangteng_monastery_2019-08-23_b.jpg", "Phobjikha Glacial Valley & Gangtey Monastery"),
        ("paro_rinpung.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/7/75/Rinpung_Dzong%2C_Bhutan_01.jpg/1280px-Rinpung_Dzong%2C_Bhutan_01.jpg", "Paro: Rinpung Dzong & Ta Dzong National Museum"),
        ("paro_tigers_nest.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/a/a6/Paro_Taktsang%2C_Bhutan_%28edited%29.jpg/1280px-Paro_Taktsang%2C_Bhutan_%28edited%29.jpg", "Paro: Legendary Tiger's Nest Monastery (Paro Taktsang, 3,120m)"),
        ("paro_kyichu.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/90/Kyichu_Lhakhang-060701.JPG/1280px-Kyichu_Lhakhang-060701.JPG", "Paro: 7th-Century Kyichu Lhakhang & Drukgyel Dzong"),
        ("chelela_pass.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/c/c9/Prayer_flags_at_the_pass.jpg/1280px-Prayer_flags_at_the_pass.jpg", "Chele La Pass (3,988m) & Haa Valley"),
        ("paro_archery.jpg", "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&auto=format&fit=crop&q=80", "Paro: Traditional Archery & Pa Chhu Willow Riverbanks"),
        ("paro_airport.jpg", "https://thumb.wikimedia.org/wikipedia/commons/thumb/7/75/Paro_day_1-58_%288202279871%29.jpg/1280px-Paro_day_1-58_%288202279871%29.jpg", "Paro International Airport (PBH) Runway & Alpine Valley"),
        ("hotel_le_meridien_thimphu.jpg", "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&auto=format&fit=crop&q=80", "Le Méridien Thimphu / Hotel Druk"),
        ("hotel_dhensa_punakha.jpg", "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=800&auto=format&fit=crop&q=80", "Dhensa Boutique Resort / Zhingkham Resort Punakha"),
        ("hotel_le_meridien_paro.jpg", "https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800&auto=format&fit=crop&q=80", "Le Méridien Paro Riverfront / Zhiwa Ling Heritage Paro"),
        ("hotel_dewachen_phobjikha.jpg", "https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800&auto=format&fit=crop&q=80", "Dewachen Hotel & Spa Phobjikha Valley")
    ]
}

# 30+ Global Country Database for Dynamic Resolution of unlisted countries
GLOBAL_COUNTRY_DATABASE = {
    "germany": {
        "title": "Germany Imperial Castles & Cultural Cities",
        "arrival_airport": "Munich Airport (MUC)", "departure_airport": "Frankfurt Airport (FRA)",
        "cities": ["Munich (Bavaria)", "Berlin (Capital)", "Frankfurt (Hesse)"],
        "attractions": ["Marienplatz & Nymphenburg Palace", "Neuschwanstein Fairy Tale Castle", "Brandenburg Gate & Reichstag", "Museum Island Berlin", "Römerberg Historic Square Frankfurt"]
    },
    "greece": {
        "title": "Greece Classical Athens & Cycladic Islands",
        "arrival_airport": "Athens International Airport (ATH)", "departure_airport": "Santorini Airport (JTR)",
        "cities": ["Athens (Acropolis)", "Santorini (Caldera)", "Mykonos (Windmills)"],
        "attractions": ["Acropolis & Parthenon", "Plaka Old Town Athens", "Oia Sunset & Fira Caldera", "Red Beach & Volcanic Hot Springs", "Little Venice & Mykonos Windmills"]
    },
    "turkey": {
        "title": "Turkey Bosphorus Heritage & Cappadocia Valleys",
        "arrival_airport": "Istanbul Airport (IST)", "departure_airport": "Nevşehir Kapadokya Airport (NAV)",
        "cities": ["Istanbul (Bosphorus)", "Cappadocia (Fairy Chimneys)", "Antalya (Mediterranean Coast)"],
        "attractions": ["Hagia Sophia & Blue Mosque", "Grand Bazaar & Bosphorus Cruise", "Cappadocia Hot Air Balloon Sunrise", "Göreme Open-Air Museum", "Kaleiçi Old Town Antalya"]
    },
    "egypt": {
        "title": "Egypt Pharaoh's Heritage & Nile River Wonder",
        "arrival_airport": "Cairo International Airport (CAI)", "departure_airport": "Luxor International Airport (LXR)",
        "cities": ["Cairo (Giza Pyramids)", "Luxor (Valley of the Kings)", "Aswan (Nile Temples)"],
        "attractions": ["Great Pyramids of Giza & Sphinx", "Grand Egyptian Museum", "Valley of the Kings & Tutankhamun Tomb", "Karnak & Luxor Temples", "Philae Temple & Abu Simbel"]
    },
    "maldives": {
        "title": "Maldives Tropical Atolls & Luxury Overwater Villas",
        "arrival_airport": "Velana International Airport (MLE), Male", "departure_airport": "Velana International Airport (MLE), Male",
        "cities": ["Male (Capital)", "Maafushi Island", "South Ari Atoll"],
        "attractions": ["Overwater Villa Lagoon Relaxation", "Coral Reef Snorkeling with Sea Turtles", "Whale Shark & Manta Ray Safari", "Sandbank Private Sunset Dinner", "Male Grand Friday Mosque"]
    },
    "australia": {
        "title": "Australia Coastal Marvels: Sydney, Melbourne & Great Barrier Reef",
        "arrival_airport": "Sydney Kingsford Smith Airport (SYD)", "departure_airport": "Melbourne Airport (MEL)",
        "cities": ["Sydney (Harbour)", "Cairns (Barrier Reef)", "Melbourne (Culture & Yarra)"],
        "attractions": ["Sydney Opera House & Harbour Bridge", "Bondi Beach Coastal Walk", "Great Barrier Reef Snorkel Safari", "Great Ocean Road & 12 Apostles", "Melbourne Laneways & Street Art"]
    },
    "united states": {
        "title": "United States Coast-to-Coast: New York & San Francisco",
        "arrival_airport": "John F. Kennedy International Airport (JFK), New York", "departure_airport": "San Francisco Airport (SFO)",
        "cities": ["New York City", "Washington D.C.", "San Francisco (Bay Area)"],
        "attractions": ["Statue of Liberty & Times Square", "Central Park & Empire State Building", "National Mall & Smithsonian Museums", "Golden Gate Bridge & Alcatraz Island", "Fisherman's Wharf & Cable Cars"]
    },
    "usa": {
        "title": "United States Coast-to-Coast: New York & San Francisco",
        "arrival_airport": "John F. Kennedy International Airport (JFK), New York", "departure_airport": "San Francisco Airport (SFO)",
        "cities": ["New York City", "Washington D.C.", "San Francisco (Bay Area)"],
        "attractions": ["Statue of Liberty & Times Square", "Central Park & Empire State Building", "National Mall & Smithsonian Museums", "Golden Gate Bridge & Alcatraz Island", "Fisherman's Wharf & Cable Cars"]
    },
    "switzerland": {
        "title": "Switzerland Alpine Peaks & Pristine Lakes Circuit",
        "arrival_airport": "Zurich Airport (ZRH)", "departure_airport": "Geneva Airport (GVA)",
        "cities": ["Zurich (Financial & Lake)", "Lucerne (Mt. Titlis)", "Interlaken (Jungfraujoch)", "Geneva (Lake Geneva)"],
        "attractions": ["Lake Zurich & Bahnhofstrasse", "Mt. Titlis Revolving Cable Car & Glacier Cave", "Jungfraujoch Top of Europe (3,454m)", "Lauterbrunnen 72 Waterfalls Valley", "Jet d'Eau & United Nations Geneva"]
    },
    "france": {
        "title": "France Grand Boulevard & French Riviera Romance",
        "arrival_airport": "Paris Charles de Gaulle (CDG)", "departure_airport": "Nice Côte d'Azur (NCE)",
        "cities": ["Paris (City of Light)", "Nice (French Riviera)", "Monaco (Monte Carlo)"],
        "attractions": ["Eiffel Tower Summit & Seine Cruise", "Louvre Museum & Mona Lisa", "Arc de Triomphe & Champs-Élysées", "Promenade des Anglais Nice", "Monaco Palace & Monte Carlo Casino"]
    },
    "italy": {
        "title": "Italy Classical Renaissance: Rome, Florence & Venice",
        "arrival_airport": "Rome Leonardo da Vinci (FCO)", "departure_airport": "Venice Marco Polo (VCE)",
        "cities": ["Rome (Eternal City)", "Florence (Renaissance)", "Venice (Canals)"],
        "attractions": ["Colosseum & Roman Forum", "Vatican City & St. Peter's Basilica", "Florence Duomo & Uffizi Gallery", "Ponte Vecchio & Michelangelo Piazza", "Venice Gondola Ride & St. Mark's Basilica"]
    },
    "united arab emirates": {
        "title": "UAE Futuristic Oasis: Dubai & Abu Dhabi Grandeur",
        "arrival_airport": "Dubai International Airport (DXB)", "departure_airport": "Zayed International Airport (AUH), Abu Dhabi",
        "cities": ["Dubai (Futuristic Skyline)", "Abu Dhabi (Capital & Grand Mosque)"],
        "attractions": ["Burj Khalifa 124th Floor At The Top", "Dubai Desert Safari & Dune Bashing", "Palm Jumeirah & Atlantis The Palm", "Museum of the Future", "Sheikh Zayed Grand Mosque Abu Dhabi"]
    },
    "dubai": {
        "title": "Dubai Futuristic Luxury & Desert Wonders",
        "arrival_airport": "Dubai International Airport (DXB)", "departure_airport": "Dubai International Airport (DXB)",
        "cities": ["Downtown Dubai", "Dubai Marina & Palm Jumeirah", "Abu Dhabi (Excursion)"],
        "attractions": ["Burj Khalifa 124th Floor At The Top", "Dubai Desert Safari & Dune Bashing", "Palm Jumeirah & Atlantis The Palm", "Museum of the Future", "Sheikh Zayed Grand Mosque Abu Dhabi"]
    },
    "singapore": {
        "title": "Singapore Garden City & Sentosa Island Adventure",
        "arrival_airport": "Singapore Changi Airport (SIN)", "departure_airport": "Singapore Changi Airport (SIN)",
        "cities": ["Singapore Marina Bay", "Sentosa Island"],
        "attractions": ["Marina Bay Sands SkyPark Observation Deck", "Gardens by the Bay & Supertree Grove", "Universal Studios Singapore Sentosa", "S.E.A. Aquarium & Wings of Time", "Changi Jewel Rain Vortex Waterfall"]
    },
    "bali": {
        "title": "Bali Tropical Paradise: Ubud Culture, Nusa Penida & Beaches",
        "arrival_airport": "Ngurah Rai International Airport (DPS), Bali", "departure_airport": "Ngurah Rai International Airport (DPS), Bali",
        "cities": ["Ubud (Cultural Heart)", "Nusa Penida (Island Clifftops)", "Seminyak & Kuta (Coastal Sunset)"],
        "attractions": ["Tegallalang Rice Terraces & Jungle Swing", "Sacred Monkey Forest Sanctuary", "Kelingking T-Rex Beach Nusa Penida", "Uluwatu Cliff Temple & Kecak Fire Dance", "Tanah Lot Sea Temple Sunset"]
    },
    "indonesia": {
        "title": "Bali & Indonesia Island Marvels",
        "arrival_airport": "Ngurah Rai International Airport (DPS), Bali", "departure_airport": "Ngurah Rai International Airport (DPS), Bali",
        "cities": ["Ubud (Cultural Heart)", "Nusa Penida (Island Clifftops)", "Seminyak & Kuta (Coastal Sunset)"],
        "attractions": ["Tegallalang Rice Terraces & Jungle Swing", "Sacred Monkey Forest Sanctuary", "Kelingking T-Rex Beach Nusa Penida", "Uluwatu Cliff Temple & Kecak Fire Dance", "Tanah Lot Sea Temple Sunset"]
    },
    "united kingdom": {
        "title": "United Kingdom Royal Heritage & Scottish Highlands",
        "arrival_airport": "London Heathrow Airport (LHR)", "departure_airport": "Edinburgh Airport (EDI)",
        "cities": ["London (Royal Capital)", "Edinburgh (Historic Scotland)", "Highlands & Loch Ness"],
        "attractions": ["Big Ben, Westminster & London Eye", "Tower of London & Crown Jewels", "Buckingham Palace Changing of Guard", "Edinburgh Castle & Royal Mile", "Loch Ness & Scottish Highlands Vistas"]
    },
    "uk": {
        "title": "United Kingdom Royal Heritage & Scottish Highlands",
        "arrival_airport": "London Heathrow Airport (LHR)", "departure_airport": "Edinburgh Airport (EDI)",
        "cities": ["London (Royal Capital)", "Edinburgh (Historic Scotland)", "Highlands & Loch Ness"],
        "attractions": ["Big Ben, Westminster & London Eye", "Tower of London & Crown Jewels", "Buckingham Palace Changing of Guard", "Edinburgh Castle & Royal Mile", "Loch Ness & Scottish Highlands Vistas"]
    },
    "spain": {
        "title": "Spain Iberian Splendor: Barcelona & Madrid Heritage",
        "arrival_airport": "Barcelona–El Prat Airport (BCN)", "departure_airport": "Madrid–Barajas Airport (MAD)",
        "cities": ["Barcelona (Catalonia)", "Madrid (Imperial Capital)"],
        "attractions": ["Sagrada Família & Park Güell", "Casa Batlló & Las Ramblas", "Gothic Quarter Barcelona", "Royal Palace of Madrid & Plaza Mayor", "Prado Museum & Retiro Park"]
    },
    "norway": {
        "title": "Norway Fjord Wonders & Northern Lights Frontier",
        "arrival_airport": "Oslo Airport (OSL)", "departure_airport": "Bergen Airport (BGO)",
        "cities": ["Oslo (Capital)", "Bergen (Fjord Gateway)", "Geiranger & Flåm (Fjords)"],
        "attractions": ["Vigeland Sculpture Park & Opera House", "Bryggen Hanseatic Wharf Bergen", "Flåm Railway & Sognefjord Cruise", "Geirangerfjord UNESCO Waterfall Cruise", "Fløibanen Funicular Mountain View"]
    },
    "iceland": {
        "title": "Iceland Land of Fire & Ice: Geysers, Waterfalls & Blue Lagoon",
        "arrival_airport": "Keflavik International Airport (KEF)", "departure_airport": "Keflavik International Airport (KEF)",
        "cities": ["Reykjavik (Capital)", "Golden Circle & South Coast", "Vik (Black Sand Beach)"],
        "attractions": ["Blue Lagoon Geothermal Mineral Spa", "Gullfoss Waterfall & Geysir Geothermal Field", "Thingvellir National Park Rift", "Seljalandsfoss & Skógafoss Waterfalls", "Reynisfjara Black Sand Beach & Basalt Columns"]
    },
    "new zealand": {
        "title": "New Zealand Middle-Earth Wonders & Southern Alps",
        "arrival_airport": "Auckland Airport (AKL)", "departure_airport": "Queenstown Airport (ZQN)",
        "cities": ["Auckland (City of Sails)", "Rotorua (Geothermal)", "Queenstown (Adventure Capital)"],
        "attractions": ["Auckland Sky Tower & Harbour", "Hobbiton Movie Set Tour", "Te Puia Geothermal Geysers Rotorua", "Milford Sound Scenic Fiord Cruise", "Queenstown Skyline Gondola & Lake Wakatipu"]
    },
    "malaysia": {
        "title": "Malaysia Tropical Diversity: Kuala Lumpur, Penang & Langkawi",
        "arrival_airport": "Kuala Lumpur International (KUL)", "departure_airport": "Langkawi International (LGK)",
        "cities": ["Kuala Lumpur (Twin Towers)", "Penang (Heritage & Street Food)", "Langkawi (Archipelago)"],
        "attractions": ["Petronas Twin Towers & Skybridge", "Batu Caves Rainbow Steps & Murugan Statue", "George Town UNESCO Street Art & Clan Jetties", "Langkawi SkyCab Cable Car & SkyBridge", "Kilim Geoforest Mangrove Boat Safari"]
    },
    "south africa": {
        "title": "South Africa Rainbow Nation: Cape Town & Kruger Safari",
        "arrival_airport": "Cape Town International (CPT)", "departure_airport": "OR Tambo Johannesburg (JNB)",
        "cities": ["Cape Town (Table Mountain)", "Kruger National Park (Big Five)", "Johannesburg (History)"],
        "attractions": ["Table Mountain Aerial Cableway", "Cape of Good Hope & Boulders Beach Penguins", "Kruger Big Five Open-Top Safari Game Drive", "Kirstenbosch National Botanical Garden", "Soweto & Nelson Mandela Sanctuary"]
    },
    "sri lanka": {
        "title": "Sri Lanka Pearl of Indian Ocean: Sigiriya, Kandy & Galle",
        "arrival_airport": "Bandaranaike International (CMB), Colombo", "departure_airport": "Bandaranaike International (CMB), Colombo",
        "cities": ["Colombo (Capital)", "Sigiriya & Dambulla (Cultural Triangle)", "Kandy (Hill Country)", "Galle (Dutch Fort)"],
        "attractions": ["Sigiriya Ancient Lion Rock Fortress", "Dambulla Golden Cave Temple", "Temple of Sacred Tooth Relic Kandy", "Scenic Hill Country Tea Train", "Galle Dutch Fort UNESCO Ramparts"]
    },
    "bhutan": {
        "title": "Bhutan Himalayan Kingdom of Happiness: Thimphu, Punakha & Paro Valley",
        "arrival_airport": "Paro International Airport (PBH)", "departure_airport": "Paro International Airport (PBH)",
        "cities": ["Thimphu (Royal Capital)", "Punakha (Ancient River Valley)", "Paro (Tiger's Nest Valley)"],
        "attractions": ["Tiger's Nest Monastery (Paro Taktsang)", "Punakha Dzong & Long Suspension Bridge", "Giant Buddha Dordenma Statue", "Dochula Pass 108 Memorial Chortens", "Tashichho Dzong Royal Fortress", "Rinpung Dzong & National Museum Paro", "Chimi Lhakhang Fertility Temple", "National Memorial Chorten Thimphu"]
    },
    "nepal": {
        "title": "Nepal Himalayan Majesty: Kathmandu, Pokhara & Chitwan",
        "arrival_airport": "Tribhuvan International Airport (KTM), Kathmandu", "departure_airport": "Tribhuvan International Airport (KTM), Kathmandu",
        "cities": ["Kathmandu (Historic Capital)", "Pokhara (Phewa Lake & Annapurna Vistas)", "Chitwan (National Park Safari)"],
        "attractions": ["Pashupatinath Temple & Boudhanath Stupa", "Swayambhunath Monkey Temple", "Pokhara Phewa Lake Boat Cruise", "Sarangkot Annapurna Sunrise Viewpoint", "Chitwan Jungle Safari & Rhino Sanctuary"]
    },
    "mauritius": {
        "title": "Mauritius Tropical Turquoise Paradise: Lagoons, Waterfalls & Coral Reefs",
        "arrival_airport": "Sir Seewoosagur Ramgoolam International Airport (MRU)", "departure_airport": "Sir Seewoosagur Ramgoolam International Airport (MRU)",
        "cities": ["Port Louis (Capital)", "Grand Baie (Northern Coast)", "Belle Mare & Flic-en-Flac (Beaches)"],
        "attractions": ["Chamarel Seven Coloured Earths & Waterfall", "Île aux Cerfs Island Catamaran Cruise", "Pamplemousses Botanical Garden", "Le Morne Brabant UNESCO Mountain", "Grand Baie Coastal Lagoon & Beaches"]
    },
    "seychelles": {
        "title": "Seychelles Exotic Granite Islands: Mahé, Praslin & La Digue",
        "arrival_airport": "Seychelles International Airport (SEZ), Mahé", "departure_airport": "Seychelles International Airport (SEZ), Mahé",
        "cities": ["Mahé (Victoria Capital)", "Praslin (Vallée de Mai)", "La Digue (Anse Source d'Argent)"],
        "attractions": ["Anse Source d'Argent Granite Boulder Beach", "Vallée de Mai UNESCO Coco de Mer Reserve", "Beau Vallon Beach & Coral Reefs", "Anse Lazio Turquoise Bay", "Victoria Clocktower & Sir Selwyn Market"]
    },
    "kenya": {
        "title": "Kenya Big Five Safari: Maasai Mara, Amboseli & Rift Valley",
        "arrival_airport": "Jomo Kenyatta International Airport (NBO), Nairobi", "departure_airport": "Jomo Kenyatta International Airport (NBO), Nairobi",
        "cities": ["Nairobi (Capital)", "Maasai Mara (National Reserve)", "Amboseli (Mt. Kilimanjaro Views)"],
        "attractions": ["Maasai Mara Big Five Game Drive", "Great Wildebeest Migration Savannah", "Amboseli Elephant Herds with Mt. Kilimanjaro View", "Giraffe Centre & Karen Blixen Museum", "Nairobi National Park Safari"]
    },
    "tanzania": {
        "title": "Tanzania Wilderness & Zanzibar Spice Island",
        "arrival_airport": "Abeid Amani Karume International Airport (ZNZ), Zanzibar", "departure_airport": "Kilimanjaro International Airport (JRO)",
        "cities": ["Zanzibar (Stone Town & Beaches)", "Serengeti (National Park)", "Ngorongoro (Crater Safari)"],
        "attractions": ["Serengeti Endless Plains Big Five Safari", "Ngorongoro Crater UNESCO Wildlife Caldera", "Stone Town UNESCO Heritage Alleyways", "Nungwi Beach Sunset Cruise", "Spice Plantation Tour Zanzibar"]
    },
    "cambodia": {
        "title": "Cambodia Ancient Khmer Empire: Angkor Wat & Phnom Penh",
        "arrival_airport": "Siem Reap–Angkor International Airport (SAI)", "departure_airport": "Phnom Penh International Airport (PNH)",
        "cities": ["Siem Reap (Angkor Wat Gateway)", "Phnom Penh (Royal Capital)"],
        "attractions": ["Angkor Wat Sunrise & Ancient Temple City", "Bayon Smiling Stone Faces Temple", "Ta Prohm Jungle Temple", "Royal Palace & Silver Pagoda Phnom Penh", "Tonle Sap Floating Village Boat Tour"]
    },
    "austria": {
        "title": "Austria Imperial Elegance: Vienna, Salzburg & Hallstatt Alpine Wonder",
        "arrival_airport": "Vienna International Airport (VIE)", "departure_airport": "Salzburg Airport (SZG)",
        "cities": ["Vienna (Imperial Capital)", "Salzburg (Mozart & Sound of Music)", "Innsbruck (Tyrolean Alps)", "Hallstatt (UNESCO Lake Village)"],
        "attractions": ["Schönbrunn Palace & Imperial Gardens", "St. Stephen's Cathedral Vienna", "Hohensalzburg Fortress & Mirabell Palace", "Hallstatt Lake Promenade & Skywalk", "Innsbruck Golden Roof & Nordkette Cable Car"]
    },
    "netherlands": {
        "title": "Netherlands Golden Age: Amsterdam Canals, Windmills & Dutch Culture",
        "arrival_airport": "Amsterdam Airport Schiphol (AMS)", "departure_airport": "Amsterdam Airport Schiphol (AMS)",
        "cities": ["Amsterdam (Canals & Museums)", "Rotterdam (Modern Architecture)", "The Hague (Peace Palace)"],
        "attractions": ["Amsterdam Canal Cruise & Jordaan District", "Rijksmuseum & Van Gogh Museum", "Anne Frank House & Dam Square", "Zaanse Schans Historic Windmills", "Keukenhof Tulip Gardens & Flower Strip"]
    },
    "portugal": {
        "title": "Portugal Atlantic Charm: Lisbon, Sintra Palaces & Porto Riverfront",
        "arrival_airport": "Lisbon Humberto Delgado Airport (LIS)", "departure_airport": "Francisco Sá Carneiro Airport (OPO), Porto",
        "cities": ["Lisbon (Historic Capital)", "Porto (Douro River & Wine Cellars)", "Sintra & Cascais (Palaces)"],
        "attractions": ["Belém Tower & Jerónimos Monastery", "Pena National Palace & Quinta da Regaleira Sintra", "Tram 28 Historic Alfama District", "Ribeira Douro Riverfront Porto", "Dom Luís I Double-Deck Bridge"]
    },
    "morocco": {
        "title": "Morocco Imperial Cities & Sahara Mirage: Marrakech, Fes & Chefchaouen",
        "arrival_airport": "Marrakesh Menara Airport (RAK)", "departure_airport": "Mohammed V International Airport (CMN), Casablanca",
        "cities": ["Marrakech (Red City & Medina)", "Fes (Ancient Imperial City)", "Casablanca (Hassan II Mosque)", "Chefchaouen (Blue Pearl)"],
        "attractions": ["Jemaa el-Fnaa Square & Koutoubia Mosque", "Bahia Palace & Majorelle Garden", "Fes el-Bali Medieval Medina & Chouara Tannery", "Hassan II Mosque Casablanca", "Chefchaouen Blue-Washed Streets"]
    },
    "south korea": {
        "title": "South Korea K-Wave & Dynastic Palaces: Seoul, Busan & Jeju Island",
        "arrival_airport": "Incheon International Airport (ICN), Seoul", "departure_airport": "Gimhae International Airport (PUS), Busan",
        "cities": ["Seoul (Modern Capital & Palaces)", "Busan (Coastal Metropolis)", "Jeju Island (Volcanic Wonder)"],
        "attractions": ["Gyeongbokgung Royal Palace & Bukchon Hanok Village", "N Seoul Tower & Myeongdong", "Haeundae Beach & Gamcheon Culture Village Busan", "Seongsan Ilchulbong Sunrise Peak Jeju", "Jeju Hallasan Volcanic National Park"]
    },
    "hong kong": {
        "title": "Hong Kong Pearl of the Orient: Victoria Peak, Skyline & Lantau",
        "arrival_airport": "Hong Kong International Airport (HKG)", "departure_airport": "Hong Kong International Airport (HKG)",
        "cities": ["Hong Kong Central & Victoria Peak", "Kowloon (Tsim Sha Tsui)", "Lantau Island (Big Buddha)"],
        "attractions": ["Victoria Peak Tram & Sky Terrace 428", "Star Ferry Victoria Harbour Cruise", "Tian Tan Big Buddha & Po Lin Monastery", "Symphony of Lights Tsim Sha Tsui", "Temple Street Night Market"]
    },
    "philippines": {
        "title": "Philippines Tropical Archipelago: Manila, Boracay & El Nido Palawan",
        "arrival_airport": "Ninoy Aquino International Airport (MNL), Manila", "departure_airport": "Mactan–Cebu International Airport (CEB)",
        "cities": ["Manila (Historic Capital)", "Boracay (White Beach)", "El Nido Palawan (Limestone Lagoons)", "Cebu (Islands & Waterfalls)"],
        "attractions": ["El Nido Big Lagoon & Secret Lagoon Island Hopping", "Boracay White Beach Sunset Paraw Sailing", "Intramuros Historic Walled City Manila", "Kawasan Canyoneering & Falls Cebu", "Chocolate Hills Bohol Panorama"]
    },
    "canada": {
        "title": "Canada Rocky Mountains & Cosmopolitan Metropolises",
        "arrival_airport": "Vancouver International Airport (YVR)", "departure_airport": "Toronto Pearson International Airport (YYZ)",
        "cities": ["Vancouver (Pacific Gateway)", "Banff & Lake Louise (Canadian Rockies)", "Toronto (Niagara Falls Gateway)", "Montreal (Old French Quarter)"],
        "attractions": ["Banff National Park & Turquoise Lake Louise", "Niagara Falls Hornblower Boat Cruise", "CN Tower & Toronto Waterfront", "Stanley Park & Capilano Suspension Bridge Vancouver", "Old Montreal & Notre-Dame Basilica"]
    },
    "oman": {
        "title": "Oman Desert Castles, Emerald Wadis & Arabian Fjords",
        "arrival_airport": "Muscat International Airport (MCT)", "departure_airport": "Muscat International Airport (MCT)",
        "cities": ["Muscat (Capital & Grand Mosque)", "Nizwa (Historic Fort & Oasis)", "Wahiba Sands (Desert Dunes)", "Salalah (Frankincense Coast)"],
        "attractions": ["Sultan Qaboos Grand Mosque Muscat", "Mutrah Corniche & Traditional Souq", "Nizwa Fort & Friday Cattle Market", "Wahiba Sands Desert Safari & Camp", "Bimmah Sinkhole & Wadi Shab Emerald Pools"]
    },
    "georgia": {
        "title": "Georgia Caucasus Peaks & Ancient Wine Valleys: Tbilisi & Kazbegi",
        "arrival_airport": "Shota Rustaveli Tbilisi International Airport (TBS)", "departure_airport": "Batumi International Airport (BUS)",
        "cities": ["Tbilisi (Old Town & Sulphur Baths)", "Kazbegi / Stepantsminda (Caucasus Peaks)", "Batumi (Black Sea Coast)"],
        "attractions": ["Narikala Fortress & Tbilisi Old Town Sulphur Baths", "Gergeti Trinity Church with Mt. Kazbek Backdrop", "Ananuri Fortress & Jinvali Water Reservoir", "Batumi Boulevard & Ali and Nino Moving Statue", "Kakheti Wine Valley Traditional Qvevri Tasting"]
    },
    "azerbaijan": {
        "title": "Azerbaijan Land of Fire: Baku Flame Towers & Silk Road Caravans",
        "arrival_airport": "Heydar Aliyev International Airport (GYD), Baku", "departure_airport": "Heydar Aliyev International Airport (GYD), Baku",
        "cities": ["Baku (Flame Towers & Caspian Coast)", "Gabala (Caucasus Mountains)", "Sheki (Silk Road Heritage)"],
        "attractions": ["Baku Old City (Icherisheher) & Maiden Tower", "Heydar Aliyev Center Architectural Marvel", "Flame Towers & Baku Seaside Boulevard", "Gobustan Rock Art & Mud Volcanoes", "Sheki Khan's Palace Stained Glass"]
    },
    "uzbekistan": {
        "title": "Uzbekistan Silk Road Jewels: Samarkand, Bukhara & Tashkent",
        "arrival_airport": "Islam Karimov Tashkent International Airport (TAS)", "departure_airport": "Samarkand International Airport (SKD)",
        "cities": ["Tashkent (Capital)", "Samarkand (Registan Square)", "Bukhara (Silk Road Oasis)"],
        "attractions": ["Registan Square Three Grand Madrassahs Samarkand", "Gur-e-Amir Mausoleum (Tamerlane Tomb)", "Bukhara Ark Fortress & Po-i-Kalyan Complex", "Shah-i-Zinda Blue Tile Necropolis", "Chorsu Bazaar & Tashkent Metro Stations"]
    },
    "czech republic": {
        "title": "Czech Bohemia Wonders: Prague Castle, Český Krumlov & Spas",
        "arrival_airport": "Václav Havel Airport Prague (PRG)", "departure_airport": "Václav Havel Airport Prague (PRG)",
        "cities": ["Prague (City of a Hundred Spires)", "Český Krumlov (Fairy Tale Castle)", "Karlovy Vary (Spa Town)"],
        "attractions": ["Prague Castle & St. Vitus Cathedral", "Charles Bridge & Old Town Square Astronomical Clock", "Český Krumlov UNESCO Castle & Vltava River", "Karlovy Vary Colonnades & Mineral Springs", "Jewish Quarter (Josefov) Prague"]
    },
    "hungary": {
        "title": "Hungary Danube Royalty: Budapest Thermal Spas & Imperial Bridges",
        "arrival_airport": "Budapest Ferenc Liszt International Airport (BUD)", "departure_airport": "Budapest Ferenc Liszt International Airport (BUD)",
        "cities": ["Budapest (Danube Pearl & Thermal Baths)", "Lake Balaton", "Eger (Historic Castle & Wine)"],
        "attractions": ["Hungarian Parliament Building & Danube Promenade", "Buda Castle & Fisherman's Bastion", "Széchenyi Thermal Bath & City Park", "St. Stephen's Basilica & Chain Bridge", "Ruin Bars & Great Market Hall Budapest"]
    }
}
