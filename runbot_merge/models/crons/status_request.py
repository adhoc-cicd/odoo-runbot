import logging

import requests

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class StatusRequest(models.Model):
    _name = 'runbot_merge.pull_requests.status.request'
    _description = "requests that the runbot computes / generates / sends statuses"

    pull_request_id = fields.Many2one('runbot_merge.pull_requests')

    @api.model_create_multi
    def create(self, vals_list):
        self.env.ref('runbot_merge.cron_status_request')._trigger()
        return super().create(vals_list)

    def _run(self):
        # hide from pytest as it's not on the PYTHONPATH
        from odoo.addons.saas_worker.auth_util import SaasAuth
        prs = self.search([])
        names = prs.mapped('pull_request_id.display_name')
        prs.unlink()
        _logger.info("Trigger statuses for %s", ", ".join(names))
        res = requests.post(
            'https://runbot.odoo.com/runbot/request_ci',
            auth=SaasAuth(),
            json={'pull_requests': names}
        )
        if not res.ok:
            _logger.warning(
                "Statuses request failed %s\n%s",
                res.status_code,
                res.text,
            )