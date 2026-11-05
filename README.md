# Aeterna MF Engine

Rates every Indian equity and index mutual fund on its track record, and powers the public site at aeternawealth.com.

- `engine/`: data ingestion, metrics, category protocols, holdings analysis, AMC downloaders.
- `run_monthly.py`: full monthly run (`--daily` for the weekday-morning NAV refresh).
- `site/`: public website (`app.html`); `build_data.py` and `build_site.py` produce `site/dist/`.
- `.github/workflows/`: daily (08:45 IST, Tue–Sat) and monthly (12th) automation.
- `AGENTS.md`: methodology. `audit/`: Nov-2026 audit and backtest scripts.
