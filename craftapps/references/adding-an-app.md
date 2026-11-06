# Adding a Craft app

Most apps share a transport and `engine.execute` / `engine.commands`, and differ in auth, method names and document model.

1. **Find how it starts.** `<APP>.app/Contents/Resources/README.md`, its upstream `docs/control-protocol.md`, the binary's
   `--help`. Note the port flag and environment variable, the isolated-profile variable, any token, and any required file roots.
2. **Write `apps/<app>/app.json`.** Copy the closest app's. Fields:
   - `binary`, `cli`: per platform. `port`: `default` (an unused one) and `env`. `profile_env`.
   - `auth`: `{"kind": "none"}`; `{"kind": "auth_request", "token_file_flag": …}` (first request is `auth`, as PhotoCraft);
     `{"kind": "token_field", "token_dir": …, "port_file": …}` (a `token` on the first request, as SolidCraft).
   - `roots` if it refuses paths without them. `batch`, `undo_group`, `render` where it has them. `screenshot_params` if a capture takes focus.
     `docs`: raw URLs of its protocol docs.
3. **Write `apps/<app>/adapter.py`.** Functions: `state`, `inspect`, `history_len`, `open`, `save`, `export`, `render`, `tree`, `dialog_info`,
   `dialog_set`, `dialog_ok`, `dialog_cancel`. `state` returns `document, dirty, documents, tool, selection, dialog, busy, revision`, read from `ui.inspect`
   with a document open and something selected: look at it first. Test whether `batch` is atomic and how many undo steps it makes.
4. **Sweep.** Add a seed to `SEEDS` in `scripts/sweep.py`, then against `craft.py <app> launch --isolated`:
   `sweep.py <app> out.json --port P`. Look at `other_error` and `timeout`: they show what the client or your assumptions have wrong.
5. **Do real tasks,** several, end to end, looking at the results: create, amend, export, and one live flow with a real dialog and pointer input.
   Everything that surprises you belongs in the pitfalls.
6. **Write `apps/<app>/APP.md`:** the document model, the workflows from step 5, command families, how to drive its GUI, headless use, teaching fundamentals, pitfalls.
   Keep it to what the live catalogue can't tell you.
7. **Add it** to the table in `SKILL.md` and to the skill's `description`, so the skill triggers on the app's name.
