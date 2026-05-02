"""
Risk Assessor - Branching Logic từ Sequence Diagram.

Logic phân nhánh:
- Nếu có ROI → kiểm tra zone intrusion + hành vi
- Nếu không ROI → chỉ giám sát hành vi (bạo lực/té ngã/vật nguy hiểm)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from loguru import logger

from module_edge_firmware.analysis.roi_checker import ROIChecker
from module_edge_firmware.analysis.proximity_detector import ProximityDetector, ProximityAlert
from module_edge_firmware.analysis.fall_detector import FallDetector, FallEvent
from module_edge_firmware.inference.multi_task_runner import FrameAnalysis


class RiskLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskAssessment:
    """Đánh giá rủi ro tổng hợp cho một frame."""
    level: RiskLevel = RiskLevel.NONE
    reasons: list[str] = field(default_factory=list)
    zone_intrusions: list[str] = field(default_factory=list)
    proximity_alerts: list[ProximityAlert] = field(default_factory=list)
    fall_event: FallEvent | None = None
    should_alert: bool = False

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "reasons": self.reasons,
            "zone_intrusions": self.zone_intrusions,
            "should_alert": self.should_alert,
            "fall_event": self.fall_event.to_dict() if self.fall_event else None,
            "proximity_alerts": [a.to_dict() for a in self.proximity_alerts],
        }


class RiskAssessor:
    """
    Đánh giá rủi ro dựa trên branching logic.

    Kết hợp tất cả nguồn thông tin: ROI, detections, poses, behavior
    để đưa ra quyết định cảnh báo.
    """

    def __init__(self):
        self.roi_checker = ROIChecker()
        self.proximity_detector = ProximityDetector()
        self.fall_detector = FallDetector()

    def assess(self, analysis: FrameAnalysis) -> RiskAssessment:
        """
        Đánh giá rủi ro cho frame analysis.

        Args:
            analysis: Kết quả từ MultiTaskRunner.

        Returns:
            RiskAssessment chứa mức độ rủi ro và lý do.
        """
        assessment = RiskAssessment()

        # === Branch 1: Kiểm tra ROI (nếu có) ===
        if self.roi_checker.has_zones and analysis.detections:
            children = analysis.detections.get_children()
            for i in range(len(children)):
                intrusions = self.roi_checker.check_box_intrusion(children.boxes[i])
                if intrusions:
                    zone_names = [z.label for z in intrusions]
                    assessment.zone_intrusions.extend(zone_names)
                    assessment.reasons.append(
                        f"Trẻ xâm nhập vùng nguy hiểm: {', '.join(zone_names)}"
                    )
                    assessment.level = RiskLevel.HIGH

        # === Branch 2: Kiểm tra vật thể nguy hiểm ===
        if analysis.has_dangerous_objects and analysis.has_children:
            dangerous = analysis.detections.get_dangerous_objects()
            obj_names = list(set(dangerous.class_names))
            assessment.reasons.append(f"Vật nguy hiểm gần trẻ: {', '.join(obj_names)}")
            if assessment.level.value < RiskLevel.MEDIUM.value:
                assessment.level = RiskLevel.MEDIUM

        # === Branch 3: Kiểm tra hand-mouth proximity ===
        if analysis.poses and analysis.detections:
            prox_alerts = self.proximity_detector.check(analysis.poses, analysis.detections)
            if prox_alerts:
                assessment.proximity_alerts = prox_alerts
                for alert in prox_alerts:
                    if alert.nearby_object:
                        assessment.reasons.append(
                            f"Trẻ đưa {alert.nearby_object} gần miệng!"
                        )
                        assessment.level = RiskLevel.CRITICAL
                    else:
                        assessment.reasons.append("Trẻ đưa tay gần miệng")

        # === Branch 4: Kiểm tra té ngã ===
        if analysis.poses:
            fall = self.fall_detector.update(analysis.poses)
            if fall:
                assessment.fall_event = fall
                if fall.is_injury:
                    assessment.reasons.append(
                        f"Té ngã chấn thương! Bất động {fall.duration_still:.1f}s"
                    )
                    assessment.level = RiskLevel.CRITICAL
                else:
                    assessment.reasons.append("Té ngã nhẹ (chơi đùa)")
                    if assessment.level.value < RiskLevel.LOW.value:
                        assessment.level = RiskLevel.LOW

        # === Branch 5: Kiểm tra bạo lực ===
        if analysis.has_violence:
            assessment.reasons.append(
                f"Hành vi bạo lực: {analysis.behavior.class_name} "
                f"({analysis.behavior.confidence:.0%})"
            )
            assessment.level = RiskLevel.CRITICAL

        # Quyết định cảnh báo
        assessment.should_alert = assessment.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

        if assessment.should_alert:
            logger.warning(f"RISK {assessment.level.value}: {'; '.join(assessment.reasons)}")

        return assessment
