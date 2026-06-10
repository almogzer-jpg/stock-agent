# -*- coding: utf-8 -*-
"""Alert delivery: console + file log (free, zero-setup)."""
from datetime import datetime

from config import ALERTS_LOG, DATE_FMT


class Notifier:
    """Sends alerts to the console and appends them to a log file.

    Kept deliberately small so other channels (Telegram, email) can subclass
    and override send() without touching the rest of the agent.
    """

    def __init__(self, log_path: str = ALERTS_LOG):
        self.log_path = log_path
        self.history: list[dict] = []   # every alert sent this run (for alerts.csv)

    def send(self, message: str, level: str = "מידע") -> None:
        """Print the alert and append it to the log file (DD/MM/YYYY HH:MM)."""
        ts = datetime.now().strftime(DATE_FMT + " %H:%M")
        line = f"[{ts}] {level}: {message}"
        print(line)
        self.history.append({"זמן": ts, "רמה": level, "הודעה": message})
        try:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError as exc:
            print(f"  ! could not write alert log: {exc}")
