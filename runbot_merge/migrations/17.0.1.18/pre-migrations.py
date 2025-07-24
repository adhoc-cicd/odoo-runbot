def migrate(cr, _version):
    cr.execute("UPDATE ir_module_module SET state = 'to remove' WHERE name = 'forwardport'")
    cr.execute("""
    UPDATE ir_model_data a
       SET module = 'runbot_merge'
     WHERE module = 'forwardport'
       AND model IN (
           'ir.actions.act_window',
           'ir.actions.server',
           'ir.cron',
           'ir.model',
           'ir.model.access',
           'ir.model.fields',
           'ir.model.fields.selection',
           'ir.model.inherit',
           'ir.model.relations',
           'ir.ui.menu'
       )
       AND NOT EXISTS (
         SELECT FROM ir_model_data
          WHERE module = 'runbot_merge'
            AND name = a.name
       );
    """)
    # only move primary views as extensions have been merged into the base views
    cr.execute("""
    UPDATE ir_model_data
       SET module = 'runbot_merge'
      FROM ir_ui_view
     WHERE module = 'forwardport'
       AND ir_model_data.model = 'ir.ui.view'
       AND res_id = ir_ui_view.id
       AND ir_ui_view.mode = 'primary'
    """)
