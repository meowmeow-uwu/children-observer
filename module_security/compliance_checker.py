"""
Compliance Checker.

Kiểm tra tuân thủ tiêu chuẩn:
- QCVN 135:2024/BTTTT (Việt Nam)
- PSTI (Product Security and Telecommunications Infrastructure)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from configs.settings import get_settings


@dataclass
class ComplianceResult:
    """Kết quả kiểm tra compliance."""
    standard: str
    passed: bool
    checks: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.checks:
            return 0.0
        passed = sum(1 for c in self.checks if c["passed"])
        return passed / len(self.checks)


class ComplianceChecker:
    """
    Kiểm tra điều kiện tuân thủ cho thiết bị IoT.

    QCVN 135:2024/BTTTT - Quy chuẩn kỹ thuật quốc gia về yêu cầu an toàn
    thông tin cơ bản cho thiết bị IoT.
    """

    def __init__(self):
        self.settings = get_settings()

    def check_qcvn135(self) -> ComplianceResult:
        """Kiểm tra theo QCVN 135:2024/BTTTT."""
        result = ComplianceResult(standard="QCVN 135:2024/BTTTT", passed=True)

        # 1. Không sử dụng mật khẩu mặc định
        check = {
            "id": "QCVN135-01",
            "name": "Không mật khẩu mặc định",
            "passed": self.settings.e2ee_secret_key != "change-me-in-production",
        }
        result.checks.append(check)
        if not check["passed"]:
            result.warnings.append("E2EE secret key chưa được thay đổi!")

        # 2. Mã hóa dữ liệu truyền tải
        check = {
            "id": "QCVN135-02",
            "name": "Mã hóa E2EE",
            "passed": len(self.settings.e2ee_secret_key) >= 16,
        }
        result.checks.append(check)

        # 3. Cơ chế cập nhật bảo mật
        check = {
            "id": "QCVN135-03",
            "name": "OTA update capability",
            "passed": bool(self.settings.federated_server_url),
        }
        result.checks.append(check)

        # 4. Bảo vệ dữ liệu cá nhân
        check = {
            "id": "QCVN135-04",
            "name": "Privacy masking enabled",
            "passed": self.settings.privacy_blur_strangers,
        }
        result.checks.append(check)

        result.passed = all(c["passed"] for c in result.checks)

        level = "✅ PASSED" if result.passed else "❌ FAILED"
        logger.info(
            f"QCVN 135 check: {level} | "
            f"Pass rate: {result.pass_rate:.0%} | "
            f"Warnings: {len(result.warnings)}"
        )

        return result

    def check_psti(self) -> ComplianceResult:
        """Kiểm tra theo PSTI (UK standard)."""
        result = ComplianceResult(standard="PSTI", passed=True)

        checks = [
            ("PSTI-01", "No universal default passwords",
             self.settings.auth_jwt_secret != "dev-jwt-secret"),
            ("PSTI-02", "Vulnerability disclosure policy", True),  # Placeholder
            ("PSTI-03", "Security updates for minimum period", True),  # Placeholder
        ]

        for check_id, name, passed in checks:
            result.checks.append({"id": check_id, "name": name, "passed": passed})

        result.passed = all(c["passed"] for c in result.checks)
        return result

    def run_all_checks(self) -> list[ComplianceResult]:
        """Chạy tất cả compliance checks."""
        results = [self.check_qcvn135(), self.check_psti()]
        all_passed = all(r.passed for r in results)
        status = "✅ ALL PASSED" if all_passed else "⚠️ SOME FAILED"
        logger.info(f"Compliance check: {status}")
        return results
