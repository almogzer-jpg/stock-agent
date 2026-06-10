"""news/ — free headline feed.

Best-effort recent headlines per ticker via yfinance (Yahoo Finance). No paid
APIs. Returns [] on any failure — news is an enrichment, never load-bearing.
Extend later with sentiment scoring or extra free RSS sources.
"""
