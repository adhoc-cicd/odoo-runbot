import functools
import operator
from datetime import datetime, timedelta

import pytest

from utils import Commit, to_pr

pytestmark = pytest.mark.usefixtures("reviewer_admin")

@pytest.fixture
def prs(env, repo, users, config):
    """Creates and stages 4 PRs, then triggers a split, and leaves that on the floor for the tests
    """
    prs = []
    with repo:
        [m] = repo.make_commits(None, Commit('initial', tree={'x': 'x'}), ref='heads/master')

        for i in range(1, 5):
            [c] = repo.make_commits(m, Commit(f'pr {i}', tree={chr(i+96): 'x'}), ref=f'heads/branch{i}')
            prs.append(pr := repo.make_pr(target='master', head=f'branch{i}'))
            repo.post_status(c, 'success')
            pr.post_comment('hansen r+', config['role_reviewer']['token'])
    env.run_crons()
    with repo:
        repo.post_status('staging.master', 'failure')
    env.run_crons()

    assert env['runbot_merge.stagings'].search([]), \
        "a new staging should have been created with the first half of the original"
    assert env['runbot_merge.split'].search([]), \
        "the last two PRs should be in a split still"

    return prs

def test_reset(env, repo, users, config, prs):
    """reset=staging will unconditionally cancel the staging
    """
    pr_ids = functools.reduce(operator.or_, (to_pr(env, p) for p in prs))
    assert not pr_ids[-1].staging_id
    with repo:
        prs[-1].post_comment('hansen reset=staging', config['role_reviewer']['token'])
    env.run_crons()

    assert not env['runbot_merge.split'].search([])
    st = env['runbot_merge.stagings'].search([])
    assert len(st.pr_ids) == 4

    with repo:
        prs[-2].post_comment('hansen reset=staging', config['role_reviewer']['token'])
    env.run_crons()

    assert st.state == 'cancelled'
    st2 = env['runbot_merge.stagings'].search([])
    assert st2 != st
    assert len(st2.pr_ids) == 4

    with repo:
        repo.post_status('staging.master', 'failure')
    env.run_crons()

    assert env['runbot_merge.split'].search([])
    assert pr_ids[0].staging_id
    with repo:
        prs[0].post_comment('hansen r- reset=staging', config['role_reviewer']['token'])
    env.run_crons()

    assert pr_ids[0].state == 'validated'
    assert env['runbot_merge.stagings'].search([]).pr_ids == pr_ids[1:]

def test_reset_splits(env, repo, users, config, prs):
    """reset=split will delete the splits but leave an eventual staging
    """
    pr_ids = functools.reduce(operator.or_, (to_pr(env, p) for p in prs))
    assert not pr_ids[-1].staging_id
    with repo:
        prs[-1].post_comment('hansen reset=splits', config['role_reviewer']['token'])
    env.run_crons()

    assert not env['runbot_merge.split'].search([])
    st = env['runbot_merge.stagings'].search([])
    assert st.pr_ids == pr_ids[:2], "the staging should not have been cancelled"
    assert not pr_ids[2].staging_id
    assert not pr_ids[3].staging_id

def test_reset_splits_implicit(env, repo, users, config, prs):
    """interaction between reset=splits and r- on a staged PR
    """
    pr_ids = functools.reduce(operator.or_, (to_pr(env, p) for p in prs))
    assert not pr_ids[-1].staging_id
    with repo:
        prs[0].post_comment('hansen r- reset=splits', config['role_reviewer']['token'])
    env.run_crons()

    assert not env['runbot_merge.split'].search([])
    st = env['runbot_merge.stagings'].search([])
    assert st.pr_ids == pr_ids[1:], "the staging should have been cancelled by the r-"

def test_reset_auto(env, project, repo, users, config, prs):
    """reset=auto resets the staging if it's "young" but leaves it if
    it's "old", as it's better to keep a staging nearing completion to
    not waste the build time.
    """
    # since we're using >1h staging durations increase the ci timeout to
    # avoid timeout failures
    project.ci_timeout = 600
    env['runbot_merge.stagings'].create([
        {'target': project.branch_ids.id, 'state': 'success', 'active': False,
         'staging_batch_ids': [(0, 0, {'runbot_merge_batch_id': 1})],
         'staged_at': start, 'staging_end': end}
        for start, end in (
            ('2025-12-11 15:47:00', '2025-12-11 17:20:00'),
            ('2025-12-22 22:32:00', '2025-12-23 00:06:00'),
            ('2026-01-14 20:21:00', '2026-01-14 21:38:00'),
        )
    ])

    st = env['runbot_merge.stagings'].search([])
    st.staged_at = (datetime.now() - timedelta(hours=1)).isoformat(sep=' ', timespec='seconds')
    with repo:
        prs[-1].post_comment('hansen reset=auto', config['role_reviewer']['token'])
    env.run_crons()

    assert env['runbot_merge.stagings'].search([]) == st, \
        "the staging is aged like fine wine and left to ferment"
    assert not env['runbot_merge.split'].search([])

    st.staged_at = (datetime.now() - timedelta(minutes=15)).isoformat(sep=' ', timespec='seconds')
    with repo:
        prs[-1].post_comment('hansen reset=auto', config['role_reviewer']['token'])
    env.run_crons()

    assert not st.active
    assert env['runbot_merge.stagings'].search([]) != st, \
        "he's a loose cannon we should never have hired him"

def test_reset_nauto(env, repo, users, config, prs):
    """no previous staging ~ always cancel
    """
    pr_ids = functools.reduce(operator.or_, (to_pr(env, p) for p in prs))
    assert not pr_ids[-1].staging_id
    with repo:
        prs[-1].post_comment('hansen reset=auto', config['role_reviewer']['token'])
    env.run_crons()

    assert not env['runbot_merge.split'].search([])
    st = env['runbot_merge.stagings'].search([])
    assert len(st.pr_ids) == 4