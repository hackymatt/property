"""SQLAlchemy models for logger service (reflected from DB)"""

from sqlalchemy.ext.automap import automap_base

# Will be populated by reflection after engine connect
Base = automap_base()
ScheduleLog = None  # populated after reflect()
