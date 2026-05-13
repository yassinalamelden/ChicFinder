# tests/test_config.py
"""Unit tests for chic_finder.config.Config."""
import pytest
from chic_finder.config import Config, settings


@pytest.mark.unit
def test_api_v1_str_default():
    assert settings.API_V1_STR == "/api/v1"


@pytest.mark.unit
def test_project_name_default():
    assert settings.PROJECT_NAME == "ChicFinder"


@pytest.mark.unit
def test_get_image_url_format():
    cfg = Config()
    cfg.SUPABASE_URL = "https://abc.supabase.co"
    url = cfg.get_image_url("zara_001_0")
    assert url == "https://abc.supabase.co/storage/v1/object/public/product-images/zara_001_0.jpg"


@pytest.mark.unit
def test_get_image_url_no_double_extension():
    cfg = Config()
    cfg.SUPABASE_URL = "https://abc.supabase.co"
    url = cfg.get_image_url("zara_001_0.jpg")
    assert url.endswith(".jpg")
    assert ".jpg.jpg" not in url


@pytest.mark.edge
def test_get_image_url_raises_without_supabase_url():
    cfg = Config()
    cfg.SUPABASE_URL = ""
    with pytest.raises(RuntimeError, match="SUPABASE_URL is not configured"):
        cfg.get_image_url("any_file")


@pytest.mark.unit
def test_embedding_dim_is_512():
    assert settings.EMBEDDING_DIM == 512


@pytest.mark.unit
def test_gemini_model_default():
    assert settings.GEMINI_MODEL == "gemini-2.5-flash"
