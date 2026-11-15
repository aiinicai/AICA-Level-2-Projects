def register_views(app):
    from . import auth, billing, calendar_view, clients, dashboard, reports, settings, staff, tasks, trackers, whatsapp, lookup, activity, timesheet, matters

    for module in (auth, dashboard, clients, trackers, calendar_view, tasks, billing, reports, staff, settings, whatsapp, lookup, activity, timesheet, matters):
        app.register_blueprint(module.bp)
