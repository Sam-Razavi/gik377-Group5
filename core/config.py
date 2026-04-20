from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    bankid_base_url: str
    bankid_cert_file: str
    bankid_cert_password: str
    bankid_ca_file: str
    bankid_end_user_ip: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()