from enum import Enum


class FeedType(Enum):
    MERCHANT = 0
    AUTH = 1
    SETTLED = 2
    REFUND = 3
