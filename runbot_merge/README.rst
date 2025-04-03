=========
Merge Bot
=========

The mergebot is Odoo's internal tool for merging PRs.

It is conceptually rooted in Graydon Hoare's `"not rocket science" rule of
software engineering <https://graydon2.dreamwidth.org/1597.html>`_:

    "automatically maintain a repository of code that always passes all the tests"

That is not only should PRs pass tests before being merged, PRs should be tested
*as integrated*, in order to avoid logical conflicts (two PRs which pass tests
independently but do not pass when merged together, or the PR was tested with
an older version of the target branch but doesn't work with the latest).

This idea has become a lot more popular and democratized with the advent of
gitlab's `merge trains <https://docs.gitlab.com/ci/pipelines/merge_trains/>`_
and github's `merge queues <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue>`_.

Justification of Existence
==========================

Although merge queues exist for the general public, they are unsuitable for Odoo
for a number of reasons:

- Odoo development has multi-repo dependencies, which merge queues simply do not
  support (as of rewriting this readme, an odoo change can involve up to 6
  repositories, some of which are co-dependent). This is by far the biggest
  ticket as it makes merge queues a non-contender.
- Github access rights are pretty rough, especially when using the old pricing
  model (which limits roles to admin, write, and read).
- Some cross-repository tasks should be synchronised with staging (e.g.
  freezing, patching), though they could always just fuck with the queue.
- Github does not support forward- or back-ports internally, which still
  requires extra tooling to manage this (as well as ACLs on the ports).

Development
===========

Because the mergebot has significant interactions with github (via git, the
github API, and webhooks from github) it is not trivial to test. Not only that,
but although it is possible to run the test suite against github actual because
of the rate limits (primary and secondary) it takes literally days to go through
the 500-odd integration tests.

As a result, the mergebot is mostly tested locally, which requires its specific
setup and tooling.

Shared Setup
------------

Although the mergebot might be testable in addons-path layout, it has only been
tested with a :env:`PYTHONPATH` layout, that is::

    /
    ├── odoo           ── odoo/odoo checkout here
    ├── community
    │   └── odoo
    │       └── addons -> ../../odoo/addons
    ├── enterprise
    │   └── odoo
    │       └── addons ── odoo/enterprise checkout here
    └── runbot
        └── odoo
            └── addons ── odoo/runbot checkout here

and using PYTHONPATH to add the addon directories to odoo via python
namespaces (rather than ``--addons-path``).

This also requires [#pytest.ini]_ a ``pytest.ini`` file such that pytest can know
the project root (``rootpath``), and because the rootpath is not inside any
repository (it's at the ``/`` in the block above) it has to be created by hand.

A working sample file currently is:

.. include:: ../pytest.ini.sample
   :code: ini

.. hint::

    Assuming the sample works out of the box, you can just create a symlink to
    that sample file from the root::

        ln -s runbot/odoo/addons/pylint.ini.sample pylint.ini

    Although you may not want to do that if you need local changes e.g. remove
    the ``addopt`` because you want to change defaults or not use xdist
    implicitly.

.. [#pytest.ini] does it still?

Local testing
-------------

The test suite should mostly be run locally as it can be run at a much higher
clip, and concurrently. However this requires some setup as the test harness was
kept (mostly) unaware of the difference to limit the risk of divergences from
github actual which absolutely plagued the previous mock-based version).

Thus running the test suite locally requires:

- `mitmproxy <https://mitmproxy.org/>`_ (follow instructions to set up locally),
  which is used to redirect requests to Github (from both the test harness and
  the running Odoo instances) to
- `dummy-central <https://github.com/odoo/dummy-central>`_, a simulator of the
  github API (mostly implementing the stuff which is or used to be needed to run
  the test suite)

Configuration
'''''''''''''

- mitmproxy should be run as::

      mitmdump -M '|^https?://(\w+\.)?github.com/|http://localhost:$PORT/'

  where ``$PORT`` is the port to which dummy-central is bound. It should also
  have the following configuration keys set (in its config file, or via
  ``--set`` parameters): ``upstream_cert: false`` and
  ``connection_strategy: lazy``. Missing *either* of those causes mitmproxy to
  connect to github.com unnecessarily, which

  - consumes github resources for no reason
  - causes flakiness in the local test suite when the connection fails (e.g.
    because github or the network is down)
  - slows mitmproxy down
- dummy-central should probably be run from a git checkout. It could be
  installed but development to the mergebot may -- and likely will -- require
  additions or changes to DC, leading to a local build being much easier::

      cargo run --release -- $USERS_FILE -p $PORT

- the test suite *should* be run with ``pytest-xdist`` installed [#perf]_::

      HTTPS_PROXY=$PROXY_ADDR pytest -n logical --users $USERS_FILE

  .. note:: ``logical`` runs an xdist worker per thread which seems to work well
            on a Ryzen 5 7530U (6 cores 12 threads) [#numprocesses]_.

``PROXY_ADDR``
    The address on which mitmproxy is bound, defaults to
    ``http://localhost:8080`` unless ``--listen-port`` (``-p``) is used.
``USERS_FILE``
    The description of the users roles / github users / github organisation,
    see `users file`_.

Users File
''''''''''

This is a JSON file which serves to:

- Tell dummy-central what github-level organisations and users to expose.
- Tell the test suite what these users are (when communicating with
  dummy-central, or github actual) and how they map to internal *roles*.

It should be shared between dummy-central and the test suite to ensure
consistent behaviour. The users file is a JSON object, where each key is a
github identifier (login), and each value is an object with the following
entries:

``type``
    Can be either ``Organization`` or ``User``.
``role``
    The role of the user in the test suite, used to avoid addressing entities
    in a way which is non-portable.

    There should be 4 or 5 role-bearing entities in the array:

    ``user``
        Is the primary actor, used as the bot user, and should have write access
        to...
    ``owner``
        The location where repositories are created by default, if present
        should be an organisation, otherwise repositories are created in
        ``user``'s account [#owner]_.
    ``reviewer``
        A non-bot user which is assigned review rights by default.
    ``self_reviewer``
        A non-bot user which is assigned self-review rights by default.
    ``other``
        A non-bot user which is assigned no rights by default (and does not even
        have a partner setup), can represent an employee without special access
        or a community member.

    .. note:: Since they have no special attachment (access to) the organisation
              the last 3 roles should probably be removed and their users
              selected at random for upgrade when a ``reviewer`` or
              ``self_reviewer`` fixture is requested by a test, this would allow
              providing more (though probably not less) users and would avoid
              reliance on specific accounts creeping in.
``email``
    The email address of the entity, mostly used to compose git authorship.
    information.
``token``
    An array of access tokens, the test suite will use the first of each array
    to access github.

Github actual
-------------

Running against github actual is not much less involved as it needs both several
*actual* user accounts, and a tunnel to hook webhooks back in.

Tunnels
'''''''

The test suite has first-class support for tunnels via the ``--tunnel``
parameter which should link to a tunnel script. The repository bundles an
``ngrok`` script which adapts the tunnel protocol for ngrok agents (ideally ran
as a daemon, that avoids startup synchronisation issues)::

    pytest --tunnel runbot_merge/ngrok

should automatically create and teardown tunnels from github, and create
webhooks to the remote end of the tunnel.

The tunnel script simply takes the local port as first argument, should print
the remote address of the tunnel on stdout (don't forget to flush so the test
suite can read it), then close the tunnel on SIGTERM and SIGINT (the test suite
uses SIGTERM to close tunnels, but when testing a tunnel script Ctrl+C sends
SIGINT).

Accounts
''''''''

As the test suite itself requires multiple accounts, they also have to be
provided when running against github actual, with a similar setup to
`local testing`_, although:

- the top-level keys (organisation and user logins) need to be valid github accounts
- the TODO fields are not used
- The accounts need to be legitimate

  - While github has become more accepting of multiple user accounts (with an
    integrated account switcher), accounts should be ramped up slowly lest
    they be flagged as spam.

    This is especially problematic for the non-``user`` roles here as their
    near entire activity is leaving comments, which is a very spammy workload.
  - Although attractive due to easier handling, the ``user`` role probably
    should not be your primary github account: the main brake on running the
    test suite is the secondary rate limit on pull requests creation [#git]_,
    and once it is hit you will not be able to open PRs for several hours
    *with that entire account*, including via the web UI and the online
    vscode.
- The personal tokens neeed to be valid

  - Every user token needs ``public_repo`` and ``delete_repo``.
  - The ``user`` role further needs ``admin:repo_hook`` and ``user:email`` (?).
- xdist *may not* be enabled, github's TOS / API recommendation strongly
  request no concurrency, and this will just trigger rate limits faster.
- The test suite should be run in ``--sw`` (stepwise): it will stop at the first
  failure (like ``-x``), but will then resume from the failed case, which allows

  - Resuming after fix in case of true negative, limiting the need for duplicat
    test runs (not an issue normally, but a major concern with rate limiting).
  - Resuming immediately in case of false negative (e.g. concurrency / timeout
    issue).
  - Waiting a few hours in case of secondary rate limit failure (generally
    translating to).

.. warning::

    If trying to both run the test suite against github actual and work with
    local tests at the same time, it is necessary to use ``-o cache_dir``:
    pytest's cache feature (which is used by stepwise, last-failed,
    failed-first, etc...) is not compatible with concurrent runs so the two runs
    will influence one another and generate strange run states.

    It is likely preferrable for the run against github actual to use a bespoke
    ``cache_dir``, and for the "default" cache to be used by the (much faster
    and more reliable) local test runs.

    See `configuration options: cache_dir
    <https://docs.pytest.org/en/stable/reference/reference.html#confval-cache_dir>`_
    for more details.

.. [#git] especially since the switch to using git directly, as the mergebot's
          need to call the rate-limited github API has gone down
          *significantly*: as of writing this it's down to ~1500 calls/h whe
          running the test suite, ~300/h in production.
.. [#perf]
    Although it is not required, because of all the waiting around to leave time
    for webhooks to be dispatched the test suite has a pretty low level of
    average CPU utilisation (about 50%, of one core), and thus takes *ages* to
    complete. Using xdist is a very easy way to fill up the CPU with work, and
    thus complete the test suite faster.
.. [#owner] well that's how it's supposed to work anyway, I'm not sure I've ever
            tested it...
.. [#numprocesses]

    It does trigger the odd false negative but does so at a very reasonable
    (low) rate. ``auto`` (worker per core) *might be slightly more reliable, but
    on my current machine it mostly leads to a significant slowdown in wallclock
    run time, from::

        3 failed, 461 passed, 10 skipped, 2 xfailed in 1220.60s (0:20:20)
        5436.98s user 901.32s system 518% cpu 20:22.01 total

    to::

        2 failed, 462 passed, 10 skipped, 2 xfailed in 1972.72s (0:32:52)
        3687.33s user 671.44s system 220% cpu 32:54.30 total
