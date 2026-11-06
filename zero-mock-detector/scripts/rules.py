"""
Zero-Mock Detection Rules & Finding Models (October 2026 Standards)
Categorizes mock violations by architectural severity and integrates repo-level debt ledgers.
"""
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List, Optional, Pattern, Set, Tuple
import re

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass
class Finding:
    rule_id: str
    severity: Severity
    file_path: str
    line_number: int
    symbol_name: Optional[str]
    message: str
    code_snippet: Optional[str] = None
    is_exempted: bool = False
    exemption_reason: Optional[str] = None
    citation: Optional[str] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data

@dataclass
class DebtEntry:
    symbol_name: str
    file_path: Optional[str]
    reason: str
    citation: str
    source_ledger: str

# Rule 1: Mocking framework imports in production source
MOCK_IMPORT_PATTERNS: List[Tuple[str, Pattern, str]] = [
    (
        "MOCK_IMPORT_PY",
        re.compile(r"^\s*(from|import)\s+(unittest\.mock|pytest_mock|faker|moto|responses|freezegun)\b"),
        "Python test mocking/faking framework imported in production source"
    ),
    (
        "MOCK_IMPORT_JS",
        re.compile(r"""(?:import|require)\s*\(?.*['"](@faker-js/faker|sinon|jest|vitest|nock|msw)['"]"""),
        "JavaScript/TypeScript test mocking framework imported in production source"
    ),
    (
        "MOCK_IMPORT_RS",
        re.compile(r"""^\s*(use\s+(mockall|wiremock|fake)::|#\[automock\])"""),
        "Rust test mocking framework referenced in production source"
    ),
    (
        "MOCK_IMPORT_GO",
        re.compile(r"""["']github\.com/(golang/mock|stretchr/testify/mock|DATA-DOG/go-sqlmock)["']"""),
        "Go test mock package imported in production source"
    ),
    (
        "MOCK_IMPORT_JVM",
        re.compile(r"""^\s*import\s+(org\.mockito|org\.powermock|com\.github\.tomakehurst\.wiremock)\b"""),
        "JVM Mockito/WireMock framework imported in production source"
    ),
]

# Rule 2: Mock symbol naming in production code
RE_MOCK_SYMBOL = re.compile(
    r"""(?i)\b(mock|stub|fake|dummy|spy)[a-z0-9_]*\b|\b[a-z0-9_]*(mock|stub|fake|dummy|spy)\b"""
)

# Legitimate exclusions to avoid false positives
EXCLUDED_SYMBOLS: Set[str] = {
    "mocktail", "stubborn", "packet_stuffer", "stuffer", "hash_table",
    "stub", "stubs", "dummy", "zeromockdetector", "mockdetector", "mockauditor",
    "mockanalyzer", "mockchecker", "mockscanner"
}

# Rule 3: Fake latency / Simulated network delay
RE_FAKE_LATENCY = re.compile(
    r"""(?:\b(tokio::time::sleep|std::thread::sleep|time\.sleep|setTimeout|setInterval)\s*\()"""
)

# Rule 4: Stubbed / Abandoned implementation
RE_STUBBED_CODE = re.compile(
    r"""(?:\btodo!\s*\(|\bunimplemented!\s*\(|throw\s+new\s+Error\s*\(\s*['"].*?(?:todo|stub|mock|not\s+implemented).*?['"]|raise\s+NotImplementedError\s*\(\s*['"].*?(?:todo|stub|mock).*?['"])""",
    re.IGNORECASE
)

# Rule 5: Poisoned environment mock bypass toggles
RE_MOCK_BYPASS_FLAG = re.compile(
    r"""(?:\bprocess\.env\.NODE_ENV\s*===?\s*['"]test['"]|\b(?:MOCK_ENABLED|USE_MOCK|IS_MOCK|MOCK_DATA|MOCK_MODE)\b)"""
)

# Rule 6: Silent fallback / Error swallowing patterns in production
RE_SILENT_FALLBACK = re.compile(
    r"""(?:catch\s*\([^\)]*\)\s*\{\s*\}|except(?:\s+[A-Za-z0-9_]+)?:\s*pass\b)"""
)

# Rule 7: Bodyless / Trivial Constant Return in Production (AnyPS5 STUB_BODY Pattern)
# Matches functions discarding arguments or immediately returning static trivial constants without logic
RE_STUB_BODY_C = re.compile(
    r"""^(?:\s*(?:\(void\)\s*\w+\s*;|static_cast<void>\(\s*\w+\s*\)\s*;|\w+;)\s*)*"""
    r"""(?:\s*return\s*\(?\s*(?:-?(?:0x[0-9a-fA-F]+|\d+)[uUlL]*|nullptr|NULL|true|false|0|\w*_OK)?\s*\)?\s*;)?\s*$"""
)

RE_STUB_BODY_RUST = re.compile(
    r"""^\s*(?:Ok\(\s*\(\s*\)\s*\)|Ok\(\s*None\s*\)|None|\(\s*\)|0|false|true)\s*$"""
)

RE_STUB_BODY_PY = re.compile(
    r"""^\s*(?:pass|return(?:\s+(?:None|True|False|0|\[\]|\{\}))?)\s*$"""
)

RE_STUB_BODY_TS = re.compile(
    r"""^\s*(?:return(?:\s+(?:null|undefined|true|false|0|\[\]|\{\}))?;?)\s*$"""
)

# Rule 8: Rationalizing comments attempting to justify fakes/mocks
RE_RATIONALIZING_COMMENT = re.compile(
    r"""(?i)(?://|#|/\*)\s*(?:assume\s+success|dummy\s+(?:mock|fallback|return)|fake\s+(?:implementation|response|data)|mock\s+(?:for\s+now|temporar(?:y|ily)|data)|hardcoded\s+for\s+now|temporary\s+stub\b)"""
)

# Rule 9: Agent note & scratch file pollution in production directories
POLLUTION_FILENAME_PATTERNS: List[Pattern] = [
    re.compile(r"""^(?:notes\.md|agent_notes\.md|scratch.*\.py|temp_.*\.py|test_mesh_ping\.txt)$""", re.IGNORECASE),
    re.compile(r"""^.*\.(?:log|tmp|bak|orig)$""", re.IGNORECASE),
]

# In-code annotation pattern for legitimate cited exemptions
RE_INCODE_ALLOW_STUB = re.compile(
    r"""(?i)(?://|#)\s*@allow-stub:\s*([^(\n]+)(?:\(citation:\s*([^)\n]+)\))?"""
)
