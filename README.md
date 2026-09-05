# Codex IDE Themes

Eight IDE-inspired light and dark themes for the Codex CLI. The pack uses
TextMate scopes, terminal-friendly contrast, deterministic UUIDs, and a small
dependency-free Python generator.

Optional extra: [Codex token/cache usage Hook (中文使用说明)](hooks/cache-meter/README.md)
prints a per-turn token summary after Codex finishes a response. It is installed
separately; `./install.sh` still installs only themes.

## Themes

| Style | Dark | Light |
| --- | --- | --- |
| Xcode | `codex-xcode-dark` | `codex-xcode-light` |
| VS Code | `codex-vscode-dark` | `codex-vscode-light` |
| GitHub | `codex-github-dark` | `codex-github-light` |
| TRAE | `codex-trae-dark` | `codex-trae-light` |

## Install

```bash
git clone https://github.com/Attiv/codex-ide-themes.git
cd codex-ide-themes
./install.sh
```

The installer writes the themes to `${CODEX_HOME:-$HOME/.codex}/themes`. It
creates timestamped backups before replacing existing files.

Start Codex, enter `/theme`, then search for `codex-` and select a theme.

### Manual installation

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/themes"
cp themes/*.tmTheme "${CODEX_HOME:-$HOME/.codex}/themes/"
```

## Development

Validate the palette and rendered plist documents:

```bash
./install.sh --check
```

Regenerate the committed theme files:

```bash
python3 tools/generate_ide_themes.py --output themes --no-backup
```

Run the test suite:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

For the intended appearance, use a terminal with 24-bit color support. If you
deliberately set the standard `NO_COLOR` environment variable, the terminal UI
may suppress color output.

## Attribution

These are unofficial themes inspired by the visual language of Xcode, Visual
Studio Code, GitHub, and TRAE. This project is not affiliated with or endorsed
by Apple, Microsoft, GitHub, ByteDance, TRAE, or OpenAI. All product names and
trademarks belong to their respective owners.

## License

[MIT](LICENSE)
