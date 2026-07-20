#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import math
import re
import shutil
import struct
import tempfile
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from urllib.parse import urlparse

from style_registry import StyleError, load_style, style_file


SCHEMA_VERSION = 4
ACTIVE_COVER_STYLE = "clean-editorial"
COVER_VIEWBOX = (2000, 400)
COVER_PNG_SIZE = (4000, 800)
COVER_SAFE_BOX = (96, 48, 1904, 352)
SOCIAL_VIEWBOX = (2048, 1024)
SOCIAL_PNG_SIZE = (1280, 640)
SOCIAL_SAFE_BOX = (128, 128, 1920, 896)
PROMO_VIEWBOX = (1920, 1080)
PROMO_PNG_SIZE = (3840, 2160)
PROMO_SAFE_BOX = (120, 100, 1800, 980)
COVER_TEMPLATE_PATH = Path()
SOCIAL_TEMPLATE_PATH = Path()
PROMO_TEMPLATE_PATH = Path()
COVER_PALETTE = {
    "background": "#ffffff",
    "primary": "#2855d9",
    "text": "#202124",
    "muted": "#5f6368",
    "subtle": "#72767d",
    "border": "#d9dfef",
}
COVER_FIT: dict[str, dict[str, int]] = {}
SOCIAL_FIT: dict[str, dict[str, int]] = {}
PROMO_FIT: dict[str, dict[str, int]] = {}
COVER_IDENTITY = {"center_y": 96, "height": 64, "maximum_width": 1000}
SOCIAL_IDENTITY = {"center_y": 257, "height": 180, "maximum_width": 1500}
PROMO_IDENTITY = {"center_y": 206, "height": 170, "maximum_width": 1400}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LANGUAGE_PATTERN = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]+)*$")
RTL_SCRIPTS = {"arab", "hebr", "nkoo", "rohg", "syrc", "thaa"}
RTL_LANGUAGES = {"ar", "dv", "fa", "he", "ks", "ps", "sd", "ug", "ur", "yi"}
UPRIGHT_LANGUAGES = {
    "am",
    "bn",
    "bo",
    "gu",
    "hi",
    "hy",
    "ka",
    "km",
    "kn",
    "lo",
    "ml",
    "mr",
    "my",
    "ne",
    "or",
    "pa",
    "si",
    "ta",
    "te",
    "th",
    "ti",
}
class CoverError(RuntimeError):
    pass


def _style_pair(value: object, field: str) -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(not isinstance(item, int) or item <= 0 for item in value)
    ):
        raise CoverError(f"{field} must contain two positive integers")
    return int(value[0]), int(value[1])


def _style_box(value: object, field: str) -> tuple[int, int, int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or any(not isinstance(item, int) for item in value)
    ):
        raise CoverError(f"{field} must contain four integers")
    left, top, right, bottom = (int(item) for item in value)
    if left < 0 or top < 0 or right <= left or bottom <= top:
        raise CoverError(f"{field} must define a positive safe box")
    return left, top, right, bottom


def _fit_config(value: object, field: str) -> dict[str, dict[str, int]]:
    if not isinstance(value, dict):
        raise CoverError(f"{field} must be a JSON object")
    result: dict[str, dict[str, int]] = {}
    for key in ("defaults", "minimums", "maximum_widths"):
        raw = value.get(key)
        if not isinstance(raw, dict) or not raw:
            raise CoverError(f"{field}.{key} must be a non-empty JSON object")
        normalized: dict[str, int] = {}
        for name, item in raw.items():
            if not isinstance(name, str) or not isinstance(item, int) or item <= 0:
                raise CoverError(f"{field}.{key} values must be positive integers")
            normalized[name] = item
        result[key] = normalized
    if not (result["defaults"].keys() == result["minimums"].keys() == result["maximum_widths"].keys()):
        raise CoverError(f"{field} keys must match across defaults, minimums, and maximum_widths")
    return result


def _identity_config(value: object, field: str) -> dict[str, int]:
    if not isinstance(value, dict):
        raise CoverError(f"{field} must be a JSON object")
    result = {}
    for key in ("center_y", "height", "maximum_width"):
        item = value.get(key)
        if not isinstance(item, int) or item <= 0:
            raise CoverError(f"{field}.{key} must be a positive integer")
        result[key] = item
    return result


def configure_cover_style(style_id: str) -> dict[str, object]:
    global ACTIVE_COVER_STYLE
    global COVER_VIEWBOX, COVER_PNG_SIZE, COVER_SAFE_BOX, COVER_TEMPLATE_PATH
    global SOCIAL_VIEWBOX, SOCIAL_PNG_SIZE, SOCIAL_SAFE_BOX, SOCIAL_TEMPLATE_PATH
    global PROMO_VIEWBOX, PROMO_PNG_SIZE, PROMO_SAFE_BOX, PROMO_TEMPLATE_PATH
    global COVER_PALETTE, COVER_FIT, SOCIAL_FIT, PROMO_FIT
    global COVER_IDENTITY, SOCIAL_IDENTITY, PROMO_IDENTITY

    try:
        style = load_style("cover", style_id)
    except StyleError as exc:
        raise CoverError(str(exc)) from exc
    palette = style.get("palette")
    artboards = style.get("artboards")
    if not isinstance(palette, dict) or not isinstance(artboards, dict):
        raise CoverError(f"cover style {style_id!r} has incomplete configuration")
    required_colors = ("background", "primary", "text", "muted", "subtle", "border")
    normalized_palette: dict[str, str] = {}
    for key in required_colors:
        color = palette.get(key)
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise CoverError(f"cover style palette.{key} must be a hex color")
        normalized_palette[key] = color.lower()

    configured: dict[str, dict[str, object]] = {}
    for name in ("cover", "social", "promo"):
        raw = artboards.get(name)
        if not isinstance(raw, dict):
            raise CoverError(f"cover style artboards.{name} must be a JSON object")
        try:
            template_path = style_file(
                style, raw.get("template"), f"artboards.{name}.template"
            )
        except StyleError as exc:
            raise CoverError(str(exc)) from exc
        configured[name] = {
            "template": template_path,
            "viewbox": _style_pair(raw.get("viewbox"), f"artboards.{name}.viewbox"),
            "png_size": _style_pair(raw.get("png_size"), f"artboards.{name}.png_size"),
            "safe_box": _style_box(raw.get("safe_box"), f"artboards.{name}.safe_box"),
            "identity": _identity_config(raw.get("identity"), f"artboards.{name}.identity"),
            "fit": _fit_config(raw.get("fit"), f"artboards.{name}.fit"),
        }

    ACTIVE_COVER_STYLE = style_id
    COVER_PALETTE = normalized_palette
    COVER_TEMPLATE_PATH = configured["cover"]["template"]  # type: ignore[assignment]
    COVER_VIEWBOX = configured["cover"]["viewbox"]  # type: ignore[assignment]
    COVER_PNG_SIZE = configured["cover"]["png_size"]  # type: ignore[assignment]
    COVER_SAFE_BOX = configured["cover"]["safe_box"]  # type: ignore[assignment]
    COVER_IDENTITY = configured["cover"]["identity"]  # type: ignore[assignment]
    COVER_FIT = configured["cover"]["fit"]  # type: ignore[assignment]
    SOCIAL_TEMPLATE_PATH = configured["social"]["template"]  # type: ignore[assignment]
    SOCIAL_VIEWBOX = configured["social"]["viewbox"]  # type: ignore[assignment]
    SOCIAL_PNG_SIZE = configured["social"]["png_size"]  # type: ignore[assignment]
    SOCIAL_SAFE_BOX = configured["social"]["safe_box"]  # type: ignore[assignment]
    SOCIAL_IDENTITY = configured["social"]["identity"]  # type: ignore[assignment]
    SOCIAL_FIT = configured["social"]["fit"]  # type: ignore[assignment]
    PROMO_TEMPLATE_PATH = configured["promo"]["template"]  # type: ignore[assignment]
    PROMO_VIEWBOX = configured["promo"]["viewbox"]  # type: ignore[assignment]
    PROMO_PNG_SIZE = configured["promo"]["png_size"]  # type: ignore[assignment]
    PROMO_SAFE_BOX = configured["promo"]["safe_box"]  # type: ignore[assignment]
    PROMO_IDENTITY = configured["promo"]["identity"]  # type: ignore[assignment]
    PROMO_FIT = configured["promo"]["fit"]  # type: ignore[assignment]
    return style


def _single_line(value: object, field: str, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise CoverError(f"{field} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise CoverError(f"{field} must not be empty")
    if len(normalized) > max_length:
        raise CoverError(f"{field} must be at most {max_length} characters")
    return normalized


def _string_list(
    value: object,
    field: str,
    *,
    length: int,
    max_length: int,
) -> list[str]:
    if not isinstance(value, list) or len(value) != length:
        raise CoverError(f"{field} must contain exactly {length} strings")
    return [
        _single_line(item, f"{field}[{index}]", max_length=max_length)
        for index, item in enumerate(value)
    ]


def _project_url(value: object) -> str:
    normalized = _single_line(value, "project_url", max_length=240)
    parsed = urlparse(normalized)
    path_parts = [part for part in parsed.path.split("/") if part]
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.params
        or parsed.query
        or parsed.fragment
        or len(path_parts) != 2
    ):
        raise CoverError(
            "project_url must be an HTTPS GitHub repository URL without credentials, "
            "query parameters, or fragments"
        )
    owner, repository = path_parts
    repository = repository.removesuffix(".git")
    if not owner or not repository:
        raise CoverError("project_url must identify a GitHub owner and repository")
    return f"https://github.com/{owner}/{repository}"


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def _png_alpha_bounds(path: Path) -> tuple[tuple[int, int], tuple[int, int, int, int]]:
    try:
        source = path.read_bytes()
    except FileNotFoundError as exc:
        raise CoverError(f"missing PNG: {path}") from exc
    if not source.startswith(PNG_SIGNATURE):
        raise CoverError(f"invalid PNG: {path}")

    cursor = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = interlace = None
    compressed = bytearray()
    while cursor + 12 <= len(source):
        length = struct.unpack(">I", source[cursor : cursor + 4])[0]
        chunk_type = source[cursor + 4 : cursor + 8]
        chunk_start = cursor + 8
        chunk_end = chunk_start + length
        crc_end = chunk_end + 4
        if crc_end > len(source):
            raise CoverError(f"truncated PNG chunk in {path}")
        chunk = source[chunk_start:chunk_end]
        expected_crc = struct.unpack(">I", source[chunk_end:crc_end])[0]
        actual_crc = zlib.crc32(chunk_type)
        actual_crc = zlib.crc32(chunk, actual_crc) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise CoverError(f"invalid PNG checksum in {path}")
        if chunk_type == b"IHDR":
            if length != 13:
                raise CoverError(f"invalid PNG header in {path}")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            if compression != 0 or filtering != 0:
                raise CoverError(f"unsupported PNG compression or filter method in {path}")
        elif chunk_type == b"IDAT":
            compressed.extend(chunk)
        elif chunk_type == b"IEND":
            break
        cursor = crc_end

    if width is None or height is None or bit_depth != 8 or color_type not in {4, 6}:
        raise CoverError(f"logo_lockup must be an 8-bit PNG with an alpha channel: {path}")
    if interlace != 0:
        raise CoverError(f"interlaced logo_lockup PNG files are not supported: {path}")
    bytes_per_pixel = 2 if color_type == 4 else 4
    stride = width * bytes_per_pixel
    try:
        scanlines = zlib.decompress(bytes(compressed))
    except zlib.error as exc:
        raise CoverError(f"invalid compressed PNG data in {path}") from exc
    expected_length = height * (stride + 1)
    if len(scanlines) != expected_length:
        raise CoverError(f"unexpected PNG scanline length in {path}")

    previous = bytearray(stride)
    minimum_x = width
    minimum_y = height
    maximum_x = maximum_y = -1
    offset = 0
    alpha_index = 1 if color_type == 4 else 3
    for y in range(height):
        filter_type = scanlines[offset]
        offset += 1
        row = bytearray(scanlines[offset : offset + stride])
        offset += stride
        for index in range(stride):
            left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            up = previous[index]
            upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            if filter_type == 1:
                row[index] = (row[index] + left) & 0xFF
            elif filter_type == 2:
                row[index] = (row[index] + up) & 0xFF
            elif filter_type == 3:
                row[index] = (row[index] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                row[index] = (row[index] + _paeth(left, up, upper_left)) & 0xFF
            elif filter_type != 0:
                raise CoverError(f"unsupported PNG row filter in {path}")
        for x in range(width):
            if row[x * bytes_per_pixel + alpha_index] == 0:
                continue
            minimum_x = min(minimum_x, x)
            minimum_y = min(minimum_y, y)
            maximum_x = max(maximum_x, x)
            maximum_y = max(maximum_y, y)
        previous = row

    if maximum_x < minimum_x or maximum_y < minimum_y:
        raise CoverError(f"logo_lockup PNG is fully transparent: {path}")
    return (width, height), (
        minimum_x,
        minimum_y,
        maximum_x + 1,
        maximum_y + 1,
    )


def _logo_lockup(
    path: Path,
    value: object,
    logo_style: dict[str, object],
) -> tuple[str | None, str, tuple[int, int] | None, tuple[int, int, int, int] | None]:
    if value is None:
        return None, "", None, None
    normalized = _single_line(value, "logo_lockup", max_length=240)
    relative_path = Path(normalized)
    if (
        relative_path.is_absolute()
        or ".." in relative_path.parts
        or "://" in normalized
        or re.match(r"^[A-Za-z]:[\\/]", normalized)
        or relative_path.suffix.lower() != ".png"
    ):
        raise CoverError(
            "logo_lockup must be a relative PNG path without parent traversal"
        )
    asset_path = (path.parent / relative_path).resolve()
    try:
        asset_path.relative_to(path.parent.resolve())
    except ValueError as exc:
        raise CoverError(
            "logo_lockup must resolve inside the specification directory"
        ) from exc
    lockup = logo_style.get("lockup")
    if not isinstance(lockup, dict):
        raise CoverError("logo style is missing its lockup configuration")
    expected_size = _style_pair(lockup.get("png_size"), "logo_style.lockup.png_size")
    size, content_box = _png_alpha_bounds(asset_path)
    if size != expected_size:
        raise CoverError(
            f"logo_lockup must be {expected_size[0]}x{expected_size[1]}, "
            f"got {size[0]}x{size[1]}"
        )
    return normalized, asset_path.as_uri(), size, content_box


def _cover_copy(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CoverError(f"{field} must be a JSON object")
    return {
        "headline": _single_line(
            value.get("headline"),
            f"{field}.headline",
            max_length=160,
        ),
        "description_lines": _string_list(
            value.get("description_lines"),
            f"{field}.description_lines",
            length=2,
            max_length=120,
        ),
    }


def _promo_copy(value: object, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise CoverError(f"{field} must be a JSON object")
    return {
        "headline": _single_line(
            value.get("headline"),
            f"{field}.headline",
            max_length=100,
        ),
        "description_lines": _string_list(
            value.get("description_lines"),
            f"{field}.description_lines",
            length=2,
            max_length=120,
        ),
        "notice": _single_line(
            value.get("notice"),
            f"{field}.notice",
            max_length=80,
        ),
        "cta": _single_line(
            value.get("cta"),
            f"{field}.cta",
            max_length=32,
        ),
    }


def _locales(value: object, default_locale: str) -> dict[str, dict[str, object]]:
    if not isinstance(value, dict) or not value:
        raise CoverError("locales must be a non-empty JSON object")
    locales: dict[str, dict[str, object]] = {}
    for key, locale in value.items():
        if not isinstance(key, str) or not SLUG_PATTERN.fullmatch(key):
            raise CoverError("locales keys must be lowercase slugs such as en or zh")
        if not isinstance(locale, dict):
            raise CoverError(f"locales.{key} must be a JSON object")
        language = _single_line(
            locale.get("language"),
            f"locales.{key}.language",
            max_length=24,
        )
        if not LANGUAGE_PATTERN.fullmatch(language):
            raise CoverError(f"locales.{key}.language must be a tag such as zh-CN")
        cover = _cover_copy(locale.get("cover"), f"locales.{key}.cover")
        social_value = locale.get("social_preview")
        social_preview = (
            cover
            if social_value is None
            else _cover_copy(social_value, f"locales.{key}.social_preview")
        )
        locales[key] = {
            "language": language,
            "cover": cover,
            "social_preview": social_preview,
            "promo": _promo_copy(locale.get("promo"), f"locales.{key}.promo"),
        }
    if default_locale not in locales:
        raise CoverError("default_locale must identify an entry in locales")
    return locales


def load_spec(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CoverError(f"spec not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CoverError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise CoverError("spec root must be a JSON object")
    if raw.get("schema_version") != SCHEMA_VERSION:
        if raw.get("schema_version") == 3:
            raise CoverError(
                "schema_version 3 is no longer supported; use schema_version 4, replace "
                "style with cover_style and logo_style, and reference a PNG logo_lockup"
            )
        raise CoverError(f"schema_version must be {SCHEMA_VERSION}")

    cover_style = _single_line(raw.get("cover_style"), "cover_style", max_length=64)
    logo_style_id = _single_line(raw.get("logo_style"), "logo_style", max_length=64)
    configure_cover_style(cover_style)
    try:
        logo_style = load_style("logo", logo_style_id)
    except StyleError as exc:
        raise CoverError(str(exc)) from exc

    slug = _single_line(raw.get("repository_slug"), "repository_slug", max_length=64)
    if not SLUG_PATTERN.fullmatch(slug):
        raise CoverError("repository_slug must contain lowercase letters, digits, and hyphens")

    default_locale = _single_line(
        raw.get("default_locale"),
        "default_locale",
        max_length=64,
    )
    if not SLUG_PATTERN.fullmatch(default_locale):
        raise CoverError("default_locale must be a lowercase slug such as en or zh")

    source_files = raw.get("source_files")
    if not isinstance(source_files, list) or not source_files:
        raise CoverError("source_files must be a non-empty JSON array")
    normalized_sources = []
    for index, source in enumerate(source_files):
        normalized = _single_line(source, f"source_files[{index}]", max_length=240)
        source_path = Path(normalized)
        if (
            source_path.is_absolute()
            or ".." in source_path.parts
            or "://" in normalized
            or re.match(r"^[A-Za-z]:[\\/]", normalized)
        ):
            raise CoverError(f"source_files[{index}] must be a repository-relative path")
        normalized_sources.append(normalized)

    logo_lockup, logo_data_uri, logo_size, logo_content_box = _logo_lockup(
        path,
        raw.get("logo_lockup"),
        logo_style,
    )
    locales = _locales(raw.get("locales"), default_locale)

    return {
        "schema_version": SCHEMA_VERSION,
        "cover_style": cover_style,
        "logo_style": logo_style_id,
        "repository_slug": slug,
        "project_name": _single_line(raw.get("project_name"), "project_name", max_length=80),
        "project_url": _project_url(raw.get("project_url")),
        "logo_lockup": logo_lockup,
        "_logo_data_uri": logo_data_uri,
        "_logo_size": logo_size,
        "_logo_content_box": logo_content_box,
        "default_locale": default_locale,
        "locales": locales,
        "source_files": normalized_sources,
    }


def output_paths(
    output_dir: Path,
    slug: str,
    locale_suffixes: tuple[str, ...] = (),
) -> dict[str, Path]:
    paths = {
        "cover_png": output_dir / f"{slug}-cover.png",
        "social_png": output_dir / f"{slug}-social-preview.png",
        "promo_png": output_dir / f"{slug}-promo.png",
    }
    for suffix in locale_suffixes:
        paths[f"cover_{suffix}_png"] = output_dir / f"{slug}-cover-{suffix}.png"
        paths[f"social_{suffix}_png"] = output_dir / f"{slug}-social-preview-{suffix}.png"
        paths[f"promo_{suffix}_png"] = output_dir / f"{slug}-promo-{suffix}.png"
    return paths


def _locale_suffixes(spec: dict[str, object]) -> tuple[str, ...]:
    locales = spec.get("locales")
    if not isinstance(locales, dict):
        return ()
    default_locale = str(spec["default_locale"])
    return tuple(sorted(str(key) for key in locales if key != default_locale))


def _localized_spec(
    spec: dict[str, object],
    locale: dict[str, object],
) -> dict[str, object]:
    localized = dict(spec)
    cover = locale["cover"]
    social_preview = locale["social_preview"]
    promo = locale["promo"]
    assert isinstance(cover, dict)
    assert isinstance(social_preview, dict)
    assert isinstance(promo, dict)
    localized["language"] = locale["language"]
    localized["headline"] = cover["headline"]
    localized["description_lines"] = cover["description_lines"]
    localized["social_preview"] = social_preview
    localized["promo"] = promo
    return localized


def _ordered_locale_keys(spec: dict[str, object]) -> tuple[str, ...]:
    locales = spec.get("locales")
    assert isinstance(locales, dict)
    default_locale = str(spec["default_locale"])
    return (default_locale, *sorted(str(key) for key in locales if key != default_locale))


def _locale_path_keys(locale_key: str, default_locale: str) -> dict[str, str]:
    if locale_key == default_locale:
        return {
            "cover_png": "cover_png",
            "social_png": "social_png",
            "promo_png": "promo_png",
        }
    return {
        "cover_png": f"cover_{locale_key}_png",
        "social_png": f"social_{locale_key}_png",
        "promo_png": f"promo_{locale_key}_png",
    }


def _replace_placeholders(template: str, replacements: dict[str, str]) -> str:
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    unresolved = sorted(set(re.findall(r"__[A-Z0-9_]+__", template)))
    if unresolved:
        raise CoverError(f"unresolved template placeholders: {', '.join(unresolved)}")
    return template


def _palette_replacements() -> dict[str, str]:
    return {
        "__COLOR_BACKGROUND__": COVER_PALETTE["background"],
        "__COLOR_PRIMARY__": COVER_PALETTE["primary"],
        "__COLOR_TEXT__": COVER_PALETTE["text"],
        "__COLOR_MUTED__": COVER_PALETTE["muted"],
        "__COLOR_SUBTLE__": COVER_PALETTE["subtle"],
        "__COLOR_BORDER__": COVER_PALETTE["border"],
    }


def _project_identity(
    spec: dict[str, object],
    sizes: dict[str, int | float],
    *,
    prefix: str,
    name_id: str,
    name_y: int,
    name_size_key: str,
    name_x: int,
    name_anchor: str = "middle",
) -> str:
    data_uri = str(spec.get("_logo_data_uri") or "")
    logo_size = spec.get("_logo_size")
    content_box = spec.get("_logo_content_box")
    if data_uri and isinstance(logo_size, tuple) and isinstance(content_box, tuple):
        width, height = logo_size
        left, top, right, bottom = content_box
        return (
            f'<g id="{prefix}-logo" direction="ltr" unicode-bidi="isolate" '
            f'transform="translate({sizes[f"{prefix}_logo_x"]} '
            f'{sizes[f"{prefix}_logo_y"]}) scale({sizes[f"{prefix}_logo_scale"]})">'
            f'<image width="{width}" height="{height}" href="{data_uri}"/>'
            f'<rect id="{prefix}-logo-bounds" data-safe-logo="true" '
            f'x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" '
            'fill="#000000" opacity="0"/></g>'
        )
    return (
        f'<text id="{name_id}" data-safe-text="true" x="{name_x}" y="{name_y}" '
        f'text-anchor="{name_anchor}" fill="{COVER_PALETTE["text"]}" direction="ltr" '
        'unicode-bidi="isolate" '
        'font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Helvetica Neue, '
        'Helvetica, Arial, sans-serif" '
        f'font-size="{sizes[name_size_key]}" font-weight="650" letter-spacing="0">'
        f'{html.escape(str(spec["project_name"]), quote=False)}</text>'
    )


def _language_typography(language: object) -> dict[str, str]:
    normalized = str(language)
    parts = normalized.split("-")
    primary = parts[0].lower()
    script = next(
        (part.lower() for part in parts[1:] if len(part) == 4 and part.isalpha()),
        "",
    )
    rtl = script in RTL_SCRIPTS or (not script and primary in RTL_LANGUAGES)

    if primary == "zh":
        headline = "'Songti SC', 'Noto Serif CJK SC', SimSun, serif"
        body = (
            "'PingFang SC', 'Noto Sans CJK SC', 'Microsoft YaHei', "
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
        )
    elif primary == "ja":
        headline = "'Yu Mincho', 'Hiragino Mincho ProN', 'Noto Serif CJK JP', serif"
        body = (
            "'Hiragino Sans', 'Yu Gothic', 'Noto Sans CJK JP', "
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
        )
    elif primary == "ko":
        headline = "AppleMyungjo, 'Noto Serif CJK KR', serif"
        body = (
            "'Apple SD Gothic Neo', 'Noto Sans CJK KR', "
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
        )
    elif script == "arab" or primary in {"ar", "fa", "ps", "sd", "ug", "ur"}:
        headline = "'Noto Naskh Arabic', 'Geeza Pro', 'Traditional Arabic', serif"
        body = "'Noto Sans Arabic', 'Geeza Pro', Arial, sans-serif"
    elif script == "hebr" or primary in {"he", "yi"}:
        headline = "'Noto Serif Hebrew', 'Times New Roman', serif"
        body = "'Noto Sans Hebrew', Arial, sans-serif"
    else:
        headline = "Georgia, 'Times New Roman', Times, serif"
        body = (
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', "
            "Helvetica, Arial, sans-serif"
        )

    if script in {"latn", "cyrl", "grek"}:
        headline_style = "italic"
    elif script:
        headline_style = "normal"
    elif primary in {"zh", "ja", "ko"} | RTL_LANGUAGES | UPRIGHT_LANGUAGES:
        headline_style = "normal"
    else:
        headline_style = "italic"

    return {
        "language": normalized,
        "direction": "rtl" if rtl else "ltr",
        "headline_family": headline,
        "body_family": body,
        "headline_style": headline_style,
    }


def build_cover_svg(spec: dict[str, object], sizes: dict[str, int | float]) -> str:
    template = COVER_TEMPLATE_PATH.read_text(encoding="utf-8")
    description_lines = spec["description_lines"]
    assert isinstance(description_lines, list)
    typography = _language_typography(spec["language"])
    rtl = typography["direction"] == "rtl"
    primary_x = 1880 if rtl else 120
    secondary_x = 720 if rtl else 1280
    text_anchor = "end" if rtl else "start"
    identity = _project_identity(
        spec,
        sizes,
        prefix="cover",
        name_id="project-name",
        name_y=112,
        name_size_key="project_name",
        name_x=primary_x,
        name_anchor=text_anchor,
    )
    replacements = {
        **_palette_replacements(),
        "__LANGUAGE__": html.escape(typography["language"], quote=True),
        "__TEXT_DIRECTION__": typography["direction"],
        "__ACCESSIBLE_TITLE__": html.escape(str(spec["project_name"]), quote=False),
        "__ACCESSIBLE_DESCRIPTION__": html.escape(
            "{} {} {}".format(spec["headline"], description_lines[0], description_lines[1]),
            quote=False,
        ),
        "__PROJECT_IDENTITY__": identity,
        "__PRIMARY_X__": str(primary_x),
        "__SECONDARY_X__": str(secondary_x),
        "__TEXT_ANCHOR__": text_anchor,
        "__DIVIDER_X__": "800" if rtl else "1200",
        "__RULE_X__": "656" if rtl else "1280",
        "__HEADLINE__": html.escape(str(spec["headline"]), quote=False),
        "__HEADLINE_SIZE__": str(sizes["headline"]),
        "__HEADLINE_FONT_FAMILY__": typography["headline_family"],
        "__HEADLINE_FONT_STYLE__": typography["headline_style"],
        "__DESCRIPTION_LINE_1__": html.escape(str(description_lines[0]), quote=False),
        "__DESCRIPTION_LINE_2__": html.escape(str(description_lines[1]), quote=False),
        "__DESCRIPTION_SIZE__": str(sizes["description"]),
        "__DESCRIPTION_FONT_FAMILY__": typography["body_family"],
    }
    return _replace_placeholders(template, replacements)


def build_social_svg(spec: dict[str, object], sizes: dict[str, int | float]) -> str:
    template = SOCIAL_TEMPLATE_PATH.read_text(encoding="utf-8")
    social_preview = spec["social_preview"]
    assert isinstance(social_preview, dict)
    description_lines = social_preview["description_lines"]
    assert isinstance(description_lines, list)
    identity = _project_identity(
        spec,
        sizes,
        prefix="social",
        name_id="project-name",
        name_y=325,
        name_size_key="project_name",
        name_x=SOCIAL_VIEWBOX[0] // 2,
    )
    typography = _language_typography(spec["language"])
    replacements = {
        **_palette_replacements(),
        "__LANGUAGE__": html.escape(typography["language"], quote=True),
        "__TEXT_DIRECTION__": typography["direction"],
        "__ACCESSIBLE_TITLE__": html.escape(str(spec["project_name"]), quote=False),
        "__ACCESSIBLE_DESCRIPTION__": html.escape(
            "{} {} {}".format(
                social_preview["headline"],
                description_lines[0],
                description_lines[1],
            ),
            quote=False,
        ),
        "__PROJECT_IDENTITY__": identity,
        "__HEADLINE__": html.escape(str(social_preview["headline"]), quote=False),
        "__HEADLINE_SIZE__": str(sizes["headline"]),
        "__HEADLINE_FONT_FAMILY__": typography["headline_family"],
        "__HEADLINE_FONT_STYLE__": typography["headline_style"],
        "__DESCRIPTION_LINE_1__": html.escape(str(description_lines[0]), quote=False),
        "__DESCRIPTION_LINE_2__": html.escape(str(description_lines[1]), quote=False),
        "__DESCRIPTION_SIZE__": str(sizes["description"]),
        "__DESCRIPTION_FONT_FAMILY__": typography["body_family"],
    }
    return _replace_placeholders(template, replacements)


def _load_segno():
    try:
        import segno
    except ModuleNotFoundError as exc:
        raise CoverError(
            "Segno is required for promotional QR codes. Install it with "
            "`python3 -m pip install playwright==1.61.0 segno==1.6.6` "
            "(or use another Python 3.10+ executable)."
        ) from exc
    return segno


def qr_path(project_url: str) -> tuple[str, int]:
    segno = _load_segno()
    qr = segno.make(project_url, error="q", micro=False)
    rows = [tuple(row) for row in qr.matrix_iter(scale=1, border=4)]
    if not rows or any(len(row) != len(rows) for row in rows):
        raise CoverError("QR generator returned a non-square matrix")

    commands: list[str] = []
    for y, row in enumerate(rows):
        start: int | None = None
        for x, dark in enumerate((*row, False)):
            if dark and start is None:
                start = x
            elif not dark and start is not None:
                width = x - start
                commands.append(f"M{start} {y}h{width}v1h-{width}z")
                start = None
    if not commands:
        raise CoverError("QR generator returned an empty matrix")
    return "".join(commands), len(rows)


def build_promo_svg(spec: dict[str, object], sizes: dict[str, int | float]) -> str:
    template = PROMO_TEMPLATE_PATH.read_text(encoding="utf-8")
    promo = spec["promo"]
    assert isinstance(promo, dict)
    description_lines = promo["description_lines"]
    assert isinstance(description_lines, list)
    project_url = str(spec["project_url"])
    typography = _language_typography(spec["language"])
    rtl = typography["direction"] == "rtl"
    qr_data, qr_modules = qr_path(project_url)
    identity = _project_identity(
        spec,
        sizes,
        prefix="promo",
        name_id="promo-project-name",
        name_y=270,
        name_size_key="promo_project_name",
        name_x=PROMO_VIEWBOX[0] // 2,
    )
    replacements = {
        **_palette_replacements(),
        "__LANGUAGE__": html.escape(typography["language"], quote=True),
        "__TEXT_DIRECTION__": typography["direction"],
        "__ACCESSIBLE_TITLE__": html.escape(str(spec["project_name"]), quote=False),
        "__ACCESSIBLE_DESCRIPTION__": html.escape(
            "{} {} {} {}".format(
                promo["headline"],
                description_lines[0],
                description_lines[1],
                project_url,
            ),
            quote=False,
        ),
        "__PROJECT_IDENTITY__": identity,
        "__PROMO_HEADLINE__": html.escape(str(promo["headline"]), quote=False),
        "__PROMO_HEADLINE_SIZE__": str(sizes["promo_headline"]),
        "__PROMO_HEADLINE_FONT_FAMILY__": typography["headline_family"],
        "__PROMO_HEADLINE_FONT_STYLE__": typography["headline_style"],
        "__PROMO_DESCRIPTION_LINE_1__": html.escape(
            str(description_lines[0]), quote=False
        ),
        "__PROMO_DESCRIPTION_LINE_2__": html.escape(
            str(description_lines[1]), quote=False
        ),
        "__PROMO_DESCRIPTION_SIZE__": str(sizes["promo_description"]),
        "__PROMO_BODY_FONT_FAMILY__": typography["body_family"],
        "__NOTICE__": html.escape(str(promo["notice"]), quote=False),
        "__NOTICE_SIZE__": str(sizes["promo_notice"]),
        "__CTA__": html.escape(str(promo["cta"]), quote=False),
        "__PROJECT_URL__": html.escape(project_url, quote=True),
        "__DISPLAY_URL__": html.escape(project_url.removeprefix("https://"), quote=False),
        "__URL_SIZE__": str(sizes["promo_url"]),
        "__QR_PATH__": qr_data,
        "__QR_MODULES__": str(qr_modules),
        "__QR_SCALE__": f"{180 / qr_modules:.8f}",
        "__QR_BOX_X__": "1130" if rtl else "570",
        "__QR_TRANSLATE_X__": "1150" if rtl else "590",
        "__PROMO_LINK_TEXT_X__": "1080" if rtl else "840",
        "__PROMO_CTA_TEXT_ANCHOR__": "start",
        "__PROMO_URL_TEXT_ANCHOR__": "end" if rtl else "start",
    }
    return _replace_placeholders(template, replacements)


def write_svg(
    path: Path,
    spec: dict[str, object],
    sizes: dict[str, int | float],
    *,
    kind: str,
) -> None:
    if kind == "cover":
        source = build_cover_svg(spec, sizes)
    elif kind == "social":
        source = build_social_svg(spec, sizes)
    elif kind == "promo":
        source = build_promo_svg(spec, sizes)
    else:
        raise CoverError(f"unknown SVG kind: {kind}")
    path.write_text(source, encoding="utf-8")
    try:
        ET.parse(path)
    except ET.ParseError as exc:
        raise CoverError(f"generated invalid SVG: {exc}") from exc


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise CoverError(
            "Playwright is required. Install it with "
            "`python3 -m pip install playwright==1.61.0 segno==1.6.6` "
            "and `python3 -m playwright install chromium` (or use another "
            "Python 3.10+ executable)."
        ) from exc
    return sync_playwright


def launch_browser(playwright):
    try:
        return playwright.chromium.launch(headless=True)
    except Exception as exc:
        raise CoverError(
            "Chromium could not start. Run `python3 -m playwright install chromium` "
            f"and retry. Original error: {exc}"
        ) from exc


def measure_text(
    browser,
    svg_path: Path,
    viewbox: tuple[int, int],
) -> list[dict[str, float | str]]:
    page = browser.new_page(viewport={"width": viewbox[0], "height": viewbox[1]})
    try:
        page.goto(svg_path.resolve().as_uri(), wait_until="load")
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
        page.evaluate(
            "() => Promise.all(Array.from(document.images).map((image) => "
            "image.decode ? image.decode() : Promise.resolve()))"
        )
        return page.evaluate(
            """() => Array.from(document.querySelectorAll(
                '[data-safe-text="true"], [data-safe-logo="true"]'
            )).map((element) => {
                const box = element.getBoundingClientRect();
                return {id: element.id, x: box.x, y: box.y, width: box.width, height: box.height};
            })"""
        )
    finally:
        page.close()


def _position_logo(
    spec: dict[str, object],
    sizes: dict[str, int | float],
    *,
    prefix: str,
    canvas_width: int,
    center_y: float,
    desired_height: float,
    maximum_width: float,
    start_x: float | None = None,
    end_x: float | None = None,
) -> None:
    content_box = spec.get("_logo_content_box")
    if not isinstance(content_box, tuple) or len(content_box) != 4:
        raise CoverError("Logo content bounds are unavailable")
    left, top, right, bottom = (float(item) for item in content_box)
    native_x = left
    native_y = top
    native_width = right - left
    native_height = bottom - top
    if native_width <= 0 or native_height <= 0:
        raise CoverError("Logo has no measurable visible geometry")

    scale = min(desired_height / native_height, maximum_width / native_width)
    logo_width = native_width * scale
    logo_height = native_height * scale
    if start_x is not None and end_x is not None:
        raise CoverError("Logo positioning cannot set both start_x and end_x")
    if start_x is not None:
        logo_x = start_x
    elif end_x is not None:
        logo_x = end_x - logo_width
    else:
        logo_x = (canvas_width - logo_width) / 2

    sizes[f"{prefix}_logo_scale"] = round(scale, 8)
    sizes[f"{prefix}_logo_x"] = round(logo_x - native_x * scale, 4)
    sizes[f"{prefix}_logo_y"] = round(
        center_y - logo_height / 2 - native_y * scale,
        4,
    )


def fit_cover_svg(
    browser,
    svg_path: Path,
    spec: dict[str, object],
) -> list[dict[str, float | str]]:
    has_logo = bool(spec.get("_logo_data_uri"))
    sizes: dict[str, int | float] = {
        **COVER_FIT["defaults"],
        "cover_logo_x": 0,
        "cover_logo_y": 0,
        "cover_logo_scale": 1,
    }
    minimums = COVER_FIT["minimums"]
    maximum_widths = COVER_FIT["maximum_widths"]

    for _ in range(5):
        write_svg(svg_path, spec, sizes, kind="cover")
        boxes = measure_text(browser, svg_path, COVER_VIEWBOX)
        widths = {
            "project_name": max(
                (float(box["width"]) for box in boxes if box["id"] == "project-name"),
                default=0,
            ),
            "headline": max(
                (float(box["width"]) for box in boxes if box["id"] == "headline"),
                default=0,
            ),
            "description": max(
                (
                    float(box["width"])
                    for box in boxes
                    if str(box["id"]).startswith("description-line-")
                ),
                default=0,
            ),
        }
        changed = False
        for key, width in widths.items():
            limit = maximum_widths[key]
            if width <= limit:
                continue
            proposed = max(minimums[key], math.floor(sizes[key] * limit / width) - 1)
            if proposed >= sizes[key]:
                proposed = sizes[key] - 1
            if proposed < minimums[key] or (sizes[key] == minimums[key] and width > limit):
                raise CoverError(f"{key} is too long for the template; shorten the copy")
            sizes[key] = proposed
            changed = True
        if not changed:
            if has_logo:
                _position_logo(
                    spec,
                    sizes,
                    prefix="cover",
                    canvas_width=COVER_VIEWBOX[0],
                    center_y=COVER_IDENTITY["center_y"],
                    desired_height=COVER_IDENTITY["height"],
                    maximum_width=COVER_IDENTITY["maximum_width"],
                    end_x=1880
                    if _language_typography(spec["language"])["direction"] == "rtl"
                    else None,
                    start_x=120
                    if _language_typography(spec["language"])["direction"] != "rtl"
                    else None,
                )
                write_svg(svg_path, spec, sizes, kind="cover")
                boxes = measure_text(browser, svg_path, COVER_VIEWBOX)
            validate_safe_area(boxes, COVER_SAFE_BOX, "cover")
            return boxes

    raise CoverError("text fitting did not converge; shorten the cover copy")


def fit_social_svg(
    browser,
    svg_path: Path,
    spec: dict[str, object],
) -> list[dict[str, float | str]]:
    has_logo = bool(spec.get("_logo_data_uri"))
    sizes: dict[str, int | float] = {
        **SOCIAL_FIT["defaults"],
        "social_logo_x": 0,
        "social_logo_y": 0,
        "social_logo_scale": 1,
    }
    minimums = SOCIAL_FIT["minimums"]
    maximum_widths = SOCIAL_FIT["maximum_widths"]

    for _ in range(5):
        write_svg(svg_path, spec, sizes, kind="social")
        boxes = measure_text(browser, svg_path, SOCIAL_VIEWBOX)
        widths = {
            "project_name": max(
                (float(box["width"]) for box in boxes if box["id"] == "project-name"),
                default=0,
            ),
            "headline": max(
                (float(box["width"]) for box in boxes if box["id"] == "headline"),
                default=0,
            ),
            "description": max(
                (
                    float(box["width"])
                    for box in boxes
                    if str(box["id"]).startswith("description-line-")
                ),
                default=0,
            ),
        }
        changed = False
        for key, width in widths.items():
            limit = maximum_widths[key]
            if width <= limit:
                continue
            proposed = max(minimums[key], math.floor(sizes[key] * limit / width) - 1)
            if proposed >= sizes[key]:
                proposed = sizes[key] - 1
            if proposed < minimums[key] or (sizes[key] == minimums[key] and width > limit):
                raise CoverError(f"social {key} is too long for the template; shorten the copy")
            sizes[key] = proposed
            changed = True
        if not changed:
            if has_logo:
                _position_logo(
                    spec,
                    sizes,
                    prefix="social",
                    canvas_width=SOCIAL_VIEWBOX[0],
                    center_y=SOCIAL_IDENTITY["center_y"],
                    desired_height=SOCIAL_IDENTITY["height"],
                    maximum_width=SOCIAL_IDENTITY["maximum_width"],
                )
                write_svg(svg_path, spec, sizes, kind="social")
                boxes = measure_text(browser, svg_path, SOCIAL_VIEWBOX)
            validate_safe_area(boxes, SOCIAL_SAFE_BOX, "social preview")
            return boxes

    raise CoverError("social text fitting did not converge; shorten the social copy")


def fit_promo_svg(
    browser,
    svg_path: Path,
    spec: dict[str, object],
) -> list[dict[str, float | str]]:
    has_logo = bool(spec.get("_logo_data_uri"))
    sizes: dict[str, int | float] = {
        **PROMO_FIT["defaults"],
        "promo_logo_x": 0,
        "promo_logo_y": 0,
        "promo_logo_scale": 1,
    }
    minimums = PROMO_FIT["minimums"]
    maximum_widths = PROMO_FIT["maximum_widths"]
    prefixes = {
        "promo_project_name": ("promo-project-name",),
        "promo_headline": ("promo-headline",),
        "promo_description": ("promo-description-line-",),
        "promo_notice": ("promo-notice",),
        "promo_url": ("promo-project-url",),
    }

    for _ in range(5):
        write_svg(svg_path, spec, sizes, kind="promo")
        boxes = measure_text(browser, svg_path, PROMO_VIEWBOX)
        widths: dict[str, float] = {}
        for key, id_prefixes in prefixes.items():
            widths[key] = max(
                (
                    float(box["width"])
                    for box in boxes
                    if any(str(box["id"]).startswith(prefix) for prefix in id_prefixes)
                ),
                default=0,
            )

        changed = False
        for key, width in widths.items():
            limit = maximum_widths[key]
            if width <= limit:
                continue
            proposed = max(minimums[key], math.floor(sizes[key] * limit / width) - 1)
            if proposed >= sizes[key]:
                proposed = sizes[key] - 1
            if proposed < minimums[key] or (sizes[key] == minimums[key] and width > limit):
                raise CoverError(f"{key} is too long for the template; shorten the copy")
            sizes[key] = proposed
            changed = True
        if not changed:
            if has_logo:
                _position_logo(
                    spec,
                    sizes,
                    prefix="promo",
                    canvas_width=PROMO_VIEWBOX[0],
                    center_y=PROMO_IDENTITY["center_y"],
                    desired_height=PROMO_IDENTITY["height"],
                    maximum_width=PROMO_IDENTITY["maximum_width"],
                )
                write_svg(svg_path, spec, sizes, kind="promo")
                boxes = measure_text(browser, svg_path, PROMO_VIEWBOX)
            validate_safe_area(boxes, PROMO_SAFE_BOX, "promotional")
            return boxes

    raise CoverError("promotional text fitting did not converge; shorten the copy")


def validate_safe_area(
    boxes: list[dict[str, float | str]],
    safe_box: tuple[int, int, int, int],
    label: str,
) -> None:
    left, top, right, bottom = safe_box
    if not boxes:
        raise CoverError("SVG does not contain measurable cover text")
    for box in boxes:
        x = float(box["x"])
        y = float(box["y"])
        width = float(box["width"])
        height = float(box["height"])
        if x < left or y < top or x + width > right or y + height > bottom:
            raise CoverError(f"{box['id']} falls outside the {label} safe area")


def screenshot(browser, svg_path: Path, output_path: Path, width: int, height: int) -> None:
    page = browser.new_page(viewport={"width": width, "height": height})
    try:
        page.goto(svg_path.resolve().as_uri(), wait_until="load")
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
        page.evaluate(
            "() => Promise.all(Array.from(document.images).map((image) => "
            "image.decode ? image.decode() : Promise.resolve()))"
        )
        page.screenshot(path=str(output_path))
    finally:
        page.close()


def png_dimensions(path: Path) -> tuple[int, int]:
    try:
        header = path.read_bytes()[:24]
    except FileNotFoundError as exc:
        raise CoverError(f"missing PNG: {path}") from exc
    if len(header) != 24 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise CoverError(f"invalid PNG: {path}")
    return struct.unpack(">II", header[16:24])


def validate_svg_source(
    path: Path,
    *,
    allowed_href: str | None = None,
    allowed_image_href: str | None = None,
    require_qr: bool = False,
) -> None:
    try:
        tree = ET.parse(path)
    except FileNotFoundError as exc:
        raise CoverError(f"missing SVG: {path}") from exc
    except ET.ParseError as exc:
        raise CoverError(f"invalid SVG: {path}: {exc}") from exc
    source = path.read_text(encoding="utf-8")
    if "__" in source and re.search(r"__[A-Z0-9_]+__", source):
        raise CoverError(f"unresolved template placeholder in {path}")

    qr_found = False
    for element in tree.getroot().iter():
        tag = element.tag.rsplit("}", 1)[-1].lower()
        if tag in {"script", "foreignobject"}:
            raise CoverError(f"{tag} elements are not allowed in {path}")
        if tag == "image" and (
            allowed_image_href is None
            or element.attrib.get("href") != allowed_image_href
        ):
            raise CoverError(f"unapproved embedded image in {path}")
        if element.attrib.get("id") == "promo-qr-modules":
            qr_found = True
        for attribute, value in element.attrib.items():
            attribute_name = attribute.rsplit("}", 1)[-1].lower()
            if attribute_name == "src":
                raise CoverError(f"embedded asset references are not allowed in {path}")
            if attribute_name != "href":
                continue
            if tag == "image" and allowed_image_href is not None and value == allowed_image_href:
                continue
            if allowed_href is not None and value == allowed_href:
                continue
            raise CoverError(f"unapproved link {value!r} in {path}")
    if require_qr and not qr_found:
        raise CoverError(f"promotional SVG is missing its embedded QR path: {path}")


def validate_png_pair(cover_path: Path, social_path: Path) -> tuple[tuple[int, int], tuple[int, int]]:
    cover_size = png_dimensions(cover_path)
    social_size = png_dimensions(social_path)
    if cover_size != COVER_PNG_SIZE:
        raise CoverError(
            f"cover PNG must be {COVER_PNG_SIZE[0]}x{COVER_PNG_SIZE[1]}, "
            f"got {cover_size[0]}x{cover_size[1]}"
        )
    if social_size != SOCIAL_PNG_SIZE:
        raise CoverError(
            f"social preview must be {SOCIAL_PNG_SIZE[0]}x{SOCIAL_PNG_SIZE[1]}, "
            f"got {social_size[0]}x{social_size[1]}"
        )
    return cover_size, social_size


def validate_promo_png(path: Path) -> tuple[int, int]:
    size = png_dimensions(path)
    if size != PROMO_PNG_SIZE:
        raise CoverError(
            f"promotional PNG must be {PROMO_PNG_SIZE[0]}x{PROMO_PNG_SIZE[1]}, "
            f"got {size[0]}x{size[1]}"
        )
    return size


def _source_paths(
    source_dir: Path,
    slug: str,
    locale_key: str,
    default_locale: str,
) -> dict[str, Path]:
    suffix = "" if locale_key == default_locale else f"-{locale_key}"
    return {
        "cover": source_dir / f"{slug}-cover{suffix}.svg",
        "social": source_dir / f"{slug}-social-preview{suffix}.svg",
        "promo": source_dir / f"{slug}-promo{suffix}.svg",
    }


def _validate_layouts(spec: dict[str, object], browser, source_dir: Path) -> None:
    locales = spec.get("locales")
    assert isinstance(locales, dict)
    default_locale = str(spec["default_locale"])
    slug = str(spec["repository_slug"])
    allowed_image_href = str(spec.get("_logo_data_uri") or "") or None
    for locale_key in _ordered_locale_keys(spec):
        locale = locales[locale_key]
        assert isinstance(locale, dict)
        localized_spec = _localized_spec(spec, locale)
        sources = _source_paths(source_dir, slug, locale_key, default_locale)
        fit_cover_svg(browser, sources["cover"], localized_spec)
        fit_social_svg(browser, sources["social"], localized_spec)
        fit_promo_svg(browser, sources["promo"], localized_spec)
        validate_svg_source(
            sources["cover"],
            allowed_image_href=allowed_image_href,
        )
        validate_svg_source(
            sources["social"],
            allowed_image_href=allowed_image_href,
        )
        validate_svg_source(
            sources["promo"],
            allowed_href=str(spec["project_url"]),
            allowed_image_href=allowed_image_href,
            require_qr=True,
        )


def validate_outputs(spec: dict[str, object], output_dir: Path, browser=None) -> dict[str, object]:
    suffixes = _locale_suffixes(spec)
    paths = output_paths(output_dir, str(spec["repository_slug"]), suffixes)
    locales = spec.get("locales")
    assert isinstance(locales, dict)
    default_locale = str(spec["default_locale"])
    localized_outputs: dict[str, dict[str, object]] = {}
    for locale_key in _ordered_locale_keys(spec):
        key_map = _locale_path_keys(locale_key, default_locale)
        cover_png = paths[key_map["cover_png"]]
        social_png = paths[key_map["social_png"]]
        promo_png = paths[key_map["promo_png"]]
        cover_size, social_size = validate_png_pair(cover_png, social_png)
        promo_size = validate_promo_png(promo_png)
        localized_outputs[locale_key] = {
            "language": locales[locale_key]["language"],
            "cover_png": str(cover_png),
            "social_png": str(social_png),
            "promo_png": str(promo_png),
            "cover_size": list(cover_size),
            "social_size": list(social_size),
            "promo_size": list(promo_size),
        }
    if browser is not None:
        with tempfile.TemporaryDirectory(prefix="cover-layout-validation-") as temp_name:
            _validate_layouts(spec, browser, Path(temp_name))
    return {
        "cover_style": spec["cover_style"],
        "logo_style": spec["logo_style"],
        "default_locale": default_locale,
        "locales": localized_outputs,
    }


def command_render(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec).resolve()
    output_dir = Path(args.output_dir).resolve()
    spec = load_spec(spec_path)
    suffixes = _locale_suffixes(spec)
    paths = output_paths(output_dir, str(spec["repository_slug"]), suffixes)
    existing = [path for path in paths.values() if path.exists()]
    if existing and not args.force:
        names = ", ".join(path.name for path in existing)
        raise CoverError(f"refusing to overwrite existing output(s): {names}; use --force")

    output_dir.mkdir(parents=True, exist_ok=True)
    sync_playwright = _load_playwright()
    with tempfile.TemporaryDirectory(prefix="github-cover-", dir=output_dir) as temp_name:
        temp_dir = Path(temp_name)
        temp_paths = output_paths(temp_dir, str(spec["repository_slug"]), suffixes)
        with sync_playwright() as playwright:
            browser = launch_browser(playwright)
            try:
                locales = spec.get("locales")
                assert isinstance(locales, dict)
                default_locale = str(spec["default_locale"])
                for locale_key in _ordered_locale_keys(spec):
                    locale = locales[locale_key]
                    assert isinstance(locale, dict)
                    localized_spec = _localized_spec(spec, locale)
                    key_map = _locale_path_keys(locale_key, default_locale)
                    sources = _source_paths(
                        temp_dir,
                        str(spec["repository_slug"]),
                        locale_key,
                        default_locale,
                    )
                    cover_svg = sources["cover"]
                    social_svg = sources["social"]
                    promo_svg = sources["promo"]
                    fit_cover_svg(browser, cover_svg, localized_spec)
                    fit_social_svg(browser, social_svg, localized_spec)
                    fit_promo_svg(browser, promo_svg, localized_spec)
                    allowed_image_href = str(spec.get("_logo_data_uri") or "") or None
                    validate_svg_source(
                        cover_svg,
                        allowed_image_href=allowed_image_href,
                    )
                    validate_svg_source(
                        social_svg,
                        allowed_image_href=allowed_image_href,
                    )
                    validate_svg_source(
                        promo_svg,
                        allowed_href=str(spec["project_url"]),
                        allowed_image_href=allowed_image_href,
                        require_qr=True,
                    )
                    screenshot(
                        browser,
                        cover_svg,
                        temp_paths[key_map["cover_png"]],
                        *COVER_PNG_SIZE,
                    )
                    screenshot(
                        browser,
                        social_svg,
                        temp_paths[key_map["social_png"]],
                        *SOCIAL_PNG_SIZE,
                    )
                    screenshot(
                        browser,
                        promo_svg,
                        temp_paths[key_map["promo_png"]],
                        *PROMO_PNG_SIZE,
                    )
                validate_outputs(spec, temp_dir)
            finally:
                browser.close()

        for key, temp_path in temp_paths.items():
            destination = paths[key]
            if destination.exists():
                destination.unlink()
            shutil.move(str(temp_path), str(destination))

    result = validate_outputs(spec, output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    spec = load_spec(Path(args.spec).resolve())
    output_dir = Path(args.output_dir).resolve()
    sync_playwright = _load_playwright()
    with sync_playwright() as playwright:
        browser = launch_browser(playwright)
        try:
            result = validate_outputs(spec, output_dir, browser=browser)
        finally:
            browser.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render and validate styled project Cover, Social Preview, and Promo PNGs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    render = subparsers.add_parser("render", help="Render PNG files from a specification.")
    render.add_argument("spec", help="Path to the cover specification JSON.")
    render.add_argument("--output-dir", default="assets", help="Output directory (default: assets).")
    render.add_argument("--force", action="store_true", help="Replace existing generated files.")
    render.set_defaults(func=command_render)

    validate = subparsers.add_parser("validate", help="Validate generated PNG files and layouts.")
    validate.add_argument("spec", help="Path to the cover specification JSON.")
    validate.add_argument("--output-dir", default="assets", help="Output directory (default: assets).")
    validate.set_defaults(func=command_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except CoverError as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
