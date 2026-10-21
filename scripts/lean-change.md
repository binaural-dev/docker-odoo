## Lean change (sdd-builder only)

Solve the whole task with the least new code that fully works. The spec decides scope; lean never overrides it.

Take the first option that fully works:
1. Does it need to exist? Anything not in the spec is skipped; name it in one line.
2. Already in this repo or in Odoo (helper, mixin, model, existing module)? Reuse it the way the surrounding code does.
3. ORM or standard library before new code. An already-installed dependency before a new one.
4. Otherwise the minimum code that works. No wrapper, option, abstraction or "for later" code nobody asked for.

Never cut: spec requirements (EARS ids), tests and coverage > 90 %, security (`ir.model.access.csv`, record rules), validation at trust boundaries, `_()` with `.format()`, `ensure_one()`, manifest and data files Odoo requires.

Bug fix: grep every caller of the function you touch, then fix the root cause once in the shared code.
A shortcut with a known limit gets a comment: `shortcut: <limit>, <when to upgrade>` (English).
Do not replace the structured outputs (`NEEDS_HUMAN_INPUT`, handoffs). Put what you skipped and any risk in one `lean_notes:` line of the result.
