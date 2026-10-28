"""Execute the real publishing step against a local remote, then resume intake."""
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import intake_large_cap_review_candidates as intake


def test_intake_throttle_survives_workflow_publish_and_clean_checkout(tmp_path):
    root = Path(__file__).resolve().parents[1]
    workflow = (root / '.github/workflows/candidate_collection.yml').read_text()
    step = workflow.split('      - name: Commit candidate additions and collection status', 1)[1]
    step = step.split('      - name:', 1)[0].split('        run: |\n', 1)[1]
    script = '\n'.join(line[10:] for line in step.splitlines())

    def git(*args, cwd=tmp_path):
        return subprocess.run(['git', *map(str, args)], cwd=cwd, check=True,
                              capture_output=True, text=True)

    remote, first, resumed = [tmp_path / name for name in ('remote.git', 'first', 'resumed')]
    git('init', '--bare', '--initial-branch=data-validation-mvp', remote)
    git('clone', remote, first)
    git('config', 'user.name', 'regression test', cwd=first)
    git('config', 'user.email', 'test@example.invalid', cwd=first)
    (first / 'data').mkdir()
    state = first / 'data/large_cap_review_intake_status.json'
    state.write_text(json.dumps({'last_intake_date_kst': '2026-10-27'}))
    for filename in ('stock_universe_candidates.csv', 'unranked_us_stock_master.csv',
                     'monitoring_universe.csv', 'yahoo_large_cap_candidate_review.csv'):
        (first / 'data' / filename).write_text('symbol\nEXISTING\n')
    (first / 'data/candidate_collection_status.json').write_text('{}')
    git('add', 'data', cwd=first)
    git('commit', '-m', 'seed', cwd=first)
    git('push', 'origin', 'HEAD:data-validation-mvp', cwd=first)

    # Simulate output of the first successful intake. The workflow must publish
    # both its additions and its durable once-per-KST-day marker.
    state.write_text(json.dumps({'last_intake_date_kst': '2026-10-28', 'last_batch_added': 250}))
    (first / 'data/candidate_collection_status.json').write_text(json.dumps({'large_cap_review_candidates_added': 250}))
    subprocess.run(['bash', '-e', '-c', script], cwd=first, check=True,
                   capture_output=True, text=True)
    git('clone', remote, resumed)
    persisted = json.loads((resumed / 'data/large_cap_review_intake_status.json').read_text())
    assert persisted['last_intake_date_kst'] == '2026-10-28'

    paths = {'CANDIDATES_PATH': 'stock_universe_candidates.csv',
             'UNIVERSE_PATH': 'monitoring_universe.csv',
             'QUEUE_PATH': 'yahoo_large_cap_candidate_review.csv',
             'CAP_STATUS_PATH': 'unused.json',
             'STATUS_PATH': 'candidate_collection_status.json',
             'INTAKE_STATUS_PATH': 'large_cap_review_intake_status.json'}
    candidates_before = (resumed / 'data/stock_universe_candidates.csv').read_bytes()
    with ExitStack() as stack:
        for name, filename in paths.items():
            stack.enter_context(patch.object(intake, name, resumed / 'data' / filename))
        clock = stack.enter_context(patch.object(intake, 'datetime'))
        clock.now.return_value = datetime(2026, 10, 28, 10, tzinfo=timezone.utc)
        stack.enter_context(patch.object(intake, '_queue_is_fresh', return_value=(True, 'fresh')))
        stack.enter_context(patch.object(intake, 'refresh_existing_review_mappings', side_effect=lambda c: (c, 0)))
        build = stack.enter_context(patch.object(intake, 'build_review_only_candidates'))
        assert intake.main() == 0
        build.assert_not_called()
    result = json.loads((resumed / 'data/candidate_collection_status.json').read_text())
    assert result['large_cap_review_candidates_added'] == 0
    assert result['large_cap_review_candidates_status'] == 'daily_intake_already_completed'
    assert (resumed / 'data/stock_universe_candidates.csv').read_bytes() == candidates_before
