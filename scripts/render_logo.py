#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import html
import json
import math
import re
import shutil
import struct
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

PRIMARY_COLOR = "#2855d9"
SECONDARY_COLOR = "#202124"
MARK_VIEWBOX = (512, 512)
MARK_PNG_SIZE = (1024, 1024)
LOCKUP_VIEWBOX = (1600, 400)
LOCKUP_PNG_SIZE = (3200, 800)
LOCKUP_WORDMARK_WIDTH = 1200
MARK_TO_WORDMARK_SIZE = 0.73666667
LOCKUP_GAP = 36
CONTACT_SHEET_SIZE = (2400, 1400)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CONCEPT_FILENAMES = ("concept-a.svg", "concept-b.svg", "concept-c.svg")
GEOMETRY_TAGS = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"}
ALLOWED_TAGS = {"svg", "g", *GEOMETRY_TAGS}
ALLOWED_COLORS = {"none", PRIMARY_COLOR, SECONDARY_COLOR}
COMMON_GEOMETRY_ATTRIBUTES = {
    "fill",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
    "fill-rule",
    "opacity",
    "transform",
}
ALLOWED_ATTRIBUTES = {
    "svg": {"viewBox"},
    "g": {"transform", "opacity"},
    "path": {"d", *COMMON_GEOMETRY_ATTRIBUTES},
    "rect": {"x", "y", "width", "height", "rx", "ry", *COMMON_GEOMETRY_ATTRIBUTES},
    "circle": {"cx", "cy", "r", *COMMON_GEOMETRY_ATTRIBUTES},
    "ellipse": {"cx", "cy", "rx", "ry", *COMMON_GEOMETRY_ATTRIBUTES},
    "line": {"x1", "y1", "x2", "y2", *COMMON_GEOMETRY_ATTRIBUTES},
    "polyline": {"points", *COMMON_GEOMETRY_ATTRIBUTES},
    "polygon": {"points", *COMMON_GEOMETRY_ATTRIBUTES},
}
FINAL_ALLOWED_TAGS = {"svg", "title", "desc", "g", "text", *GEOMETRY_TAGS}
FINAL_ALLOWED_ATTRIBUTES = {
    **ALLOWED_ATTRIBUTES,
    "svg": {"viewBox", "role", "aria-labelledby"},
    "title": {"id"},
    "desc": {"id"},
    "g": {"id", "transform", "opacity"},
    "text": {
        "id",
        "x",
        "y",
        "fill",
        "font-family",
        "font-size",
        "font-weight",
        "letter-spacing",
    },
}


class LogoError(RuntimeError):
    pass


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def _single_line(value: object, field: str, *, max_length: int) -> str:
    if not isinstance(value, str):
        raise LogoError(f"{field} must be a string")
    normalized = " ".join(value.split())
    if not normalized:
        raise LogoError(f"{field} must not be empty")
    if len(normalized) > max_length:
        raise LogoError(f"{field} must be at most {max_length} characters")
    return normalized


def _slug(value: object) -> str:
    normalized = _single_line(value, "slug", max_length=64)
    if not SLUG_PATTERN.fullmatch(normalized):
        raise LogoError("slug must contain lowercase letters, digits, and hyphens")
    return normalized


def _parse_viewbox(value: str | None) -> tuple[float, float, float, float]:
    if value is None:
        raise LogoError("SVG is missing viewBox")
    parts = re.split(r"[\s,]+", value.strip())
    if len(parts) != 4:
        raise LogoError("SVG viewBox must contain exactly four numbers")
    try:
        return tuple(float(part) for part in parts)  # type: ignore[return-value]
    except ValueError as exc:
        raise LogoError("SVG viewBox contains a non-numeric value") from exc


def _read_svg(path: Path) -> tuple[ET.ElementTree, ET.Element, str]:
    try:
        source = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise LogoError(f"missing SVG: {path}") from exc
    lowered = source.lower()
    for forbidden in ("<!doctype", "<!entity", "<script", "<style", "javascript:", "data:", "url("):
        if forbidden in lowered:
            raise LogoError(f"forbidden SVG content {forbidden!r} in {path}")
    try:
        tree = ET.ElementTree(ET.fromstring(source))
    except ET.ParseError as exc:
        raise LogoError(f"invalid SVG {path}: {exc}") from exc
    root = tree.getroot()
    if _local_name(root.tag) != "svg":
        raise LogoError(f"root element must be svg: {path}")
    return tree, root, source


def _validate_attributes(element: ET.Element, tag: str, path: Path, *, final: bool) -> None:
    allowlist = FINAL_ALLOWED_ATTRIBUTES if final else ALLOWED_ATTRIBUTES
    for raw_name, value in element.attrib.items():
        name = _local_name(raw_name)
        lowered_name = name.lower()
        lowered_value = value.lower()
        if lowered_name.startswith("on") or lowered_name in {"href", "src"}:
            raise LogoError(f"attribute {name!r} is not allowed in {path}")
        if name not in allowlist.get(tag, set()):
            raise LogoError(f"attribute {name!r} is not allowed on {tag} in {path}")
        if any(token in lowered_value for token in ("url(", "javascript:", "data:")):
            raise LogoError(f"unsafe attribute value on {tag} in {path}")


def _validate_geometry_color(element: ET.Element, path: Path, *, monochrome: bool = False) -> None:
    if "fill" not in element.attrib:
        raise LogoError(f"every geometry element must declare fill explicitly in {path}")
    expected = {"none", SECONDARY_COLOR} if monochrome else ALLOWED_COLORS
    for attribute in ("fill", "stroke"):
        if attribute not in element.attrib:
            continue
        value = element.attrib[attribute].lower()
        if value not in expected:
            allowed = ", ".join(sorted(expected))
            raise LogoError(f"{attribute}={value!r} is not allowed in {path}; use {allowed}")


def _is_full_canvas_rect(
    element: ET.Element,
    canvas: tuple[int, int] = MARK_VIEWBOX,
) -> bool:
    if _local_name(element.tag) != "rect" or element.attrib.get("fill", "none").lower() == "none":
        return False
    try:
        x = float(element.attrib.get("x", "0"))
        y = float(element.attrib.get("y", "0"))
        width = float(element.attrib.get("width", "0"))
        height = float(element.attrib.get("height", "0"))
    except ValueError:
        return False
    return x <= 0 and y <= 0 and width >= canvas[0] and height >= canvas[1]


def validate_candidate(path: Path) -> ET.Element:
    _, root, _ = _read_svg(path)
    if _parse_viewbox(root.attrib.get("viewBox")) != (0.0, 0.0, 512.0, 512.0):
        raise LogoError(f"candidate viewBox must be exactly '0 0 512 512': {path}")

    geometry_count = 0
    for element in root.iter():
        tag = _local_name(element.tag)
        if tag not in ALLOWED_TAGS:
            raise LogoError(f"element {tag!r} is not allowed in candidate {path}")
        _validate_attributes(element, tag, path, final=False)
        if tag in GEOMETRY_TAGS:
            geometry_count += 1
            _validate_geometry_color(element, path)
            if _is_full_canvas_rect(element):
                raise LogoError(f"candidate must have a transparent background: {path}")

    if geometry_count == 0:
        raise LogoError(f"candidate contains no visible geometry: {path}")
    if geometry_count > 16:
        raise LogoError(f"candidate contains {geometry_count} geometry elements; maximum is 16")
    return root


def _geometry_markup(root: ET.Element, *, monochrome: bool = False) -> str:
    children = [copy.deepcopy(child) for child in list(root)]
    if monochrome:
        for child in children:
            for element in child.iter():
                if _local_name(element.tag) not in GEOMETRY_TAGS:
                    continue
                for attribute in ("fill", "stroke"):
                    value = element.attrib.get(attribute)
                    if value is not None and value.lower() != "none":
                        element.set(attribute, SECONDARY_COLOR)
    return "".join(ET.tostring(child, encoding="unicode") for child in children)


def _svg_document(
    *,
    viewbox: tuple[int, int],
    title: str,
    description: str,
    body: str,
) -> str:
    width, height = viewbox
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="{SVG_NS}" viewBox="0 0 {width} {height}" '
        'role="img" aria-labelledby="logo-title logo-description">\n'
        f'  <title id="logo-title">{html.escape(title, quote=False)}</title>\n'
        f'  <desc id="logo-description">{html.escape(description, quote=False)}</desc>\n'
        f"{body}\n"
        "</svg>\n"
    )


def build_mark_svg(root: ET.Element, project_name: str) -> str:
    body = f'  <g id="logo-mark">{_geometry_markup(root, monochrome=False)}</g>'
    return _svg_document(
        viewbox=MARK_VIEWBOX,
        title=f"{project_name} logo mark",
        description=f"Editable vector mark for {project_name}.",
        body=body,
    )


def _wordmark_size(
    project_name: str,
    *,
    available_width: int = LOCKUP_WORDMARK_WIDTH,
    minimum_size: int = 80,
) -> int:
    estimated_units = max(1.0, sum(1.0 if ord(char) < 128 else 1.7 for char in project_name))
    size = min(180, math.floor(available_width / (estimated_units * 0.61)))
    if size < minimum_size:
        raise LogoError("project name is too long for the horizontal lockup")
    return size


def build_lockup_svg(
    root: ET.Element,
    project_name: str,
    *,
    mark_x: float = 0,
    mark_y: float = 0,
    mark_scale: float = 1,
    wordmark_x: float = 700,
) -> str:
    size = _wordmark_size(project_name)
    body = (
        '  <g id="logo-lockup">\n'
        f'    <g id="logo-mark" transform="translate({mark_x:g} {mark_y:g}) '
        f'scale({mark_scale:g})">'
        f"{_geometry_markup(root, monochrome=False)}</g>\n"
        f'    <text id="logo-wordmark" x="{wordmark_x:g}" y="258" fill="{SECONDARY_COLOR}" '
        'font-family="Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" '
        f'font-size="{size}" font-weight="700" letter-spacing="0">'
        f"{html.escape(project_name, quote=False)}</text>\n"
        "  </g>"
    )
    return _svg_document(
        viewbox=LOCKUP_VIEWBOX,
        title=f"{project_name} horizontal logo",
        description=f"Editable horizontal vector logo for {project_name}.",
        body=body,
    )


def _preview_mark(root: ET.Element, x: float, y: float, size: float, *, monochrome: bool) -> str:
    scale = size / MARK_VIEWBOX[0]
    return (
        f'<g transform="translate({x:g} {y:g}) scale({scale:.8f})">'
        f"{_geometry_markup(root, monochrome=monochrome)}</g>"
    )


def build_contact_sheet(project_name: str, roots: list[ET.Element]) -> str:
    labels = ("Concept A", "Concept B", "Concept C")
    columns: list[str] = []
    for index, (root, label) in enumerate(zip(roots, labels, strict=True)):
        left = 60 + index * 780
        center = left + 360
        wordmark_size = min(
            74,
            _wordmark_size(
                project_name,
                available_width=520,
                minimum_size=32,
            ),
        )
        columns.extend(
            [
                f'<g id="concept-{chr(97 + index)}">',
                f'<rect x="{left}" y="150" width="720" height="1140" rx="24" fill="#ffffff" stroke="#dfe3e8" stroke-width="2"/>',
                f'<text x="{left + 36}" y="214" fill="{SECONDARY_COLOR}" font-family="ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="30" font-weight="650">{label}</text>',
                _preview_mark(root, center - 170, 270, 340, monochrome=False),
                f'<g transform="translate({left + 44} 670) scale(0.1953125)">{_geometry_markup(root, monochrome=False)}</g>',
                f'<text x="{left + 166}" y="746" fill="{SECONDARY_COLOR}" font-family="ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="{wordmark_size}" font-weight="700">{html.escape(project_name, quote=False)}</text>',
                f'<text x="{left + 36}" y="845" fill="#656b73" font-family="ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="24">Monochrome</text>',
                _preview_mark(root, left + 36, 882, 128, monochrome=True),
                f'<text x="{left + 230}" y="845" fill="#656b73" font-family="ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="24">Small-size checks</text>',
                f'<rect x="{left + 230}" y="882" width="70" height="70" rx="10" fill="#f4f6f8"/>',
                _preview_mark(root, left + 257, 909, 16, monochrome=False),
                f'<text x="{left + 250}" y="984" fill="#656b73" font-family="ui-monospace, SFMono-Regular, Consolas, monospace" font-size="18">16px</text>',
                f'<rect x="{left + 326}" y="882" width="86" height="86" rx="10" fill="#f4f6f8"/>',
                _preview_mark(root, left + 353, 909, 32, monochrome=False),
                f'<text x="{left + 342}" y="984" fill="#656b73" font-family="ui-monospace, SFMono-Regular, Consolas, monospace" font-size="18">32px</text>',
                f'<rect x="{left + 448}" y="882" width="176" height="176" rx="14" fill="#f4f6f8"/>',
                _preview_mark(root, left + 472, 906, 128, monochrome=False),
                f'<text x="{left + 502}" y="1087" fill="#656b73" font-family="ui-monospace, SFMono-Regular, Consolas, monospace" font-size="18">128px</text>',
                f'<text x="{left + 36}" y="1190" fill="#656b73" font-family="ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="21">Transparent SVG / two colors / no effects</text>',
                "</g>",
            ]
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="{SVG_NS}" viewBox="0 0 {CONTACT_SHEET_SIZE[0]} {CONTACT_SHEET_SIZE[1]}">\n'
        '  <rect x="0" y="0" width="2400" height="1400" fill="#f4f6f8"/>\n'
        f'  <text x="60" y="92" fill="{SECONDARY_COLOR}" font-family="ui-sans-serif, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" font-size="48" font-weight="700">{html.escape(project_name, quote=False)} logo concepts</text>\n'
        + "\n".join(f"  {item}" for item in columns)
        + "\n</svg>\n"
    )


def logo_paths(output_dir: Path, slug: str) -> dict[str, Path]:
    return {
        "mark_svg": output_dir / f"{slug}-logo-mark.svg",
        "mark_png": output_dir / f"{slug}-logo-mark.png",
        "lockup_svg": output_dir / f"{slug}-logo-lockup.svg",
        "lockup_png": output_dir / f"{slug}-logo-lockup.png",
    }


def _load_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:
        raise LogoError(
            "Playwright is required. Install it with `python -m pip install playwright` "
            "and `python -m playwright install chromium`."
        ) from exc
    return sync_playwright


def _launch_browser(playwright):
    try:
        return playwright.chromium.launch(headless=True)
    except Exception as exc:
        raise LogoError(
            "Chromium could not start. Run `python -m playwright install chromium` "
            f"and retry. Original error: {exc}"
        ) from exc


def _screenshot(browser, svg_path: Path, output_path: Path, size: tuple[int, int], *, transparent: bool) -> None:
    page = browser.new_page(viewport={"width": size[0], "height": size[1]})
    try:
        page.goto(svg_path.resolve().as_uri(), wait_until="load")
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
        page.screenshot(path=str(output_path), omit_background=transparent)
    finally:
        page.close()


def _measure_logo(browser, svg_path: Path) -> dict[str, dict[str, float]]:
    page = browser.new_page(viewport={"width": LOCKUP_VIEWBOX[0], "height": LOCKUP_VIEWBOX[1]})
    try:
        page.goto(svg_path.resolve().as_uri(), wait_until="load")
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
        return page.evaluate(
            """() => Object.fromEntries(['logo-mark', 'logo-wordmark'].map((id) => {
                const box = document.getElementById(id).getBoundingClientRect();
                return [id, {x: box.x, y: box.y, width: box.width, height: box.height}];
            }))"""
        )
    finally:
        page.close()


def _fit_lockup_svg(browser, path: Path, root: ET.Element, project_name: str) -> None:
    _write_svg(path, build_lockup_svg(root, project_name))
    boxes = _measure_logo(browser, path)
    mark = boxes["logo-mark"]
    wordmark = boxes["logo-wordmark"]
    native_width = float(mark["width"])
    native_height = float(mark["height"])
    if native_width <= 0 or native_height <= 0 or float(wordmark["width"]) <= 0:
        raise LogoError("logo geometry and wordmark must be measurable")

    target_size = _wordmark_size(project_name) * MARK_TO_WORDMARK_SIZE
    scale = target_size / max(native_width, native_height)
    mark_width = native_width * scale
    mark_height = native_height * scale
    total_width = mark_width + LOCKUP_GAP + float(wordmark["width"])
    start_x = (LOCKUP_VIEWBOX[0] - total_width) / 2
    wordmark_center_y = float(wordmark["y"]) + float(wordmark["height"]) / 2
    mark_x = start_x - float(mark["x"]) * scale
    mark_y = wordmark_center_y - mark_height / 2 - float(mark["y"]) * scale
    wordmark_x = start_x + mark_width + LOCKUP_GAP

    _write_svg(
        path,
        build_lockup_svg(
            root,
            project_name,
            mark_x=round(mark_x, 4),
            mark_y=round(mark_y, 4),
            mark_scale=round(scale, 8),
            wordmark_x=round(wordmark_x, 4),
        ),
    )


def png_metadata(path: Path) -> tuple[int, int, int]:
    try:
        header = path.read_bytes()[:26]
    except FileNotFoundError as exc:
        raise LogoError(f"missing PNG: {path}") from exc
    if len(header) != 26 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise LogoError(f"invalid PNG: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return width, height, header[25]


def _validate_final_svg(
    path: Path,
    expected_viewbox: tuple[int, int],
    *,
    allow_wordmark: bool,
) -> None:
    _, root, _ = _read_svg(path)
    expected = (0.0, 0.0, float(expected_viewbox[0]), float(expected_viewbox[1]))
    if _parse_viewbox(root.attrib.get("viewBox")) != expected:
        raise LogoError(f"unexpected viewBox in {path}; expected 0 0 {expected_viewbox[0]} {expected_viewbox[1]}")
    for element in root.iter():
        tag = _local_name(element.tag)
        if tag not in FINAL_ALLOWED_TAGS:
            raise LogoError(f"element {tag!r} is not allowed in {path}")
        _validate_attributes(element, tag, path, final=True)
        if tag in GEOMETRY_TAGS:
            _validate_geometry_color(element, path, monochrome=False)
            if _is_full_canvas_rect(element, expected_viewbox):
                raise LogoError(f"logo must have a transparent background: {path}")
        if tag == "text":
            if not allow_wordmark:
                raise LogoError(f"logo mark must not contain text: {path}")
            if element.attrib.get("fill", "").lower() != SECONDARY_COLOR:
                raise LogoError(f"wordmark text must use {SECONDARY_COLOR} in {path}")


def load_logo_lockup(path: Path) -> tuple[str, float]:
    """Return validated horizontal Logo geometry and its wordmark font size."""
    _validate_final_svg(path, LOCKUP_VIEWBOX, allow_wordmark=True)
    _, root, _ = _read_svg(path)
    lockup = next(
        (
            element
            for element in root.iter()
            if _local_name(element.tag) == "g" and element.attrib.get("id") == "logo-lockup"
        ),
        None,
    )
    wordmarks = [
        element
        for element in root.iter()
        if _local_name(element.tag) == "text"
    ]
    if lockup is None or len(wordmarks) != 1:
        raise LogoError(f"horizontal Logo structure is incomplete in {path}")
    wordmark = wordmarks[0]
    if wordmark.attrib.get("id") != "logo-wordmark":
        raise LogoError(f"horizontal Logo wordmark id is invalid in {path}")
    geometry = "".join(
        ET.tostring(copy.deepcopy(child), encoding="unicode") for child in list(lockup)
    )
    if not geometry:
        raise LogoError(f"horizontal Logo contains no geometry in {path}")
    try:
        font_size = float(wordmark.attrib["font-size"])
    except (KeyError, ValueError) as exc:
        raise LogoError(f"Logo wordmark has an invalid font size in {path}") from exc
    return geometry, font_size


def _validate_png(path: Path, expected_size: tuple[int, int]) -> tuple[int, int]:
    width, height, color_type = png_metadata(path)
    if (width, height) != expected_size:
        raise LogoError(f"{path.name} must be {expected_size[0]}x{expected_size[1]}, got {width}x{height}")
    if color_type not in {4, 6}:
        raise LogoError(f"{path.name} must contain an alpha channel")
    return width, height


def validate_logo_outputs(slug: str, output_dir: Path) -> dict[str, object]:
    paths = logo_paths(output_dir, slug)
    _validate_final_svg(paths["mark_svg"], MARK_VIEWBOX, allow_wordmark=False)
    _validate_final_svg(paths["lockup_svg"], LOCKUP_VIEWBOX, allow_wordmark=True)
    load_logo_lockup(paths["lockup_svg"])
    sizes = {
        "mark_png": list(_validate_png(paths["mark_png"], MARK_PNG_SIZE)),
        "lockup_png": list(_validate_png(paths["lockup_png"], LOCKUP_PNG_SIZE)),
    }
    return {
        "slug": slug,
        "outputs": {key: str(path) for key, path in paths.items()},
        "png_sizes": sizes,
        "transparent_pngs": True,
    }


def _write_svg(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")
    try:
        ET.parse(path)
    except ET.ParseError as exc:
        raise LogoError(f"generated invalid SVG {path}: {exc}") from exc


def _ensure_writable_outputs(paths: list[Path], *, force: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not force:
        names = ", ".join(path.name for path in existing)
        raise LogoError(f"refusing to overwrite existing output(s): {names}; use --force")


def command_preview(args: argparse.Namespace) -> int:
    project_name = _single_line(args.project_name, "project_name", max_length=80)
    slug = _slug(args.slug)
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    inputs = [input_dir / filename for filename in CONCEPT_FILENAMES]
    discovered = sorted(path.name for path in input_dir.glob("*.svg"))
    if discovered != list(CONCEPT_FILENAMES):
        expected = ", ".join(CONCEPT_FILENAMES)
        raise LogoError(f"input directory must contain exactly these SVG files: {expected}")
    roots = [validate_candidate(path) for path in inputs]
    sheet_svg = output_dir / f"{slug}-logo-concepts.svg"
    sheet_png = output_dir / f"{slug}-logo-concepts.png"
    _ensure_writable_outputs([sheet_svg, sheet_png], force=args.force)

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="logo-preview-", dir=output_dir) as temp_name:
        temp_dir = Path(temp_name)
        temp_svg = temp_dir / sheet_svg.name
        temp_png = temp_dir / sheet_png.name
        _write_svg(temp_svg, build_contact_sheet(project_name, roots))
        sync_playwright = _load_playwright()
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright)
            try:
                _screenshot(browser, temp_svg, temp_png, CONTACT_SHEET_SIZE, transparent=False)
            finally:
                browser.close()
        width, height, _ = png_metadata(temp_png)
        if (width, height) != CONTACT_SHEET_SIZE:
            raise LogoError(f"contact sheet must be {CONTACT_SHEET_SIZE[0]}x{CONTACT_SHEET_SIZE[1]}")
        for source, destination in ((temp_svg, sheet_svg), (temp_png, sheet_png)):
            if destination.exists():
                destination.unlink()
            shutil.move(str(source), str(destination))

    result = {
        "project_name": project_name,
        "concepts": [str(path) for path in inputs],
        "contact_sheet_svg": str(sheet_svg),
        "contact_sheet_png": str(sheet_png),
        "contact_sheet_size": list(CONTACT_SHEET_SIZE),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_render(args: argparse.Namespace) -> int:
    project_name = _single_line(args.project_name, "project_name", max_length=80)
    slug = _slug(args.slug)
    mark_path = Path(args.mark).resolve()
    root = validate_candidate(mark_path)
    output_dir = Path(args.output_dir).resolve()
    paths = logo_paths(output_dir, slug)
    _ensure_writable_outputs(list(paths.values()), force=args.force)

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="logo-render-", dir=output_dir) as temp_name:
        temp_dir = Path(temp_name)
        temp_paths = logo_paths(temp_dir, slug)

        sync_playwright = _load_playwright()
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright)
            try:
                _write_svg(temp_paths["mark_svg"], build_mark_svg(root, project_name))
                _fit_lockup_svg(browser, temp_paths["lockup_svg"], root, project_name)
                _screenshot(
                    browser,
                    temp_paths["mark_svg"],
                    temp_paths["mark_png"],
                    MARK_PNG_SIZE,
                    transparent=True,
                )
                _screenshot(
                    browser,
                    temp_paths["lockup_svg"],
                    temp_paths["lockup_png"],
                    LOCKUP_PNG_SIZE,
                    transparent=True,
                )
            finally:
                browser.close()
        validate_logo_outputs(slug, temp_dir)
        for key, temp_path in temp_paths.items():
            destination = paths[key]
            if destination.exists():
                destination.unlink()
            shutil.move(str(temp_path), str(destination))

    print(json.dumps(validate_logo_outputs(slug, output_dir), ensure_ascii=False, indent=2))
    return 0


def _raster_target(svg_path: Path) -> tuple[str, str, tuple[int, int], tuple[int, int], bool]:
    if svg_path.name.endswith("-logo-mark.svg"):
        return "-logo-mark.svg", "mark_png", MARK_VIEWBOX, MARK_PNG_SIZE, False
    if svg_path.name.endswith("-logo-lockup.svg"):
        return "-logo-lockup.svg", "lockup_png", LOCKUP_VIEWBOX, LOCKUP_PNG_SIZE, True
    raise LogoError(
        "editable SVG filename must end with '-logo-mark.svg' or '-logo-lockup.svg'"
    )


def command_rasterize(args: argparse.Namespace) -> int:
    svg_path = Path(args.svg).resolve()
    suffix, output_key, expected_viewbox, expected_size, allow_wordmark = _raster_target(
        svg_path
    )
    slug = _slug(svg_path.name[: -len(suffix)])
    _validate_final_svg(
        svg_path,
        expected_viewbox,
        allow_wordmark=allow_wordmark,
    )
    output_dir = Path(args.output_dir).resolve()
    output_path = logo_paths(output_dir, slug)[output_key]
    _ensure_writable_outputs([output_path], force=args.force)

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="logo-raster-", dir=output_dir) as temp_name:
        temp_png = Path(temp_name) / output_path.name
        sync_playwright = _load_playwright()
        with sync_playwright() as playwright:
            browser = _launch_browser(playwright)
            try:
                _screenshot(browser, svg_path, temp_png, expected_size, transparent=True)
            finally:
                browser.close()
        _validate_png(temp_png, expected_size)
        if output_path.exists():
            output_path.unlink()
        shutil.move(str(temp_png), str(output_path))

    result = {
        "svg": str(svg_path),
        "png": str(output_path),
        "png_size": list(_validate_png(output_path, expected_size)),
        "transparent": True,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    slug = _slug(args.slug)
    result = validate_logo_outputs(slug, Path(args.output_dir).resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview concepts and render transparent project Mark and Lockup assets."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview = subparsers.add_parser("preview", help="Validate three concepts and create a contact sheet.")
    preview.add_argument("--project-name", required=True, help="Exact project display name.")
    preview.add_argument("--slug", required=True, help="Lowercase hyphenated repository slug.")
    preview.add_argument("--input-dir", required=True, help="Directory containing concept-a/b/c.svg.")
    preview.add_argument("--output-dir", required=True, help="Temporary contact-sheet output directory.")
    preview.add_argument("--force", action="store_true", help="Replace existing contact-sheet files.")
    preview.set_defaults(func=command_preview)

    render = subparsers.add_parser(
        "render", help="Create Mark and horizontal Lockup SVG/PNG files from an approved concept."
    )
    render.add_argument("--project-name", required=True, help="Exact project display name.")
    render.add_argument("--slug", required=True, help="Lowercase hyphenated repository slug.")
    render.add_argument("--mark", required=True, help="Path to the approved 512x512 mark SVG.")
    render.add_argument("--output-dir", default="assets", help="Output directory (default: assets).")
    render.add_argument("--force", action="store_true", help="Replace existing generated logo files.")
    render.set_defaults(func=command_render)

    rasterize = subparsers.add_parser("rasterize", help="Render one PNG from a manually edited Logo SVG.")
    rasterize.add_argument("svg", help="Path to an editable generated logo SVG.")
    rasterize.add_argument("--output-dir", default="assets", help="Output directory (default: assets).")
    rasterize.add_argument("--force", action="store_true", help="Replace the corresponding PNG file.")
    rasterize.set_defaults(func=command_rasterize)

    validate = subparsers.add_parser("validate", help="Validate the generated Logo SVG and PNG.")
    validate.add_argument("--slug", required=True, help="Lowercase hyphenated repository slug.")
    validate.add_argument("--output-dir", default="assets", help="Output directory (default: assets).")
    validate.set_defaults(func=command_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except LogoError as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
