from app.data_sources.catalog import seed_sources
from app.knowledge.library import seed_knowledge


def initialize(db):
    seed_sources(db)
    seed_knowledge(db)
    db.execute("INSERT OR IGNORE INTO watchlists VALUES('default','My watchlist')")
