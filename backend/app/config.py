from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://tidenursery:tidenursery@localhost:5434/tidenursery"
    jwt_secret: str = "tide-nursery-jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    # 换入水约定默认盐度（ppt）：结束冲程自动追加水质样时使用，详见 README
    inlet_default_salinity_ppt: float = 30.0


settings = Settings()
