from fastapi import APIRouter, HTTPException

from app.schemas.api_contract import SimulationStartRequest, SimulationStartResponse
from app.services.simulation_service import SimulationService


router = APIRouter(tags=["simulation"])
simulation_service = SimulationService()


@router.post("/simulation/start", response_model=SimulationStartResponse)
def start_simulation(payload: SimulationStartRequest) -> SimulationStartResponse:
    if not payload.caseRef and not (payload.chartSpecRef and payload.metadataRef):
        raise HTTPException(
            status_code=400,
            detail="caseRef is required, or provide both chartSpecRef and metadataRef",
        )
    return simulation_service.run_sync(payload)

