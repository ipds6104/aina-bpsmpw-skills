"""
Hermetic, Parallel-ready Unit Tests for CodeGraph AST Impact Analyzer.
Tests are completely stateless and isolated to allow full parallel execution.
"""

import tempfile
from pathlib import Path
import unittest

from codegraph_impact import PythonAstParser, GenericRegexParser, CodeGraph, ImpactAnalyzer


class TestCodeGraphImpactHermetic(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_single_responsibility_python_ast_parsing(self):
        py_file = self.root / "service.py"
        py_file.write_text(
            """
import os

class PaymentGateway:
    def process_charge(self, amount):
        return True

def handle_checkout():
    gateway = PaymentGateway()
    return gateway.process_charge(100)
"""
        )

        test_file = self.root / "test_service.py"
        test_file.write_text(
            """
from service import handle_checkout, PaymentGateway

def test_checkout():
    assert handle_checkout() is True
"""
        )

        graph = CodeGraph(parsers=[PythonAstParser()])
        graph.index_directory(self.root)

        analyzer = ImpactAnalyzer(graph)
        analysis = analyzer.analyze_symbol("process_charge")

        self.assertIn("service.py", analysis["declared_in"][0])
        self.assertTrue(len(analysis["affected_tests"]) > 0 or len(analysis["calling_symbols"]) > 0)
        self.assertEqual(analysis["blast_radius_risk"], "LOW")

    def test_generic_regex_parser(self):
        ts_file = self.root / "userService.ts"
        ts_file.write_text(
            """
export class UserService {
    async getUser(id: string) {
        return { id };
    }
}
"""
        )

        graph = CodeGraph(parsers=[GenericRegexParser()])
        graph.index_directory(self.root)

        analyzer = ImpactAnalyzer(graph)
        analysis = analyzer.analyze_symbol("UserService")
        self.assertEqual(len(analysis["declared_in"]), 1)


if __name__ == "__main__":
    unittest.main()
