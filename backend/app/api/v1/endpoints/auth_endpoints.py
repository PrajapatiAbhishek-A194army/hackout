import logging
from typing import List, Optional
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.session import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.auth import (
    UserLoginRequest, TokenResponse, UserResponse,
    UserCreateRequest, UserSignupRequest, AuditLogResponse, AuditLogListResponse
)
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user, require_roles
from app.core.audit import log_audit_event

logger = logging.getLogger("backend.api.auth")

router = APIRouter()

def normalize_role(role_raw: str) -> str:
    r = (role_raw or "").strip().lower().replace("_", "-")
    if r in ["operator", "grid-operator", "grid_operator", "sldc", "nldc"]:
        return "grid-operator"
    if r in ["utility", "discom", "procurement"]:
        return "utility"
    if r in ["plant-owner", "plant_owner", "ipp", "generator"]:
        return "plant-owner"
    if r in ["energy-trader", "energy_trader", "trader", "analyst"]:
        return "energy-trader"
    if r in ["admin", "administrator"]:
        return "admin"
    return "grid-operator"

# Default accounts seeded for quick role switching and testing
DEFAULT_SEEDS = [
    {
        "email": "operator@gridflow.ai",
        "password": "OperatorPassword@123",
        "full_name": "Senior Grid Operator (NLDC)",
        "role": "grid-operator",
        "organization": "National Load Despatch Centre (NLDC)",
        "is_superuser": False
    },
    {
        "email": "utility@gridflow.ai",
        "password": "UtilityPassword@123",
        "full_name": "Chief Procurement Officer",
        "role": "utility",
        "organization": "State Electricity Distribution Co. (DISCOM)",
        "is_superuser": False
    },
    {
        "email": "plantowner@gridflow.ai",
        "password": "PlantPassword@123",
        "full_name": "Solar & Wind Asset Director",
        "role": "plant-owner",
        "organization": "Adani Green & ReNew IPP Assets",
        "is_superuser": False
    },
    {
        "email": "trader@gridflow.ai",
        "password": "TraderPassword@123",
        "full_name": "Lead Power Market Arbitrageur",
        "role": "energy-trader",
        "organization": "Indian Energy Exchange (IEX) Trading Desk",
        "is_superuser": False
    },
    {
        "email": "admin@gridflow.ai",
        "password": "AdminPassword@123",
        "full_name": "Chief Platform Architect",
        "role": "admin",
        "organization": "GridFlow Central Control",
        "is_superuser": True
    }
]

def seed_default_users_if_empty(db: Session):
    """
    Seeds default role accounts if users table is empty.
    """
    count = db.query(User).count()
    if count == 0:
        logger.info("Empty users table detected. Initializing default system accounts...")
        for seed in DEFAULT_SEEDS:
            u = User(
                email=seed["email"],
                hashed_password=hash_password(seed["password"]),
                full_name=seed["full_name"],
                role=seed["role"],
                organization=seed["organization"],
                is_active=True,
                is_superuser=seed["is_superuser"]
            )
            db.add(u)
        db.commit()
        logger.info("Successfully seeded 4 default accounts (admin, operator, analyst, auditor).")

@router.post("/seed-default-users", response_model=dict)
def trigger_seed_users(db: Session = Depends(get_db)):
    """
    Idempotent endpoint to seed default system accounts.
    """
    seed_default_users_if_empty(db)
    users = db.query(User).all()
    return {
        "status": "success",
        "total_users": len(users),
        "seeded_accounts": [u.email for u in users]
    }

@router.post("/login", response_model=TokenResponse)
def login(
    credentials: UserLoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Authenticates user credentials and issues a signed JWT access token.
    Records audit entry for all login attempts.
    """
    # Auto-seed if database is empty on first login attempt
    seed_default_users_if_empty(db)

    client_ip = request.client.host if request.client else "unknown"

    user = db.query(User).filter(User.email == credentials.email.lower()).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        log_audit_event(
            db=db,
            action="LOGIN_FAILED",
            resource_type="auth",
            user_email=credentials.email,
            ip_address=client_ip,
            status="DENIED",
            details={"reason": "Invalid credentials"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        log_audit_event(
            db=db,
            action="LOGIN_REJECTED",
            resource_type="auth",
            user=user,
            ip_address=client_ip,
            status="DENIED",
            details={"reason": "User account inactive"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated. Contact system administrator."
        )

    user_role = normalize_role(user.role)

    # Issue JWT Token
    access_token = create_access_token(
        subject=user.email,
        role=user_role,
        user_id=user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    log_audit_event(
        db=db,
        action="LOGIN_SUCCESS",
        resource_type="auth",
        user=user,
        ip_address=client_ip,
        status="SUCCESS",
        details={"role": user_role}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        role=user_role,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        organization=user.organization
    )

@router.post("/signup", response_model=TokenResponse)
def signup(
    req: UserSignupRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public self-registration endpoint for energy market participants:
    Grid Operators, Utility Companies, Renewable Plant Owners, Energy Traders.
    Immediately issues signed JWT session token upon registration.
    """
    seed_default_users_if_empty(db)
    
    clean_email = req.email.strip().lower()
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{clean_email}' already exists. Please log in."
        )

    assigned_role = normalize_role(req.role)
    org = (req.organization or "").strip()
    if not org:
        default_orgs = {
            "grid-operator": "State / National Load Despatch Centre",
            "utility": "Power Distribution Utility (DISCOM)",
            "plant-owner": "Independent Renewable Power Producer (IPP)",
            "energy-trader": "Power Exchange Trading Desk"
        }
        org = default_orgs.get(assigned_role, "Clean Energy Enterprise")

    new_user = User(
        email=clean_email,
        hashed_password=hash_password(req.password),
        full_name=req.full_name.strip(),
        role=assigned_role,
        organization=org,
        is_active=True,
        is_superuser=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    client_ip = request.client.host if request.client else "unknown"
    log_audit_event(
        db=db,
        action="USER_SIGNUP",
        resource_type="auth",
        user=new_user,
        ip_address=client_ip,
        status="SUCCESS",
        details={"role": assigned_role, "organization": org}
    )

    access_token = create_access_token(
        subject=new_user.email,
        role=assigned_role,
        user_id=new_user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        role=assigned_role,
        user_id=new_user.id,
        full_name=new_user.full_name,
        email=new_user.email,
        organization=new_user.organization
    )

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Returns authenticated user's profile and active permissions.
    """
    return current_user

@router.post("/register", response_model=UserResponse)
def register_new_user(
    req: UserCreateRequest,
    request: Request,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Registers a new platform user. Restricted to Administrator role.
    """
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{req.email}' already exists."
        )

    new_user = User(
        email=req.email.lower(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name,
        role=req.role.lower(),
        organization=req.organization,
        is_active=True,
        is_superuser=(req.role.lower() == "admin")
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    log_audit_event(
        db=db,
        action="USER_CREATED",
        resource_type="users",
        user=current_user,
        resource_id=str(new_user.id),
        ip_address=request.client.host if request.client else None,
        status="SUCCESS",
        details={"created_email": new_user.email, "role": new_user.role}
    )

    return new_user

@router.get("/users", response_model=List[UserResponse])
def list_users(
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db)
):
    """
    Lists all platform users. Restricted to Administrator role.
    """
    return db.query(User).order_by(User.created_at.desc()).all()

@router.get("/audit-logs", response_model=AuditLogListResponse)
def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action"),
    resource_type: Optional[str] = Query(None, description="Filter by resource"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles(["admin", "auditor"])),
    db: Session = Depends(get_db)
):
    """
    Returns governance and security audit trails. Restricted to Admin and Auditor roles.
    """
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    if user_email:
        q = q.filter(AuditLog.user_email.ilike(f"%{user_email}%"))

    logs = q.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return AuditLogListResponse(
        total_count=len(logs),
        logs=[AuditLogResponse.model_validate(l) for l in logs]
    )
