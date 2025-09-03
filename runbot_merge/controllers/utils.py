__all__ = ['from_role']

try:
    from odoo.addons.saas_worker.util import from_role
except ImportError:
    def from_role(*_, **__):
        return lambda _: None
