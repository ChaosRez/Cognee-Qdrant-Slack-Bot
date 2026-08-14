from seal_bot.catalog import load_catalog
from seal_bot.models import MatchResult, SearchMatch
from seal_bot.slack import match_response, parse_slack_file_id


def test_parse_slack_file_reference():
    assert parse_slack_file_id("F012ABCDEF") == "F012ABCDEF"
    assert parse_slack_file_id("https://workspace.slack.com/files/U123/F012ABCDEF/photo.jpg") == "F012ABCDEF"
    assert parse_slack_file_id("https://example.com/image.jpg") is None


def test_match_response_contains_warning_and_confirmation():
    products = load_catalog()
    product = products[0]
    item = SearchMatch(product=product, score=0.91, raw_rank=3)
    unknown_dimensions = SearchMatch(product=products[3], score=0.80, raw_rank=4)
    result = MatchResult(
        case_id="seal-abc123",
        query_label="demo.jpg",
        query_sha256="sha",
        raw_matches=(item, unknown_dimensions),
        displayed_matches=(item, unknown_dimensions),
        override_applied=True,
        override_reason="known demo",
        actor="U123",
    )

    response = match_response(result)
    rendered = str(response)

    assert "F3267" in rendered
    assert "Raw Hyper3/Qdrant rank" in rendered
    assert "Always measure" in rendered
    assert "not listed" in rendered
    assert "/seal-confirm seal-abc123 F3267" in rendered
