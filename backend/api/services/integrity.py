"""Timing-anomaly signals for human review — never evidence of fraud, and
never identifies who cast which ballot. Signals: consecutive ballots under
5 seconds apart, and any 60-second window holding more than 10 ballots."""

from api.models import Ballot

RAPID_SUCCESSION_THRESHOLD_SECONDS = 5
VELOCITY_WINDOW_SECONDS = 60
VELOCITY_THRESHOLD = 10


def _ordered_timestamps(election):
    return list(
        Ballot.objects.filter(election=election)
        .order_by("submitted_at")
        .values_list("submitted_at", flat=True)
    )


def find_rapid_succession_pairs(election):
    timestamps = _ordered_timestamps(election)
    pairs = []
    for previous, current in zip(timestamps, timestamps[1:]):
        gap = (current - previous).total_seconds()
        if gap < RAPID_SUCCESSION_THRESHOLD_SECONDS:
            pairs.append({"gap_seconds": round(gap, 1), "timestamp": current.isoformat()})
    return pairs


def find_velocity_bursts(election):
    """Reports one entry per distinct burst episode — the window position
    where the count first exceeds the threshold — rather than every sliding
    window position while a burst is ongoing, which would otherwise flood a
    single incident into dozens of near-duplicate entries. Not specified by
    03-API-SPEC.md; a deliberate choice, logged in docs/PROGRESS.md."""
    timestamps = _ordered_timestamps(election)
    bursts = []
    start = 0
    in_burst = False
    for end in range(len(timestamps)):
        while (timestamps[end] - timestamps[start]).total_seconds() > VELOCITY_WINDOW_SECONDS:
            start += 1
        count = end - start + 1
        if count > VELOCITY_THRESHOLD:
            if not in_burst:
                bursts.append(
                    {"window_end": timestamps[end].isoformat(), "ballots_in_window": count}
                )
                in_burst = True
        else:
            in_burst = False
    return bursts
