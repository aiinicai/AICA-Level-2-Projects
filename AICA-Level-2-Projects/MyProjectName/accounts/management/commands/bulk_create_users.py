"""
Bulk-create login accounts from an Excel sheet of Username/password pairs.

Built for onboarding many users at once (e.g. from an HR export) without
re-keying each one through the admin. Two things this command deliberately
does differently from the normal account-creation path:

1. Passwords are set with `set_password()` directly, which never calls
   Django's `AUTH_PASSWORD_VALIDATORS` — so a password from the sheet that
   wouldn't pass the site's normal password policy is still accepted
   exactly as given. This was an explicit, deliberate request; it does mean
   these accounts may have weaker passwords than the policy would normally
   allow, so treat the sheet itself as sensitive and delete/secure it after
   the import.
2. Every created account is forced to `is_staff=False, is_superuser=False`
   and is NOT added to any RBAC group — a bare login with no permissions
   beyond authenticating. No row in the sheet can grant superuser/admin
   access, regardless of what's in the sheet. If a username in the sheet
   collides with an EXISTING superuser account, that row is skipped
   entirely (not even the password is touched) so this command can never
   be used to overwrite an admin account's credentials.

Usage:
    python manage.py bulk_create_users path/to/usercreate.xlsx
    python manage.py bulk_create_users path/to/usercreate.xlsx --dry-run

Expected sheet layout: first row is a header, then one row per user with
the username in column A and the password in column B (column names are
read but not required to match exactly — the first two columns are used
positionally).
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = "Bulk-create bare login accounts (no role, no staff/superuser access) from an Excel sheet of Username/password pairs."

    def add_arguments(self, parser):
        parser.add_argument("excel_path", help="Path to the .xlsx file (Username in column A, password in column B).")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Show what would happen without writing anything to the database.",
        )

    def handle(self, *args, **options):
        try:
            import openpyxl
        except ImportError:
            raise CommandError("openpyxl is required for this command — run: pip install openpyxl")

        path = options["excel_path"]
        dry_run = options["dry_run"]

        try:
            wb = openpyxl.load_workbook(path, data_only=True)
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")
        ws = wb.active

        rows = list(ws.iter_rows(min_row=2, values_only=True))
        created, updated, skipped_superuser, skipped_blank = [], [], [], 0

        for row in rows:
            if not row or row[0] is None or str(row[0]).strip() == "":
                skipped_blank += 1
                continue
            username = str(row[0]).strip()
            password = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
            if not password:
                self.stderr.write(self.style.WARNING(f"  ! {username}: no password in sheet, skipped"))
                continue

            existing = User.objects.filter(username=username).first()
            if existing and (existing.is_superuser or existing.is_staff):
                skipped_superuser.append(username)
                self.stderr.write(self.style.WARNING(
                    f"  ! {username}: existing account has staff/superuser access — left untouched for safety"
                ))
                continue

            if dry_run:
                (created if not existing else updated).append(username)
                continue

            user, was_created = User.objects.get_or_create(username=username)
            user.is_staff = False
            user.is_superuser = False
            user.set_password(password)
            user.save()
            # Deliberately not added to any group — bare login only, per request.
            (created if was_created else updated).append(username)

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Created: {len(created)}, updated (password reset): {len(updated)}, "
            f"blank rows skipped: {skipped_blank}, existing staff/superuser accounts skipped: {len(skipped_superuser)}"
        ))
        if skipped_superuser:
            self.stdout.write(self.style.WARNING(
                "The following usernames already exist as staff/superuser accounts and were NOT modified: "
                + ", ".join(skipped_superuser)
            ))
        if not dry_run:
            self.stdout.write(
                "All accounts created with is_staff=False, is_superuser=False, and no RBAC group assigned. "
                "Assign roles individually from /admin/ (Users → select user → Groups) if/when needed."
            )
