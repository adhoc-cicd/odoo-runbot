import logging

from odoo import api, fields, models
from ... import git


_logger = logging.getLogger(__name__)

class CheckCommits(models.Model):
    _name = 'runbot_merge.pull_requests.check_commits'
    _description = "uses git to compute a PR's commit count"

    pull_request_id = fields.Many2one('runbot_merge.pull_requests', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        self.env.ref('runbot_merge.cron_check_commits')._trigger()
        return super().create(vals_list)

    def _run(self):
        # this cron should be needed extremely rarely, and has low time
        # sensitivity, so we can just process one item at a time.
        t = self.search([], limit=1)
        if not t:
            return

        pr_id = t.pull_request_id
        repo = git.get_local(pr_id.repository)
        target_head, pr_head = sorted(
            repo.fetch_heads(
                pr_id.repository,
                f"refs/heads/{pr_id.target.name}",
                pr_id.head,
            ),
            key=lambda h: h == pr_id.head,
        )
        r = repo.stdout().with_config(
            check=True,
            encoding='utf-8',
        ).rev_list('--count', f'{target_head}..{pr_head}')
        _logger.info("%s: %s commits", pr_id.display_name, r.stdout.strip())
        pr_id.squash = int(r.stdout) == 1

        t.unlink()
        self.env.ref('runbot_merge.cron_check_commits')._trigger()
