from __future__ import annotations

from pathlib import Path

from ..domain.models import AuditIssue, ManifestRun, StagingDryRunReport
from ..infrastructure.path_policy import is_same_volume, validate_for_staging


class StagingService:
    def dry_run(self, manifest: ManifestRun, review_dir: Path, limits: dict[str, int] | None = None) -> StagingDryRunReport:
        staging_dir = review_dir / "_ManualReview_Staging" / manifest.run_id
        path_result = validate_for_staging(review_dir, staging_dir, same_volume_required=True)
        issues: list[AuditIssue] = []
        if not path_result.ok:
            issues.append(AuditIssue("ERROR", path_result.error_code, affected_paths=[str(staging_dir)], why_it_blocks=path_result.message, suggested_action="检查路径或关闭 physical staging。"))
        return StagingDryRunReport(
            ok=not issues,
            run_id=manifest.run_id,
            checked_groups=0,
            same_volume=is_same_volume(review_dir, staging_dir),
            message="physical staging 默认关闭；dry-run 未移动文件。",
            issues=issues,
        )

    def enable(self, manifest: ManifestRun, confirmation: str, review_dir: Path) -> dict[str, str]:
        if confirmation != "STAGE":
            return {"state": "disabled", "error_code": "STAGING_DISABLED", "message": "需要输入 STAGE 才能启用 physical staging。"}
        report = self.dry_run(manifest, review_dir)
        if not report.ok:
            return {"state": "blocked", "error_code": report.issues[0].error_code, "message": report.issues[0].why_it_blocks}
        return {"state": "enabled_for_sample_only", "message": "physical staging 已通过 dry-run；真实数据仍需单独授权。"}
