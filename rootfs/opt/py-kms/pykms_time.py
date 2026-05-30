"""Timestamp parsing helpers (no py-kms dependencies)."""

import datetime


def parse_ts(ts):
    """Unix epoch from int, numeric string, or ISO datetime (py-kms variants)."""
    if ts is None or ts == '':
        return None
    if isinstance(ts, bool):
        return None
    if isinstance(ts, (int, float)):
        return int(ts)
    if isinstance(ts, str):
        s = ts.strip()
        if not s:
            return None
        if s.isdigit():
            return int(s)
        try:
            return int(float(s))
        except ValueError:
            pass
        iso = s[:-1] + '+00:00' if s.endswith('Z') else s
        try:
            return int(datetime.datetime.fromisoformat(iso).timestamp())
        except ValueError:
            pass
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
            try:
                return int(datetime.datetime.strptime(s, fmt).timestamp())
            except ValueError:
                continue
    return None


def format_ts(ts):
    parsed = parse_ts(ts)
    if parsed is None:
        return 'Never'
    return datetime.datetime.fromtimestamp(parsed).strftime('%Y-%m-%d %H:%M:%S')
