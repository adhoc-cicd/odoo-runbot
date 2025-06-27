import collections
import datetime
import pathlib

import werkzeug.urls

from odoo.http import route, request
from odoo.osv import expression
from odoo.addons.runbot_merge.controllers.dashboard import MergebotDashboard

DEFAULT_DELTA = datetime.timedelta(days=7)
class Dashboard(MergebotDashboard):
    def _entries(self):
        changelog = pathlib.Path(__file__).parent / 'changelog'
        if not changelog.is_dir():
            return super()._entries()

        return super()._entries() + [
            (d.name, [f.read_text(encoding='utf-8') for f in d.iterdir() if f.is_file()])
            for d in changelog.iterdir()
        ]


    @route('/forwardport/outstanding', type='http', methods=['GET'], auth="user", website=True, sitemap=False)
    def outstanding(self, partner=0, authors=True, reviewers=True, group=0):
        Partners = request.env['res.partner']
        partner = Partners.browse(int(partner))
        group = Partners.browse(int(group))
        authors = int(authors)
        reviewers = int(reviewers)
        link = lambda **kw: '?' + werkzeug.urls.url_encode({'partner': partner.id or 0, 'authors': authors, 'reviewers': reviewers, **kw, })
        groups = Partners.search([('is_company', '=', True), ('child_ids', '!=', False)])
        if not (authors or reviewers):
            return request.render('forwardport.outstanding', {
                'authors': 0,
                'reviewers': 0,
                'single': partner,
                'culprits': partner,
                'groups': groups,
                'current_group': group,
                'outstanding': [],
                'outstanding_per_author': {partner: 0},
                'outstanding_per_reviewer': {partner: 0},
                'link': link,
            })

        partner_filter = None
        if partner:
            if authors and reviewers:
                partner_filter = lambda p: p.author == partner or p.reviewed_by == partner
            elif authors:
                partner_filter = lambda p: p.author == partner
            elif reviewers:
                partner_filter = lambda p: p.reviewed_by == partner
        elif group:
            if authors and reviewers:
                partner_filter = lambda p: \
                    p.author.commercial_partner_id == group\
                    or p.reviewed_by.commercial_partner_id == group
            elif authors:
                partner_filter = lambda p: p.author.commercial_partner_id == group
            elif reviewers:
                partner_filter = lambda p: p.reviewed_by.commercial_partner_id == group

        now = datetime.datetime.now()
        Batches = request.env['runbot_merge.batch']
        outstanding = Batches.search([
            ('parent_id', '!=', False),
            ('merge_date', '=', False),
            ('blocked', '!=', False),
            ('create_date', '<', now - DEFAULT_DELTA),
        ])
        outstandings = collections.defaultdict(Batches.browse)
        outstanding_per_group = collections.Counter()
        outstanding_per_author = collections.Counter()
        outstanding_per_reviewer = collections.Counter()
        for batch in outstanding:
            source = batch.source
            if partner_filter and not any(partner_filter(p) for p in source.prs):
                continue

            outstandings[source] |= batch
            sources = source.prs
            if authors:
                outstanding_per_author.update(sources.author)
            if reviewers:
                outstanding_per_reviewer.update(sources.reviewed_by)
            outstanding_per_group.update(
                sources.author.commercial_partner_id
              | sources.reviewed_by.commercial_partner_id
            )

        culprits = Partners.browse(p.id for p, _ in (outstanding_per_reviewer + outstanding_per_author).most_common())
        return request.render('forwardport.outstanding', {
            'authors': authors,
            'reviewers': reviewers,
            'single': partner,
            'culprits': culprits,
            'groups': groups,
            'current_group': group,
            'outstanding_per_author': outstanding_per_author,
            'outstanding_per_reviewer': outstanding_per_reviewer,
            'outstanding_per_group': outstanding_per_group,
            'outstanding': dict(sorted(
                outstandings.items(),
                key=lambda item: item[0].merge_date or now,
            )),
            'link': link,
        })
