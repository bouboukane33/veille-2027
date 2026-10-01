import json

import pytest

from src.utils.config import load_config


@pytest.mark.parametrize("change", [
    {"lookback_days": 0}, {"enable_news": "false"}, {"max_youtube_videos_per_personality": 51},
    {"visibility_weights": {"news": .5, "views": .3, "engagement": .15, "frequency": .2}},
    {"visibility_weights": {"news": float("nan"), "views": .3, "engagement": .15, "frequency": .2}},
])
def test_configuration_rejects_invalid_settings_before_collecting(config, change):
    path = config.root / "config" / "settings.json"
    path.write_text(json.dumps(config.settings | change), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(config.root)


def test_minimal_requested_settings_use_safe_defaults(config):
    settings = {k: config.settings[k] for k in ("lookback_days", "max_news_per_personality",
        "max_youtube_videos_per_personality", "enable_news", "enable_youtube")}
    (config.root / "config" / "settings.json").write_text(json.dumps(settings))
    assert load_config(config.root).settings["request_timeout_seconds"] == 15
