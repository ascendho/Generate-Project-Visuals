#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


STYLE_SCHEMA_VERSION = 1
STYLE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STYLE_KINDS = {"cover", "logo"}
SKILL_ROOT = Path(__file__).resolve().parent.parent
STYLES_ROOT = SKILL_ROOT / "styles"


class StyleError(RuntimeError):
    pass


def load_style(kind: str, style_id: str) -> dict[str, object]:
    if kind not in STYLE_KINDS:
        raise StyleError(f"unknown style kind: {kind}")
    if not STYLE_ID_PATTERN.fullmatch(style_id):
        raise StyleError(f"{kind} style must be a lowercase hyphenated identifier")

    style_root = (STYLES_ROOT / kind / style_id).resolve()
    try:
        style_root.relative_to((STYLES_ROOT / kind).resolve())
    except ValueError as exc:
        raise StyleError(f"{kind} style resolves outside the style directory") from exc

    manifest_path = style_root / "style.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        available = ", ".join(list_styles(kind)) or "none"
        raise StyleError(
            f"unknown {kind} style {style_id!r}; available styles: {available}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise StyleError(f"invalid style manifest {manifest_path}: {exc}") from exc

    if not isinstance(manifest, dict):
        raise StyleError(f"style manifest must be a JSON object: {manifest_path}")
    if manifest.get("schema_version") != STYLE_SCHEMA_VERSION:
        raise StyleError(
            f"style manifest schema_version must be {STYLE_SCHEMA_VERSION}: {manifest_path}"
        )
    if manifest.get("kind") != kind or manifest.get("id") != style_id:
        raise StyleError(
            f"style manifest kind/id must match {kind}/{style_id}: {manifest_path}"
        )
    description = manifest.get("description")
    if not isinstance(description, str) or not description.strip():
        raise StyleError(f"style manifest requires a description: {manifest_path}")

    manifest["_root"] = style_root
    return manifest


def style_file(style: dict[str, object], relative: object, field: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise StyleError(f"{field} must be a non-empty relative path")
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise StyleError(f"{field} must stay inside its style directory")
    root = style.get("_root")
    if not isinstance(root, Path):
        raise StyleError("style manifest is missing its resolved root")
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise StyleError(f"{field} resolves outside its style directory") from exc
    if not path.is_file():
        raise StyleError(f"missing style file for {field}: {path}")
    return path


def list_styles(kind: str) -> tuple[str, ...]:
    if kind not in STYLE_KINDS:
        raise StyleError(f"unknown style kind: {kind}")
    root = STYLES_ROOT / kind
    if not root.is_dir():
        return ()
    return tuple(
        path.name
        for path in sorted(root.iterdir())
        if path.is_dir()
        and STYLE_ID_PATTERN.fullmatch(path.name)
        and (path / "style.json").is_file()
    )
