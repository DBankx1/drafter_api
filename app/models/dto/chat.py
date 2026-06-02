import base64
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator


# ------------------------------------------------------------------ #
#  Conversation creation                                               #
# ------------------------------------------------------------------ #

class StartConversationRequest(BaseModel):
    customer_name: str = ""
    customer_email: str | None = None


class StartConversationResponse(BaseModel):
    conversation_id: str


# ------------------------------------------------------------------ #
#  WebSocket input                                                     #
# ------------------------------------------------------------------ #

class ChatMessageInput(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("message cannot be empty")
        return stripped


# ------------------------------------------------------------------ #
#  Message output                                                      #
# ------------------------------------------------------------------ #

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str           # serialised from ChatRoles enum → "user" / "assistant"
    content: str
    timestamp: datetime
    intent: str | None = None
    meta: dict[str, Any] | None = None
    token_count: int | None = None

    @field_validator("role", mode="before")
    @classmethod
    def coerce_role(cls, v: Any) -> str:
        """Handles ChatRoles enum → string coercion when reading from ORM."""
        return v.value if hasattr(v, "value") else str(v)


# ------------------------------------------------------------------ #
#  Unified message list response (cursor + offset)                     #
# ------------------------------------------------------------------ #

class MessagesResponse(BaseModel):
    """
    Unified paginated response returned by GET /conversations/{id}/messages.

    The populated fields depend on the pagination mode used:

    Cursor mode (?cursor=<token> or no cursor for first load):
      items, total, order, next_cursor, has_more, limit

    Offset mode (cursor param absent):
      items, total, order, page, pages, size
    """
    items: list[MessageResponse]
    total: int
    order: Literal["asc", "desc"]

    # --- Cursor mode ---
    next_cursor: str | None = None  # pass as ?cursor= to load the next batch of older messages
    has_more: bool = False           # true if older messages exist before the current batch
    limit: int | None = None         # effective page size in cursor mode

    # --- Offset mode ---
    page: int | None = None
    pages: int | None = None
    size: int | None = None


# ------------------------------------------------------------------ #
#  Cursor encode / decode                                              #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
#  Conversation list                                                   #
# ------------------------------------------------------------------ #

class ConversationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    customer_name: str
    customer_email: str | None = None
    status: str
    started_at: datetime


class ConversationsResponse(BaseModel):
    items: list[ConversationItem]
    total: int
    has_more: bool
    next_cursor: str | None = None
    limit: int


# ------------------------------------------------------------------ #
#  Cursor encode / decode                                              #
# ------------------------------------------------------------------ #

def encode_cursor(timestamp: datetime, message_id: str) -> str:
    """
    Encodes (timestamp, message_id) into an opaque URL-safe base64 string.

    Both fields are included so the server can position the cursor accurately
    even when two messages share the same millisecond timestamp (rare but possible).
    """
    raw = f"{timestamp.isoformat()}:{message_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    """
    Decodes a cursor string back to (timestamp, message_id).
    Raises ValueError with a user-safe message on malformed input.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        ts_str, message_id = raw.rsplit(":", 1)
        return datetime.fromisoformat(ts_str), message_id
    except Exception as exc:
        raise ValueError("Invalid or expired cursor.") from exc
