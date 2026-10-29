# coi-lint — launch video plan

**Angle:** the boring, error-prone job (reading insurance certificates by eye) done in one command, with the real CLI output as the star.
**Hook (0–3.4s):** a fictional certificate card next to "Checking insurance certificates by eye?" — two rows light up red ("✗ required", "✗ needs $5,000,000") → "Two misses here."
**Highlights:** real terminal run of `coi-lint check` (all 14 real findings, DEFICIENT verdict); real `--format letter` deficiency draft.
**Punchline:** coi-lint · 8 rules · offline · MIT licensed · repo URL · roadmap line (PDF input and folder sweeps are labelled as roadmap).
**Tone:** default (punchy, clean). Format 1920×1080, 30 fps, 20.0 s, with music.

## Storyboard (sums to 20.0s)
| # | Time | Scene |
|---|------|-------|
| 1 | 0.00–3.40 | Hook: certificate card + headline; misses highlighted at 1.95s / 2.2s |
| – | 3.40–3.65 | dip through background |
| 2 | 3.65–6.55 | Reveal: `coi-lint` wordmark with blinking amber caret, tagline "Linting for certificates of insurance.", "Your requirements in YAML → pass · warn · fail" |
| 3 | 6.80–12.60 | Terminal: command typed, 14 findings tick in (0.2s apart), DEFICIENT badge "2 fail, 1 warn, 11 pass" |
| 4 | 12.85–16.45 | "Deficiency letter, drafted." + real letter draft (3 bullets), "Draft · review before sending" |
| 5 | 16.70–20.00 | Outro card |

## Honesty notes
- All terminal and letter text is the real output of `coi-lint check examples/cert_sample.json --rules examples/requirements.yaml --today 2026-10-29` from the repo.
- Company/agency names are the repo's fictional sample data (marked "(fictional)"). No real people, customers, metrics or logos. No YC company is shown or implied as a user.
- Planned features appear only as "Roadmap: PDF input and folder sweeps".

## Visual identity (as actually used in the video's CSS)
- Background colour: `#0E1216` (with a soft amber radial glow top-left `rgba(245,184,61,.10)`, faint green glow bottom-right and a dark vignette)
- Card / surface colour: `#161C22` (border `#26303A`; terminal body `#0A0D10`)
- Text colour: `#E8ECEF`
- Muted text colour: `#8A96A3`
- Accent colour: `#F5B83D`
- Status: pass `#3FB97A`, warn `#E8A23A`, fail `#F0605A`
- Font family: **Inter** (headings/UI) + JetBrains Mono (terminal, wordmark)
- Google Fonts CSS URL: https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&family=JetBrains+Mono:wght@400;600;700&display=swap

## Sound
- Key and mode: **A minor** (progression Am – F – C – G, 100 bpm, 2.4 s per chord)
- Soft pad from 0s; bass + plucked arpeggio from the reveal; soft kick + hats under the terminal and letter scenes.
- SFX in key: soft whooshes on each scene change, two low E notes on the hook highlights, A/E chime on the reveal, pitched ticks for each finding (lower for ✗), A–C chime on the verdict, ticks on letter bullets, A–E–A chime on the outro. Soft-clipped and normalised to −1 dBFS.

## Deliverables
brag.mp4 (poster baked in as frame 0), brag.jpg (poster, frame at 11.9s), brag-thumb.jpg (1280×720), brag-share-copy.txt, brag-plan.md.
Note: the brag skill names files after the project (coi-lint.*); this run uses brag.* because the weekly task's later steps expect those names.
