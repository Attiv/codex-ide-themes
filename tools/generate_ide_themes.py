#!/usr/bin/env python3
"""Generate and install Codex TextMate themes.

The palette table and TextMate scope map are intentionally data-driven so new
themes can be added without changing the renderer or installer. Each theme file
is replaced atomically; installing a multi-theme pack is not transactional.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import os
import plistlib
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
from typing import Literal, Sequence
import uuid


ColorRole = Literal[
    "background",
    "foreground",
    "selection",
    "line_highlight",
    "comment",
    "keyword",
    "storage",
    "string",
    "number",
    "constant",
    "function",
    "type_name",
    "variable",
    "property_name",
    "tag",
    "attribute",
    "regexp",
    "escape",
    "link",
    "inserted",
    "deleted",
    "changed",
    "invalid",
]

FontStyle = Literal["italic", "bold", "underline"]

COLOR_FIELDS: tuple[ColorRole, ...] = (
    "background",
    "foreground",
    "selection",
    "line_highlight",
    "comment",
    "keyword",
    "storage",
    "string",
    "number",
    "constant",
    "function",
    "type_name",
    "variable",
    "property_name",
    "tag",
    "attribute",
    "regexp",
    "escape",
    "link",
    "inserted",
    "deleted",
    "changed",
    "invalid",
)

_SAFE_THEME_NAME = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}\Z")


@dataclass(frozen=True)
class ThemePalette:
    """All semantic colors required to render one Codex theme."""

    name: str
    display_name: str
    appearance: Literal["dark", "light"]
    background: str
    foreground: str
    selection: str
    line_highlight: str
    comment: str
    keyword: str
    storage: str
    string: str
    number: str
    constant: str
    function: str
    type_name: str
    variable: str
    property_name: str
    tag: str
    attribute: str
    regexp: str
    escape: str
    link: str
    inserted: str
    deleted: str
    changed: str
    invalid: str

    def __post_init__(self) -> None:
        if self.appearance not in ("dark", "light"):
            raise ValueError("appearance must be 'dark' or 'light'")


@dataclass(frozen=True)
class RoleRule:
    """Map one or more TextMate scopes to a palette color role."""

    name: str
    scopes: tuple[str, ...]
    color_role: ColorRole
    font_style: FontStyle | None = None


PALETTES: tuple[ThemePalette, ...] = (
    ThemePalette(
        name="codex-xcode-dark",
        display_name="Codex Xcode Dark",
        appearance="dark",
        background="#1F1F24",
        foreground="#D9D9D9",
        selection="#515B70",
        line_highlight="#252B32",
        comment="#788896",
        keyword="#FC5FA3",
        storage="#FD8F3F",
        string="#FC6A5D",
        number="#D0BF69",
        constant="#D0BF69",
        function="#67B7A4",
        type_name="#5DD8FF",
        variable="#D9D9D9",
        property_name="#41A1C0",
        tag="#FC5FA3",
        attribute="#D0A8FF",
        regexp="#FC6A5D",
        escape="#D0BF69",
        link="#D0A8FF",
        inserted="#5FB68B",
        deleted="#FF6B68",
        changed="#6CB6FF",
        invalid="#FF4D4F",
    ),
    ThemePalette(
        name="codex-xcode-light",
        display_name="Codex Xcode Light",
        appearance="light",
        background="#FFFFFF",
        foreground="#242424",
        selection="#A4CDFF",
        line_highlight="#E8F2FF",
        comment="#5D6C79",
        keyword="#9B2393",
        storage="#643820",
        string="#C41A16",
        number="#1C00CF",
        constant="#1C00CF",
        function="#316B74",
        type_name="#0B4F79",
        variable="#242424",
        property_name="#0B4F79",
        tag="#9B2393",
        attribute="#3900A0",
        regexp="#C41A16",
        escape="#1C00CF",
        link="#3900A0",
        inserted="#187E3D",
        deleted="#C41A16",
        changed="#0058A3",
        invalid="#D12F1B",
    ),
    ThemePalette(
        name="codex-vscode-dark",
        display_name="Codex VS Code Dark",
        appearance="dark",
        background="#1F1F1F",
        foreground="#CCCCCC",
        selection="#264F78",
        line_highlight="#2A2D2E",
        comment="#6A9955",
        keyword="#C586C0",
        storage="#569CD6",
        string="#CE9178",
        number="#B5CEA8",
        constant="#4FC1FF",
        function="#DCDCAA",
        type_name="#4EC9B0",
        variable="#9CDCFE",
        property_name="#9CDCFE",
        tag="#569CD6",
        attribute="#9CDCFE",
        regexp="#D16969",
        escape="#D7BA7D",
        link="#569CD6",
        inserted="#4EC9B0",
        deleted="#F44747",
        changed="#569CD6",
        invalid="#F44747",
    ),
    ThemePalette(
        name="codex-vscode-light",
        display_name="Codex VS Code Light",
        appearance="light",
        background="#FFFFFF",
        foreground="#3B3B3B",
        selection="#ADD6FF",
        line_highlight="#F5F5F5",
        comment="#008000",
        keyword="#AF00DB",
        storage="#0000FF",
        string="#A31515",
        number="#098658",
        constant="#0070C1",
        function="#795E26",
        type_name="#267F99",
        variable="#001080",
        property_name="#001080",
        tag="#800000",
        attribute="#E50000",
        regexp="#811F3F",
        escape="#EE0000",
        link="#005FB8",
        inserted="#008000",
        deleted="#C72E0F",
        changed="#005FB8",
        invalid="#CD3131",
    ),
    ThemePalette(
        name="codex-github-dark",
        display_name="Codex GitHub Dark",
        appearance="dark",
        background="#0D1117",
        foreground="#E6EDF3",
        selection="#264F78",
        line_highlight="#161B22",
        comment="#8B949E",
        keyword="#FF7B72",
        storage="#FF7B72",
        string="#A5D6FF",
        number="#79C0FF",
        constant="#79C0FF",
        function="#D2A8FF",
        type_name="#FFA657",
        variable="#FFA657",
        property_name="#79C0FF",
        tag="#7EE787",
        attribute="#79C0FF",
        regexp="#A5D6FF",
        escape="#79C0FF",
        link="#58A6FF",
        inserted="#7EE787",
        deleted="#FF7B72",
        changed="#58A6FF",
        invalid="#F85149",
    ),
    ThemePalette(
        name="codex-github-light",
        display_name="Codex GitHub Light",
        appearance="light",
        background="#FFFFFF",
        foreground="#1F2328",
        selection="#B6D7FF",
        line_highlight="#F6F8FA",
        comment="#57606A",
        keyword="#CF222E",
        storage="#CF222E",
        string="#0A3069",
        number="#0550AE",
        constant="#0550AE",
        function="#8250DF",
        type_name="#953800",
        variable="#953800",
        property_name="#0550AE",
        tag="#116329",
        attribute="#0550AE",
        regexp="#0A3069",
        escape="#0550AE",
        link="#0969DA",
        inserted="#116329",
        deleted="#CF222E",
        changed="#0969DA",
        invalid="#A40E26",
    ),
    ThemePalette(
        name="codex-trae-dark",
        display_name="Codex TRAE Dark",
        appearance="dark",
        background="#0A0B0D",
        foreground="#EDEFF2",
        selection="#154D37",
        line_highlight="#121314",
        comment="#787D87",
        keyword="#32F08C",
        storage="#0FDC78",
        string="#A0FDE7",
        number="#64B4FF",
        constant="#64B4FF",
        function="#60F2BD",
        type_name="#A599FF",
        variable="#FFB86B",
        property_name="#60F2BD",
        tag="#32F08C",
        attribute="#64B4FF",
        regexp="#A0FDE7",
        escape="#FFB86B",
        link="#0FDC78",
        inserted="#32D583",
        deleted="#FF6B7A",
        changed="#64B4FF",
        invalid="#FF4D64",
    ),
    ThemePalette(
        name="codex-trae-light",
        display_name="Codex TRAE Light",
        appearance="light",
        background="#F5F9FE",
        foreground="#121314",
        selection="#BDF5DB",
        line_highlight="#EDEFF2",
        comment="#646A73",
        keyword="#007A50",
        storage="#007C60",
        string="#087E67",
        number="#1759DD",
        constant="#1759DD",
        function="#007552",
        type_name="#4C37E6",
        variable="#B34700",
        property_name="#087E67",
        tag="#008257",
        attribute="#1759DD",
        regexp="#087E67",
        escape="#B34700",
        link="#00724B",
        inserted="#006F55",
        deleted="#C8324B",
        changed="#1759DD",
        invalid="#B4233A",
    ),
)


ROLE_RULES: tuple[RoleRule, ...] = (
    RoleRule(
        "Comments",
        ("comment", "punctuation.definition.comment"),
        "comment",
        "italic",
    ),
    RoleRule(
        "Keywords",
        ("keyword", "keyword.control", "keyword.operator.word"),
        "keyword",
    ),
    RoleRule(
        "Storage and preprocessor",
        ("storage", "storage.type", "storage.modifier", "meta.preprocessor"),
        "storage",
    ),
    RoleRule(
        "Strings",
        ("string", "string.quoted", "string.unquoted"),
        "string",
    ),
    RoleRule("Numbers", ("constant.numeric",), "number"),
    RoleRule(
        "Constants",
        ("constant.language", "constant.character"),
        "constant",
    ),
    RoleRule(
        "Functions",
        ("entity.name.function", "support.function", "meta.function-call"),
        "function",
    ),
    RoleRule(
        "Types and classes",
        ("entity.name.type", "entity.name.class", "support.type", "support.class"),
        "type_name",
        "bold",
    ),
    RoleRule(
        "Variables and parameters",
        ("variable", "entity.name.variable", "variable.parameter"),
        "variable",
    ),
    RoleRule(
        "Properties",
        (
            "variable.other.property",
            "support.type.property-name",
            "meta.object-literal.key",
        ),
        "property_name",
    ),
    RoleRule(
        "Tags",
        ("entity.name.tag", "entity.name.tag.html", "entity.name.tag.xml"),
        "tag",
    ),
    RoleRule(
        "Attributes",
        ("entity.other.attribute-name", "entity.other.attribute-name.html"),
        "attribute",
    ),
    RoleRule("Regular expressions", ("string.regexp", "constant.regexp"), "regexp"),
    RoleRule(
        "Escapes and embedded sections",
        ("constant.character.escape", "punctuation.section.embedded"),
        "escape",
    ),
    RoleRule(
        "Links",
        ("markup.underline.link", "string.other.link"),
        "link",
        "underline",
    ),
    RoleRule("Headings", ("markup.heading",), "link", "bold"),
    RoleRule("Inline code", ("markup.inline.raw",), "string"),
    RoleRule("Bold markup", ("markup.bold",), "foreground", "bold"),
    RoleRule("Italic markup", ("markup.italic",), "foreground", "italic"),
    RoleRule(
        "Inserted diff",
        ("markup.inserted", "meta.diff.range.inserted"),
        "inserted",
    ),
    RoleRule(
        "Deleted diff",
        ("markup.deleted", "meta.diff.range.deleted"),
        "deleted",
    ),
    RoleRule(
        "Changed diff",
        ("markup.changed", "meta.diff.header"),
        "changed",
    ),
    RoleRule(
        "Invalid and deprecated",
        ("invalid", "invalid.illegal", "invalid.deprecated"),
        "invalid",
    ),
)


def validate_configuration(allow_empty: bool = True) -> None:
    """Validate palette and scope configuration before rendering or writing."""

    if not PALETTES and not allow_empty:
        raise ValueError("configuration must contain at least one theme palette")

    names: set[str] = set()
    for palette in PALETTES:
        if not palette.name or not _SAFE_THEME_NAME.fullmatch(palette.name):
            raise ValueError(
                f"theme name {palette.name!r} must be a non-empty safe slug"
            )
        if palette.name in names:
            raise ValueError(f"duplicate theme name: {palette.name!r}")
        names.add(palette.name)
        if not palette.display_name.strip():
            raise ValueError(f"theme {palette.name!r} has an empty display name")
        if palette.appearance not in ("dark", "light"):
            raise ValueError(
                f"theme {palette.name!r} has invalid appearance "
                f"{palette.appearance!r}"
            )
        for color_field in COLOR_FIELDS:
            color = getattr(palette, color_field)
            if not isinstance(color, str) or not _HEX_COLOR.fullmatch(color):
                raise ValueError(
                    f"theme {palette.name!r} color {color_field!r} must be #RRGGBB"
                )

    valid_color_roles = set(COLOR_FIELDS)
    declared_scopes: set[str] = set()
    for rule in ROLE_RULES:
        if not isinstance(rule, RoleRule):
            raise ValueError(f"invalid role rule: {rule!r}")
        if not rule.name.strip():
            raise ValueError("role rule name must be non-empty")
        if not rule.scopes:
            raise ValueError(f"role rule {rule.name!r} must declare a scope")
        if rule.font_style not in (None, "italic", "bold", "underline"):
            raise ValueError(
                f"role rule {rule.name!r} has invalid font style "
                f"{rule.font_style!r}"
            )
        if rule.color_role not in valid_color_roles:
            raise ValueError(
                f"role rule {rule.name!r} has invalid color role "
                f"{rule.color_role!r}"
            )
        for scope in rule.scopes:
            normalized_scope = scope.strip() if isinstance(scope, str) else ""
            if not normalized_scope:
                raise ValueError(f"role rule {rule.name!r} contains an empty scope")
            if normalized_scope in declared_scopes:
                raise ValueError(f"duplicate scope: {normalized_scope!r}")
            declared_scopes.add(normalized_scope)


def token_rule(
    name: str,
    scopes: tuple[str, ...],
    foreground: str,
    font_style: str | None = None,
) -> dict[str, object]:
    """Build one TextMate token-color rule."""

    settings = {"foreground": foreground}
    if font_style:
        settings["fontStyle"] = font_style
    return {
        "name": name,
        "scope": ", ".join(scopes),
        "settings": settings,
    }


def theme_document(palette: ThemePalette) -> dict[str, object]:
    """Return the plist-compatible TextMate document for *palette*."""

    global_settings = {
        "settings": {
            "background": palette.background,
            "caret": palette.foreground,
            "foreground": palette.foreground,
            "invisibles": palette.comment,
            "lineHighlight": palette.line_highlight,
            "selection": palette.selection,
        }
    }
    semantic_rules = [
        token_rule(
            rule.name,
            rule.scopes,
            getattr(palette, rule.color_role),
            rule.font_style,
        )
        for rule in ROLE_RULES
    ]
    return {
        "name": palette.display_name,
        "settings": [global_settings, *semantic_rules],
        "uuid": str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"codex-theme:{palette.name}")
        ),
    }


def render_theme(palette: ThemePalette) -> bytes:
    """Render *palette* as an XML property list."""

    return plistlib.dumps(
        theme_document(palette),
        fmt=plistlib.FMT_XML,
        sort_keys=False,
    )


def _backup_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _fsync_directory(directory: Path) -> None:
    """Best-effort directory sync for platforms that support it."""

    descriptor: int | None = None
    try:
        descriptor = os.open(
            directory,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _write_exclusive_temporary(
    directory: Path,
    prefix: str,
    content: bytes,
) -> Path:
    """Write and fsync a process-owned random temporary file."""

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=prefix,
            suffix=".tmp",
            dir=directory,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        return temporary_path
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _copy_target_to_temporary(target: Path) -> Path:
    """Copy the current target to an fsynced, exclusive temporary file."""

    source_descriptor: int | None = None
    temporary_path: Path | None = None
    try:
        source_descriptor = os.open(
            target,
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        )
        if not stat.S_ISREG(os.fstat(source_descriptor).st_mode):
            raise ValueError(
                f"refusing to back up non-regular target: {target}"
            )
        source = os.fdopen(source_descriptor, "rb")
        source_descriptor = None
        with source, tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=f".{target.name}.backup-",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            shutil.copyfileobj(source, temporary)
            temporary.flush()
            os.fsync(temporary.fileno())
        return temporary_path
    except BaseException:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    finally:
        if source_descriptor is not None:
            os.close(source_descriptor)


def _publish_backup(target: Path, temporary_backup: Path) -> Path:
    """Publish a backup atomically without overwriting an existing candidate."""

    base = target.with_name(f"{target.name}.bak-{_backup_timestamp()}")
    counter = 0
    while True:
        candidate = (
            base if counter == 0 else base.with_name(f"{base.name}-{counter}")
        )
        try:
            os.link(
                temporary_backup,
                candidate,
                follow_symlinks=False,
            )
        except FileExistsError:
            counter += 1
            continue
        temporary_backup.unlink()
        _fsync_directory(target.parent)
        return candidate


def _render_validated_pack() -> list[tuple[ThemePalette, bytes]]:
    """Render and parse every theme before installation changes any target."""

    validate_configuration(allow_empty=True)
    rendered_pack: list[tuple[ThemePalette, bytes]] = []
    for palette in PALETTES:
        try:
            rendered = render_theme(palette)
            plistlib.loads(rendered)
        except Exception as error:
            raise ValueError(
                f"theme {palette.name!r} failed render validation: {error}"
            ) from error
        rendered_pack.append((palette, rendered))
    return rendered_pack


def install_themes(
    output_dir: Path,
    backup_existing: bool = True,
) -> list[Path]:
    """Install configured themes with per-file atomic replacement.

    The entire theme pack is deliberately not transactional: an I/O failure may
    happen after an earlier theme was installed successfully.
    """

    output_dir = Path(output_dir).expanduser()
    rendered_pack = _render_validated_pack()
    output_dir.mkdir(parents=True, exist_ok=True)
    installed: list[Path] = []

    for palette, rendered in rendered_pack:
        target = output_dir / f"{palette.name}.tmTheme"
        theme_temporary: Path | None = None
        backup_temporary: Path | None = None
        try:
            theme_temporary = _write_exclusive_temporary(
                output_dir,
                f".{target.name}.",
                rendered,
            )

            if backup_existing:
                try:
                    backup_temporary = _copy_target_to_temporary(target)
                except FileNotFoundError:
                    pass
                else:
                    _publish_backup(target, backup_temporary)
                    backup_temporary = None

            theme_temporary.replace(target)
            theme_temporary = None
            _fsync_directory(output_dir)
            installed.append(target)
        except Exception as error:
            raise RuntimeError(
                f"failed to install theme {palette.name!r} at {target}: {error}"
            ) from error
        finally:
            if theme_temporary is not None:
                theme_temporary.unlink(missing_ok=True)
            if backup_temporary is not None:
                backup_temporary.unlink(missing_ok=True)

    return installed


def _validate_themes() -> int:
    return len(_render_validated_pack())


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate IDE-inspired TextMate themes for Codex CLI."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("~/.codex/themes"),
        help="installation directory (default: ~/.codex/themes)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="replace existing theme files without creating backups",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="render and validate themes without writing files",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _argument_parser().parse_args(argv)
    try:
        if args.check:
            count = _validate_themes()
            print(f"Validated {count} theme(s).")
        else:
            installed = install_themes(
                args.output,
                backup_existing=not args.no_backup,
            )
            for installed_path in installed:
                print(f"Installed {installed_path}")
            print(
                f"Installed {len(installed)} theme(s) to "
                f"{args.output.expanduser()}."
            )
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
