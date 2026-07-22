import logging
import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from extension.backend.middleware.security import verify_api_key
from extension.backend.database import fetch_all
from extension.backend.routers.api import _reconstruct_summary_from_row

logger = logging.getLogger("capsule.admin")
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(verify_api_key)])

@router.get("/dashboard")
async def get_admin_dashboard(api_key: str = Depends(verify_api_key)):
    """
    Returns an aggregated view for Super Admins:
    Profiles (teams), Repositories they are working on, and Recent PR activity.
    """
    # Assuming the API Key determines access, here we just check if it's valid.
    # In a full implementation, the API key might map to a user/profile to verify `is_super_admin`.
    
    profiles = await fetch_all("SELECT * FROM profiles")
    repos = await fetch_all("SELECT * FROM repository_mappings")
    pr_analyses = await fetch_all("SELECT * FROM pr_analyses ORDER BY analyzed_at DESC LIMIT 50")
    
    dashboard_data = {
        "profiles": [dict(p) for p in profiles],
        "repository_mappings": [dict(r) for r in repos],
        "recent_prs": []
    }
    
    for r in pr_analyses:
        try:
            summary = await _reconstruct_summary_from_row(r)
            sum_dict = summary.model_dump()
            sum_dict["analyzed_at"] = r.get("analyzed_at")
            dashboard_data["recent_prs"].append(sum_dict)
        except Exception as e:
            logger.error(f"Error reconstructing PR summary for admin dashboard: {e}")
            
    return {"status": "success", "data": dashboard_data}

@router.get("/compliance/report")
async def get_compliance_report(format: str = "json", api_key: str = Depends(verify_api_key)):
    """
    Exports the audit log for compliance reporting in JSON or CSV format.
    """
    logs = await fetch_all("SELECT * FROM audit_log ORDER BY timestamp DESC")
    
    if format.lower() == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(["ID", "PR Number", "Input Hash", "Model", "Tokens", "Latency MS", "Timestamp"])
        for log in logs:
            writer.writerow([
                log.get("id"),
                log.get("pr_number"),
                log.get("input_hash"),
                log.get("model"),
                log.get("tokens"),
                log.get("latency_ms"),
                log.get("timestamp")
            ])
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]), 
            media_type="text/csv", 
            headers={"Content-Disposition": "attachment; filename=compliance_report.csv"}
        )
    
    return {"status": "success", "data": [dict(log_item) for log_item in logs]}
