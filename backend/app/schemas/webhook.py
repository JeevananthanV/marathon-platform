from typing import Any, Dict, Optional
from pydantic import BaseModel


class RazorpayWebhookPayload(BaseModel):
    entity: str
    account_id: str
    event: str
    contains: list[str]
    payload: Dict[str, Any]
    created_at: int
