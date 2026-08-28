import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.twitter_bot import twitter_bot

client = TestClient(app)


def test_twitter_alert_generators():
    """Verify all tweet alert generation methods return properly formatted text."""
    arb_tweet = twitter_bot.generate_arbitrage_tweet()
    assert "[MARKET SPREAD]" in arb_tweet
    assert "#Polygon" in arb_tweet
    assert "dashboard" in arb_tweet

    um_tweet = twitter_bot.generate_urban_mining_tweet()
    assert "[SCRAP YIELD]" in um_tweet
    assert "Net Settlement Value" in um_tweet
    assert "#UrbanMining" in um_tweet
    assert "dashboard" in um_tweet

    summary_tweet = twitter_bot.generate_market_summary_tweet()
    assert "[SPOT BENCHMARK]" in summary_tweet
    assert "Silver" in summary_tweet
    assert "Copper" in summary_tweet
    assert "dashboard" in summary_tweet


@pytest.mark.asyncio
async def test_twitter_post_simulation_mode():
    """Verify dry-run simulation mode returns simulated result object."""
    sample_text = twitter_bot.generate_arbitrage_tweet()
    result = await twitter_bot.post_tweet(sample_text, dry_run=True)
    assert result["status"] == "simulated"
    assert result["mode"] == "dry_run"
    assert result["length"] == len(sample_text)


def test_twitter_preview_endpoint():
    """Verify GET /api/v1/oracle/twitter-alerts/preview returns valid tweets."""
    resp = client.get("/api/v1/oracle/twitter-alerts/preview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "sample_tweets" in data
    assert "arbitrage_alert" in data["sample_tweets"]
    assert "urban_mining_alert" in data["sample_tweets"]


def test_twitter_dispatch_endpoint_dry_run():
    """Verify POST /api/v1/oracle/twitter-alerts/dispatch executes in dry-run mode."""
    resp = client.post("/api/v1/oracle/twitter-alerts/dispatch?alert_type=arbitrage&dry_run=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "simulated"
    assert "[MARKET SPREAD]" in data["tweet_text"]


def test_web_dashboard_endpoints():
    """Verify /dashboard and /playground serve HTML web UI."""
    resp_dash = client.get("/dashboard")
    assert resp_dash.status_code == 200
    assert "text/html" in resp_dash.headers["content-type"]
    assert "Urban Mining" in resp_dash.text
    assert "Minerals Oracle" in resp_dash.text

    resp_play = client.get("/playground")
    assert resp_play.status_code == 200
    assert "Minerals Oracle" in resp_play.text

    # Root with browser Accept header
    resp_root_html = client.get("/", headers={"accept": "text/html,application/xhtml+xml"})
    assert resp_root_html.status_code == 200
    assert "text/html" in resp_root_html.headers["content-type"]
