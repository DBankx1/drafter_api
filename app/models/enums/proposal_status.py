from enum import Enum

class ProposalStatus(Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    CUSTOMER_VIEWED = "customer_viewed"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"