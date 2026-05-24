#!/usr/bin/env python3
"""
Config loader for printime.
Loads settings from .env file and printer.yaml
"""

import os
from dotenv import load_dotenv
from typing import Dict, Any


def load_env():
    """Load .env file if present."""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)
    elif os.path.exists('.env'):
        load_dotenv('.env', override=True)


def get_env(key: str, default: Any = None) -> Any:
    """Get environment variable or default."""
    return os.getenv(key, default)


def get_printer_config() -> Dict[str, Any]:
    """Get printer configuration from environment and defaults."""
    load_env()

    return {
        'device': get_env('PRINTER_DEVICE', '/dev/usb/lp5'),
        'profile': get_env('PRINTER_PROFILE', 'ITPP047'),
        'width': int(get_env('PRINTER_WIDTH', '32')),
        'usb': {
            'vendor_id': get_env('PRINTER_USB_VENDOR', '0x0416'),
            'product_id': get_env('PRINTER_USB_PRODUCT', '0x5011'),
        }
    }


def get_server_config() -> Dict[str, Any]:
    """Get server configuration from environment."""
    load_env()

    return {
        'port': int(get_env('SERVER_PORT', '8080')),
    }


def get_anytype_config() -> Dict[str, Any]:
    """Get Anytype configuration from environment."""
    load_env()

    return {
        'api_key': get_env('ANYTYPE_API_KEY'),
        'space_id': get_env('ANYTYPE_SPACE_ID'),
    }


def get_latex_config() -> Dict[str, Any]:
    """Get LaTeX configuration from environment."""
    load_env()

    return {
        'command': get_env('LATEX_COMMAND', 'pdflatex'),
        'pdf_to_png': get_env('PDF_TO_PNG_COMMAND', 'pdftoppm'),
        'scale': int(get_env('LATEX_SCALE', '150')),
    }


def load_yaml_config(config_path: str = None) -> Dict[str, Any]:
    """Load YAML configuration file."""
    import yaml

    if config_path is None:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'printer.yaml')
        if not os.path.exists(config_path):
            config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'printer.yaml')

    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    return {}


def get_config() -> Dict[str, Any]:
    """Get full configuration (env + yaml merged)."""
    load_env()

    yaml_config = load_yaml_config()

    # Merge with env overrides
    if 'printer' not in yaml_config:
        yaml_config['printer'] = {}

    yaml_config['printer']['device'] = get_env('PRINTER_DEVICE', yaml_config['printer'].get('device', '/dev/usb/lp5'))
    yaml_config['printer']['width'] = int(get_env('PRINTER_WIDTH', yaml_config['printer'].get('width', 32)))
    yaml_config['printer']['profile'] = get_env('PRINTER_PROFILE', yaml_config['printer'].get('profile', 'ITPP047'))

    if 'usb' not in yaml_config['printer']:
        yaml_config['printer']['usb'] = {}
    yaml_config['printer']['usb']['vendor_id'] = get_env('PRINTER_USB_VENDOR', yaml_config['printer']['usb'].get('vendor_id', '0x0416'))
    yaml_config['printer']['usb']['product_id'] = get_env('PRINTER_USB_PRODUCT', yaml_config['printer']['usb'].get('product_id', '0x5011'))

    return yaml_config


if __name__ == '__main__':
    config = get_config()
    print("Current config:")
    import json
    print(json.dumps(config, indent=2))