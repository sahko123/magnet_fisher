"""Human-readable formatting helpers."""


def format_size(n: int) -> str:
    """Format bytes as a human-readable size string."""
    if n < 0:
        return '—'
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024:
            return f'{n:.1f} {unit}'
        n /= 1024
    return f'{n:.1f} PB'


def format_rate(bps: float) -> str:
    """Format bytes-per-second as a human-readable rate."""
    return format_size(int(bps)) + '/s'


def format_eta(seconds: float) -> str:
    """Format seconds remaining as a human-readable ETA."""
    if seconds <= 0 or seconds != seconds:  # <= 0 or NaN
        return '—'
    secs = int(seconds)
    if secs < 60:
        return f'{secs}s'
    if secs < 3600:
        return f'{secs // 60}m {secs % 60}s'
    h = secs // 3600
    m = (secs % 3600) // 60
    return f'{h}h {m}m'


def format_progress(downloaded: int, total: int) -> str:
    """Format downloaded/total as a human-readable string."""
    if total <= 0:
        return '—'
    return f'{format_size(downloaded)} / {format_size(total)}'
