from fastapi import APIRouter, HTTPException
from services.scheduler_service import run_placement_scheduler, mark_problem_completed
from pydantic import BaseModel

router = APIRouter()

class CompleteRequest(BaseModel):
    db_id: str

@router.post("/generate")
async def generate_schedule(user_id: str = "JARVIS_ADMIN"):
    try:
        res = await run_placement_scheduler(days=7, user_id=user_id)
        if not res:
            raise HTTPException(status_code=500, detail="Failed to generate schedule")
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/complete")
async def complete_problem(req: CompleteRequest, user_id: str = "JARVIS_ADMIN"):
    try:
        success = await mark_problem_completed(req.db_id, user_id=user_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to mark problem completed")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
