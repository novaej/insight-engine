from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    openai_model: str
    azure_translator_key: str
    azure_translator_endpoint: str
    azure_translator_region: str

    # Email alerts / monitoring (all optional; app boots without them)
    mailgun_api_key: str = ""
    mailgun_domain: str = ""
    mailgun_from_email: str = ""
    monitoring_token: str = ""
    monitoring_enabled: bool = False
    monitoring_cron: str = "0 9 * * *"  # daily at 09:00

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
