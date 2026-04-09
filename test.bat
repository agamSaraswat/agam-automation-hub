@echo off
python -m unittest tests/test_web_endpoints.py tests/test_services_automation.py tests/test_settings_manager.py tests/test_run_history.py
