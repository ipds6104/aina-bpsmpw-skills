"""
Parallel-ready, hermetic unit tests for static_srp_analyzer.py.
"""

import tempfile
from pathlib import Path
import unittest

from static_srp_analyzer import SrpLengthRule, AbstractionBypassRule, StaticAnalysisRunner


class TestStaticSrpAnalyzer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detects_bloated_function_srp_violation(self):
        long_func_code = "def bloated_processor():\n" + "\n".join([f"    x_{i} = {i}" for i in range(70)])
        py_file = self.root / "orders.py"
        py_file.write_text(long_func_code)

        runner = StaticAnalysisRunner([SrpLengthRule(max_func_lines=50)])
        violations = runner.scan_path(self.root)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].category, "SRP_LENGTH")
        self.assertEqual(violations[0].symbol, "bloated_processor")

    def test_detects_bloated_component_srp_violation(self):
        long_tsx = "// React component\n" + "\n".join([f"const Item{i} = () => <div>{i}</div>;" for i in range(250)])
        tsx_file = self.root / "DashboardView.tsx"
        tsx_file.write_text(long_tsx)

        runner = StaticAnalysisRunner([SrpLengthRule(max_class_lines=180)])
        violations = runner.scan_path(self.root)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].category, "SRP_LENGTH")
        self.assertIn("DashboardView.tsx", violations[0].file_path)

    def test_detects_direct_db_coupling_abstraction_bypass(self):
        code = """
def checkout_order(order_id):
    query = "SELECT * FROM orders WHERE id = " + str(order_id)
    return query
"""
        service_file = self.root / "checkout_service.py"
        service_file.write_text(code)

        runner = StaticAnalysisRunner([AbstractionBypassRule()])
        violations = runner.scan_path(self.root)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].category, "ABSTRACTION_BYPASS")

    def test_clean_srp_and_di_code_passes(self):
        clean_code = """
class PaymentService:
    def __init__(self, gateway):
        self.gateway = gateway

    def pay(self, amount):
        return self.gateway.charge(amount)
"""
        clean_file = self.root / "payment_service.py"
        clean_file.write_text(clean_code)

        runner = StaticAnalysisRunner([SrpLengthRule(), AbstractionBypassRule()])
        violations = runner.scan_path(self.root)
        self.assertEqual(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
