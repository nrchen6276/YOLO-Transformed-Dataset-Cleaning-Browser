from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import ASSET_DIR
from .version import PROGRAMME_VERSION, UI_VERSION


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
        self.write_design_tokens()
        self.write_procedural_svgs()
        self.write_prompt_log()
        self.write_manifest()
        return self.asset_dir

    def write_design_tokens(self) -> None:
        tokens: dict[str, Any] = {
            "themes": {
                "light": {
                    "window_bg": "#EEF2F6",
                    "panel": "rgba(255,255,255,0.76)",
                    "text_primary": "#17201C",
                    "text_secondary": "#667085",
                    "deep_green": "#094438",
                    "official_green": "#024638",
                    "light_gold": "#D1C18D",
                    "hku_blue": "#009CD5",
                    "academic_red": "#EF4022",
                    "soft_grey": "#E8EDF2",
                },
                "dark": {
                    "window_bg": "#111827",
                    "panel": "rgba(31,41,55,0.78)",
                    "text_primary": "#F9FAFB",
                    "text_secondary": "#CBD5E1",
                    "deep_green": "#3A6960",
                    "official_green": "#356B60",
                    "light_gold": "#D1C18D",
                    "hku_blue": "#33B0DD",
                    "academic_red": "#F2664E",
                    "soft_grey": "#1F2937",
                },
                "high_contrast": {
                    "window_bg": "#FFFFFF",
                    "panel": "#FFFFFF",
                    "text_primary": "#000000",
                    "text_secondary": "#1C1C1C",
                    "deep_green": "#024638",
                    "light_gold": "#7A5A00",
                    "hku_blue": "#005F8F",
                    "academic_red": "#B00020",
                },
            },
            "spacing": {"xs": 4, "sm": 8, "md": 12, "lg": 18, "xl": 24},
            "radius": {"panel": 22, "card": 18, "button": 12},
            "shadow": {"soft": "0 18 45 rgba(15,23,42,0.16)"},
            "image_card": {"min_width": 220, "min_height": 260, "preview_height": 190},
            "default_theme": "light",
            "default_visual_quality": "Balanced",
            "motion": {"normal_ms": 160, "reduced_ms": 0},
        }
        (self.asset_dir / "design_tokens.json").write_text(json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_procedural_svgs(self) -> None:
        assets = {
            "app_icon.svg": ("图源筛选", "✓", "#094438"),
            "empty_state.svg": ("选择目录", "＋", "#009CD5"),
            "loading_overlay.svg": ("加载索引", "…", "#D1C18D"),
            "review_board.svg": ("目录大盘", "B", "#024638"),
            "safe_gate_badge.svg": ("安全门", "G", "#EF4022"),
            "lock_state.svg": ("目录锁", "L", "#331C0F"),
            "recovery_state.svg": ("恢复中心", "R", "#EF4022"),
            "error_state.svg": ("错误", "!", "#EF4022"),
            "manifest_state.svg": ("Manifest", "M", "#009CD5"),
            "staging_state.svg": ("Staging", "S", "#024638"),
            "diagnostics_state.svg": ("诊断", "D", "#009CD5"),
            "dashboard_state.svg": ("仪表盘", "P", "#D1C18D"),
            "shortcut_overlay.svg": ("快捷键", "?", "#094438"),
        }
        for filename, (title, glyph, colour) in assets.items():
            path = self.asset_dir / filename
            if not path.exists():
                path.write_text(self.svg_template(title, glyph, colour), encoding="utf-8")

    @staticmethod
    def svg_template(title: str, glyph: str, colour: str) -> str:
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="640" height="420" viewBox="0 0 640 420" role="img" aria-label="{title}">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="#FDFDFD"/>
    <stop offset="1" stop-color="#E8EDF2"/>
  </linearGradient>
  <linearGradient id="line" x1="0" y1="0" x2="1" y2="1">
    <stop stop-color="#094438"/>
    <stop offset="0.55" stop-color="{colour}"/>
    <stop offset="1" stop-color="#D1C18D"/>
  </linearGradient>
</defs>
<rect width="640" height="420" rx="36" fill="url(#bg)"/>
<rect x="56" y="54" width="528" height="312" rx="30" fill="rgba(255,255,255,0.72)" stroke="#D1C18D" stroke-width="3"/>
<path d="M124 286 C192 210 248 250 312 162 C372 244 462 190 526 278" fill="none" stroke="url(#line)" stroke-width="13" stroke-linecap="round"/>
<rect x="110" y="92" width="112" height="78" rx="18" fill="#094438" opacity="0.13"/>
<rect x="264" y="92" width="112" height="78" rx="18" fill="#009CD5" opacity="0.12"/>
<rect x="418" y="92" width="112" height="78" rx="18" fill="#D1C18D" opacity="0.2"/>
<circle cx="320" cy="220" r="52" fill="{colour}" opacity="0.16"/>
<text x="320" y="240" text-anchor="middle" font-family="Arial, sans-serif" font-size="66" font-weight="700" fill="{colour}">{glyph}</text>
</svg>'''

    def write_prompt_log(self) -> None:
        prompt_log = {
            "programme_version": PROGRAMME_VERSION,
            "ui_version": UI_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "assets": [
                {
                    "asset_name": "image2_glass_cockpit.svg",
                    "generated_by": "image_generation",
                    "prompt_hash": "sha256:8f4a6a35c5c5e54d0f0f2e7f0df2b6092e86ad230b4d9813b8d2a713d08f2f8a",
                    "prompt_summary": "Abstract Apple-like glass UI cockpit using HKU-inspired palette, geometric queues, manifest sheets, path lines, locks and status symbols; no real scenes or dataset-like imagery.",
                    "contains_dataset_image": False,
                }
            ],
        }
        (self.asset_dir / "asset_prompt_log.json").write_text(json.dumps(prompt_log, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_manifest(self) -> None:
        assets: list[dict[str, Any]] = []
        for path in sorted(self.asset_dir.iterdir()):
            if not path.is_file() or path.name == "asset_manifest.json":
                continue
            if path.suffix.lower() not in {".svg", ".json"}:
                continue
            generated_by = "image_generation" if path.name == "image2_glass_cockpit.svg" else "procedural_svg"
            if path.name in {"design_tokens.json", "asset_prompt_log.json"}:
                generated_by = "manual_placeholder"
            assets.append(
                {
                    "asset_name": path.name,
                    "asset_type": path.suffix.lower().lstrip("."),
                    "generated_by": generated_by,
                    "source": "generated" if generated_by == "image_generation" else "procedural",
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
                "forbidden_motifs": [
                    "real street scenes",
                    "faces",
                    "surveillance imagery",
                    "public-safety incidents",
                    "dataset-like samples",
                    "HKU crest/logo without authorisation",
                ],
            },
            "assets": assets,
        }
        (self.asset_dir / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def asset(self, name: str) -> Path:
        path = self.asset_dir / name
        if path.exists():
            return path
        self.ensure_assets()
        return path if path.exists() else self.asset_dir / "empty_state.svg"
