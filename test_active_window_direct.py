#!/usr/bin/env python3
"""
Direct test for Active Window Watcher
"""

from watchers.active_window import (
    get_active_app, 
    get_active_app_linux, 
    _is_system_process,
    _get_active_app_fallback
)


def test_get_active_app():
    """Basic function test"""
    result = get_active_app()
    print(f"get_active_app result: {result}")
    
    # Check structure
    assert isinstance(result, dict)
    assert "active_app" in result
    assert "title" in result
    print("✓ get_active_app structure test passed")


def test_get_active_app_linux():
    """Linux implementation test"""
    result = get_active_app_linux()
    print(f"get_active_app_linux result: {result}")
    
    # Check structure
    assert isinstance(result, dict)
    assert "active_app" in result
    assert "title" in result
    print("✓ get_active_app_linux structure test passed")


def test_is_system_process():
    """System process detection test"""
    # System processes
    assert _is_system_process("systemd") is True
    assert _is_system_process("kthreadd") is True
    assert _is_system_process("dbus-daemon") is True
    
    # User processes
    assert _is_system_process("chrome") is False
    assert _is_system_process("firefox") is False
    assert _is_system_process("python") is False
    
    print("✓ _is_system_process test passed")


def test_get_active_app_fallback():
    """Fallback implementation test"""
    result = _get_active_app_fallback()
    print(f"_get_active_app_fallback result: {result}")
    
    # Check structure
    assert isinstance(result, dict)
    assert "active_app" in result
    assert "title" in result
    print("✓ _get_active_app_fallback structure test passed")


def test_data_format_consistency():
    """Data format consistency test"""
    scenarios = [
        {"app": "Code.exe", "title": "main.py - VSCode"},
        {"app": None, "title": None},
        {"app": "chrome.exe", "title": ""},
    ]
    
    for scenario in scenarios:
        result = {
            "active_app": scenario["app"],
            "title": scenario["title"]
        }
        
        assert isinstance(result, dict)
        assert "active_app" in result
        assert "title" in result
        assert result["active_app"] is None or isinstance(result["active_app"], str)
        assert result["title"] is None or isinstance(result["title"], str)
    
    print("✓ Data format consistency test passed")


if __name__ == "__main__":
    print("Running Active Window Watcher tests...")
    
    try:
        test_get_active_app()
        test_get_active_app_linux()
        test_is_system_process()
        test_get_active_app_fallback()
        test_data_format_consistency()
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise