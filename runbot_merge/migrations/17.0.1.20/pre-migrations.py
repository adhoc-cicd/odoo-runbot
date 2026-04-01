def migrate(cr, _version):
    cr.execute("""
ALTER TYPE runbot_merge_acls_state_type
    RENAME TO runbot_merge_acls_effect_type;
""")