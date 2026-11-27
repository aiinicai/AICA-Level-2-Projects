"""
Audit trail: a time-stamped log of every import, remap, override and export,
kept per session and written into the Excel workbook ('Audit Trail' sheet).
"""
import datetime as dt


class AuditTrail:
    def __init__(self):
        self.entries = []

    def log(self, action, detail="", user="Preparer"):
        self.entries.append({
            "time": dt.datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
            "user": user,
            "action": action,
            "detail": detail,
        })

    def rows(self):
        return [(e["time"], e["user"], e["action"], e["detail"]) for e in self.entries]

    def clear(self):
        self.entries = []


TRAIL = AuditTrail()
