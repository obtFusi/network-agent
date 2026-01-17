# Chat Router
"""Chat endpoint for interacting with the Network Agent."""

import asyncio
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException

from agent.api.dependencies import get_session_store
from agent.api.models.chat import ChatRequest, ChatResponse
from agent.api.services.session_store import SessionStore

logger = structlog.get_logger()

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_session_id: Optional[UUID] = Header(None, alias="X-Session-ID"),
    store: SessionStore = Depends(get_session_store),
):
    """Send a message to the Network Agent and get a response.

    If X-Session-ID header is not provided, a new session is automatically created.
    Use the returned session_id in subsequent requests to continue the conversation.
    """
    # Auto-create session if no ID provided
    if x_session_id is None:
        session_id = store.create()
        logger.info("Auto-created new session", session_id=str(session_id))
    else:
        session_id = x_session_id

    session_info = store.get(session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info(
        "Processing chat request",
        session_id=str(session_id),
        message_length=len(request.message),
    )

    # Run synchronous agent in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(
            None,
            session_info.agent.run,
            request.message,
        )
    except Exception as e:
        logger.error(
            "Agent error",
            session_id=str(session_id),
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    logger.info(
        "Chat request completed",
        session_id=str(session_id),
        response_length=len(response),
    )

    return ChatResponse(
        response=response,
        session_id=str(session_id),
    )
