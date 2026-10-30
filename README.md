# vectorcraft-skill

An agent skill that drives the
[VectorCraft](https://github.com/storytold/vectorcraft) vector editor (an Illustrator-compatible app) through its
JSON control port. With it, a coding agent can build and revise figures with you, including multi-artboard documents and
LaTeX-typeset math. It can also teach you to do the same steps by hand.

[![Two prompts, one figure: an agent builds a Michaelis–Menten figure in VectorCraft, then a revised v2 on a second artboard](media/demo.gif)](media/demo.mp4)

*Recorded live at ×6 speed with [`demo/record_demo.py`](demo/record_demo.py). The prompts are in
[`demo/prompts`](demo/prompts), the exported files in [`demo/output`](demo/output), and the full-quality
video is [`media/demo.mp4`](media/demo.mp4).*

## Quickstart

1. **Start VectorCraft with its control port.** Quit it first if it's running, because a running app ignores new
   arguments. To use another port, set `VECTORCRAFT_PORT`.
   ```bash
   open -a VectorCraft --args --control 12345                                    # macOS
   vectorcraft --control 12345                                                   # Linux
   "$LOCALAPPDATA/Programs/ArtCraft/VectorCraft/vectorcraft.exe" --control 12345  # Windows (Git Bash)
   ```

2. **Install the skill** by putting the `vectorcraft/` folder in your agent's skills folder (for Claude Code,
   `~/.claude/skills/`; symlink it instead if you want `git pull` to update it).
   ```bash
   git clone https://github.com/hessammehr/vectorcraft-skill
   cp -r vectorcraft-skill/vectorcraft ~/.claude/skills/
   ```

3. **Install [uv](https://docs.astral.sh/uv/)**, which runs the skill's scripts and fetches their dependencies.
   Your agent can do this for you: the skill checks for uv and offers to install it, asking you first.
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh                                     # macOS, Linux
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"  # Windows
   ```

4. **Check the connection.**
   ```bash
   uv run ~/.claude/skills/vectorcraft/scripts/vc.py ping
   ```

Then **ask your agent** for things like:
- *"Open `fig - v2.svg` and make a v3: drop the solvent note, add a 0–30 ms tick axis, export SVG in mm."*
- *"Draw a two-panel schematic of … with the equation typeset in LaTeX and TikZ-style arrows."*
- *"Put v1 and v2 of this figure on separate artboards and export one PDF."*
- *"How would I do that by hand? Show me in the app."*

Typeset math requires a TeX installation (TeX Live or MacTeX). Everything else needs only VectorCraft and uv.
To refresh the generated references after a VectorCraft update, run
`uv run vectorcraft/scripts/build_reference.py`.

## Re-recording the demo

```bash
uv run demo/record_demo.py launch                                  # clean VectorCraft on port 12346
uv run demo/record_demo.py claude rec demo/prompts/*.md --claude claude
uv run demo/record_demo.py compose rec --out media/demo.mp4 --gif media/demo.gif --crop 0,0.08,0.78,0.86
```

`claude` runs each prompt headlessly with the Claude Code CLI (`claude -p`, follow-ups continue the session) while the
window is sampled, and turns the agent's messages into captions. For another agent, use `record` and log captions
with `vc.py note` (see the script's help). Video encoding uses the ffmpeg bundled with `imageio-ffmpeg`.

## License

MIT. The arrow-tip geometry follows PGF/TikZ's arrow definitions. The files `vectorcraft/references/{commands,menus,tools}.md`
are generated from VectorCraft's own command catalogue (VectorCraft is MIT/Apache-2.0).
