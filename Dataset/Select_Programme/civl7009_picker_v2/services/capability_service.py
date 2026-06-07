from __future__ import annotations

from ..domain.models import Capability


class CapabilityMatrixService:
    def get_matrix(self) -> list[Capability]:
        return [
            Capability(
                name="manual_selection_move",
                display_name="人工筛选移动（Manual Selection Move）",
                default_state="lock + recovery + FastReviewIndex + full audit clean 后启用",
                risk="medium",
                raw_file_movement=True,
                gate="V1.9.1 inherited safe policy",
                enabled=True,
                description="选中图进入 done，其余进入 out。",
            ),
            Capability(
                name="manifest_only_queue",
                display_name="清单队列（Manifest-only Queue）",
                default_state="enabled",
                risk="low",
                raw_file_movement=False,
                gate="none; non-mutating",
                storage="Runtime_Manifests/<session_id>/review_manifest.sqlite",
                enabled=True,
                description="只持久化路径和状态，不移动 raw files。",
            ),
            Capability(
                name="physical_staging",
                display_name="物理暂存（Physical Staging）",
                default_state="disabled",
                risk="high",
                raw_file_movement=True,
                gate="STAGE confirmation + dry-run + same-volume + recovery clean",
                enabled=False,
                description="默认关闭；真实数据需单独授权。",
            ),
            Capability(
                name="id_initialisation_write",
                display_name="ID 初始化写入（ID Initialisation Write）",
                default_state="dry-run first",
                risk="medium-high",
                raw_file_movement=True,
                gate="INIT confirmation",
                enabled=True,
                description="复制生成 ManualReview 大盘；原始 YOLO 数据不移动不删除。",
            ),
            Capability(
                name="diagnostic_bundle",
                display_name="诊断包（Diagnostic Bundle）",
                default_state="enabled",
                risk="low",
                raw_file_movement=False,
                gate="export action",
                enabled=True,
                description="支持 full local 与 redacted share，永不包含 raw files。",
            ),
            Capability(
                name="image2_assets",
                display_name="image2 视觉资产（image2 Assets）",
                default_state="enabled if available",
                risk="low",
                raw_file_movement=False,
                gate="asset manifest policy",
                enabled=True,
                description="生成抽象 UI 资产；禁止 dataset-derived imagery。",
            ),
        ]
