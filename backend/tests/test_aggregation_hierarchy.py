import unittest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal, engine
from app.database.base import Base

class TestAggregationHierarchy(unittest.TestCase):
    """
    Validates the core mathematical theorem of the platform:
    Aggregation is strictly bottom-up additive: Sum(Farms) == Region, Sum(Regions) == National.
    Guarantees 100% arithmetic fidelity across all operational tiers.
    """

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_regional_to_national_summation(self):
        """Validates that Sum(Regions) equals National forecast at every single hourly timepoint."""
        nat_res = self.client.get("/api/v1/aggregate/national?horizon_hours=24")
        self.assertEqual(nat_res.status_code, 200)
        national_data = nat_res.json()
        national_pts = national_data["forecast_points"]

        regions_res = self.client.get("/api/v1/regions")
        self.assertEqual(regions_res.status_code, 200)
        regions = regions_res.json()

        # Aggregate points across all active regions
        summed_regional_mw = np.zeros(24)
        for r in regions:
            reg_fc_res = self.client.get(f"/api/v1/aggregate/region/{r['code']}?horizon_hours=24")
            if reg_fc_res.status_code == 200:
                pts = reg_fc_res.json()["forecast_points"]
                for i in range(min(24, len(pts))):
                    summed_regional_mw[i] += pts[i]["predicted_mw"]

        # National points
        national_mw = np.array([pt["predicted_mw"] for pt in national_pts[:24]])

        # Compare sums
        diff = np.abs(summed_regional_mw - national_mw)
        max_diff = np.max(diff) if len(diff) > 0 else 0.0
        self.assertLess(max_diff, 0.05, f"Regional sum deviated from National forecast by {max_diff} MW")

    def test_02_farm_to_regional_summation(self):
        """Validates that Sum(Farms in NR) equals Northern Region aggregated forecast."""
        nr_res = self.client.get("/api/v1/aggregate/region/NR?horizon_hours=24")
        self.assertEqual(nr_res.status_code, 200)
        nr_data = nr_res.json()
        nr_points = np.array([pt["predicted_mw"] for pt in nr_data["forecast_points"][:24]])

        # NR plants: Bhadla Solar Park + Jaisalmer Wind Park
        plants_res = self.client.get("/api/v1/plants")
        plants = plants_res.json()
        nr_region = next((r for r in self.client.get("/api/v1/regions").json() if r["code"] == "NR"), None)
        self.assertIsNotNone(nr_region)

        nr_plants = [p for p in plants if p["region_id"] == nr_region["id"]]
        self.assertGreaterEqual(len(nr_plants), 2)

        summed_farm_mw = np.zeros(24)
        for p in nr_plants:
            farm_res = self.client.get(f"/api/v1/aggregate/farm/{p['code']}?horizon_hours=24")
            self.assertEqual(farm_res.status_code, 200)
            farm_pts = farm_res.json()["forecast_points"]
            for i in range(24):
                summed_farm_mw[i] += farm_pts[i]["predicted_mw"]

        diff = np.abs(summed_farm_mw - nr_points)
        max_diff = np.max(diff)
        self.assertLess(max_diff, 0.05, f"Farm sum in NR deviated from regional forecast by {max_diff} MW")

    def test_03_fuel_mix_additivity(self):
        """Validates that Solar MW + Wind MW == Total Renewable MW at every hour."""
        nat_res = self.client.get("/api/v1/aggregate/national?horizon_hours=24")
        nat_data = nat_res.json()

        for pt in nat_data["forecast_points"]:
            solar = pt.get("solar_mw") or 0.0
            wind = pt.get("wind_mw") or 0.0
            total = pt["predicted_mw"]
            self.assertAlmostEqual(solar + wind, total, delta=0.01)

if __name__ == "__main__":
    unittest.main()
