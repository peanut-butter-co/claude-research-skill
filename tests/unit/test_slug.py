import pytest
from scripts.slug import make_slug


def test_fr002a_worked_example():
    assert make_slug("Compare jest, vitest, and playwright on speed") == "compare-jest-vitest-playwright-speed"


def test_stop_words_dropped():
    assert make_slug("the quick fox") == "quick-fox"
    assert make_slug("a vs an or and") == ""
    assert make_slug("testing for the win with style") == "testing-win-style"


def test_punctuation_stripped():
    assert make_slug("hello, world.") == "hello-world"
    assert make_slug('"quoted" title') == "quoted-title"
    assert make_slug("one...two") == "onetwo"


def test_result_is_lowercase():
    assert make_slug("UPPER CASE WORDS") == "upper-case-words"
    assert make_slug("MiXeD CaSe") == "mixed-case"


def test_60_char_cap_word_boundary():
    topic = "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo"
    result = make_slug(topic)
    assert len(result) <= 60
    assert not result.endswith("-")
    assert result == "alpha-bravo-charlie-delta-echo-foxtrot-golf-hotel-india"


def test_first_word_over_60_chars_truncated_at_60():
    long_word = "a" * 80
    result = make_slug(long_word)
    assert len(result) == 60
    assert result == "a" * 60


def test_unicode_input_ascii_safe_output():
    assert make_slug("café résumé naïve") == "cafe-resume-naive"
    assert make_slug("日本語 english") == "english"


def test_short_input_unchanged():
    assert make_slug("benchmarks") == "benchmarks"
    assert make_slug("rust python go") == "rust-python-go"


def test_all_stop_words_returns_empty_string():
    assert make_slug("the and or a an") == ""
    assert make_slug("to for of in on") == ""
