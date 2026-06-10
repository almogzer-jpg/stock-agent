# -*- coding: utf-8 -*-
"""Email alert delivery via SMTP (Gmail by default).

Credentials are read from environment variables first, then from
email_config.json (kept out of version control). If nothing is configured,
send() is a safe no-op so the daily scan never fails because of email.

Environment variables (override the JSON file):
    STOCK_AGENT_SMTP_HOST, STOCK_AGENT_SMTP_PORT,
    STOCK_AGENT_EMAIL_SENDER, STOCK_AGENT_EMAIL_PASSWORD,
    STOCK_AGENT_EMAIL_RECIPIENT
"""
import json
import os
import smtplib
import ssl
from email.message import EmailMessage

from config import EMAIL_CONFIG_FILE


def _load_email_config() -> dict:
    """Build email settings from defaults + JSON file + environment vars."""
    cfg = {
        "smtp_host": "smtp.gmail.com",   # Gmail SMTP
        "smtp_port": 587,                # STARTTLS port
        "sender": "",
        "app_password": "",
        "recipient": "",
    }
    # Layer 1: JSON file (only non-empty values override the defaults).
    if os.path.exists(EMAIL_CONFIG_FILE):
        try:
            with open(EMAIL_CONFIG_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
            cfg.update({k: v for k, v in data.items()
                        if k in cfg and v not in (None, "")})
        except (OSError, ValueError):
            pass
    # Layer 2: environment variables take precedence (keep secrets off disk).
    env = os.environ
    cfg["smtp_host"] = env.get("STOCK_AGENT_SMTP_HOST", cfg["smtp_host"])
    cfg["smtp_port"] = int(env.get("STOCK_AGENT_SMTP_PORT", cfg["smtp_port"]))
    cfg["sender"] = env.get("STOCK_AGENT_EMAIL_SENDER", cfg["sender"])
    cfg["app_password"] = env.get("STOCK_AGENT_EMAIL_PASSWORD", cfg["app_password"])
    cfg["recipient"] = env.get("STOCK_AGENT_EMAIL_RECIPIENT", cfg["recipient"])
    return cfg


class EmailNotifier:
    """Sends an HTML+plain-text email via SMTP with STARTTLS."""

    def __init__(self):
        self.cfg = _load_email_config()

    def is_configured(self) -> bool:
        """True only when sender, app password, and recipient are all set."""
        c = self.cfg
        return bool(c["sender"] and c["app_password"] and c["recipient"])

    def send(self, subject: str, html_body: str, text_body: str = "",
             images: dict | None = None) -> bool:
        """Send the email. Returns True on success; never raises.

        `images` maps a content-id (referenced in the HTML as
        ``<img src="cid:THE_ID">``) to PNG bytes, embedded inline.
        """
        if not self.is_configured():
            print("  ! מייל לא מוגדר (ראו email_config.json) — דילוג על שליחה")
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.cfg["sender"]
        msg["To"] = self.cfg["recipient"]
        # Plain-text fallback for clients that don't render HTML.
        msg.set_content(text_body or "צפייה בגרסת ה‑HTML של ההודעה.")
        msg.add_alternative(html_body, subtype="html")

        # Attach inline images as 'related' parts of the HTML alternative.
        if images:
            html_part = msg.get_payload()[-1]
            for cid, data in images.items():
                html_part.add_related(data, "image", "png", cid=f"<{cid}>")

        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(self.cfg["smtp_host"], self.cfg["smtp_port"], timeout=30) as srv:
                srv.starttls(context=ctx)
                srv.login(self.cfg["sender"], self.cfg["app_password"])
                srv.send_message(msg)
            print(f"  ✓ מייל נשלח אל {self.cfg['recipient']}")
            return True
        except Exception as exc:  # auth/network errors shouldn't kill the run
            print(f"  ! שליחת המייל נכשלה: {exc}")
            return False
