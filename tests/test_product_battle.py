import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, init_db
from models.product import Product
from services.product_service import ProductService
from services.battle_service import BattleService
from services.nlp_service import NLPService, IntentType
from services.query_router import QueryRouter


class TestProductBattle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.db = SessionLocal()
        raw_products = cls.db.query(Product).limit(5).all()
        cls.products = [ProductService.get_by_id(cls.db, p.id) for p in raw_products if p]

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_battle_scoring_formula_and_rounds(self):
        """Verify that 5 rounds are calculated and the weighted formula matches exactly."""
        self.assertGreaterEqual(len(self.products), 2, "Database must have at least 2 products for testing")
        p1 = self.products[0]
        p2 = self.products[1]

        battle_res = BattleService.run_battle(
            db=self.db,
            p1=p1,
            p2=p2,
            user_id=None
        )

        self.assertIn("rounds", battle_res)
        self.assertEqual(len(battle_res["rounds"]), 5, "Must have exactly 5 rounds")
        
        rounds = battle_res["rounds"]
        r1_perf = rounds[0]
        r2_price = rounds[1]
        r3_disp = rounds[2]
        r4_batt = rounds[3]
        r5_rat = rounds[4]

        self.assertEqual(r1_perf["title"], "Performance Battle")
        self.assertEqual(r2_price["title"], "Price Value Battle")
        self.assertEqual(r3_disp["title"], "Display Battle")
        self.assertEqual(r4_batt["title"], "Battery Battle")
        self.assertEqual(r5_rat["title"], "User Rating Battle")

        # Verify mathematical formula
        expected_p1 = round(
            (r1_perf["p1_score"] * 0.40) +
            (r2_price["p1_score"] * 0.20) +
            (r3_disp["p1_score"] * 0.15) +
            (r4_batt["p1_score"] * 0.10) +
            (r5_rat["p1_score"] * 0.15),
            1
        )
        expected_p2 = round(
            (r1_perf["p2_score"] * 0.40) +
            (r2_price["p2_score"] * 0.20) +
            (r3_disp["p2_score"] * 0.15) +
            (r4_batt["p2_score"] * 0.10) +
            (r5_rat["p2_score"] * 0.15),
            1
        )

        self.assertEqual(battle_res["product_1_score"], expected_p1)
        self.assertEqual(battle_res["product_2_score"], expected_p2)
        self.assertIn("ai_verdict", battle_res)
        self.assertIn("key_reasons", battle_res)
        self.assertTrue(len(battle_res["key_reasons"]) > 0)

    def test_battle_duplicate_product_prevention(self):
        """Verify that comparing a product against itself raises ValueError."""
        p1 = self.products[0]
        with self.assertRaises(ValueError):
            BattleService.run_battle(
                db=self.db,
                p1=p1,
                p2=p1,
                user_id=None
            )

    def test_nlp_battle_intent_classification(self):
        """Verify that battle phrases correctly trigger battle intents."""
        q1 = "Battle ASUS ROG and MSI Titan"
        res1 = NLPService.parse_query_heuristics(q1)
        self.assertEqual(res1["intent"], IntentType.PRODUCT_BATTLE)

        q2 = "Who wins between 1 and 2?"
        res2 = NLPService.parse_query_heuristics(q2)
        self.assertEqual(res2["intent"], IntentType.BATTLE_VERDICT)

        q3 = "Why did ASUS win the battle?"
        res3 = NLPService.parse_query_heuristics(q3)
        self.assertEqual(res3["intent"], IntentType.BATTLE_EXPLANATION)

    def test_query_router_battle_dispatch(self):
        """Verify that QueryRouter dispatches battle queries with full structured battle payload."""
        p1 = self.products[0]
        p2 = self.products[1]
        active_products = [p1, p2]

        user_q = "Battle 1 and 2"
        nlp_data = NLPService.parse_query_heuristics(user_q)

        routed = QueryRouter.route_query(
            db=self.db,
            user_query=user_q,
            nlp_data=nlp_data,
            active_products=active_products,
            session_id="test_battle_session"
        )

        self.assertEqual(routed["intent"], IntentType.PRODUCT_BATTLE)
        self.assertEqual(routed["type"], "battle")
        self.assertIn("battle", routed)
        self.assertEqual(len(routed["battle"]["rounds"]), 5)
        self.assertIn("ai_verdict", routed["battle"])


if __name__ == "__main__":
    unittest.main()
