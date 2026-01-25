from enum import Enum


class PricingType(Enum):
    FIXED = "fixed"
    HOURLY = "hourly"
    TIERED = "tiered"