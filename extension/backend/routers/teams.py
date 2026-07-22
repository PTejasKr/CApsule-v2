from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from extension.backend.database import execute, fetch_all

from extension.backend.middleware.security import verify_api_key

def verify_super_admin(auth: dict = Depends(verify_api_key)):
    # if it's an API key (string), allow it for scripts.
    if isinstance(auth, str):
        return auth
    # if it's a JWT payload (dict), check role.
    if isinstance(auth, dict):
        if auth.get("global_role") not in ["super_admin", "lead"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized. Requires super_admin or lead role."
            )
        return auth
    
    raise HTTPException(status_code=401, detail="Unauthorized")

router = APIRouter(prefix="/teams", tags=["teams"], dependencies=[Depends(verify_super_admin)])

class TeamCreate(BaseModel):
    name: str
    created_by: int

class TeamMemberCreate(BaseModel):
    profile_id: int
    role: str = "member"

class RepoMapCreate(BaseModel):
    source_repo: str

@router.post("")
async def create_team(team: TeamCreate):
    try:
        await execute(
            "INSERT INTO teams (name, created_by) VALUES (?, ?)",
            (team.name, team.created_by)
        )
        return {"status": "success", "message": "Team created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("")
async def get_teams():
    try:
        teams = await fetch_all("SELECT * FROM teams")
        return {"status": "success", "teams": [dict(t) for t in teams]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{team_id}/members")
async def add_team_member(team_id: int, member: TeamMemberCreate):
    try:
        await execute(
            "INSERT INTO team_members (team_id, profile_id, role) VALUES (?, ?, ?)",
            (team_id, member.profile_id, member.role)
        )
        return {"status": "success", "message": "Member added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{team_id}/members")
async def get_team_members(team_id: int):
    try:
        members = await fetch_all(
            """
            SELECT p.id, p.name, tm.role 
            FROM team_members tm 
            JOIN profiles p ON tm.profile_id = p.id 
            WHERE tm.team_id = ?
            """,
            (team_id,)
        )
        return {"status": "success", "members": [dict(m) for m in members]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{team_id}/projects")
async def map_project_to_team(team_id: int, mapping: RepoMapCreate):
    try:
        await execute(
            "INSERT INTO repository_mappings (source_repo, team_id) VALUES (?, ?)",
            (mapping.source_repo, team_id)
        )
        return {"status": "success", "message": "Repository mapped successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{team_id}/projects")
async def get_team_projects(team_id: int):
    try:
        projects = await fetch_all(
            "SELECT source_repo, created_at FROM repository_mappings WHERE team_id = ?",
            (team_id,)
        )
        return {"status": "success", "projects": [dict(p) for p in projects]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
