Forwardport Bot
===============

Extension to `runbot_merge` (the mergebot) to perform and handle porting forward
after merges.

Functionally deprecated in that it should be merged into `runbot_merge` and
removed. This was initially developed separately in case third parties might
want to use just the merge part, however:

- The mergebot is very specific to Odoo's requirements, and with the advent of
  tools like github's merge queues the likelihood a third party would need the
  mergebot are *extremely* remote.
- Forward-porting can be disabled by just not enabling it on a project, and for
  this purpose it would be better with a single module as this would ensure the
  base behaviour is not broken.
