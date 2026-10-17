from whiskaz.dictionary import Correction, Dictionary, compile_pattern, warnings_for


def make(*pairs):
    return Dictionary(corrections=[Correction(s, t) for s, t in pairs])


def test_spaced_hyphenated_and_glued_variants_are_caught():
    d = make(("cloud code", "Claude Code"))
    text, applied = d.apply("I use cloud code, CloudCode and Cloud-Code today")
    assert text == "I use Claude Code, Claude Code and Claude Code today"
    assert applied == [("cloud code", "Claude Code", 3)]


def test_common_prefix_word_is_not_touched():
    d = make(("cloud code", "Claude Code"))
    text, applied = d.apply("Cloudflare and the cloud are fine")
    assert text == "Cloudflare and the cloud are fine"
    assert applied == []


def test_single_word_rule_respects_word_boundaries():
    d = make(("cloud", "Claude"))
    text, _ = d.apply("cloud, Cloudflare, clouds, cloud.")
    assert text == "Claude, Cloudflare, clouds, Claude."


def test_longest_source_wins():
    d = make(("cloud", "Claude"), ("cloud code", "Claude Code"))
    text, _ = d.apply("cloud code")
    assert text == "Claude Code"


def test_umlauts_are_word_characters():
    d = make(("muller", "Müller"))
    text, _ = d.apply("Herr muller, nicht mullerei")
    assert text == "Herr Müller, nicht mullerei"


def test_replacement_is_literal_even_with_backslashes():
    d = make(("path", r"C:\new"))
    text, _ = d.apply("open path")
    assert text == r"open C:\new"


def test_pattern_is_case_insensitive():
    assert compile_pattern("supabase").search("SUPABASE")


def test_empty_source_yields_no_pattern():
    assert compile_pattern("   ") is None


def test_warning_for_single_common_word():
    assert warnings_for("cloud")
    assert not warnings_for("cloud code")


def test_bias_prompt_is_capped():
    d = Dictionary(words=[f"w{i}" for i in range(50)])
    assert len(d.bias_prompt().split(", ")) == 20
