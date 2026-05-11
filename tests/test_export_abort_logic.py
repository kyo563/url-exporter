from scripts.export_urls import should_abort_before_write


def test_should_abort_default_true_when_partial_api_error() -> None:
    assert should_abort_before_write(True, 3, True) is True


def test_should_abort_when_api_error_and_zero_urls_even_if_flag_false() -> None:
    assert should_abort_before_write(True, 0, False) is True


def test_should_not_abort_when_partial_allowed() -> None:
    assert should_abort_before_write(True, 3, False) is False


def test_should_not_abort_when_no_api_error_and_zero_urls() -> None:
    assert should_abort_before_write(False, 0, True) is False


def test_should_not_abort_when_no_api_error_and_urls_exist() -> None:
    assert should_abort_before_write(False, 2, True) is False
