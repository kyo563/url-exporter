from scripts.duration import parse_iso8601_duration_to_seconds


def test_parse_duration_valid_cases() -> None:
    assert parse_iso8601_duration_to_seconds("PT1H2M3S") == 3723
    assert parse_iso8601_duration_to_seconds("PT15M") == 900
    assert parse_iso8601_duration_to_seconds("PT45S") == 45
    assert parse_iso8601_duration_to_seconds("PT0S") == 0


def test_parse_duration_invalid_case() -> None:
    assert parse_iso8601_duration_to_seconds("INVALID") is None
