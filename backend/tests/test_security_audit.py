import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal, engine
from app.database.base import Base
from app.models.user import User
from app.models.audit_log import AuditLog
from app.core.security import hash_password, verify_password, create_access_token

class TestSecurityAndAudit(unittest.TestCase):
    """Verifies BCrypt hashing, JWT authentication, RBAC authorization, and audit logs."""

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Create test users if not existing
        cls.admin_email = "sec_admin@grid.gov.in"
        cls.operator_email = "sec_operator@grid.gov.in"

        cls.admin_user = cls.db.query(User).filter(User.email == cls.admin_email).first()
        if not cls.admin_user:
            cls.admin_user = User(
                email=cls.admin_email,
                hashed_password=hash_password("SuperSecretAdmin1!"),
                role="admin",
                full_name="Security Admin",
                is_active=True
            )
            cls.db.add(cls.admin_user)

        cls.operator_user = cls.db.query(User).filter(User.email == cls.operator_email).first()
        if not cls.operator_user:
            cls.operator_user = User(
                email=cls.operator_email,
                hashed_password=hash_password("OperatorPass123!"),
                role="grid_operator",
                full_name="Grid Dispatcher",
                is_active=True
            )
            cls.db.add(cls.operator_user)
        cls.db.commit()

        cls.admin_token = create_access_token(subject=cls.admin_user.email, role="admin", user_id=cls.admin_user.id)
        cls.operator_token = create_access_token(subject=cls.operator_user.email, role="grid_operator", user_id=cls.operator_user.id)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_bcrypt_hashing_and_verification(self):
        plain = "GridSecurity2026!"
        hashed = hash_password(plain)
        self.assertNotEqual(plain, hashed)
        self.assertTrue(hashed.startswith("$2b$"))
        self.assertTrue(verify_password(plain, hashed))
        self.assertFalse(verify_password("WrongPassword!", hashed))

    def test_02_jwt_token_validity(self):
        self.assertIsNotNone(self.admin_token)
        self.assertIsInstance(self.admin_token, str)

        # Query /auth/me with admin token
        res = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["email"], self.admin_email)
        self.assertEqual(data["role"], "admin")

    def test_03_rbac_unauthorized_rejection(self):
        # 1. Anonymous request to admin-only user list -> 401
        res = self.client.get("/api/v1/auth/users")
        self.assertEqual(res.status_code, 401)

        # 2. Operator request to admin-only user list -> 403 Forbidden
        res = self.client.get(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {self.operator_token}"}
        )
        self.assertEqual(res.status_code, 403)

        # 3. Admin request to admin-only user list -> 200 OK
        res = self.client.get(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.json(), list)

    def test_04_audit_log_persistence(self):
        logs = self.db.query(AuditLog).order_by(AuditLog.id.desc()).limit(10).all()
        self.assertGreater(len(logs), 0, "Audit logs must record platform activity")
        first_log = logs[0]
        self.assertIsNotNone(first_log.action)
        self.assertIsNotNone(first_log.status)

if __name__ == "__main__":
    unittest.main()
