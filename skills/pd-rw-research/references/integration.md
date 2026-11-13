# Integration and minimal context restoration

Read when configuring WorkBuddy, switching projects, or diagnosing project-version mismatches.

## Authoritative locations

- Scientific rule owner: https://github.com/phr-devil/Problem-Data-Research-Workflow
- Default entry: `AGENTS.md`; scientific controller: `WORKFLOW.md`
- Existing project sources: `STATE.md` or `STATE.json`, `RESEARCH_RECORD.md`, `PAPER_BLUEPRINT.md` as applicable; actual Run/protocol/manifests are primary scientific evidence.
- WorkBuddy Skill entry: `skills/pd-rw-research/SKILL.md` **in this adapter repository**, not a replacement for PD-RW `AGENTS.md`.

## Configure once on the operator's computer

Copy `config/project-map.example.json` from the **development repository root** to `project-map.local.json`; fill in real local paths. Do not add real project directories, unpublished data, user chats, or credentials to the Skill archive or public GitHub.

```powershell
python skills/pd-rw-research/scripts/bridge.py doctor --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
python skills/pd-rw-research/scripts/bridge.py resume --project-id "example-project" --project-map "./project-map.local.json" --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
```

Do not assume the WorkBuddy current working directory; use an absolute path to the installed script if necessary. Installed skills do not include the external `project-map.local.json`. A project may use `STATE.md` or PD-RW's machine `STATE.json`; when both exist, specify the intended source explicitly in the local mapping. For machine STATE, `expected_state_project_id` can flag a declared ID mismatch, but even a matching ID is not sufficient identity proof.

## Recovery order

1. Confirm ID/name/dataset against the original user request and project root; the map alone is not identity proof.
2. Read PD-RW `AGENTS.md` and the appropriate source version; note `RULE_REPO | RULE_COMMIT | LOADED_FILES` only when established.
3. Read `RESEARCH_RECORD` current snapshot, then `STATE` references. If missing, fall back to original Run/protocol pointers, not fabricated completion.
4. Read the minimum relevant authentic evidence and original authorization for the next action. A machine STATE index is not a verified EVENTS chain: call the PD-RW evidence checker **only when appropriate**, and never use a checker to open an unauthorized SEALED source.
5. Read the one appropriate owner document from PD-RW's current `AGENTS.md` routing. Use `python scripts/context.py route --workflow-root ...` for a dynamically parsed topic list; provide `--topic` to select an unambiguous row. Only fetch additional docs when blocked.

## Version handling

The helper reports **local** Git HEAD only. It does not contact GitHub or attest remote freshness. If the remote cannot be checked, mark `RULE_VERSION_UNVERIFIED`; do not silently edit, pull, rebase, or migrate an old project.

A new PD-RW version changes routing **through PD-RW itself**; never update a second copy of PD-RW science policy inside this Skill.
