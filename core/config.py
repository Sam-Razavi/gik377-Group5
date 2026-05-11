from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    bankid_mock_mode: bool = True
    bankid_base_url: str = "https://appapi2.test.bankid.com"
    bankid_cert_file: str = ""
    bankid_cert_password: str = ""
    bankid_ca_file: str = ""
    bankid_end_user_ip: str = "127.0.0.1"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
