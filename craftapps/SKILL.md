---
name: craftapps
description: Drive the Craft desktop apps through their JSON control ports, either as a live copilot in the window the person is using or independently, and teach them to do the same by hand. Covers VectorCraft (vector graphics, Illustrator-style), SolidCraft (parametric 3D CAD, Fusion-style), PhotoCraft (raster editing, Photoshop-style) and DesignCraft (page layout, InDesign-style), and moving work between them. Use whenever the person mentions any of these apps, asks to draw, model, retouch, lay out, revise or export something in them, asks for help with what they have open, or asks how to do something in them or in the apps they resemble.
---

# Craft apps

Each Craft app exposes all its operations over a JSON control channel on `127.0.0.1`. One client, `scripts/craft.py`,
drives them all; each app's details live in `apps/<app>/`. **Read this file, then the `APP.md` of the app you're using.**

| App | Like | Read | Files |
|---|---|---|---|
| VectorCraft | Illustrator | `apps/vectorcraft/APP.md` | `.vectorcraft`, SVG, PDF, `.ai`, EPS, DXF |
| SolidCraft | Fusion | `apps/solidcraft/APP.md` | `.sc`, STEP, IGES, STL, 3MF, OBJ, URDF, DXF |
| PhotoCraft | Photoshop | `apps/photocraft/APP.md` | `.pcraft`, PSD, PNG, JPEG, TIFF, WebP, EXR |
| DesignCraft | InDesign | `apps/designcraft/APP.md` | `.designcraft`, IDML, INDD (read), PDF, EPUB |

Below, `craft.py` means `uv run <this skill's folder>/scripts/craft.py`.

## 1. Connect

```bash
craft.py apps                  # which apps are installed and running, and on what port
craft.py solidcraft status     # what the person has open: document, unsaved changes, tool, selection, dialog
craft.py solidcraft launch     # start it with its control channel (reports it if already running)
```

- **Running without a port:** only SolidCraft opens its port by default. Any other app started from the Dock has none, and a
  running app ignores new arguments. The client says so. Ask the person to save and quit it before relaunching: never kill it.
- **uv missing** (`command -v uv` fails): tell them the skill uses uv and **ask before installing**. On a yes, run
  `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS, Linux) or
  `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows), or `brew install uv` if they
  prefer. It lands in `~/.local/bin`. If they decline, `python3 scripts/craft.py` works: only `compare.py` needs uv.
- **File access:** PhotoCraft refuses paths outside the folders given at launch. `launch` allows the home folder;
  `--roots DIR` narrows it. `--isolated` starts a throwaway profile on another port, for tests only.

## 2. Pick the mode

| The person… | Mode | How |
|---|---|---|
| is working in the app, says "help me", "this", "here", "what's wrong with…" | **Copilot** | `references/live-copilot.md`: work in their window, on their selection, in turns |
| asks for a whole result ("make a figure of…", "model a…") | **Independent** | In the live app, so they can watch and step in. Build, check, report. Copilot rules still apply to their documents |
| wants many files processed, or there's no display | **Headless** | The app's command-line tool: see "Headless" in its `APP.md` |
| asks "how do I…", or wants to learn | **Teaching** | `references/teaching.md` |

**Default to the live app.** Being able to see and take over the work is the point of this skill; go headless only for batch work or when there's no display.

## 3. Ground rules

- **Their files are theirs.** Opening a file doesn't change it. Write results under a new name (`fig - v4.svg`) unless told to
  overwrite. Plain Save writes back to the original, so save with an explicit new path.
- **Their documents are theirs.** Don't close, revert or edit a document they had open unless that is the request. Check
  `status` before each script: tabs, selection and active document change under you. Say which document you're about to change.
- **Never kill an app.** It can lose unsaved work, and it leaves crash notices. Quit with the app's own `app.quit`, and only apps you started.
- **Don't take focus.** Bring a window forward only when GUI input or a screenshot needs it, and say so first (`craft.py APP front`).
- **Keep edits undoable.** Group them where the app can (section 5), name them, and tell the person how to undo.
- **Check before reporting.** Look at a render or screenshot, read the state back, and report what you couldn't verify.

## 4. Finding any operation

Every app describes itself, and these read the running app, so they match its version. **Don't guess names.**

```bash
craft.py APP families              # the whole surface: every command family with its size
craft.py APP find fillet           # search ids, labels, menus (--all: parameter docs too; --params: show them)
craft.py APP params solid.fillet   # one command's full parameter doc
craft.py APP how "outline stroke"  # where a person finds it: menu path, ribbon tab, tool, shortcut
craft.py APP run COMMAND '{"k": 1}'   # run it; a wrong key is refused, naming what it takes
craft.py APP call ui.inspect       # any raw control method (also ui.screenshot, ui.pointer, ui.key…)
craft.py APP docs                  # download the app's protocol docs, prints paths: grep them, they're large
```

Error messages name what's needed: read them and correct the call. If a capability seems to be missing, search with `find --all`
and grep the docs before saying so.

From Python: `sys.path.insert(0, "<skill>/scripts"); from craft import Craft; c = Craft("solidcraft")`, then `c.run(...)`, `c.call(...)`,
`c.batch([...])`, `c.seq([...])`, `c.state()`, `c.render(path)`, `c.shot(path)`, `c.open(path)`, `c.save(path)`, `c.export(path)`.

## 5. Doing several things at once

The apps differ, so `c.batch` and `c.seq` use what each one offers:

| App | `batch` | On failure | Undo |
|---|---|---|---|
| VectorCraft | `command.batch` | everything rolled back | one step |
| SolidCraft | `engine.batch` | everything rolled back | one step per command; `edit.checkpoint` / `edit.restore_checkpoint` return to a point |
| DesignCraft | steps one by one; `script.run {text}` checks all commands first and takes `$N.path` references | stops at the failure | one step per command |
| PhotoCraft | steps one by one (`batch` exists only in `photocraft-cli serve`) | steps undone by `craft.py` | one history state per command; `history.newSnapshot` marks a point |

`c.seq` also lets a step use an earlier result: `{"id": "$0.id"}`.

## 6. Checking your work

```bash
craft.py APP render out.png        # the document's own pixels, without the UI (SolidCraft: the model, in the window's theme)
craft.py APP shot win.png          # the whole window, as the person sees it (fails if the window is covered: use render)
craft.py APP tree                  # outline: layers, objects, pages or features
uv run <skill>/scripts/compare.py a.png b.png --pt-scale 2 --blur 1.5 --out diff.png
```

Read the images you produce. `compare.py` gives the share of changed pixels and where, which suits revisions against a target.

## 7. Moving work between apps

| From → to | Route |
|---|---|
| SolidCraft → PhotoCraft or DesignCraft | `craft.py solidcraft render x.png`, with the view set first |
| PhotoCraft → DesignCraft | `craft.py photocraft export x.png` (a flattened copy), then `file.place` |
| VectorCraft → DesignCraft | export PDF or SVG, then `file.place`; details in `apps/designcraft/APP.md` |
| LaTeX → VectorCraft or DesignCraft | `scripts/latex_math.py --app …`: math, mhchem and siunitx as vector art on a baseline |

Check the result in the target app, not only that the export succeeded.

## 8. Adding an app

The suite has more apps (DeckCraft, WordCraft, PdfCraft, SoundCraft…). `references/adding-an-app.md` covers it: a manifest, an adapter,
a sweep with `scripts/sweep.py`, then an `APP.md` from real tasks.
