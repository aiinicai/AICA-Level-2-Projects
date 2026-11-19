from django.core.management.base import BaseCommand

from workflow.recurrence import generate_due_tasks


class Command(BaseCommand):
    help = "Create tasks for recurring deadlines whose lead window has opened (all firms). Schedule daily via cron."

    def handle(self, *args, **options):
        result = generate_due_tasks()
        self.stdout.write(self.style.SUCCESS(f"{result['tasks_created']} task(s) created from {result['rules_checked']} rule(s)."))
