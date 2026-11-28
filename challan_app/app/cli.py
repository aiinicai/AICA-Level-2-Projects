import click
from werkzeug.security import generate_password_hash

from .extensions import db
from .models import ADMIN, MNRC, MRC, Plant, SeriesConfig, User


def bootstrap(admin_password="admin123"):
    """Create tables and the minimum data needed to log in. Safe to run repeatedly."""
    db.create_all()
    if not db.session.get(SeriesConfig, MRC):
        db.session.add(SeriesConfig(ctype=MRC, prefix="MRC", fy_style="short", pad=4,
                                    title="Manual Returnable Challan", returnable=True))
        db.session.add(SeriesConfig(ctype=MNRC, prefix="MNRC", fy_style="short", pad=4,
                                    title="Manual Non-Returnable Challan", returnable=False))
    if not User.query.filter_by(username="admin").first():
        db.session.add(User(username="admin", full_name="Administrator", role=ADMIN,
                            password_hash=generate_password_hash(admin_password), must_change_password=True))
    db.session.commit()


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create tables, numbering series and the default admin login (admin / admin123)."""
        bootstrap()
        click.echo("Database ready. Login: admin / admin123 (you must change the password at first login).")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Load demo plant, users, vendors and a few challans."""
        from .sample_data import load_demo
        bootstrap()
        load_demo()
        click.echo("Demo data loaded. Users: admin/admin123, requester1/Demo@1234, approver1/Demo@1234")
