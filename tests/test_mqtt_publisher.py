import pytest
from unittest.mock import patch, MagicMock
from mqtt_publisher import publish

@patch("mqtt_publisher.mqtt.Client")
def test_mqtt_publisher_success(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    record = {
        "site_id": "demo_site_001",
        "data_source": "mock",
        "utc_timestamp": "2026-09-08T18:56:17Z",
        "stale": False,
        "solar_power_w": 4191.0,
        "battery_power_w": 3698.0,
        "battery_soc_pct": 55.0,
        "grid_power_w": 0.0,
        "load_power_w": 493.0,
        "energy_today_kwh": 27.7,
        "energy_lifetime_kwh": 12477.7
    }
    
    result = publish(record)
    assert result is True
    
    # Verify LWT (Last Will and Testament) is set correctly
    mock_client.will_set.assert_called_once()
    
    # Verify connection and publication parameters
    mock_client.connect.assert_called_once()
    mock_client.publish.assert_called_once()
    
    args, kwargs = mock_client.publish.call_args
    assert args[0] == "solar/site/demo_site_001/telemetry"
    assert kwargs.get("qos") == 1
    assert kwargs.get("retain") is False

@patch("mqtt_publisher.mqtt.Client")
def test_mqtt_publisher_failure_handling(mock_client_class):
    mock_client = MagicMock()
    # Force an exception during publish to test error logging and safe return
    mock_client.publish.side_effect = Exception("Connection error")
    mock_client_class.return_value = mock_client
    
    record = {"site_id": "demo_site_001"}
    result = publish(record)
    
    # Must return False and log the error without raising an exception
    assert result is False
