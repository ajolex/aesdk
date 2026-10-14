"""Generate Agent Skills (``SKILL.md``) from AESDK method packs.

Agent Skills are folders with a ``SKILL.md`` whose frontmatter ``description``
tells the agent *when* to load it; the body is read only when relevant. That
keeps the always-loaded instruction file short and loads DiD guidance only when
a DiD question comes up, instead of pasting every method into every session.

The skills follow the open Agent Skills format (https://agentskills.io):
``name`` is lowercase letters, digits, and hyphens (max 64 characters) and
matches the folder name; ``description`` is at most 1024 characters. Claude Code
reads them from ``.claude/skills``; other agents that support the standard read
``.agents/skills``. Detailed guidance lives in a sibling ``reference.md`` so the
skill body itself stays small (progressive disclosure).
"""

from __future__ import annotations

import re
from pathlib import Path

from aesdk.agent.context import agent_context
from aesdk.knowledge.catalog import get_knowledge_pack, get_method_protocol, list_method_ids

WORKFLOW_SKILL = "aesdk-workflow"
_MAX_DESCRIPTION = 1024


def skill_name(method_id: str) -> str:
    """Return the Agent Skills name for an AESDK method id (``iv_2sls`` -> ``aesdk-iv-2sls``)."""

    name = "aesdk-" + re.sub(r"[^a-z0-9]+", "-", method_id.lower()).strip("-")
    return name[:64].rstrip("-")


def _frontmatter(name: str, description: str) -> str:
    description = " ".join(description.split())
    if len(description) > _MAX_DESCRIPTION:
        description = description[: _MAX_DESCRIPTION - 3].rstrip() + "..."
    escaped = description.replace("\\", "\\\\").replace('"', '\\"')
    return f'---\nname: {name}\ndescription: "{escaped}"\nlicense: Apache-2.0\n---\n'


def render_workflow_skill() -> str:
    """The core skill: run AESDK before writing or running econometric code."""

    description = (
        "Econometrics methods check (AESDK) to run BEFORE writing or running any regression, causal-inference, "
        "or econometric analysis code (OLS, IV/2SLS, panel fixed effects, difference-in-differences, event "
        "studies, RCTs, RDD, matching, synthetic control, GMM, logit/probit, time series, MLE, DML, structural, "
        "nonparametric, Bayesian, GARCH) in Python, R, or Stata. Use when a researcher asks to estimate an "
        "effect, run a regression, analyze an experiment or policy, or review an analysis plan."
    )
    body = """
# AESDK econometrics workflow

The person is usually a researcher, not a programmer. Run every command yourself,
never paste raw JSON/YAML or tracebacks, ask plain-English questions instead of
field names, and explain findings like a careful senior RA: the concern, why it
matters, and the fix. AESDK checks that the workflow follows documented
econometric guardrails; it does not prove the design is correct.

## Steps

1. **Method.** Work out the method from what the researcher says and confirm it in
   plain language. Load the matching `aesdk-<method>` skill if one is available, or
   run `aesdk agent context --method <method>` (`aesdk methods list` lists ids).
2. **Plan.** Draft the reviewable plan from the researcher's words:
   `aesdk agent intake --prompt "<request>" --method <method> --output-dir .`
   (or `--task <file>` for a task document; never invent a task file).
3. **Record.** `aesdk agent prepare --method <method> --pap pap.yaml --proposal proposal.json --output-dir .`
   creates `.aesdk.json`, which is required even when the check blocks.
4. **Check.** `aesdk agent preflight --method <method> --pap pap.yaml --proposal proposal.json --conformance strict`
   also reads the declared dataset and cross-checks it against the plan.
   - **block** = hard stop. Explain the problem and the fix; do not write or run analysis code.
   - **warn** = explain it and get a clear plain-language go-ahead before continuing.
5. **Run under governance.** `aesdk agent run --method <method> --pap pap.yaml --proposal proposal.json --code-file analysis.py`
   (also `.do` for Stata and `.R` for R). Never run estimation scripts directly with
   `python`, `Rscript`, or `stata`; AESDK hooks may deny that.
6. **Report.** `aesdk agent report --blob .aesdk.json --output workflow.html` for a shareable summary.
7. **AI provenance.** If AI materially shaped code, data, or variables, document `ai_use` and
   write `aesdk agent ai-passport --pap pap.yaml --proposal proposal.json --output ai.lock.json`.
   Archived sessions in `.aesdk/sessions/` are picked up automatically. Never claim a human
   review that did not happen.

## Rules

- Do not invent assumptions, diagnostics, citations, estimator requirements, or AI-use evidence. Ask.
- Put research decisions in `pap.yaml` / `proposal.json`, not only in chat or agent memory, so
  they are checked and reproducible.
- If `aesdk` is missing, try `python -m aesdk ...`; if still missing, offer to install it
  (`python -m pip install aesdk`) in one sentence.
"""
    return _frontmatter(WORKFLOW_SKILL, description) + body


def render_method_skill(method_id: str) -> str:
    """Render the ``SKILL.md`` for one AESDK method."""

    protocol = get_method_protocol(method_id)
    try:
        pack = get_knowledge_pack(method_id) or {}
    except Exception:
        pack = {}
    name = protocol.get("name") or method_id
    use_when = " ".join(
        item.rstrip(".") + "." for item in (pack.get("scope") or {}).get("use_when") or []
    )
    estimators = ", ".join(protocol.get("estimators") or [])
    description = (
        f"AESDK guardrails for {name} ({method_id}): identifying assumptions, required pre-analysis-plan "
        f"fields, diagnostics, inference/clustering choices, and what AESDK blocks or warns on. "
        f"Use before writing or reviewing {name} code"
        + (f" (estimators: {estimators})" if estimators else "")
        + "."
        + (f" Typical setting: {use_when}" if use_when else "")
    )
    context = agent_context(method_id).to_markdown()
    context = context.replace(f"# AESDK Agent Context: {method_id}", f"# {name} ({method_id})", 1)
    body = f"""
Follow the `{WORKFLOW_SKILL}` steps with `--method {method_id}`. The guardrails below are what
the AESDK check enforces; explain them to the researcher in plain language.

For the estimator decision tree, failure modes, code recipes, and reporting checklist, read
[reference.md](reference.md) (or run `aesdk agent context --method {method_id} --depth full`).

{context}"""
    return _frontmatter(skill_name(method_id), description) + body


def render_method_reference(method_id: str) -> str:
    return agent_context(method_id, depth="full").to_markdown()


def write_skills(output_dir: str | Path, methods: list[str] | None = None) -> list[Path]:
    """Write the workflow skill and one skill per method under ``output_dir``."""

    root = Path(output_dir)
    written: list[Path] = []
    workflow_dir = root / WORKFLOW_SKILL
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / "SKILL.md").write_text(render_workflow_skill(), encoding="utf-8")
    written.append(workflow_dir / "SKILL.md")
    for method_id in methods or sorted(list_method_ids()):
        folder = root / skill_name(method_id)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "SKILL.md").write_text(render_method_skill(method_id), encoding="utf-8")
        (folder / "reference.md").write_text(render_method_reference(method_id), encoding="utf-8")
        written.append(folder / "SKILL.md")
    return written
