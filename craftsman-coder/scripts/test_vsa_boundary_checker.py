"""
Hermetic, parallel-ready unit tests for vsa_boundary_checker.py.
"""

import tempfile
from pathlib import Path
import unittest

from vsa_boundary_checker import VsaBoundaryChecker


class TestVsaBoundaryChecker(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detects_forbidden_cross_slice_import_python(self):
        slice_orders = self.root / "features" / "orders"
        slice_billing = self.root / "features" / "billing"
        slice_orders.mkdir(parents=True)
        slice_billing.mkdir(parents=True)

        bad_file = slice_orders / "create_order.py"
        bad_file.write_text("from features.billing.charge import charge_card\n")

        checker = VsaBoundaryChecker(slice_root="features")
        violations = checker.scan(self.root)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].source_slice, "orders")
        self.assertEqual(violations[0].target_slice, "billing")

    def test_detects_forbidden_cross_slice_import_typescript(self):
        slice_orders = self.root / "src" / "features" / "orders"
        slice_notifications = self.root / "src" / "features" / "notifications"
        slice_orders.mkdir(parents=True)
        slice_notifications.mkdir(parents=True)

        bad_file = slice_orders / "OrderHandler.ts"
        bad_file.write_text("import { sendEmail } from '../notifications/emailService';\n")

        checker = VsaBoundaryChecker(slice_root="features")
        violations = checker.scan(self.root)

        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].source_slice, "orders")
        self.assertEqual(violations[0].target_slice, "notifications")

    def test_allowed_shared_imports_pass(self):
        slice_orders = self.root / "features" / "orders"
        shared_dir = self.root / "features" / "shared"
        slice_orders.mkdir(parents=True)
        shared_dir.mkdir(parents=True)

        good_file = slice_orders / "order.py"
        good_file.write_text("from features.shared.events import OrderPlacedEvent\n")

        checker = VsaBoundaryChecker(slice_root="features")
        violations = checker.scan(self.root)
        self.assertEqual(len(violations), 0)


if __name__ == "__main__":
    unittest.main()
