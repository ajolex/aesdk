import yaml

from aesdk.core.project import Project
from aesdk.sandbox.runner import SandboxDiagnostic, SandboxResult
from aesdk.trace.replay import replay_execute_events


class _FakeSandboxRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def run(self, code: str, *, language: str = "python", timeout_seconds=None):  # noqa: ANN001
        self.calls.append((code, language))
        return SandboxResult(
            status="pass",
            diagnostics=[SandboxDiagnostic("SMOKE", f"{language} execution succeeded", "info")],
            stdout="ok",
        )


def test_replay_executes_and_matches(valid_pap_dict: dict, runtime_dir):
    pap = dict(valid_pap_dict)
    pap['identification']['strategy'] = 'OLS'
    pap['identification']['standard_errors'] = 'HC3'
    pap['data']['structure'] = 'cross-section'
    pap.pop('did_block', None)

    pap_path = runtime_dir / 'pap.yaml'
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding='utf-8')

    blob_path = runtime_dir / '.aesdk.json'
    project = Project.create(pap_path=pap_path, blob_path=blob_path, context='regulated', conformance='regulated')
    proposal = {'estimator': 'OLS', 'standard_errors': 'HC3'}
    project.propose_model(proposal)
    result = project.validate()
    assert result.status == 'pass'

    project.execute("print('ok')")

    replay_results = replay_execute_events(blob_path)
    assert len(replay_results) == 1
    assert replay_results[0].code_hash_matches is True
    assert replay_results[0].recorded_status == replay_results[0].replay_status


def test_replay_preserves_successful_non_python_language(valid_pap_dict: dict, runtime_dir):
    pap_path = runtime_dir / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")

    blob_path = runtime_dir / ".aesdk.json"
    runner = _FakeSandboxRunner()
    project = Project.create(
        pap_path=pap_path,
        blob_path=blob_path,
        context="production",
        conformance="strict",
        sandbox_runner=runner,
    )
    project.propose_model({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"})
    assert project.validate().status == "pass"

    code = "print(1)"
    project.execute(code, language="r")

    replay_runner = _FakeSandboxRunner()
    replay_results = replay_execute_events(blob_path, sandbox_runner=replay_runner)

    assert runner.calls == [(code, "r")]
    assert replay_runner.calls == [(code, "r")]
    assert replay_results[0].recorded_status == "pass"
    assert replay_results[0].replay_status == "pass"
    assert replay_results[0].code_hash_matches is True


def test_replay_normalizes_recorded_language_alias(valid_pap_dict: dict, runtime_dir):
    pap_path = runtime_dir / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")

    blob_path = runtime_dir / ".aesdk.json"
    runner = _FakeSandboxRunner()
    project = Project.create(
        pap_path=pap_path,
        blob_path=blob_path,
        context="production",
        conformance="strict",
        sandbox_runner=runner,
    )
    project.propose_model({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"})
    assert project.validate().status == "pass"

    code = "print(1)"
    project.execute(code, language="Rscript")

    replay_runner = _FakeSandboxRunner()
    replay_execute_events(blob_path, sandbox_runner=replay_runner)

    assert runner.calls == [(code, "r")]
    assert replay_runner.calls == [(code, "r")]
