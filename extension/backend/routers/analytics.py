import logging
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from extension.backend.middleware.security import verify_api_key
from extension.backend.database import fetch_all

logger = logging.getLogger("capsule.analytics")
router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(verify_api_key)])

@router.get("/history")
async def get_pr_history(
    limit: int = Query(50, description="Max records to return"),
    api_key: str = Depends(verify_api_key)
):
    """
    Returns recent PR analyses for dashboard display.
    """
    prs = await fetch_all("SELECT * FROM pr_analyses ORDER BY analyzed_at DESC LIMIT ?", (limit,))
    return {"status": "success", "data": [dict(pr) for pr in prs]}

@router.get("/trends")
async def get_trends(
    days: int = Query(30, description="Number of days to analyze"),
    api_key: str = Depends(verify_api_key)
):
    """
    Returns aggregated quality scores and violation trends over time.
    """
    prs = await fetch_all("SELECT * FROM pr_analyses ORDER BY analyzed_at ASC")
    
    # Python-side aggregation for DB agnosticism
    from collections import defaultdict
    from datetime import datetime, timedelta
    
    trends = defaultdict(lambda: {"total_prs": 0, "sum_quality": 0, "sum_confidence": 0})
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    for pr in prs:
        try:
            dt = None
            if isinstance(pr["analyzed_at"], str):
                dt = datetime.fromisoformat(pr["analyzed_at"].replace("Z", "+00:00")).replace(tzinfo=None)
            else:
                dt = pr["analyzed_at"]
            
            if dt and dt >= cutoff:
                d_str = dt.strftime("%Y-%m-%d")
                trends[d_str]["total_prs"] += 1
                trends[d_str]["sum_quality"] += pr.get("quality_score", 100) or 100
                trends[d_str]["sum_confidence"] += pr.get("confidence_score", 1.0) or 1.0
        except Exception as e:
            logger.error(f"Error parsing date {pr.get('analyzed_at')}: {e}")
            
    results = []
    for d_str, data in sorted(trends.items()):
        results.append({
            "date": d_str,
            "total_prs": data["total_prs"],
            "avg_quality_score": round(data["sum_quality"] / data["total_prs"], 2),
            "avg_confidence_score": round(data["sum_confidence"] / data["total_prs"], 2)
        })
        
    return {"status": "success", "data": results}

@router.get("/report/export")
async def export_analytics_report(
    format: str = Query("pdf", description="Format to export: pdf or csv"),
    api_key: str = Depends(verify_api_key)
):
    """
    Exports analytics report in PDF or CSV format.
    """
    prs = await fetch_all("SELECT * FROM pr_analyses ORDER BY analyzed_at DESC LIMIT 100")
    
    if format.lower() == "csv":
        import csv
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(["PR Number", "Repo", "Author", "Quality Score", "Confidence", "Analyzed At"])
        for pr in prs:
            writer.writerow([
                pr.get("pr_number"),
                pr.get("repo"),
                pr.get("author"),
                pr.get("quality_score", 100),
                pr.get("confidence_score"),
                pr.get("analyzed_at")
            ])
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=analytics_report.csv"}
        )
    elif format.lower() == "pdf":
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Capsule Analytics Report", ln=1, align='C')
            
            pdf.set_font("Arial", size=10)
            for pr in prs:
                txt = f"PR: {pr.get('pr_number')} | Repo: {pr.get('repo')} | Quality: {pr.get('quality_score', 100)}"
                pdf.cell(200, 10, txt=txt, ln=1, align='L')
                
            pdf_out = pdf.output(dest='S').encode('latin1')
            return StreamingResponse(
                io.BytesIO(pdf_out),
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=analytics_report.pdf"}
            )
        except ImportError:
            raise HTTPException(status_code=500, detail="fpdf library is required for PDF export. Install it with pip install fpdf2")
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use csv or pdf.")
