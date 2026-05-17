import os
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvType(str, Enum):
    DEV = "dev"
    RESEARCH = "research"
    PAPER = "paper"
    PROD = "prod"


class DataConfig(BaseModel):
    raw_dir: str = "data/raw"
    clean_dir: str = "data/clean"
    feature_dir: str = "data/feature"


class LogConfig(BaseModel):
    level: str = "INFO"
    file_path: Optional[str] = None


class SystemConfig(BaseSettings):
    env: EnvType = EnvType.DEV
    data: DataConfig = DataConfig()
    log: LogConfig = LogConfig()

    model_config = SettingsConfigDict(
        env_prefix="QTRADE_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def load_from_toml(cls, toml_path: str) -> "SystemConfig":
        import tomllib

        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
        return cls(**data)


_config_instance: Optional[SystemConfig] = None


def get_config() -> SystemConfig:
    global _config_instance
    if _config_instance is None:
        _config_instance = SystemConfig()
    return _config_instance


def init_config(toml_path: Optional[str] = None) -> SystemConfig:
    global _config_instance
    if toml_path and os.path.exists(toml_path):
        _config_instance = SystemConfig.load_from_toml(toml_path)
    else:
        _config_instance = SystemConfig()
    return _config_instance
