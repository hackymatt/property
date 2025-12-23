"""SQLAlchemy models for logger service (reflected from DB)"""

from sqlalchemy.ext.automap import automap_base

# Will be populated by reflection after engine connect
Base = automap_base()
Location = None
AdvertiserType = None
AdvertiserName = None
DevelopmentName = None
InvestmentState = None
MarketType = None
TransactionType = None
PropertyType = None
Room = None
Floor = None
BuildingFloor = None
ConstructionStatus = None
BuildingType = None
BuildingMaterial = None
HeatingType = None
OwnershipType = None
ApartmentListing = None
ApartmentListingChange = None
