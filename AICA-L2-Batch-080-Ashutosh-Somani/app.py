from app import create_app

app = create_app()

if __name__ == "__main__":
    # app.py acts as a minimal Flask application entry point.
    # It is recommended to run via launcher.py for the full setup,
    # but this file allows standard Flask tooling to work.
    app.run()
