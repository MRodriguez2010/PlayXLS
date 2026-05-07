from playxls.transport import TransportSnapshot, format_timestamp


def test_format_timestamp_uses_hours_only_when_needed():
    assert format_timestamp(None) == "--:--"
    assert format_timestamp(-4) == "00:00"
    assert format_timestamp(42.4) == "00:42"
    assert format_timestamp(184.8) == "03:05"
    assert format_timestamp(3661) == "1:01:01"


def test_transport_snapshot_clamps_progress_percent():
    assert TransportSnapshot(position=42, duration=184, paused=False).progress_percent == 22.82608695652174
    assert TransportSnapshot(position=200, duration=184, paused=False).progress_percent == 100.0
    assert TransportSnapshot(position=12, duration=0, paused=True).progress_percent == 0.0
