"""Behavioral verification interface; all operations use the application modules."""
from service_monitor.config import validate_config
from service_monitor.checks import check_service
from service_monitor.storage import save_result, history, latest
from service_monitor.reports import export_json, export_csv
from service_monitor.cli import main

__all__ = ['validate_config', 'check_service', 'save_result', 'history', 'latest',
           'export_json', 'export_csv', 'main']
