"""
Alert API Routes for SENTINEL AI.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import Alert
from alerts.alert_manager import alert_manager

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _release_machine(alert: Alert):
    """Once an alert is closed, let the monitoring pipeline raise new alerts for its machine."""
    alert_manager.confirmation_filter.resolve_alert(alert.machine_id)
    active = alert_manager.active_alerts.pop(alert.alert_id, None)
    if active and active.get("escalation_timer"):
        active["escalation_timer"].cancel()


@router.get("/")
def list_alerts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all alerts with optional filtering."""
    query = db.query(Alert)
    
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    
    alerts = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "alerts": alerts,
        "count": len(alerts),
        "filters": {"status": status, "severity": severity}
    }


@router.get("/{alert_id}")
def get_alert(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific alert by ID."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    mechanic_id: int,
    db: Session = Depends(get_db)
):
    """Acknowledge an alert."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "acknowledged"
    alert.responded_by_id = mechanic_id
    alert.responded_at = datetime.utcnow()
    alert.response = "acknowledged"
    
    db.commit()
    db.refresh(alert)
    
    return {"success": True, "alert": alert}


@router.post("/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    mechanic_id: int,
    resolution: str,
    notes: str = "",
    actual_failure: str = "",
    gemini_was_correct: bool = True,
    db: Session = Depends(get_db)
):
    """Resolve an alert with feedback on Gemini accuracy."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = "resolved"
    alert.resolved_by_id = mechanic_id
    alert.resolved_at = datetime.utcnow()
    alert.resolution = resolution
    alert.resolution_notes = notes
    alert.actual_failure = actual_failure
    alert.gemini_was_correct = gemini_was_correct
    
    db.commit()
    db.refresh(alert)
    _release_machine(alert)
    
    # Log feedback for model improvement
    if actual_failure:
        print(f"[Feedback] Alert {alert_id}: Gemini predicted '{alert.failure_type}', Actual was '{actual_failure}', Correct: {gemini_was_correct}")
    
    return {
        "success": True,
        "alert_id": alert_id,
        "status": "resolved",
        "gemini_accuracy": {
            "predicted": alert.failure_type,
            "actual": actual_failure,
            "correct": gemini_was_correct
        }
    }


@router.post("/{alert_id}/respond")
def mechanic_respond(
    alert_id: str,
    response: str,  # 'accepted' or 'rejected'
    eta_minutes: int = None,
    notes: str = "",
    db: Session = Depends(get_db)
):
    """Mechanic responds to an alert with accept/reject and ETA."""
    alert = db.query(Alert).filter(Alert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.status != "open":
        raise HTTPException(status_code=400, detail="Alert already responded")
    
    # Update alert based on response
    if response == "accepted":
        alert.status = "acknowledged"
        alert.eta_minutes = eta_minutes
    elif response == "rejected":
        alert.status = "rejected"
        _release_machine(alert)
    else:
        raise HTTPException(status_code=400, detail="Invalid response. Use 'accepted' or 'rejected'")
    
    alert.response = response
    alert.response_notes = notes
    alert.responded_at = datetime.utcnow()
    
    db.commit()
    db.refresh(alert)
    
    return {
        "success": True,
        "alert_id": alert_id,
        "status": alert.status,
        "response": response,
        "eta_minutes": eta_minutes,
        "responded_at": alert.responded_at
    }


@router.get("/stats/summary")
def get_alert_stats(db: Session = Depends(get_db)):
    """Get alert statistics."""
    total = db.query(Alert).count()
    open_count = db.query(Alert).filter(Alert.status == "open").count()
    acknowledged = db.query(Alert).filter(Alert.status == "acknowledged").count()
    resolved = db.query(Alert).filter(Alert.status == "resolved").count()
    rejected = db.query(Alert).filter(Alert.status == "rejected").count()
    
    critical = db.query(Alert).filter(Alert.severity == "CRITICAL").count()
    warning = db.query(Alert).filter(Alert.severity == "WARNING").count()
    
    # Gemini accuracy stats
    resolved_with_feedback = db.query(Alert).filter(
        Alert.status == "resolved",
        Alert.gemini_was_correct.isnot(None)
    ).count()
    
    correct_predictions = db.query(Alert).filter(
        Alert.gemini_was_correct == True
    ).count()
    
    accuracy_rate = round((correct_predictions / resolved_with_feedback * 100), 1) if resolved_with_feedback > 0 else 0
    
    return {
        "total": total,
        "by_status": {
            "open": open_count,
            "acknowledged": acknowledged,
            "resolved": resolved,
            "rejected": rejected
        },
        "by_severity": {
            "critical": critical,
            "warning": warning
        },
        "gemini_accuracy": {
            "resolved_with_feedback": resolved_with_feedback,
            "correct_predictions": correct_predictions,
            "accuracy_rate": accuracy_rate
        }
    }


@router.get("/stats/feedback")
def get_feedback_stats(db: Session = Depends(get_db)):
    """Get detailed feedback statistics for model improvement."""
    from sqlalchemy import func
    
    # Get all resolved alerts with feedback
    feedback_alerts = db.query(Alert).filter(
        Alert.status == "resolved",
        Alert.actual_failure.isnot(None)
    ).all()
    
    # Calculate accuracy by failure type
    failure_type_accuracy = {}
    for alert in feedback_alerts:
        predicted = alert.failure_type
        actual = alert.actual_failure
        correct = alert.gemini_was_correct
        
        if predicted not in failure_type_accuracy:
            failure_type_accuracy[predicted] = {"total": 0, "correct": 0}
        
        failure_type_accuracy[predicted]["total"] += 1
        if correct:
            failure_type_accuracy[predicted]["correct"] += 1
    
    # Calculate percentages
    for ft in failure_type_accuracy:
        total = failure_type_accuracy[ft]["total"]
        correct = failure_type_accuracy[ft]["correct"]
        failure_type_accuracy[ft]["accuracy"] = round((correct / total * 100), 1)
    
    return {
        "total_feedback": len(feedback_alerts),
        "by_failure_type": failure_type_accuracy,
        "recent_feedback": [
            {
                "alert_id": a.alert_id,
                "predicted": a.failure_type,
                "actual": a.actual_failure,
                "correct": a.gemini_was_correct,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None
            }
            for a in feedback_alerts[-10:]  # Last 10
        ]
    }
