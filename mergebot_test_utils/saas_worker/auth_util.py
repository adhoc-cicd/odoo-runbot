import io
import threading
import urllib.parse

import requests.adapters
import requests.auth
import requests.sessions

import odoo


class SaasAdapter(requests.adapters.BaseAdapter):
    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        res = requests.Response()
        res.request = request
        res.status_code = 204
        res.raw = io.BytesIO()
        return res

    def close(self) -> None:
        pass


class SaasSession(requests.sessions.Session):
    def __init__(self):
        super().__init__()
        self.mount('saas://', SaasAdapter())


class SaasAuth(requests.auth.AuthBase):
    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        dbname = threading.current_thread().dbname
        db = odoo.sql_db.db_connect(dbname)
        with db.cursor() as cr:
            env = odoo.api.Environment(cr, 1, {})
            env['saas.calls'].create({
                'method': request.method,
                'url': request.url,
                'body': request.body,
            })
        request.url = urllib.parse.urlsplit(request.url)\
            ._replace(scheme='saas')\
            .geturl()
        return request