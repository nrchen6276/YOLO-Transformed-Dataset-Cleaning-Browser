from __future__ import annotations

from pathlib import Path

from ..domain.models import AuditIssue, RecoverySnapshot


class RecoveryService:
    def scan(self, session_id: str, review_dir: Path | None = None, manifest_path: Path | None = None) -> RecoverySnapshot:
        issues: list[AuditIssue] = []
        if review_dir and (review_dir / "_ManualReview_Staging").exists():
            issues.append(
                AuditIssue(
                    severity="WARN",
                    error_code="RECOVERY_REQUIRED",
                    affected_paths=[str(review_dir / "_ManualReview_Staging")],
                    why_it_blocks="检测到 staging 目录，需要确认 manifest 状态。",
                    suggested_action="进入恢复中心（Recovery Center）检查或导出诊断包。",
                    recovery_action_available=True,
                )
            )
        if manifest_path and not manifest_path.exists():
            issues.append(
                AuditIssue(
                    severity="ERROR",
                    error_code="MANIFEST_OPEN_FAILED",
                    affected_paths=[str(manifest_path)],
                    why_it_blocks="manifest 路径不存在。",
                    suggested_action="重新构建 manifest-only queue。",
                    recovery_action_available=True,
                )
            )
        return RecoverySnapshot(clean=not any(i.severity == "ERROR" for i in issues), session_id=session_id, issues=issues)

    def apply(self, action_id: str, confirmation: str = "") -> dict[str, str]:
        high_risk = {"ROLLBACK", "RESTORE", "RESOLVE"}
        if action_id in high_risk and confirmation != action_id:
            return {"result": "blocked", "error_code": "RECOVERY_REQUIRED", "message": f"需要输入 {action_id}。"}
        return {"result": "PENDING_AUDIT", "message": "恢复动作已记录为待人工审计。"}
