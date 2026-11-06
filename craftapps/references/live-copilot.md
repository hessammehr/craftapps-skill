# Live copilot

The person has the app open and is working. You work in the same window, in turns. Every call changes what they see
immediately, and they can undo or take over at any moment. Treat it like sitting at their desk.

## The loop

1. **Look.** `craft.py APP status`. "This", "that" and "here" mean the current selection or the active document. If it's ambiguous,
   a screenshot (`craft.py APP shot`) shows what they see. Don't assume what you saw a minute ago still holds.
2. **Say what you'll do**, in a sentence, naming the object and the document. Skip this for trivial reads.
3. **Act in small, visible, undoable steps,** smallest effect first. Prefer one change they can judge over ten at once.
4. **Check** by reading the state back or looking at a render, then report in a line, including how to undo.
5. **Hand back.** If the next step is theirs, say exactly what to do, then wait: `craft.py APP wait --on selection --timeout 300`
   blocks until they act and prints what changed. Run it in the background if your harness allows it, or ask them to tell you when done.

## How visible should the action be?

Pick the lowest rung that serves the request:

| Rung | When | How |
|---|---|---|
| **Direct command** | They asked for the outcome | `craft.py APP run …`: the result just appears |
| **Prefilled dialog** | They should confirm or adjust values, or it has a preview | Open the real dialog with the values set; they press OK. Commands below |
| **Drive the tool** | Showing how it's done, or the operation is a gesture | Select the tool and send pointer events; they see it happen |
| **They do it** | They're learning, or it needs their judgement | Select the object, open the panel, say what to do, then `wait` and check |

Opening a dialog with values:

- **SolidCraft:** `craft.py solidcraft call ui.start '{"command": "solid.fillet", "params": {...}}'`; the reply says what it's waiting for.
- **PhotoCraft:** `craft.py photocraft call ui.menu.invoke '{"id": "filter.blur.gaussianBlur"}'`.
- **DesignCraft:** `craft.py designcraft call ui.dialog.open '{"id": "paragraphStyleOptions", "fields": {...}}'`, or `ui.menu.invoke {command}`.
- **VectorCraft:** `craft.py vectorcraft run ui.paramDialog '{"command": "object.align", "params": {...}}'`, or `tool.options {tool}`.

Then, in any app: `craft.py APP dialog` (read it), `dialog set '{"field": value}'`, `dialog ok`, `dialog cancel`. A dialog you open
is theirs too: leave it open if they're to decide, and close it if they decline.

**SolidCraft's agent cursor** makes your work visible as work: `craft.py solidcraft call ui.agent_cursor '{"show": true, "speed": 2}'` shows a
pointer that glides to each toolbar button and pick, naming the command. Use it when they're watching; turn it off afterwards.

## Things that can bite

- **A dialog is open or the app is busy.** `run`, `batch` and `seq` refuse until it's resolved, because acting would discard their
  input or fail. Ask them; `--force` is for dialogs you opened yourself. `call` doesn't check.
- **They're typing.** PhotoCraft reports `textEdit`, shown as "typing text" in `status`. Don't send keys or commands until they finish.
- **The window is covered or minimised.** Engine commands still run, but no frames are drawn, so `ui.click`, `ui.key`, `ui.pointer` and
  screenshots wait or fail. If GUI input seems ignored, this is why. Say so and offer `craft.py APP front`, which takes focus.
- **State moved.** Between your turns they may have switched tab, changed the selection or undone your step. Re-read `status`, and find
  objects by content (`document.find`, names, colours), not ids from earlier. A `revision` that changed means the document did.
- **Their selection is an input.** Commands without `ids` act on it, and some commands change it. Pass explicit `ids` when you
  mean specific objects; when you mean theirs, confirm what's selected first. Restore their selection after scripted work if you changed it.
- **Preferences and tool settings are theirs too.** The active tool, colours, view and panels are part of their session. Put them back if you changed them.
- **Screenshots can steal focus.** PhotoCraft raises its window for a capture unless `focus: false`; `craft.py` passes that.

## Following along without being asked

`craft.py APP watch` prints a line per change (selection, document, tool, dialog, revision). It suits a session where you're
answering questions as they work: read what changed since your last turn instead of asking. SolidCraft also offers `control.subscribe`
for pushed events and `document.revision` as a cheap change check; see its protocol docs.

## Undo, and being wrong

- Say how to reverse what you did: "Cmd+Z undoes it", or "4 undo steps: they're in the History panel".
- If you made a mess, undo your own steps with `craft.py APP undo N`, counting from the history you can read. Never undo past what you did.
- SolidCraft: take `edit.checkpoint` before exploratory work; `edit.restore_checkpoint` returns to it. PhotoCraft: `history.newSnapshot`.
- When something surprises you, stop and show them rather than trying to repair it silently.

## Independent work in the live app

The same window, longer stretches. Work in a new document unless told otherwise, leave theirs alone, and give a short summary at the end:
what you built, what you checked, what you assumed, and where it's saved. Pause and ask only for decisions they would want to make.
