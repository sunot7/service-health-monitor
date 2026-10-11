import csv
import io
import json

from .storage import FIELDS


def export_json(rows):
    return json.dumps(list(rows), indent=2, ensure_ascii=False, allow_nan=False) + '\n'


def export_csv(rows):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def terminal_text(value):
    """Escape controls only for human-readable output; machine data stays exact."""
    return ''.join(char if char.isprintable() else char.encode('unicode_escape').decode('ascii')
                   for char in str(value))


def text_report(rows):
    lines = [f"{r['name']}: {'UP' if r['success'] else 'DOWN'} status={r['status_code']} "
             f"time={r['response_time_ms']:.3f}ms error={r['error'] or '-'} at={r['timestamp']}" for r in rows]
    passed = sum(r['success'] for r in rows)
    lines.append(f'Summary: {len(rows)} checks, {passed} successful, {len(rows) - passed} failed')
    if not rows:
        lines.insert(0, 'No history available.')
    return '\n'.join(terminal_text(line) for line in lines) + '\n'
