import datetime
import json
import typing
from urllib.parse import unquote

from odoo.http import Controller, Response, request, route

from .utils import from_role

Status = typing.Literal['pending', 'success', 'error', 'failure']

class StatusesController(Controller):
    @from_role('runbot', signed=True)
    @route('/runbot_merge/<int:oid>/statuses', type='http', auth='none', csrf=False, methods=['POST'])
    def statuses_staging(
        self,
        oid: int,
        *,
        sha: str,
        context: str,
        status: Status,
        target_url: str | None = None,
        description : str | None = None,
    ) -> Response:
        staging = request.env(user=1)['runbot_merge.stagings'].browse(oid).exists()
        if not staging:
            raise request.not_found(f"{oid} not found")

        if not any(h.sha == sha for h in staging.head_ids):
            raise request.not_found(f"{sha} is not a valid head")

        statuses = json.loads(staging.statuses_cache)
        statuses.setdefault(sha, {})[context] = {
            'state': status,
            'target_url': target_url,
            'description': description,
            'updated_at': datetime.datetime.now().isoformat(timespec='seconds'),
        }
        staging.statuses_cache = json.dumps(statuses)
        return request.make_json_response(None)

    @from_role('runbot', signed=True)
    @route('/runbot_merge/<owner>/<repo>/<int:number>/statuses', type='http', auth='none', csrf=False, methods=['POST'])
    def statuses_pr(
            self,
            owner: str,
            repo: str,
            number: int,
            *,
            sha: str,
            context: str,
            status: Status,
            target_url: str | None = None,
            description: str | None = None,
    ) -> Response:
        pr = request.env(user=1)['runbot_merge.pull_requests'].search([
            ('repository.name', '=', f"{owner}/{repo}"),
            ('number', '=', int(number)),
        ])
        if not pr:
            raise request.not_found(f"{owner}/{repo}#{number} not found")

        if pr.head != sha:
            raise request.not_found(f"{sha} is not the head of {pr.display_name}")

        st = json.loads(pr.statuses)
        st[context] = {
            'state': status,
            'target_url': target_url,
            'description': description,
            'updated_at': datetime.datetime.now().isoformat(timespec='seconds'),
        }
        pr._validate(json.dumps(st))
        pr._track_set_log_message(f"statuses updated by runbot")
        return request.make_json_response(None)

