from fastapi import APIRouter, Depends, HTTPException

from insight_engine.ai.handlers import ProfileInterpretationError, interpret_profile
from insight_engine.api.deps import get_current_user
from insight_engine.api.schemas import ProfileInterpretRequest, ProfileInterpretResponse
from insight_engine.domain.models import User

router = APIRouter(prefix="/profile", tags=["profile"])


@router.post("/interpret", response_model=ProfileInterpretResponse)
async def interpret_profile_endpoint(
    request: ProfileInterpretRequest,
    user: User = Depends(get_current_user),
):
    """Derive a structured user profile from a plain-words description.

    The AI only classifies what the text expresses; the returned profile is a
    proposal for the user to review and pass to the analysis endpoints — it is
    never applied automatically.
    """
    try:
        result = interpret_profile(request.text)
    except ProfileInterpretationError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ProfileInterpretResponse(**result)
