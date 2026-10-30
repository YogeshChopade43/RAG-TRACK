"""Section boost: a query naming a chunk's section heading favours that chunk."""
from app.services.retrieval.hybrid_service import names_section


def test_single_keyword_heading_matches_singular_and_plural():
    assert names_section(["Skills"], "what skill does he have")
    assert names_section(["Education"], "where was his education?")


def test_docling_title_plus_section_still_matches():
    assert names_section(["John Doe", "Experience"], "what experience does he have")


def test_multi_word_heading_matches_on_a_word():
    assert names_section(["Work Experience"], "summarise his experience")
    assert names_section(["Technical Skills"], "list technical abilities")


def test_unrelated_query_and_short_words_do_not_match():
    assert not names_section(["Experience"], "what is his phone number")
    assert not names_section(["Q&A of it"], "what is it")
    assert not names_section([], "experience")
