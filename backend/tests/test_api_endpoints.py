import unittest
from fastapi.testclient import TestClient

from app.main import app
from app.database.session import SessionLocal, engine
from app.database.base import Base

class TestApiEndpoints(unittest.TestCase):
    """End-to-end integration tests for all primary platform API routes."""

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Cache a valid plant ID
        plants_res = cls.client.get("/api/v1/plants")
        cls.plants = plants_res.json()
        cls.sample_plant_id = cls.plants[0]["id"] if cls.plants else 7

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_health_check(self):
        res = self.client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"], "online")

    def test_02_plants_endpoints(self):
        res = self.client.get("/api/v1/plants")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(self.plants), 6)
        
        detail_res = self.client.get(f"/api/v1/plants/{self.sample_plant_id}")
        self.assertEqual(detail_res.status_code, 200)
        p_detail = detail_res.json()
        self.assertEqual(p_detail["id"], self.sample_plant_id)
        self.assertIn("capacity_mw", p_detail)

    def test_03_regions_endpoints(self):
        res = self.client.get("/api/v1/regions")
        self.assertEqual(res.status_code, 200)
        regions = res.json()
        self.assertGreaterEqual(len(regions), 3)

        states_res = self.client.get("/api/v1/regions/states")
        self.assertEqual(states_res.status_code, 200)
        states = states_res.json()
        self.assertGreaterEqual(len(states), 3)

    def test_04_weather_telemetry(self):
        res = self.client.get(f"/api/v1/weather/{self.sample_plant_id}")
        self.assertEqual(res.status_code, 200)
        weather_records = res.json()
        self.assertIsInstance(weather_records, list)

    def test_05_hierarchical_aggregations(self):
        # National
        res = self.client.get("/api/v1/aggregate/national?horizon_hours=24")
        self.assertEqual(res.status_code, 200)
        nat = res.json()
        self.assertEqual(nat["level"], "national")
        self.assertGreaterEqual(nat["expected_total_mwh"], 0.0)

        # Region (NR)
        res = self.client.get("/api/v1/aggregate/region/NR?horizon_hours=24")
        self.assertEqual(res.status_code, 200)
        reg = res.json()
        self.assertEqual(reg["level"], "region")

        # State (RJ)
        res = self.client.get("/api/v1/aggregate/state/RJ?horizon_hours=24")
        self.assertEqual(res.status_code, 200)
        st = res.json()
        self.assertEqual(st["level"], "state")

        # Farm
        res = self.client.get("/api/v1/aggregate/farm/BHADLA_SOLAR_01?horizon_hours=24")
        self.assertEqual(res.status_code, 200)
        farm = res.json()
        self.assertEqual(farm["level"], "farm")
        self.assertEqual(len(farm["forecast_points"]), 24)

    def test_06_explainability(self):
        # Global Feature Importance
        res = self.client.get("/api/v1/explain/importance/solar")
        self.assertEqual(res.status_code, 200)
        exp = res.json()
        self.assertEqual(exp["model_type"], "solar")
        self.assertIn("top_features", exp)
        self.assertIn("category_importance", exp)

        # Local SHAP Waterfall
        shap_res = self.client.get(f"/api/v1/explain/shap/{self.sample_plant_id}?horizon_hour=12")
        self.assertEqual(shap_res.status_code, 200)
        shap_data = shap_res.json()
        self.assertIn("base_value", shap_data)
        self.assertIn("waterfall_steps", shap_data)
        self.assertIn("top_positive_features", shap_data)

    def test_07_alerts_and_stats(self):
        res = self.client.get("/api/v1/alerts/stats/summary")
        self.assertEqual(res.status_code, 200)
        summary = res.json()
        self.assertIn("total_active_alerts", summary)

        list_res = self.client.get("/api/v1/alerts")
        self.assertEqual(list_res.status_code, 200)

    def test_08_battery_storage_simulation(self):
        # BESS Profile & Arbitrage
        res = self.client.get(f"/api/v1/storage/profiles/{self.sample_plant_id}?horizon_hours=24")
        self.assertEqual(res.status_code, 200)
        sim = res.json()
        self.assertIn("dispatch_schedule", sim)
        self.assertIn("financial_summary", sim)

        # Storage Custom Simulation
        sim_payload = {
            "generation_profile_mw": [120.0, 150.0, 180.0, 140.0],
            "grid_capacity_limit_mw": 130.0,
            "bess_power_mw": 50.0,
            "bess_energy_mwh": 200.0
        }
        sim_res = self.client.post("/api/v1/storage/simulate", json=sim_payload)
        self.assertEqual(sim_res.status_code, 200)
        sim_result = sim_res.json()
        self.assertIn("dispatch_schedule", sim_result)
        self.assertIn("financial_summary", sim_result)

    def test_09_reporting_cerc_dsm(self):
        # Report Types
        types_res = self.client.get("/api/v1/reports/types")
        self.assertEqual(types_res.status_code, 200)
        self.assertIn("report_types", types_res.json())

        # 96-block CERC DSM Schedule
        res = self.client.get(f"/api/v1/reports/dsm/{self.sample_plant_id}")
        self.assertEqual(res.status_code, 200)
        dsm = res.json()
        self.assertIn("time_blocks", dsm)
        self.assertEqual(len(dsm["time_blocks"]), 96)

    def test_10_mlops_drift_analysis(self):
        res = self.client.get("/api/v1/mlops/drift/solar")
        self.assertEqual(res.status_code, 200)
        drift = res.json()
        self.assertEqual(drift["model_type"], "solar")
        self.assertIn("overall_drift_status", drift)
        self.assertIn("feature_drift", drift)

    def test_11_realtime_telemetry(self):
        res = self.client.get("/api/v1/telemetry/current")
        self.assertEqual(res.status_code, 200)
        telem = res.json()
        self.assertIn("grid", telem)
        self.assertIn("plants", telem)

        stats_res = self.client.get("/api/v1/telemetry/stats")
        self.assertEqual(stats_res.status_code, 200)

    def test_12_retraining_inspection(self):
        res = self.client.get("/api/v1/retrain/status")
        self.assertEqual(res.status_code, 200)
        st = res.json()
        self.assertIn("status", st)

        hist_res = self.client.get("/api/v1/retrain/history")
        self.assertEqual(hist_res.status_code, 200)

        models_res = self.client.get("/api/v1/retrain/models")
        self.assertEqual(models_res.status_code, 200)

if __name__ == "__main__":
    unittest.main()
