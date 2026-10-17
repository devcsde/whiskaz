from whiskaz.engine import filter_hallucination


def test_known_outro_hallucination_is_dropped():
    assert filter_hallucination("Untertitel im Auftrag des ZDF") == ""


def test_normal_sentence_is_kept_and_stripped():
    assert filter_hallucination("  Das ist ein Test.  ") == "Das ist ein Test."


def test_long_text_containing_phrase_is_kept():
    text = "Untertitel im Auftrag des ZDF " + "und dann folgt noch ein sehr langer Satz " * 5
    assert filter_hallucination(text) == text.strip()
