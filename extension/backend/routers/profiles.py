import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
import httpx
from extension.backend.middleware.security import verify_api_key
from extension.backend.models.schemas import (
    ProfileCreate, ProfileResponse, RepositoryMappingCreate, 
    WebhookDeployRequest, BRDUploadResponse, BRDHistoryItem
)
from extension.backend.database import insert, fetch_one, fetch_all, execute_query
from extension.backend.services.brd_manager import BRDManager
from extension.backend.services.crypto import encrypt_token, decrypt_token

logger = logging.getLogger("capsule.profiles")
router = APIRouter(prefix="/profiles", tags=["profiles"], dependencies=[Depends(verify_api_key)])
brd_manager = BRDManager()

@router.post("/", response_model=ProfileResponse)
async def create_profile(profile: ProfileCreate):
    """
    Creates a new profile. Requires API key.
    """
    try:
        data = profile.model_dump()
        if data.get("github_token"):
            data["github_token"] = encrypt_token(data["github_token"])
        profile_id = await insert("profiles", data)
        if data.get("github_token"):
            data["github_token"] = decrypt_token(data["github_token"])
        return ProfileResponse(id=profile_id, **data)
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        raise HTTPException(status_code=400, detail="Profile creation failed (possibly duplicate name)")

@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(profile_id: int, profile: ProfileCreate):
    """
    Updates an existing profile (e.g. to save custom rules).
    """
    try:
        sql = """
            UPDATE profiles 
            SET name = ?, changelog_repo = ?, ai_model = ?, brd_content = ?, github_token = ?, custom_rules = ?
            WHERE id = ?
        """
        encrypted_token = encrypt_token(profile.github_token) if profile.github_token else profile.github_token
        updated = await execute_query(sql, (
            profile.name, profile.changelog_repo, profile.ai_model, 
            profile.brd_content, encrypted_token, profile.custom_rules, profile_id
        ))
        if not updated:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        row = await fetch_one("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        if not row:
            raise HTTPException(status_code=404, detail="Profile not found after update")
            
        row_dict = dict(row)
        if row_dict.get("github_token"):
            row_dict["github_token"] = decrypt_token(row_dict["github_token"])
        return ProfileResponse(**row_dict)
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=400, detail="Profile update failed")

@router.get("/", response_model=list[ProfileResponse])
async def list_profiles():
    """
    Lists all profiles.
    """
    rows = await fetch_all("SELECT * FROM profiles")
    profiles = []
    for row in rows:
        row_dict = dict(row)
        if row_dict.get("github_token"):
            row_dict["github_token"] = decrypt_token(row_dict["github_token"])
        profiles.append(ProfileResponse(**row_dict))
    return profiles

@router.post("/mappings")
async def map_repository(mapping: RepositoryMappingCreate):
    """
    Maps a repository to a specific profile.
    """
    profile = await fetch_one("SELECT * FROM profiles WHERE id = ?", (mapping.profile_id,))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    try:
        await insert("repository_mappings", mapping.model_dump())
        return {"status": "success", "message": f"Mapped {mapping.source_repo} to profile {mapping.profile_id}"}
    except Exception as e:
        logger.error(f"Error mapping repository: {e}")
        raise HTTPException(status_code=400, detail="Mapping failed")

@router.get("/mappings/{owner}/{repo}")
async def get_repository_mapping(owner: str, repo: str):
    """
    Gets the profile mapped to a specific repository.
    """
    full_repo = f"{owner}/{repo}"
    row = await fetch_one("""
        SELECT p.* FROM profiles p
        JOIN repository_mappings rm ON p.id = rm.profile_id
        WHERE rm.source_repo = ?
    """, (full_repo,))
    
    if not row:
        raise HTTPException(status_code=404, detail="No profile mapping found for this repository")
        
    row_dict = dict(row)
    if row_dict.get("github_token"):
        row_dict["github_token"] = decrypt_token(row_dict["github_token"])
        
    return ProfileResponse(**row_dict)

@router.post("/mappings/deploy-webhook")
async def deploy_webhook(request: WebhookDeployRequest):
    """
    Deploys a GitHub webhook to the source_repo using the profile's GitHub token.
    """
    profile = await fetch_one("SELECT * FROM profiles WHERE id = ?", (request.profile_id,))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    token = decrypt_token(profile.get("github_token"))
    if not token:
        raise HTTPException(status_code=400, detail="Profile has no github_token configured")
        
    try:
        await insert("repository_mappings", {"source_repo": request.source_repo, "profile_id": request.profile_id})
    except Exception as e:
        logger.warning(f"Repo already mapped or mapping failed: {e}")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    payload = {
        "name": "web",
        "active": True,
        "events": ["pull_request", "pull_request_review"],
        "config": {
            "url": request.webhook_url,
            "content_type": "json",
            "insecure_ssl": "0"
        }
    }
    
    url = f"https://api.github.com/repos/{request.source_repo}/hooks"
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code in [200, 201]:
            return {"status": "success", "message": "Webhook deployed successfully"}
        elif resp.status_code == 422:
            return {"status": "skipped", "message": "Webhook might already exist"}
        else:
            logger.error(f"GitHub API Error: {resp.text}")
            raise HTTPException(status_code=400, detail=f"Failed to deploy webhook: {resp.text}")


@router.post("/{profile_id}/brd/upload", response_model=BRDUploadResponse)
async def upload_brd_file(
    profile_id: int,
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    version: Optional[str] = Form(None)
):
    """
    Uploads a new BRD version for a specific profile.
    """
    if file:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8")
    elif text_content:
        content = text_content
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either file or text_content must be provided"
        )

    res = await brd_manager.upload_brd(profile_id, content, version)
    current_meta = await brd_manager.get_current_brd(profile_id)
    
    return BRDUploadResponse(
        status=res["status"],
        version=res["version"],
        hash=res["hash"],
        uploaded_at=current_meta.get("uploaded_at", "Just Uploaded") if current_meta else "Just Uploaded"
    )

@router.get("/{profile_id}/brd/current")
async def get_current_brd(profile_id: int):
    """
    Returns active BRD document details for a profile.
    """
    meta = await brd_manager.get_current_brd(profile_id)
    if not meta:
        return {"content": "", "version": "v0.0.0", "hash": "", "uploaded_at": None}
    return meta

@router.get("/{profile_id}/brd/history", response_model=List[BRDHistoryItem])
async def get_brd_history(profile_id: int):
    """
    Returns history of all uploaded BRD versions for a profile.
    """
    return await brd_manager.get_brd_history(profile_id)

@router.get("/{profile_id}/pr-history")
async def get_pr_history(profile_id: int):
    """
    Returns history of all analyzed PRs for repositories mapped to this profile.
    """
    sql = """
        SELECT pa.* FROM pr_analyses pa
        JOIN repository_mappings rm ON pa.repo LIKE rm.source_repo || '%'
        WHERE rm.profile_id = ?
        ORDER BY pa.analyzed_at DESC
    """
    rows = await fetch_all(sql, (profile_id,))
    
    from extension.backend.routers.api import _reconstruct_summary_from_row
    
    summaries = []
    for r in rows:
        try:
            summary = await _reconstruct_summary_from_row(r)
            sum_dict = summary.model_dump()
            sum_dict["analyzed_at"] = r.get("analyzed_at")
            summaries.append(sum_dict)
        except Exception as e:
            logger.error(f"Error reconstructing PR summary for history: {e}")
            
    return summaries
