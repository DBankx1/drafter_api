from pydantic import BaseModel, field_validator


class StartConversationRequest(BaseModel):
    customer_name: str = ""
    customer_email: str | None = None


class StartConversationResponse(BaseModel):
    conversation_id: str


class ChatMessageInput(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("message cannot be empty")
        return stripped
