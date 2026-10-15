from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = "127.0.0.1"
    app_port: int = 8787
    app_open_browser: bool = False

    @field_validator("app_host")
    @classmethod
    def local_only_host(cls, value: str) -> str:
        host = value.strip().lower()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("The private desk can only bind to a loopback address")
        return host

    mt5_path: str = ""
    mt5_portable: bool = False
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 60

    watchlist: str = "XAUUSD,XAGUSD,XTIUSD,US30,NAS100,EURUSD,GBPUSD,BTCUSD,ETHUSD"
    default_timeframes: str = "M15,H1,H4,D1"
    risk_per_trade_pct: float = 1.0

    def watch_symbols(self) -> list[str]:
        return [s.strip().upper() for s in self.watchlist.split(",") if s.strip()]

    def timeframes(self) -> list[str]:
        return [s.strip().upper() for s in self.default_timeframes.split(",") if s.strip()]


settings = Settings()
