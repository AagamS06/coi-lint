# Design — coi-lint

The look borrows from a site-safety clipboard: dark slate, hi-vis amber accent, clear pass/warn/fail colours. Used by the terminal output (ANSI), the Phase 2 HTML report and launch media.

## Colour palette

| Token | Dark (default) | Light | Use |
|-------|----------------|-------|-----|
| `--bg` | `#0E1216` | `#F7F5F0` | page background |
| `--surface` | `#161C22` | `#FFFFFF` | cards, panels |
| `--border` | `#26303A` | `#E2DED5` | dividers |
| `--text` | `#E8ECEF` | `#14181C` | primary text |
| `--muted` | `#8A96A3` | `#5D6670` | secondary text |
| `--accent` | `#F5B83D` | `#B97800` | brand, focus, links |
| `--pass` | `#3FB97A` | `#1E7F4F` | ✓ compliant |
| `--warn` | `#E8A23A` | `#9A5B00` | ! expiring / not yet effective |
| `--fail` | `#F0605A` | `#C2302A` | ✗ deficient |

Terminal mapping: pass = ANSI green, warn = yellow, fail = red; never rely on colour alone (✓ ! ✗ glyphs are always printed).

## Themes
- **Dark** is the default for the HTML report and media.
- **Light** follows `prefers-color-scheme: light`; tokens swap 1:1.
- Accent on `--bg` meets ≥ 4.5:1 in both themes (`#F5B83D` on `#0E1216` ≈ 10:1; `#B97800` on `#F7F5F0` ≈ 4.6:1).

## Typography
- UI: **Inter** (400, 600, 800) — `https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap`
- Code / findings: **JetBrains Mono** (400, 600)

| Step | Size / line-height | Use |
|------|--------------------|-----|
| Display | 56 / 64, 800 | report title, hero |
| H1 | 36 / 44, 800 | section titles |
| H2 | 24 / 32, 600 | card titles |
| Body | 16 / 24, 400 | text |
| Small | 13 / 20, 400 | captions, rule ids |
| Mono | 14 / 22 | findings lines |

## Spacing
4-px base: `4, 8, 12, 16, 24, 32, 48, 64`. Card padding 24; gap between findings 8; radius 12 (cards), 6 (chips).

## Components
- **Verdict badge**: pill, 6-px radius, background = status colour at 16% opacity, text = status colour, label `DEFICIENT` / `COMPLIANT WITH WARNINGS` / `COMPLIANT`.
- **Finding row**: glyph (✓ ! ✗) · rule id chip (mono, muted) · message. Fails sorted first in the HTML report.
- **Coverage card**: coverage name, policy number, dates bar (effective → expires, today marker), limits table.
- **Expiry timeline**: horizontal bar per insured, amber band for the warning window.
- **Letter preview**: mono block with a "Draft — review before sending" banner.

## Accessibility
- WCAG 2.1 AA contrast for all text; status always shown by glyph + label, not colour only.
- Keyboard: every interactive element reachable with Tab, visible 2-px accent focus ring.
- Respect `prefers-reduced-motion`; no auto-playing animation in the report.
- Terminal: `--no-color` and automatic colour off when not a TTY; output readable by screen readers (no box-drawing tables in plain mode).
