"""Archive every LLM call so AI-derived variables replicate without the model.

``ResearchLLM`` wraps any adapter. Each call appends one JSON line to
``<archive>/calls.jsonl`` with the full request (prompt, system, schema hash,
settings), the model that actually served it, the provider request id, the
stop reason, the parsed output, and the raw response. Output schemas are saved
once under ``<archive>/schemas/``. ``ai_use()`` returns the matching
``ai_use`` block for the pre-analysis plan, so the AI Replicability Passport
can hash the archive.

    llm = ResearchLLM(AnthropicAdapter(effort="high"), archive_dir="ai_archive")
    label = llm.generate(f"Classify: {text}", schema=LABEL_SCHEMA, record_id=row_id).structured
    pap["ai_use"] = llm.ai_use(role="text_classification", ai_derived_variables=["label"], input_files=["comments.csv"])
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aesdk.llm.adapters.base import LLMAdapter, LLMResponse


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ResearchLLM:
    def __init__(self, adapter: LLMAdapter, archive_dir: str | Path = "ai_archive"):
        self.adapter = adapter
        self.archive = Path(archive_dir)
        self.archive.mkdir(parents=True, exist_ok=True)
        (self.archive / "schemas").mkdir(exist_ok=True)
        self.calls_path = self.archive / "calls.jsonl"
        self.batches_path = self.archive / "batches.jsonl"

    # ---------------------------------------------------------------- helpers

    def _schema_file(self, schema: dict[str, Any] | None) -> str | None:
        if schema is None:
            return None
        text = json.dumps(schema, indent=2, sort_keys=True)
        path = self.archive / "schemas" / f"{_sha256(_canonical(schema))[:16]}.json"
        if not path.exists():
            path.write_text(text + "\n", encoding="utf-8")
        return path.as_posix()

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    def _record(
        self,
        response: LLMResponse,
        *,
        record_id: str | None,
        prompt: str,
        system: str | None,
        schema_file: str | None,
        batch_id: str | None = None,
    ) -> None:
        self._append(
            self.calls_path,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "record_id": record_id,
                "settings": self.adapter.settings(),
                "prompt": prompt,
                "prompt_sha256": _sha256(prompt),
                "system": system,
                "schema_file": schema_file,
                "batch_id": batch_id,
                "provider": response.provider,
                "requested_model": response.requested_model,
                "served_model": response.model,
                "request_id": response.request_id,
                "stop_reason": response.stop_reason,
                "refused": response.refused,
                "text": response.text,
                "structured": response.structured,
                "usage": response.usage,
                "raw": response.raw,
            },
        )

    # ------------------------------------------------------------------- API

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        record_id: str | None = None,
        max_tokens: int = 16000,
        temperature: float | None = None,
    ) -> LLMResponse:
        schema_file = self._schema_file(schema)
        response = self.adapter.generate(
            prompt, system=system, schema=schema, max_tokens=max_tokens, temperature=temperature
        )
        self._record(response, record_id=record_id, prompt=prompt, system=system, schema_file=schema_file)
        return response

    def submit_batch(
        self,
        prompts: dict[str, str],
        *,
        system: str | None = None,
        schema: dict[str, Any] | None = None,
        max_tokens: int = 16000,
    ) -> str:
        submit = getattr(self.adapter, "submit_batch", None)
        if submit is None:
            raise NotImplementedError(f"{type(self.adapter).__name__} does not support batches")
        batch_id = submit(prompts, system=system, schema=schema, max_tokens=max_tokens)
        self._append(
            self.batches_path,
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "batch_id": batch_id,
                "settings": self.adapter.settings(),
                "system": system,
                "schema_file": self._schema_file(schema),
                "prompts": prompts,
            },
        )
        return batch_id

    def collect_batch(self, batch_id: str) -> dict[str, LLMResponse | dict[str, Any]]:
        """Fetch a finished batch and archive each result like a single call."""

        submitted = self._batch_submission(batch_id)
        results = self.adapter.batch_results(batch_id, structured=bool(submitted.get("schema_file")))  # type: ignore[attr-defined]
        prompts = submitted.get("prompts") or {}
        for custom_id, result in results.items():
            if isinstance(result, LLMResponse):
                self._record(
                    result,
                    record_id=custom_id,
                    prompt=prompts.get(custom_id, ""),
                    system=submitted.get("system"),
                    schema_file=submitted.get("schema_file"),
                    batch_id=batch_id,
                )
        return results

    def _batch_submission(self, batch_id: str) -> dict[str, Any]:
        if self.batches_path.exists():
            for line in self.batches_path.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                if record.get("batch_id") == batch_id:
                    return record
        return {}

    def calls(self) -> list[dict[str, Any]]:
        if not self.calls_path.exists():
            return []
        return [json.loads(line) for line in self.calls_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def ai_use(self, *, role: str = "variable_construction", **fields: Any) -> dict[str, Any]:
        """Return an ``ai_use`` block describing the archived calls for the PAP."""

        calls = self.calls()
        served = sorted({c["served_model"] for c in calls if c.get("served_model")})
        providers = sorted({c["provider"] for c in calls if c.get("provider")})
        settings = self.adapter.settings()
        batch_ids = sorted({c["batch_id"] for c in calls if c.get("batch_id")})
        if self.batches_path.exists():
            batch_ids = sorted(set(batch_ids) | {json.loads(l)["batch_id"] for l in self.batches_path.read_text().splitlines() if l.strip()})
        schema_files = sorted({c["schema_file"] for c in calls if c.get("schema_file")})
        block: dict[str, Any] = {
            "used": True,
            "role": role,
            "provider": ", ".join(providers) or settings.get("provider"),
            "model": ", ".join(served) or settings.get("model"),
            "model_metadata_source": "api_response",
            "prompts_archived": True,
            "raw_outputs_archived": True,
            "prompt_files": [self.calls_path.as_posix()],
            "output_files": [self.calls_path.as_posix()],
            "reproducible_without_ai": True,
            "live_model_required": False,
            "ai_output_used_as_data": role in {"text_classification", "data_extraction", "variable_construction"},
        }
        if settings.get("effort"):
            block["reasoning_effort"] = settings["effort"]
        if batch_ids:
            block["batch_ids"] = batch_ids
        if schema_files:
            block["structured_output_schema_files"] = schema_files
        if len(served) > 1:
            block["notes"] = (
                "More than one model served these calls (for example a safety fallback): "
                + ", ".join(served)
                + ". Check calls.jsonl served_model per record."
            )
        block.update(fields)
        return block
