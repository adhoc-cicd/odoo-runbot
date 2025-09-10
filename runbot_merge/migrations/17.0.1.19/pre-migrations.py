def migrate(cr, _version):
    cr.execute("""
    ALTER TYPE runbot_merge_batch_priority_type
        ADD VALUE 'nice' BEFORE 'default';

    -- old migration from splitting out batch which I apparently never completed
    ALTER TABLE runbot_merge_pull_requests
        DROP COLUMN priority;
    DROP TYPE runbot_merge_pull_requests_priority_type;

    ALTER TABLE runbot_merge_batch
        DROP COLUMN priority_moved0;
    DROP TYPE runbot_merge_batch_priority;

    ALTER TABLE runbot_merge_batch
        ADD COLUMN unblocked_at timestamp;
    UPDATE runbot_merge_batch
       SET unblocked_at = write_date
     WHERE blocked is null;
    """)
