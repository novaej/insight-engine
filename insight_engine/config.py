from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    openai_model: str
    azure_translator_key: str
    azure_translator_endpoint: str
    azure_translator_region: str

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
