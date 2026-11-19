try:
    import keyring
    for sid in ["gemini", "finnhub", "trading_economics"]:
        try:
            keyring.delete_password("Finstock.EventScope", sid)
            print(f"Deleted keyring password for {sid}")
        except Exception as e:
            print(f"Keyring {sid} not present or: {e}")
except Exception as e:
    print("Keyring import error:", e)
