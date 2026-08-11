"""SQLAlchemy models for data-ingestion (reflected from DB)"""

from sqlalchemy.ext.automap import automap_base

# Will be populated by reflection after engine connect
Base = automap_base()
PropertyRaw = None  # populated after reflect()
ScraperSource = None  # populated after reflect()
