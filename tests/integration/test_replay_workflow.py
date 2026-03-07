import yaml

from aesdk.core.project import Project
from aesdk.trace.replay import replay_execute_events


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
