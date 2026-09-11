"""Pydantic request/response models for the chatbot API."""

from typing import Optional

from pydantic import BaseModel, Field

KNOWN_CATEGORIES = {"billing", "login", "refund", "bug", "feature_request", "shipping"}


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The user's support question")
    top_k: int = Field(default=5, ge=1, le=20, description="How many past tickets to retrieve")
    category: Optional[str] = Field(
        default=None, description="Restrict retrieval to one category, e.g. 'billing'"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"query": "I was charged twice this month", "top_k": 5},
                {
                    "query": "cant log in, password reset broken",
                    "top_k": 3,
                    "category": "login",
                },
            ]
        }
    }


class Source(BaseModel):
    ticket_id: str
    category: str
    score: float
    text: str
    response: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "We've refunded the duplicate charge on your Basic "
                    "subscription — it should show back on your card within "
                    "5-7 business days.",
                    "sources": [
                        {
                            "ticket_id": "1031",
                            "category": "billing",
                            "score": 0.6777,
                            "text": "I was charged twice for my Basic subscription "
                            "this month, can you refund one?",
                            "response": "We've refunded the duplicate charge on your "
                            "Basic subscription — it should show back on your card "
                            "within 5-7 business days.",
                        }
                    ],
                }
            ]
        }
    }
