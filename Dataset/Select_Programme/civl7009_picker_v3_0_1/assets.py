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
                    "panel": "rgba(255,255,255,0.78)",
                    "text_primary": "#17201C",
                    "text_secondary": "#667085",
                    "deep_green": "#094438",
                    "official_green": "#024638",
                    "light_gold": "#D1C18D",
                    "hku_blue": "#009CD5",
                    "academic_red": "#EF4022",
                    "soft_grey": "#E8EDF2",
                }
            },
            "spacing": {"xs": 4, "sm": 8, "md": 12, "lg": 18, "xl": 24},
            "radius": {"panel": 12, "card": 12, "button": 8, "chip": 8},
            "manual_objects": {"card_min_width": 240, "preview_height": 210},
            "default_theme": "light",
            "default_visual_quality": "Balanced",
        }
        (self.asset_dir / "design_tokens.json").write_text(json.dumps(tokens, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_procedural_svgs(self) -> None:
        assets = {
            "app_icon.svg": ("CIVL7009 V3.0.1", "V3", "#094438"),
            "empty_manual_objects.svg": ("选择 Manual Objects 根目录", "M", "#009CD5"),
            "manual_objects_pipeline.svg": ("跨库候选复核", "MO", "#024638"),
            "selection_saved.svg": ("选择结果已保存", "✓", "#094438"),
            "ambiguous_state.svg": ("需要人工判断", "?", "#D1C18D"),
            "error_state.svg": ("异常", "!", "#EF4022"),
            "lock_state.svg": ("只读边界", "L", "#331C0F"),
        }
        for filename, (title, glyph, colour) in assets.items():
            path = self.asset_dir / filename
            if not path.exists():
                path.write_text(self.svg_template(title, glyph, colour), encoding="utf-8")

    @staticmethod
    def svg_template(title: str, glyph: str, colour: str) -> str:
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="420" viewBox="0 0 720 420" role="img" aria-label="{title}">
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
<rect width="720" height="420" rx="28" fill="url(#bg)"/>
<rect x="58" y="54" width="604" height="312" rx="24" fill="white" opacity="0.76" stroke="#D1C18D" stroke-width="3"/>
<path d="M118 286 C190 210 246 250 326 162 C390 238 488 190 586 278" fill="none" stroke="url(#line)" stroke-width="13" stroke-linecap="round"/>
<rect x="106" y="92" width="116" height="78" rx="16" fill="#094438" opacity="0.13"/>
<rect x="282" y="92" width="116" height="78" rx="16" fill="#009CD5" opacity="0.12"/>
<rect x="458" y="92" width="116" height="78" rx="16" fill="#D1C18D" opacity="0.22"/>
<circle cx="360" cy="222" r="56" fill="{colour}" opacity="0.16"/>
<text x="360" y="242" text-anchor="middle" font-family="Arial, sans-serif" font-size="54" font-weight="800" fill="{colour}">{glyph}</text>
</svg>'''

    def write_prompt_log(self) -> None:
        prompt_log = {
            "programme_version": PROGRAMME_VERSION,
            "ui_version": UI_VERSION,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "assets": [
                {
                    "asset_name": "manual_objects_pipeline.svg",
                    "generated_by": "procedural_svg",
                    "prompt_hash": "sha256:procedural-v3-manual-objects",
                    "prompt_summary": "Abstract HKU-palette glass panels, geometric queues, manifest sheets, path lines, locks and selection symbols; no real scene, camera footage, face, or dataset-like imagery.",
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
            generated_by = "procedural_svg" if path.suffix.lower() == ".svg" else "manual_placeholder"
            assets.append(
                {
                    "asset_name": path.name,
                    "asset_type": path.suffix.lower().lstrip("."),
                    "generated_by": generated_by,
                    "source": "procedural",
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
                "forbidden_motifs": ["street scenes", "faces", "surveillance imagery", "public-safety incidents", "dataset-like samples"],
            },
            "assets": assets,
        }
        (self.asset_dir / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def asset(self, name: str) -> Path:
        path = self.asset_dir / name
        if path.exists():
            return path
        self.ensure_assets()
        return path if path.exists() else self.asset_dir / "empty_manual_objects.svg"
