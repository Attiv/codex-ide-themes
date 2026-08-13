"""Contract tests for the Codex IDE-inspired TextMate themes."""

import contextlib
import io
import plistlib
import re
import tempfile
import unittest
import uuid
import sys
from collections import Counter
from pathlib import Path
from unittest import mock

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIRECTORY = REPOSITORY_ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIRECTORY))

import generate_ide_themes


EXPECTED_THEMES = {
    "codex-xcode-dark",
    "codex-xcode-light",
    "codex-vscode-dark",
    "codex-vscode-light",
    "codex-github-dark",
    "codex-github-light",
    "codex-trae-dark",
    "codex-trae-light",
}

EXPECTED_THEME_ORDER = (
    "codex-xcode-dark",
    "codex-xcode-light",
    "codex-vscode-dark",
    "codex-vscode-light",
    "codex-github-dark",
    "codex-github-light",
    "codex-trae-dark",
    "codex-trae-light",
)

EXPECTED_PRIMARY_COLORS = {
    "codex-xcode-dark": (
        "#1F1F24", "#D9D9D9", "#515B70", "#252B32", "#788896",
        "#FC5FA3", "#FC6A5D", "#D0BF69", "#67B7A4", "#5DD8FF",
    ),
    "codex-xcode-light": (
        "#FFFFFF", "#242424", "#A4CDFF", "#E8F2FF", "#5D6C79",
        "#9B2393", "#C41A16", "#1C00CF", "#316B74", "#0B4F79",
    ),
    "codex-vscode-dark": (
        "#1F1F1F", "#CCCCCC", "#264F78", "#2A2D2E", "#6A9955",
        "#C586C0", "#CE9178", "#B5CEA8", "#DCDCAA", "#4EC9B0",
    ),
    "codex-vscode-light": (
        "#FFFFFF", "#3B3B3B", "#ADD6FF", "#F5F5F5", "#008000",
        "#AF00DB", "#A31515", "#098658", "#795E26", "#267F99",
    ),
    "codex-github-dark": (
        "#0D1117", "#E6EDF3", "#264F78", "#161B22", "#8B949E",
        "#FF7B72", "#A5D6FF", "#79C0FF", "#D2A8FF", "#FFA657",
    ),
    "codex-github-light": (
        "#FFFFFF", "#1F2328", "#B6D7FF", "#F6F8FA", "#57606A",
        "#CF222E", "#0A3069", "#0550AE", "#8250DF", "#953800",
    ),
    "codex-trae-dark": (
        "#0A0B0D", "#EDEFF2", "#154D37", "#121314", "#787D87",
        "#32F08C", "#A0FDE7", "#64B4FF", "#60F2BD", "#A599FF",
    ),
    "codex-trae-light": (
        "#F5F9FE", "#121314", "#BDF5DB", "#EDEFF2", "#646A73",
        "#007A50", "#087E67", "#1759DD", "#007552", "#4C37E6",
    ),
}

PRIMARY_COLOR_FIELDS = (
    "background",
    "foreground",
    "selection",
    "line_highlight",
    "comment",
    "keyword",
    "string",
    "number",
    "function",
    "type_name",
)

COLOR_FIELDS = (
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

REQUIRED_GLOBAL_SETTINGS = {
    "background",
    "caret",
    "foreground",
    "invisibles",
    "lineHighlight",
    "selection",
}

REQUIRED_SCOPE_PREFIXES = {
    "comment",
    "keyword",
    "string",
    "constant.numeric",
    "entity.name.function",
    "entity.name.type",
    "variable",
    "entity.name.tag",
    "entity.other.attribute-name",
    "markup.inserted",
    "markup.deleted",
    "markup.changed",
    "invalid",
}

HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}\Z")


def parse_rendered_theme(palette):
    """Render a palette and parse its plist, accepting text or bytes output."""
    rendered = generate_ide_themes.render_theme(palette)
    if isinstance(rendered, str):
        rendered = rendered.encode("utf-8")
    return plistlib.loads(rendered)


def relative_luminance(color):
    """Return WCAG relative luminance for a six-digit sRGB color."""
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]

    def linearize(channel):
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first, second):
    """Return WCAG contrast ratio for two six-digit sRGB colors."""
    lighter, darker = sorted(
        (relative_luminance(first), relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


class IdeThemeContractTests(unittest.TestCase):
    def test_palette_order_and_length_are_stable(self):
        self.assertEqual(8, len(generate_ide_themes.PALETTES))
        self.assertEqual(
            EXPECTED_THEME_ORDER,
            tuple(palette.name for palette in generate_ide_themes.PALETTES),
        )

    def test_theme_names_are_exactly_the_requested_set(self):
        actual_names = {palette.name for palette in generate_ide_themes.PALETTES}
        self.assertEqual(EXPECTED_THEMES, actual_names)

    def test_every_palette_color_is_six_digit_hex(self):
        for palette in generate_ide_themes.PALETTES:
            for field in COLOR_FIELDS:
                value = getattr(palette, field)
                with self.subTest(theme=palette.name, field=field):
                    self.assertIsInstance(value, str)
                    self.assertRegex(value, HEX_COLOR)

    def test_primary_colors_match_ide_baselines(self):
        for palette in generate_ide_themes.PALETTES:
            actual = tuple(getattr(palette, field) for field in PRIMARY_COLOR_FIELDS)
            with self.subTest(theme=palette.name):
                self.assertEqual(EXPECTED_PRIMARY_COLORS[palette.name], actual)

    def test_theme_uuids_are_deterministic(self):
        for palette in generate_ide_themes.PALETTES:
            expected = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"codex-theme:{palette.name}")
            )
            with self.subTest(theme=palette.name):
                self.assertEqual(expected, parse_rendered_theme(palette)["uuid"])

    def test_token_and_selection_contrast_meets_terminal_floor(self):
        used_roles = {rule.color_role for rule in generate_ide_themes.ROLE_RULES}
        for palette in generate_ide_themes.PALETTES:
            colors = {"foreground": palette.foreground}
            colors.update({role: getattr(palette, role) for role in used_roles})
            for role, color in colors.items():
                with self.subTest(theme=palette.name, role=role):
                    self.assertGreaterEqual(
                        contrast_ratio(color, palette.background), 4.5
                    )
            with self.subTest(theme=palette.name, role="selection"):
                self.assertGreaterEqual(
                    contrast_ratio(palette.foreground, palette.selection), 4.5
                )

    def test_diff_colors_are_distinct_and_readable(self):
        for palette in generate_ide_themes.PALETTES:
            colors = [
                palette.inserted,
                palette.deleted,
                palette.changed,
            ]
            with self.subTest(theme=palette.name):
                self.assertEqual(3, len(set(colors)))
                for color in colors:
                    self.assertGreaterEqual(
                        contrast_ratio(color, palette.background), 4.5
                    )

    def test_every_rendered_document_is_a_valid_plist(self):
        for palette in generate_ide_themes.PALETTES:
            with self.subTest(theme=palette.name):
                document = parse_rendered_theme(palette)
                self.assertIsInstance(document, dict)
                self.assertIsInstance(document.get("name"), str)
                self.assertTrue(document["name"])
                self.assertIsInstance(document.get("uuid"), str)
                self.assertTrue(document["uuid"])
                self.assertIsInstance(document.get("settings"), list)

    def test_global_settings_include_required_terminal_colors(self):
        for palette in generate_ide_themes.PALETTES:
            document = parse_rendered_theme(palette)
            global_entries = [
                entry
                for entry in document.get("settings", [])
                if not entry.get("scope")
            ]
            global_keys = {
                key
                for entry in global_entries
                for key in entry.get("settings", {})
            }
            with self.subTest(theme=palette.name):
                self.assertTrue(global_entries, "theme must have global settings")
                missing = REQUIRED_GLOBAL_SETTINGS - global_keys
                self.assertEqual(set(), missing, f"missing global settings: {missing}")

    def test_required_scope_prefixes_are_covered(self):
        for palette in generate_ide_themes.PALETTES:
            document = parse_rendered_theme(palette)
            scopes = {
                scope.strip()
                for entry in document.get("settings", [])
                for scope in entry.get("scope", "").split(",")
                if scope.strip()
            }
            missing = REQUIRED_SCOPE_PREFIXES - scopes
            with self.subTest(theme=palette.name):
                self.assertEqual(set(), missing)

    def test_scope_strings_are_declared_only_once(self):
        for palette in generate_ide_themes.PALETTES:
            document = parse_rendered_theme(palette)
            scope_counts = Counter(
                scope.strip()
                for entry in document.get("settings", [])
                for scope in entry.get("scope", "").split(",")
                if scope.strip()
            )
            duplicates = {
                scope: count for scope, count in scope_counts.items() if count > 1
            }
            with self.subTest(theme=palette.name):
                self.assertEqual({}, duplicates, f"duplicate scopes: {duplicates}")

    def test_role_rules_are_nonempty_and_scopes_are_globally_unique(self):
        self.assertTrue(generate_ide_themes.ROLE_RULES)
        scope_counts = Counter(
            scope
            for rule in generate_ide_themes.ROLE_RULES
            for scope in rule.scopes
        )
        self.assertEqual(
            {},
            {scope: count for scope, count in scope_counts.items() if count > 1},
        )

    def test_font_styles_and_emphasis_contract(self):
        self.assertTrue(
            all(
                rule.font_style in {None, "italic", "bold", "underline"}
                for rule in generate_ide_themes.ROLE_RULES
            )
        )
        styles_by_name = {
            rule.name: rule.font_style for rule in generate_ide_themes.ROLE_RULES
        }
        self.assertEqual("italic", styles_by_name["Comments"])
        self.assertEqual("bold", styles_by_name["Types and classes"])
        self.assertEqual("bold", styles_by_name["Headings"])
        self.assertEqual("underline", styles_by_name["Links"])

    def test_configuration_rejects_unsupported_font_style(self):
        invalid_rule = generate_ide_themes.RoleRule(
            "Invalid style", ("test.invalid-style",), "foreground", "blink"
        )
        with mock.patch.object(
            generate_ide_themes,
            "ROLE_RULES",
            generate_ide_themes.ROLE_RULES + (invalid_rule,),
        ):
            with self.assertRaisesRegex(ValueError, "invalid font style"):
                generate_ide_themes.validate_configuration(False)

    def test_nonempty_configuration_validates(self):
        self.assertIsNone(generate_ide_themes.validate_configuration(False))

    def test_check_cli_reports_all_eight_themes(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = generate_ide_themes.main(["--check"])
        self.assertEqual(0, exit_code)
        self.assertEqual("Validated 8 theme(s).\n", output.getvalue())

    def test_install_and_backup_smoke_test_uses_temporary_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory)
            installed = generate_ide_themes.install_themes(output_dir)
            self.assertEqual(8, len(installed))
            first_contents = {}
            for path in installed:
                first_contents[path.name] = path.read_bytes()
                self.assertIsInstance(plistlib.loads(first_contents[path.name]), dict)

            reinstalled = generate_ide_themes.install_themes(output_dir)
            self.assertEqual(installed, reinstalled)
            for path in installed:
                backups = list(output_dir.glob(f"{path.name}.bak-*"))
                self.assertEqual(1, len(backups), path.name)
                self.assertEqual(first_contents[path.name], backups[0].read_bytes())

    def test_committed_themes_match_generator_output(self):
        theme_directory = REPOSITORY_ROOT / "themes"
        expected_names = {
            f"{palette.name}.tmTheme"
            for palette in generate_ide_themes.PALETTES
        }
        actual_names = {
            path.name for path in theme_directory.glob("*.tmTheme")
        }
        self.assertEqual(expected_names, actual_names)
        for palette in generate_ide_themes.PALETTES:
            path = theme_directory / f"{palette.name}.tmTheme"
            with self.subTest(theme=palette.name):
                self.assertEqual(
                    generate_ide_themes.render_theme(palette),
                    path.read_bytes(),
                )

    def test_background_luminance_matches_appearance(self):
        for palette in generate_ide_themes.PALETTES:
            luminance = relative_luminance(palette.background)
            with self.subTest(theme=palette.name, appearance=palette.appearance):
                if palette.appearance == "dark":
                    self.assertLess(luminance, 0.08)
                elif palette.appearance == "light":
                    self.assertGreater(luminance, 0.85)
                else:
                    self.fail(f"unsupported appearance: {palette.appearance!r}")

    def test_output_filenames_are_unique(self):
        filenames = [
            f"{palette.name}.tmTheme" for palette in generate_ide_themes.PALETTES
        ]
        duplicates = {
            filename: count
            for filename, count in Counter(filenames).items()
            if count > 1
        }
        self.assertEqual({}, duplicates, f"duplicate filenames: {duplicates}")


if __name__ == "__main__":
    unittest.main()
