from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = "127.0.0.1"
    app_port: int = 8787
    app_secret: str = "change-me"

    mt5_path: str = ""
    mt5_login: int | None = None
    mt5_password: str = ""
    mt5_server: str = ""

    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
    llm_timeout_seconds: int = 60

    watchlist: str = "XAUUSD,XTIUSD,US30,EURUSD,BTCUSD"
    default_timeframes: str = "M15,H1,H4,D1"
    risk_per_trade_pct: float = 1.0

    def watch_symbols(self) -> list[str]:
        return [s.strip().upper() for s in self.watchlist.split(",") if s.strip()]

    def timeframes(self) -> list[str]:
        return [s.strip().upper() for s in self.default_timeframes.split(",") if s.strip()]


settings = Settings()
