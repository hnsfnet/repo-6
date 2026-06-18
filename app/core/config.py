import os
from dataclasses import dataclass, field
from typing import Dict, Any
import yaml


@dataclass
class ChannelConfig:
    type: str = "websocket"
    enabled: bool = True
    settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AppConfig:
    message_store_type: str = "in_memory"
    default_channel: str = "websocket"
    channels: Dict[str, ChannelConfig] = field(default_factory=dict)
    group_channels: Dict[str, str] = field(default_factory=dict)


_config: AppConfig = AppConfig()


def load_config(config_path: str = None) -> AppConfig:
    global _config

    if config_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        config_path = os.path.join(base_dir, "config", "app_config.yaml")

    default_channels = {
        "websocket": ChannelConfig(type="websocket", enabled=True)
    }
    _config = AppConfig(channels=default_channels)

    if not os.path.exists(config_path):
        return _config

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    _config.message_store_type = raw.get("message_store", {}).get("type", "in_memory")
    _config.default_channel = raw.get("channels", {}).get("default", "websocket")

    channel_configs = raw.get("channels", {}).get("list", {})
    for ch_name, ch_data in channel_configs.items():
        _config.channels[ch_name] = ChannelConfig(
            type=ch_data.get("type", ch_name),
            enabled=ch_data.get("enabled", True),
            settings=ch_data.get("settings", {})
        )

    _config.group_channels = raw.get("channels", {}).get("group_mapping", {})

    return _config


def get_config() -> AppConfig:
    return _config
