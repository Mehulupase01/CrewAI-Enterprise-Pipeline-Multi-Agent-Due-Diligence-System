from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from crewai_enterprise_pipeline_api.api.dependencies import RawDbSession
from crewai_enterprise_pipeline_api.domain.models import TokenRequest, TokenResponse
from crewai_enterprise_pipeline_api.services.auth_service import AuthService

router = APIRouter()


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    payload: TokenRequest,
    request: Request,
    session: RawDbSession,
) -> TokenResponse:
    response = await AuthService(session).issue_client_token(
        payload,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
    )
    if response is None:
        request.state.auth_failure_context = {
            "action": "AUTH_FAILURE",
            "detail": "Invalid client credentials.",
            "status_code": status.HTTP_401_UNAUTHORIZED,
            "actor_id": payload.client_id,
            "actor_email": None,
            "org_id": None,
        }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials.",
        )
    return response
