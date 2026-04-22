"""
Configuration models for Meeting Cost Tracker.
"""

from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CostRates(BaseModel):
    """Cost rate configuration."""
    
    # Default hourly rate if no specific rate found
    default_rate: float = Field(default=100.0, description="Default hourly rate in USD")
    
    # Per-person rates (email -> hourly rate)
    person_rates: Dict[str, float] = Field(default_factory=dict, description="Per-person hourly rates")
    
    # Role-based rates (role name -> hourly rate)
    role_rates: Dict[str, float] = Field(default_factory=lambda: {
        "engineer": 100.0,
        "senior_engineer": 125.0,
        "manager": 150.0,
        "senior_manager": 175.0,
        "director": 200.0,
        "vp": 250.0,
        "c_level": 300.0,
        "contractor": 150.0,
    }, description="Role-based hourly rates")
    
    # Organization rates (domain -> hourly rate)
    org_rates: Dict[str, float] = Field(default_factory=dict, description="Organization domain rates")


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        yaml_file='~/.meeting-cost-tracker/config.yaml',
        yaml_file_encoding='utf-8',
        extra='ignore',
    )
    
    # Microsoft Graph settings
    tenant_id: str = Field(default="common", description="Azure AD tenant ID")
    client_id: str = Field(default="", description="Azure AD app client ID")
    
    # Cost configuration
    costs: CostRates = Field(default_factory=CostRates, description="Cost rate settings")
    
    # Cache settings
    cache_dir: Path = Field(default=Path.home() / ".meeting-cost-tracker" / "cache")
    
    @field_validator('cache_dir')
    @classmethod
    def expand_cache_dir(cls, v: Path) -> Path:
        """Expand user home directory in cache path."""
        return v.expanduser().resolve()


def load_config() -> AppConfig:
    """Load configuration from file."""
    try:
        return AppConfig()
    except Exception:
        return AppConfig()
