# Choice definitions for models


class JobSource:
    OTODOM_SALE_APARTMENT_OWNER = 'otodom/sale/apartment/owner'
    
    CHOICES = [
        (OTODOM_SALE_APARTMENT_OWNER, 'Otodom - Sale - Apartment - Owner'),
    ]


class JobStage:
    LIST_PAGES = 'list_pages'
    LIST_ITEMS = 'list_items'
    GET_ITEM = 'get_item'
    
    CHOICES = [
        (LIST_PAGES, 'List Pages'),
        (LIST_ITEMS, 'List Items'),
        (GET_ITEM, 'Get Item'),
    ]


class ExecutionStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    SUCCESS = 'success'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    
    CHOICES = [
        (PENDING, 'Pending'),
        (RUNNING, 'Running'),
        (SUCCESS, 'Success'),
        (FAILED, 'Failed'),
        (CANCELLED, 'Cancelled'),
    ]


# Keep old variable names for backward compatibility
JOB_SOURCE_CHOICES = JobSource.CHOICES
JOB_STAGE_CHOICES = JobStage.CHOICES
EXECUTION_STATUS_CHOICES = ExecutionStatus.CHOICES

