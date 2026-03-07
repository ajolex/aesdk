# Phase 5 — Plugin Architecture & Community (`aesdk.plugins`)

**Goal:** Make AESDK extensible. Researchers should be able to contribute new estimator
validators, governance rules, sandbox checks, and LLM adapters without modifying core SDK.

---

## 5.1 Plugin Types

| Plugin Type | What it Does | Example |
|---|---|---|
| `RulePlugin` | Adds new textbook governance rules | `imbens_rubin_matching.rules.yaml` |
| `ValidatorPlugin` | Custom PAP field validation logic | Enforce discipline-specific PAP fields |
| `SandboxCheckPlugin` | New statistical soundness checks | Spatial autocorrelation (Moran's I) |
| `LLMAdapterPlugin` | New LLM provider support | Anthropic, Gemini, local Ollama |
| `TraceExporterPlugin` | Custom blob export formats | Export to OSF, Zenodo, SSRN |
| `PlotPlugin` | Custom SCA visualization | R-style coefplot, forest plot |

---

## 5.2 Plugin Interface

```python
# aesdk/plugins/base.py

from abc import ABC, abstractmethod
from aesdk.protocol import ValidationResult, PAP

class SandboxCheckPlugin(ABC):
    name: str
    version: str
    reference: str  # Textbook/paper citation

    @abstractmethod
    def check(self, model_output: dict, pap: PAP) -> list[SandboxDiagnostic]:
        """Return list of diagnostics. Empty list = pass."""
        ...

# Example implementation
class MoransISpatialCheck(SandboxCheckPlugin):
    name = "spatial_autocorrelation_morans_i"
    version = "1.0.0"
    reference = "Anselin (1988). Spatial Econometrics."

    def check(self, model_output, pap):
        if pap.data.structure != "spatial":
            return []
        # ... run Moran's I on residuals
        return diagnostics
```

---

## 5.3 Plugin Registry

```bash
# Install a community plugin
aesdk plugin install aesdk-spatial-checks

# List installed plugins
aesdk plugin list

# Validate a plugin before use
aesdk plugin validate aesdk-spatial-checks
```

---

## 5.4 Community Contribution Standards

All community-contributed rule files and plugins must meet:

1. **Citation Requirement:** Every rule must cite a specific textbook, chapter, and page/equation.
2. **Test Coverage:** Rule plugins must include unit tests with known-pass and known-fail cases.
3. **Severity Classification:** Rules must be tagged `error` (blocks execution), `warning`
   (researcher-acknowledged), or `info` (logged only).
4. **Peer Review:** Rule files covering a new estimator family require review by a domain expert
   (enforced via GitHub CODEOWNERS for `aesdk/governance/rules/`).

---

## 5.5 Task Checklist

- [ ] Define plugin base classes: `RulePlugin`, `ValidatorPlugin`, `SandboxCheckPlugin`,
      `LLMAdapterPlugin`, `TraceExporterPlugin`, `PlotPlugin`
- [ ] Build plugin registry and loader (`aesdk plugin install/list/validate`)
- [ ] Implement `LLMAdapterPlugin` for: OpenAI, Anthropic, Ollama (local)
- [ ] Implement `TraceExporterPlugin` for: OSF, Zenodo metadata export
- [ ] Write contributor guide: `CONTRIBUTING_RULES.md`
- [ ] Set up CODEOWNERS for governance rule directories
- [ ] Community templates: `rule_template.yaml`, `sandbox_check_template.py`
- [ ] Plugin validation CI: auto-test all plugins on PR

---

## 5.6 Review Criteria
- Can a new estimator's rules be added with zero core SDK modification?
- Is the citation requirement enforced in CI?
- Are plugin APIs stable enough for third-party development?