#!/usr/bin/env python3
"""Validate and create a reproducible release archive for the bundled Skill."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = REPOSITORY_ROOT / "plugins" / "generate-github-cover"
SKILL_ROOT = PLUGIN_ROOT / "skills" / "generate-github-cover"
MANIFEST_PATH = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
ARCHIVE_ROOT = "generate-github-cover"
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
REQUIRED_FILES = (
    "SKILL.md",
    "agents/openai.yaml",
    "requirements.txt",
    "references/style-authoring.md",
    "scripts/render_cover.py",
    "scripts/render_logo.py",
    "scripts/style_registry.py",
)
EXCLUDED_PARTS = {"__pycache__", ".DS_Store", ".pytest_cache"}


class PackageError(RuntimeError):
    pass


def validate_styles() -> None:
    manifests = sorted((SKILL_ROOT / "styles").glob("*/*/style.json"))
    if not manifests:
        raise PackageError("Skill must contain at least one discoverable style")
    discovered: set[tuple[str, str]] = set()
    for path in manifests:
        kind = path.parent.parent.name
        style_id = path.parent.name
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PackageError(f"cannot read style manifest {path}: {exc}") from exc
        if not isinstance(manifest, dict):
            raise PackageError(f"style manifest must be a JSON object: {path}")
        if manifest.get("schema_version") != 1:
            raise PackageError(f"style manifest schema_version must be 1: {path}")
        if manifest.get("kind") != kind or manifest.get("id") != style_id:
            raise PackageError(f"style manifest kind/id must match its path: {path}")
        if kind not in {"cover", "logo"}:
            raise PackageError(f"unsupported style kind {kind!r}: {path}")
        reference = path.parent / "reference.md"
        if not reference.is_file():
            raise PackageError(f"style is missing reference.md: {path.parent}")
        if kind == "cover":
            artboards = manifest.get("artboards")
            if not isinstance(artboards, dict):
                raise PackageError(f"Cover style is missing artboards: {path}")
            for name in ("cover", "social", "promo"):
                artboard = artboards.get(name)
                template = artboard.get("template") if isinstance(artboard, dict) else None
                if not isinstance(template, str) or not (path.parent / template).is_file():
                    raise PackageError(f"Cover style is missing its {name} template: {path}")
        discovered.add((kind, style_id))
    if not any(kind == "cover" for kind, _ in discovered):
        raise PackageError("Skill must contain a Cover style")
    if not any(kind == "logo" for kind, _ in discovered):
        raise PackageError("Skill must contain a Logo style")


def normalize_version(value: str) -> str:
    version = value.removeprefix("v")
    if not SEMVER_PATTERN.fullmatch(version):
        raise PackageError(f"version must be semantic versioning, got: {value}")
    return version


def validate_distribution(version: str) -> list[Path]:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"cannot read plugin manifest: {exc}") from exc

    if manifest.get("name") != ARCHIVE_ROOT:
        raise PackageError("plugin manifest name must be generate-github-cover")
    if manifest.get("version") != version:
        raise PackageError(
            f"plugin version {manifest.get('version')!r} does not match {version!r}"
        )

    missing = [path for path in REQUIRED_FILES if not (SKILL_ROOT / path).is_file()]
    if missing:
        raise PackageError(f"missing required Skill files: {', '.join(missing)}")
    validate_styles()

    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not skill_text.startswith("---\n") or "\n---\n" not in skill_text[4:]:
        raise PackageError("SKILL.md must begin with YAML frontmatter")
    frontmatter = skill_text.split("\n---\n", 1)[0]
    if "\nname: generate-github-cover\n" not in f"\n{frontmatter}\n":
        raise PackageError("SKILL.md name must be generate-github-cover")
    if not re.search(r"^description:\s*\S", frontmatter, flags=re.MULTILINE):
        raise PackageError("SKILL.md must define a non-empty description")

    files = []
    for path in sorted(SKILL_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(SKILL_ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        files.append(path)

    unexpected_docs = {
        path.name
        for path in files
        if path.name in {"README.md", "INSTALLATION_GUIDE.md", "CHANGELOG.md"}
    }
    if unexpected_docs:
        raise PackageError(
            f"Skill contains repository-level documentation: {', '.join(unexpected_docs)}"
        )
    return files


def _zip_info(archive_path: str, *, executable: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(archive_path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    mode = 0o755 if executable else 0o644
    info.external_attr = (0o100000 | mode) << 16
    return info


def write_archive(version: str, output_dir: Path, files: list[Path]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"{ARCHIVE_ROOT}-v{version}.zip"

    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            relative = path.relative_to(SKILL_ROOT)
            archive_path = (Path(ARCHIVE_ROOT) / relative).as_posix()
            bundle.writestr(
                _zip_info(archive_path, executable=path.parent.name == "scripts"),
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )

        license_path = REPOSITORY_ROOT / "LICENSE"
        bundle.writestr(
            _zip_info(f"{ARCHIVE_ROOT}/LICENSE"),
            license_path.read_bytes(),
            compress_type=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        )

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix(f"{archive.suffix}.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and package the generate-github-cover Skill."
    )
    parser.add_argument("version", help="Release version, such as v0.1.0 or 0.1.0")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "dist",
        help="Archive directory (default: ./dist)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate without creating an archive",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        version = normalize_version(args.version)
        files = validate_distribution(version)
        if args.check_only:
            print(f"Validated {len(files)} Skill files for v{version}")
            return 0
        archive = write_archive(version, args.output_dir, files)
    except PackageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(archive)
    print(archive.with_suffix(f"{archive.suffix}.sha256"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
