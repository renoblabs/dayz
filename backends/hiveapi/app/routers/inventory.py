"""
Inventory router for DayZ HiveAPI.

This module provides endpoints for character inventory management.
"""

import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_db, get_authenticated_server_id
from ..db.models import Character
from ..services.inventory import compute_inventory_checksum, apply_ops, detect_conflicts
from ..services.events import record_inventory_event

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Resource bounds to prevent unbounded dict creation / DoS via the path-walk.
MAX_OPS = 200
MAX_PATH_DEPTH = 8

# Define request and response models
class ApplyInventoryRequest(BaseModel):
    character_id: str
    ops: List[Dict[str, Any]]
    base_checksum: str

class SetInventoryRequest(BaseModel):
    character_id: str
    slots: Dict[str, Any]
    client_checksum: Optional[str] = None

class InventoryResponse(BaseModel):
    character_id: str
    checksum: str
    conflict: bool = False
    conflict_details: Optional[Dict[str, Any]] = None


def _validate_ops_bounds(ops: List[Dict[str, Any]]) -> None:
    """Reject oversized op batches and deeply nested paths.

    The path-walk in apply_ops creates intermediate dicts for every missing
    segment, so an attacker could otherwise drive unbounded memory growth with
    a single request. Caps the number of ops and the depth of each op's path.
    """
    if len(ops) > MAX_OPS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many operations (max {MAX_OPS})",
        )
    for op in ops:
        path = op.get("path", "") if isinstance(op, dict) else ""
        if isinstance(path, str):
            depth = len([p for p in path.split(".") if p]) if path else 0
        elif isinstance(path, (list, tuple)):
            depth = len(path)
        else:
            depth = 0
        if depth > MAX_PATH_DEPTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Operation path too deep (max {MAX_PATH_DEPTH} segments)",
            )

@router.post("/apply", response_model=InventoryResponse)
async def apply_inventory_ops(
    request: ApplyInventoryRequest,
    db: Session = Depends(get_db),
    server_id: str = Depends(get_authenticated_server_id),
):
    """
    Apply operations to a character's inventory using CRDT-like operations.

    Requires base_checksum to match the current inventory checksum,
    otherwise reports a conflict.
    """
    # Bound the work before touching the database.
    _validate_ops_bounds(request.ops)

    # Find character
    character = db.query(Character).filter(Character.id == request.character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Enforce ownership against the authenticated server id (never the body).
    if character.owned_by_server != server_id:
        logger.warning(f"Server {server_id} attempted inventory apply for character {character.id} owned by {character.owned_by_server}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Server does not own this character"
        )

    # Check for conflicts
    current_checksum = character.inventory_checksum
    if current_checksum and current_checksum != request.base_checksum:
        logger.warning(f"Inventory conflict detected for character {character.id}: base_checksum={request.base_checksum}, current={current_checksum}")
        
        # Return conflict response
        return InventoryResponse(
            character_id=character.id,
            checksum=current_checksum,
            conflict=True,
            conflict_details={
                "base_checksum": request.base_checksum,
                "current_checksum": current_checksum,
                "message": "Inventory has been modified since base_checksum was computed"
            }
        )
    
    # Get current inventory or initialize empty
    current_inventory = character.inventory_json or {}
    
    # Apply operations
    try:
        updated_inventory = apply_ops(current_inventory, request.ops)
        
        # Compute new checksum
        new_checksum = compute_inventory_checksum(updated_inventory)
        
        # Update character
        character.inventory_json = updated_inventory
        character.inventory_checksum = new_checksum
        
        # Record event
        record_inventory_event(
            db=db,
            character_id=character.id,
            server_id=server_id,
            event_type="inventory_updated",
            checksum=new_checksum,
            payload={"op_count": len(request.ops)}
        )
        
        # Commit changes
        db.commit()
        
        logger.info(f"Applied {len(request.ops)} inventory operations for character {character.id}")
        
        # Return success response
        return InventoryResponse(
            character_id=character.id,
            checksum=new_checksum
        )
    
    except Exception as e:
        logger.error(f"Error applying inventory operations: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error applying inventory operations: {str(e)}"
        )

@router.post("/set", response_model=InventoryResponse)
async def set_inventory(
    request: SetInventoryRequest,
    db: Session = Depends(get_db),
    server_id: str = Depends(get_authenticated_server_id),
):
    """
    Set a character's inventory to the provided slots.

    Computes a new checksum for the inventory.
    """
    # Find character
    character = db.query(Character).filter(Character.id == request.character_id).first()
    if not character:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Character not found"
        )

    # Enforce ownership against the authenticated server id (never the body).
    if character.owned_by_server != server_id:
        logger.warning(f"Server {server_id} attempted inventory set for character {character.id} owned by {character.owned_by_server}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Server does not own this character"
        )

    # Verify client checksum if provided
    if request.client_checksum:
        computed_checksum = compute_inventory_checksum(request.slots)
        if computed_checksum != request.client_checksum:
            logger.warning(f"Client checksum mismatch for character {character.id}")
            return InventoryResponse(
                character_id=character.id,
                checksum=computed_checksum,
                conflict=True,
                conflict_details={
                    "client_checksum": request.client_checksum,
                    "computed_checksum": computed_checksum,
                    "message": "Client checksum does not match computed checksum"
                }
            )
    
    try:
        # Compute checksum
        new_checksum = compute_inventory_checksum(request.slots)
        
        # Update character
        character.inventory_json = request.slots
        character.inventory_checksum = new_checksum
        
        # Record event
        record_inventory_event(
            db=db,
            character_id=character.id,
            server_id=server_id,
            event_type="inventory_set",
            checksum=new_checksum
        )
        
        # Commit changes
        db.commit()
        
        logger.info(f"Set inventory for character {character.id}")
        
        # Return success response
        return InventoryResponse(
            character_id=character.id,
            checksum=new_checksum
        )
    
    except Exception as e:
        logger.error(f"Error setting inventory: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error setting inventory: {str(e)}"
        )
