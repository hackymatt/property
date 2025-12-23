# Choice definitions for models
from shared.consts import Source, Stage, Status


class JobSource:
    OTODOM_SELL_APARTMENT_OWNER = Source.OTODOM_SELL_APARTMENT_OWNER
    OTODOM_SELL_APARTMENT_AGENCY = Source.OTODOM_SELL_APARTMENT_AGENCY
    OTODOM_SELL_APARTMENT_DEVELOPER = Source.OTODOM_SELL_APARTMENT_DEVELOPER

    CHOICES = [
        (OTODOM_SELL_APARTMENT_OWNER, "Otodom - Sell - Apartment - Owner"),
        (OTODOM_SELL_APARTMENT_AGENCY, "Otodom - Sell - Apartment - Agency"),
        (OTODOM_SELL_APARTMENT_DEVELOPER, "Otodom - Sell - Apartment - Developer"),
    ]


class JobStage:
    LIST_PAGES = Stage.LIST_PAGES
    LIST_ITEMS = Stage.LIST_ITEMS
    GET_ITEM = Stage.GET_ITEM

    CHOICES = [
        (LIST_PAGES, "List Pages"),
        (LIST_ITEMS, "List Items"),
        (GET_ITEM, "Get Item"),
    ]


class ExecutionStatus:
    PENDING = Status.PENDING
    RUNNING = Status.RUNNING
    SUCCESS = Status.SUCCESS
    FAILED = Status.FAILED
    CANCELLED = Status.CANCELLED

    CHOICES = [
        (PENDING, "Pending"),
        (RUNNING, "Running"),
        (SUCCESS, "Success"),
        (FAILED, "Failed"),
        (CANCELLED, "Cancelled"),
    ]
