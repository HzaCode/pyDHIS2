"""Tests for configuration classes"""

import pytest
from pydantic import ValidationError

from pydhis2.core.types import DHIS2Config, AuthMethod


def test_dhis2_config_valid():
    """Test valid configuration"""
    config = DHIS2Config(
        base_url="https://play.dhis2.org/2.41",
        auth=("user", "pass"),
        rps=10.0,
        concurrency=5,
    )
    
    assert config.base_url == "https://play.dhis2.org/2.41"
    assert config.auth == ("user", "pass")
    assert config.auth_method == AuthMethod.BASIC
    assert config.rps == 10.0
    assert config.concurrency == 5


def test_dhis2_config_url_validation():
    """Test URL validation"""
    with pytest.raises(ValidationError):
        DHIS2Config(
            base_url="invalid-url",
            auth=("user", "pass")
        )


def test_dhis2_config_url_trailing_slash():
    """Test handling of trailing slash in URL"""
    config = DHIS2Config(
        base_url="https://play.dhis2.org/2.41/",
        auth=("user", "pass")
    )
    
    assert config.base_url == "https://play.dhis2.org/2.41"


def test_dhis2_config_timeout_validation():
    """Test timeout validation"""
    with pytest.raises(ValidationError):
        DHIS2Config(
            base_url="https://play.dhis2.org/2.41",
            auth=("user", "pass"),
            timeout=-1  # negative timeout
        )


def test_dhis2_config_auth_validation():
    """Test authentication validation"""
    # Valid tuple
    config1 = DHIS2Config(
        base_url="https://play.dhis2.org/2.41",
        auth=("user", "pass")
    )
    assert config1.auth == ("user", "pass")
    
    # Valid token
    config2 = DHIS2Config(
        base_url="https://play.dhis2.org/2.41",
        auth="token123"
    )
    assert config2.auth == "token123"
    
    # Invalid tuple
    with pytest.raises(ValidationError):
        DHIS2Config(
            base_url="https://play.dhis2.org/2.41",
            auth=("user",)  # Only one element
        )
