# Teaching

The apps mirror the professional tools they resemble (Illustrator, Fusion, Photoshop, InDesign), so what someone learns here transfers,
and tutorials for those apps mostly apply. VectorCraft has a full task-to-tool table in `apps/vectorcraft/manual-howto.md`; each
other `APP.md` has a shorter one. For anything else, ask the running app:

```bash
craft.py APP how "gaussian blur"   # menu path or ribbon location, shortcut, tool and its flyout
craft.py APP find sketch           # the commands in an area, with their locations
craft.py APP tools                 # the toolbar (where the app lists it)
```

Get locations from these, not from memory: menu paths differ from the original apps in places.

## Three ways to help

1. **Explain.** Numbered steps, one action each: where (tool, menu path, panel), what (click, drag, type), the exact values, and what
   they should see afterwards. To turn a script into steps, walk its commands in order, look each up with `how`, merge those that are one
   gesture for a person, and drop what only automation needs.
2. **Show me.** Do it live, one step at a time, pausing and saying what happened and where on screen. Let them do the key click whenever
   you can: select the object, open the panel, open the dialog prefilled (`references/live-copilot.md`), and they press OK. Undo a demonstration
   if they want to try it themselves.
3. **Check my work.** They do it by hand, then you read the state (`tree`, `status`, `render`) and compare it with the target. Name the object, the
   property, the value they have and the value wanted, and how to fix it: "the fillet is 3 mm where the drawing says 4: double-click Fillet1 in the History bar and change Radius."

## Adapting

- **Experienced users** want terse paths: "Object › Path › Offset Path…, 2 pt".
- **Beginners** need the selection step, what the dialog looks like, and what to look for afterwards. Teach the fundamentals in the
  app's `APP.md` first when they're clearly new.
- Offer the next step in their terms: "want me to do this one while you watch, or check yours when you're done?"
