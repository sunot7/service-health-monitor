from datetime import datetime, timezone
from time import perf_counter

from .config import validate_config


def http_get(url, timeout):
    import requests
    # Avoid environment proxies/netrc and prevent unconfigured redirect targets.
    with requests.Session() as session:
        session.trust_env = False
        with session.get(url, timeout=timeout, allow_redirects=False, stream=True) as response:
            return response.status_code


def check_service(service, transport=None, clock=perf_counter):
    service = validate_config({'services': [service]})[0]
    transport = transport or http_get
    start = clock()
    status, error = None, None
    try:
        status = transport(service['url'], service['timeout'])
        if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
            raise ValueError('invalid HTTP status')
    except Exception as exc:
        status = None
        # Exception messages can contain credentials or URL query secrets.
        error = type(exc).__name__
    return dict(name=service['name'], url=service['url'],
                timestamp=datetime.now(timezone.utc).isoformat(), status_code=status,
                success=status is not None and 200 <= status < 300,
                response_time_ms=round(max(0, clock() - start) * 1000, 3), error=error)
