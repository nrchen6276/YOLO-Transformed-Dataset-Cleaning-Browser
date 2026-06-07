from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import ASSET_DIR
from ..version import PROGRAMME_VERSION, SCRIPT_TIMECODE, UI_VERSION


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class AssetService:
    def __init__(self, asset_dir: Path = ASSET_DIR) -> None:
        self.asset_dir = asset_dir

    def ensure_assets(self) -> Path:
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        self._write_design_tokens()
        self._write_svg_assets()
        self._write_manifest()
        return self.asset_dir

    def _write_design_tokens(self) -> None:
        tokens = {
            "themes": {
                "light": {
                    "window_bg": "#EEF2F6",
                    "glass_bg": "rgba(255,255,255,0.72)",
                    "text_primary": "#17201C",
                    "text_secondary": "#667085",
                    "accent_green": "#094438",
                    "official_green": "#024638",
                    "accent_gold": "#D1C18D",
                    "error_red": "#EF4022",
                    "hku_blue": "#009CD5",
                },
                "dark": {
                    "window_bg": "#111827",
                    "glass_bg": "rgba(31,41,55,0.76)",
                    "text_primary": "#F9FAFB",
                    "text_secondary": "#CBD5E1",
                    "accent_green": "#3A6960",
                    "official_green": "#356B60",
                    "accent_gold": "#D1C18D",
                    "error_red": "#F2664E",
                    "hku_blue": "#33B0DD",
                },
                "high_contrast": {
                    "window_bg": "#FFFFFF",
                    "glass_bg": "#FFFFFF",
                    "text_primary": "#000000",
                    "text_secondary": "#1C1C1C",
                    "accent_green": "#024638",
                    "accent_gold": "#8A6D00",
                    "error_red": "#B00020",
                },
            },
            "spacing": {"xs": 4, "sm": 8, "md": 12, "lg": 18, "xl": 24},
            "radius": {"panel": 22, "card": 18, "button": 12},
            "shadows": {"soft": "0 18 45 rgba(15,23,42,0.16)"},
            "opacity": {"glass": 0.72, "disabled": 0.42},
            "elevation": {"base": 0, "panel": 2, "modal": 8},
            "motion_duration_ms": {"fast": 90, "normal": 160, "slow": 240},
            "table": {"row_height": 34, "header_height": 38},
            "image_card": {"min_width": 220, "min_height": 240, "preview_height": 180},
            "visual_quality_modes": ["Performance", "Balanced", "Glass"],
            "default_theme": "light",
            "default_visual_quality": "Balanced",
        }
        (self.asset_dir / "design_tokens.json").write_text(json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8")

    def _svg(self, title: str, glyph: str, colour: str) -> str:
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="320" viewBox="0 0 512 320" role="img" aria-label="{title}">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#FDFDFD"/><stop offset="1" stop-color="#E8EDF2"/></linearGradient></defs>
<rect width="512" height="320" rx="32" fill="url(#g)"/>
<rect x="52" y="48" width="408" height="224" rx="28" fill="rgba(255,255,255,0.72)" stroke="#D1C18D" stroke-width="3"/>
<path d="M112 218 C166 150 214 178 256 118 C300 180 364 134 414 214" fill="none" stroke="{colour}" stroke-width="12" stroke-linecap="round"/>
<circle cx="256" cy="154" r="44" fill="{colour}" opacity="0.18"/>
<text x="256" y="170" text-anchor="middle" font-family="Arial, sans-serif" font-size="54" fill="{colour}">{glyph}</text>
</svg>'''

    def _write_svg_assets(self) -> None:
        assets = {
            "app_icon.svg": ("CIVL7009 V2", "✓", "#094438"),
            "empty_state.svg": ("空状态", "□", "#009CD5"),
            "loading_overlay.svg": ("加载", "…", "#D1C18D"),
            "staging_state.svg": ("暂存", "S", "#024638"),
            "recovery_state.svg": ("恢复", "R", "#EF4022"),
            "safe_gate_state.svg": ("安全门", "G", "#094438"),
            "lock_state.svg": ("锁定", "L", "#331C0F"),
            "error_state.svg": ("错误", "!", "#EF4022"),
            "success_state.svg": ("成功", "✓", "#00B28D"),
            "dashboard_background.svg": ("仪表盘", "D", "#009CD5"),
            "onboarding_manifest.svg": ("引导", "M", "#D1C18D"),
            "sidebar_icons.svg": ("导航", "N", "#024638"),
        }
        for filename, (title, glyph, colour) in assets.items():
            (self.asset_dir / filename).write_text(self._svg(title, glyph, colour), encoding="utf-8")

    def _write_manifest(self) -> None:
        assets: list[dict[str, Any]] = []
        for path in sorted(self.asset_dir.iterdir()):
            if path.name == "asset_manifest.json":
                continue
            if path.is_file():
                generated_by = "image_generation" if "image2" in path.stem else ("procedural_svg" if path.suffix == ".svg" else "procedural_png")
                assets.append(
                    {
                        "asset_name": path.name,
                        "asset_type": path.stem,
                        "generated_by": generated_by,
                        "source": "procedural" if generated_by.startswith("procedural") else "generated",
                        "contains_dataset_image": False,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                        "sha256": sha256_file(path),
                    }
                )
        manifest = {
            "programme_version": PROGRAMME_VERSION,
            "ui_version": UI_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "policy": {
                "contains_dataset_image": False,
                "internet_assets_used": False,
                "system_fonts_packaged": False,
                "raw_dataset_sources_used": False,
                "forbidden_motifs": [
                    "real street scenes",
                    "faces",
                    "surveillance imagery",
                    "public-safety incident scenes",
                    "dataset-like samples",
                    "HKU crest/logo without authorisation",
                ],
            },
            "assets": assets,
        }
        (self.asset_dir / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_prompt_log(self, generated_assets: list[dict[str, Any]]) -> None:
        payload = {
            "programme_version": PROGRAMME_VERSION,
            "ui_version": UI_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "assets": generated_assets,
        }
        (self.asset_dir / "asset_prompt_log.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_or_fallback(self, asset_name: str) -> Path:
        path = self.asset_dir / asset_name
        if path.exists():
            return path
        fallback = self.asset_dir / "empty_state.svg"
        if not fallback.exists():
            self.ensure_assets()
        return fallback
