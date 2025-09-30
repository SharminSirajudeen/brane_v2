"""Chat API - Streaming chat with Neurons"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import logging
import json
import time
from datetime import datetime

from db.database import get_db_session
from db.models import Neuron as NeuronModel, ChatSession, Message, User, PrivacyTier
from api.auth import get_current_user
from core.neuron.neuron_manager import get_neuron_manager
from core.security.audit import log_audit_event

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatSessionResponse(BaseModel):
    id: str
    title: str
    neuron_id: str
    message_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str
    tokens: int
    model_used: Optional[str]

    class Config:
        from_attributes = True


@router.post("/{neuron_id}/stream")
async def chat_stream(
    neuron_id: str,
    request: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Stream chat response from Neuron.

    This endpoint:
    1. Creates/retrieves chat session
    2. Stores user message
    3. Streams AI response via SSE
    4. Stores assistant message
    5. Updates neuron stats
    6. Logs audit event
    """
    start_time = time.time()

    # 1. Get neuron from DB
    result = await db.execute(
        select(NeuronModel).where(
            NeuronModel.id == neuron_id,
            NeuronModel.owner_id == user.id
        )
    )
    neuron_model = result.scalar_one_or_none()

    if not neuron_model:
        raise HTTPException(status_code=404, detail="Neuron not found")

    # 2. Get or create chat session
    session_id = request.session_id
    session = None

    if session_id:
        # Retrieve existing session
        session_result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user.id,
                ChatSession.neuron_id == neuron_id
            )
        )
        session = session_result.scalar_one_or_none()

    if not session:
        # Create new session
        session = ChatSession(
            user_id=user.id,
            neuron_id=neuron_id,
            title=request.message[:50] + "..." if len(request.message) > 50 else request.message
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        logger.info(f"Created new chat session: {session.id}")

    # 3. Store user message
    user_message = Message(
        session_id=session.id,
        role="user",
        content=request.message,
        privacy_tier=neuron_model.privacy_tier,
        tokens=len(request.message.split())  # Rough estimate
    )
    db.add(user_message)
    await db.commit()

    # 4. Get/create Neuron instance from manager
    manager = await get_neuron_manager()
    neuron = await manager.get_neuron(neuron_id)

    if not neuron:
        # Initialize neuron if not in manager
        neuron = await manager.add_neuron(neuron_id, neuron_model.config)

    # 5. Stream response
    async def generate():
        """SSE stream generator"""
        full_response = ""
        total_tokens = 0

        try:
            # Stream chunks from neuron
            async for chunk in neuron.chat(
                user_message=request.message,
                user_id=user.id,
                session_id=session.id
            ):
                full_response += chunk
                total_tokens += 1

                # Send SSE event
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # 6. Store assistant message
            assistant_message = Message(
                session_id=session.id,
                role="assistant",
                content=full_response,
                privacy_tier=neuron_model.privacy_tier,
                model_used=neuron_model.config.get("model", {}).get("provider", "unknown"),
                tokens=total_tokens,
                latency_ms=latency_ms
            )
            db.add(assistant_message)

            # 7. Update session stats
            session.message_count += 2  # user + assistant
            session.total_tokens += user_message.tokens + total_tokens
            session.updated_at = datetime.utcnow()

            # 8. Update neuron stats
            neuron_model.total_interactions += 1
            neuron_model.total_tokens += session.total_tokens
            neuron_model.last_used = datetime.utcnow()
            neuron_model.status = "idle"

            await db.commit()

            # 9. Audit log
            await log_audit_event(
                db=db,
                event_type="chat",
                action="send_message",
                user_id=user.id,
                neuron_id=neuron_id,
                result="success",
                details={
                    "session_id": session.id,
                    "tokens": total_tokens,
                    "latency_ms": latency_ms
                }
            )

            # Send completion event
            yield f"data: {json.dumps({'done': True, 'tokens': total_tokens, 'latency_ms': latency_ms})}\n\n"

        except Exception as e:
            logger.error(f"Chat streaming error: {e}", exc_info=True)

            # Update neuron status
            neuron_model.status = "error"
            await db.commit()

            # Audit log failure
            await log_audit_event(
                db=db,
                event_type="chat",
                action="send_message",
                user_id=user.id,
                neuron_id=neuron_id,
                result="failure",
                error_message=str(e)
            )

            # Send error event
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/{neuron_id}/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    neuron_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all chat sessions for a neuron"""
    # Verify neuron ownership
    result = await db.execute(
        select(NeuronModel).where(
            NeuronModel.id == neuron_id,
            NeuronModel.owner_id == user.id
        )
    )
    neuron = result.scalar_one_or_none()

    if not neuron:
        raise HTTPException(status_code=404, detail="Neuron not found")

    # Get sessions
    sessions_result = await db.execute(
        select(ChatSession).where(
            ChatSession.neuron_id == neuron_id,
            ChatSession.user_id == user.id
        ).order_by(ChatSession.updated_at.desc())
    )
    sessions = sessions_result.scalars().all()

    return [
        ChatSessionResponse(
            id=s.id,
            title=s.title,
            neuron_id=s.neuron_id,
            message_count=s.message_count,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get all messages in a chat session"""
    # Verify session ownership
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages
    messages_result = await db.execute(
        select(Message).where(
            Message.session_id == session_id
        ).order_by(Message.created_at.asc())
    )
    messages = messages_result.scalars().all()

    return [
        MessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat(),
            tokens=m.tokens,
            model_used=m.model_used
        )
        for m in messages
    ]


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete a chat session"""
    # Verify session ownership
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user.id
        )
    )
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Delete session (cascade will delete messages)
    await db.delete(session)
    await db.commit()

    # Audit log
    await log_audit_event(
        db=db,
        event_type="chat",
        action="delete_session",
        user_id=user.id,
        result="success",
        details={"session_id": session_id}
    )

    return {"message": "Session deleted successfully"}
