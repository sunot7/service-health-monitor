import json
import math
import re
from urllib.parse import urlsplit


def validate_config(config):
    if not isinstance(config, dict) or not isinstance(config.get('services'), list):
        raise ValueError('configuration must contain a services list')
    services, names = [], set()
    for item in config['services']:
        if not isinstance(item, dict):
            raise ValueError('each service must be an object')
        name, url, timeout = item.get('name'), item.get('url'), item.get('timeout', 5)
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError('service name must be nonempty with no surrounding whitespace')
        if name in names:
            raise ValueError('duplicate service name')
        if (not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url)
                or re.search(r'%(?![0-9a-fA-F]{2})', url) or '\\' in url):
            raise ValueError('invalid URL')
        try:
            parsed = urlsplit(url)
            if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                    or parsed.username is not None or parsed.password is not None
                    or parsed.fragment or parsed.port == 0 or parsed.netloc.endswith(':')):
                raise ValueError('invalid URL')
            host = parsed.hostname
            if ':' not in host:
                labels = host.encode('idna').decode().split('.')
                if any(not label or len(label) > 63 or label.startswith('-')
                       or label.endswith('-') or any(not (c.isalnum() or c == '-') for c in label)
                       for label in labels):
                    raise ValueError('invalid hostname')
        except (ValueError, UnicodeError) as exc:
            raise ValueError('URL must be valid HTTP/HTTPS without credentials or fragment') from exc
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout) or timeout <= 0):
            raise ValueError('timeout must be a positive finite number')
        names.add(name)
        services.append(dict(name=name, url=url, timeout=timeout))
    return services


def load_config(path):
    with open(path, encoding='utf-8') as source:
        return validate_config(json.load(source))
