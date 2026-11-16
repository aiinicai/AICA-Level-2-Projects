import sqlite3, json

con = sqlite3.connect(r'c:\Users\ADMIN\Desktop\Capstone\Application\FinstockEventScope-TradingView\data\eventscope.db')
con.row_factory = sqlite3.Row

rows = con.execute("""
    SELECT id, title, company, symbol, exchange, category, authority, scheduled_at, published_at, payload 
    FROM events 
    WHERE kind='Corporate'
""").fetchall()

print(f"Total Corporate Events: {len(rows)}")

exchanges = {}
authorities = {}
categories = {}
samples = 0
invalid_dates = 0

for r in rows:
    p = json.loads(r['payload'])
    ex = r['exchange'] or "None"
    exchanges[ex] = exchanges.get(ex, 0) + 1
    
    auth = r['authority'] or "None"
    authorities[auth] = authorities.get(auth, 0) + 1
    
    cat = r['category'] or "None"
    categories[cat] = categories.get(cat, 0) + 1
    
    if p.get('sample') is True or 'SAMPLE' in r['title']:
        samples += 1
        
    date_val = r['scheduled_at'] or r['published_at']
    if not date_val:
        invalid_dates += 1

print("\nExchanges:", exchanges)
print("\nAuthorities:", authorities)
print("\nCategories:", categories)
print(f"\nSynthetic/Sample records found: {samples}")
print(f"Invalid/Missing dates found: {invalid_dates}")

# Sample corporate records
print("\nSample 5 corporate records:")
for r in rows[:5]:
    p = json.loads(r['payload'])
    print(f"  • {r['title']} | Co: {r['company']} ({r['symbol']}) | Ex: {r['exchange']} | Date: {r['scheduled_at'] or r['published_at']}")

con.close()
