"""
Neurons API - CRUD operations for Neurons
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
import logging

from db import get_db_session, Neuron as NeuronModel, User, PrivacyTier
from api.auth import get_current_user
from core.security.audit import log_audit_event

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic schemas
class NeuronCreate(BaseModel):
    name: str
    description: Optional[str] = None
    config: dict
    privacy_tier: int = 0


class NeuronUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None
    privacy_tier: Optional[int] = None


class NeuronResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    privacy_tier: int
    is_active: bool
    status: str
    created_at: str
    total_interactions: int

    class Config:
        from_attributes = True


@router.get("/", response_model=List[NeuronResponse])
async def list_neurons(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all Neurons owned by current user"""
    result = await db.execute(
        select(NeuronModel).where(NeuronModel.owner_id == user.id)
    )
    neurons = result.scalars().all()

    return [
        NeuronResponse(
            id=n.id,
            name=n.name,
            description=n.description,
            privacy_tier=n.privacy_tier.value,
            is_active=n.is_active,
            status=n.status,
            created_at=n.created_at.isoformat(),
            total_interactions=n.total_interactions
        )
        for n in neurons
    ]


@router.post("/", response_model=NeuronResponse)
async def create_neuron(
    neuron_data: NeuronCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new Neuron"""

    # Create neuron
    neuron = NeuronModel(
        name=neuron_data.name,
        description=neuron_data.description,
        config=neuron_data.config,
        privacy_tier=PrivacyTier(neuron_data.privacy_tier),
        owner_id=user.id
    )

    db.add(neuron)
    await db.commit()
    await db.refresh(neuron)

    # Audit log
    await log_audit_event(
        db=db,
        event_type="neuron",
        action="create",
        user_id=user.id,
        neuron_id=neuron.id,
        result="success"
    )

    logger.info(f"Neuron created: {neuron.name} (ID: {neuron.id})")

    return NeuronResponse(
        id=neuron.id,
        name=neuron.name,
        description=neuron.description,
        privacy_tier=neuron.privacy_tier.value,
        is_active=neuron.is_active,
        status=neuron.status,
        created_at=neuron.created_at.isoformat(),
        total_interactions=neuron.total_interactions
    )


@router.get("/{neuron_id}", response_model=NeuronResponse)
async def get_neuron(
    neuron_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Get specific Neuron"""
    result = await db.execute(
        select(NeuronModel).where(
            NeuronModel.id == neuron_id,
            NeuronModel.owner_id == user.id
        )
    )
    neuron = result.scalar_one_or_none()

    if not neuron:
        raise HTTPException(status_code=404, detail="Neuron not found")

    return NeuronResponse(
        id=neuron.id,
        name=neuron.name,
        description=neuron.description,
        privacy_tier=neuron.privacy_tier.value,
        is_active=neuron.is_active,
        status=neuron.status,
        created_at=neuron.created_at.isoformat(),
        total_interactions=neuron.total_interactions
    )


@router.patch("/{neuron_id}", response_model=NeuronResponse)
async def update_neuron(
    neuron_id: str,
    updates: NeuronUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update Neuron configuration"""
    result = await db.execute(
        select(NeuronModel).where(
            NeuronModel.id == neuron_id,
            NeuronModel.owner_id == user.id
        )
    )
    neuron = result.scalar_one_or_none()

    if not neuron:
        raise HTTPException(status_code=404, detail="Neuron not found")

    # Update fields
    if updates.name is not None:
        neuron.name = updates.name
    if updates.description is not None:
        neuron.description = updates.description
    if updates.config is not None:
        neuron.config = updates.config
    if updates.privacy_tier is not None:
        neuron.privacy_tier = PrivacyTier(updates.privacy_tier)

    await db.commit()
    await db.refresh(neuron)

    # Audit log
    await log_audit_event(
        db=db,
        event_type="neuron",
        action="update",
        user_id=user.id,
        neuron_id=neuron.id,
        result="success"
    )

    return NeuronResponse(
        id=neuron.id,
        name=neuron.name,
        description=neuron.description,
        privacy_tier=neuron.privacy_tier.value,
        is_active=neuron.is_active,
        status=neuron.status,
        created_at=neuron.created_at.isoformat(),
        total_interactions=neuron.total_interactions
    )


@router.delete("/{neuron_id}")
async def delete_neuron(
    neuron_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Delete Neuron"""
    result = await db.execute(
        select(NeuronModel).where(
            NeuronModel.id == neuron_id,
            NeuronModel.owner_id == user.id
        )
    )
    neuron = result.scalar_one_or_none()

    if not neuron:
        raise HTTPException(status_code=404, detail="Neuron not found")

    await db.delete(neuron)
    await db.commit()

    # Audit log
    await log_audit_event(
        db=db,
        event_type="neuron",
        action="delete",
        user_id=user.id,
        neuron_id=neuron_id,
        result="success"
    )

    return {"message": "Neuron deleted successfully"}
