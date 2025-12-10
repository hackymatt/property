"""SQLAlchemy models for scheduler (reflected from DB)"""

from sqlalchemy.ext.automap import automap_base

# Will be populated by reflection after engine connect
Base = automap_base()
Schedule = None  # populated after reflect()
Job = None  # populated after reflect()
Domain = None  # populated after reflect()
