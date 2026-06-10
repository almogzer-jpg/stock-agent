"""alerts/ — alert delivery.

Currently a console + file-log notifier (zero setup, fully free). The Notifier
interface is intentionally simple (.send(message, level)) so additional
channels (Telegram, email) can be added as drop-in subclasses later.
"""
