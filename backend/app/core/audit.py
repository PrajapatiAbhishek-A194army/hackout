import json
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User

logger = logging.getLogger("backend.core.audit")

def log_audit_event(
    db: Session,
    action: str,
    resource_type: str,
    user: Optional[User] = None,
    user_email: Optional[str] = None,
    user_id: Optional[int] = None,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    status: str = "SUCCESS",
    details: Optional[Dict[str, Any]] = None
) -> Optional[AuditLog]:
    """
    Persists an immutable audit log entry to track security, governance,
    and operational control operations.
    """
    try:
        email = user.email if user else user_email
        uid = user.id if user else user_id

        entry = AuditLog(
            user_id=uid,
            user_email=email,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            ip_address=ip_address,
            status=status,
            details_json=json.dumps(details, default=str) if details else None
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return None
