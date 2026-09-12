from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.region_state import RegionResponse, StateResponse
from app.services import crud

router = APIRouter()

@router.get("", response_model=List[RegionResponse], summary="List all grid balancing regions")
def get_regions(db: Session = Depends(get_db)):
    """Retrieve all Indian electricity grid balancing regions (Northern, Western, Southern, etc.)."""
    return crud.get_regions(db=db)

@router.get("/states", response_model=List[StateResponse], summary="List states")
def get_states(
    region_id: Optional[int] = Query(None, description="Filter states by region ID"),
    db: Session = Depends(get_db)
):
    """Retrieve all Indian states or filter by regional grid authority."""
    return crud.get_states(db=db, region_id=region_id)

@router.get("/{region_id}", response_model=RegionResponse, summary="Get region by ID")
def get_region(
    region_id: int,
    db: Session = Depends(get_db)
):
    """Get single region by ID with nested states."""
    region = crud.get_region_by_id(db=db, region_id=region_id)
    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region with ID {region_id} not found"
        )
    return region

@router.get("/states/{state_id}", response_model=StateResponse, summary="Get state by ID")
def get_state(
    state_id: int,
    db: Session = Depends(get_db)
):
    """Get state details by ID."""
    state = crud.get_state_by_id(db=db, state_id=state_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"State with ID {state_id} not found"
        )
    return state
