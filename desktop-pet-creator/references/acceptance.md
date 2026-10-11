# Completion gate

Use checks relevant to the requested result; stop testing once the remaining concrete risks are resolved. Use a unique test project and never replace an existing user's pet while testing this skill.

## Visual

- Identity anchors match the approved reference and latest user corrections.
- Complete transparent silhouette; no white rectangle, labels or clipped parts.
- Loop is continuous; static props and outfit retain shape and position.
- Articulated movement has attached joints; guitar doesn't swing with the playing hand.
- Optional overlays fit and appear only in the configured active state.
- Small preview is readable, with no dark/light edge artifacts.

## Runtime

- `validate_assets.py` passes; actual runtime loads both idle/playing composites.
- Idle → active → paused → resumed changes frames correctly. Live player test when available; otherwise explicitly say state transitions were simulated.
- ACTIVE-but-zero-output audio fallback remains idle after its hold time.
- Drag and size persistence work; external chat resize and wheel/menu respect bounds.
- Close suppresses the current owner session; start reopens; no duplicate instance.
- Follow-app mode hides while owner is absent and after owner exit. New owner session clears prior suppression. Independent mode does not depend on Codex.
- Startup shortcut uses real absolute paths and only exists when requested. Installation and uninstall act only on their own pet.

## Delivery and publication

- Easy installation/interaction instructions, correct install path, preview and tested/untested claims.
- No tokens, user reference photos, screenshots, personal settings/PIDs, virtual environment or cache in the shared source.
- Reference assets are supplied by each user; a license for source code is not a license for arbitrary character art.
- Repository pushed successfully and remotely readable; local commit matches the remote branch.
