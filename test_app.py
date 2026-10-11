"""Offline requirements tests; runnable with pytest or stdlib unittest."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch, MagicMock

import verification_adapter as app
from service_monitor.checks import http_get
from service_monitor.config import load_config


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / 'checks.sqlite3')
        self.service = dict(name='api', url='https://example.invalid/health', timeout=2)

    def row(self, status=200):
        return app.check_service(self.service, lambda url, timeout: status, iter([1, 1.025]).__next__)

    def invalid(self, **changes):
        with self.assertRaises(ValueError):
            app.validate_config({'services': [dict(self.service, **changes)]})

    def test_valid_config(self):
        self.assertEqual(app.validate_config({'services': [self.service]}), [self.service])

    def test_default_timeout(self):
        self.assertEqual(app.validate_config({'services': [dict(name='a', url='http://localhost')]} )[0]['timeout'], 5)

    def test_empty_config(self):
        self.assertEqual(app.validate_config({'services': []}), [])

    def test_missing_services(self):
        with self.assertRaises(ValueError): app.validate_config({})

    def test_wrong_services_type(self):
        with self.assertRaises(ValueError): app.validate_config({'services': {}})

    def test_wrong_service_type(self):
        with self.assertRaises(ValueError): app.validate_config({'services': [None]})

    def test_duplicate_names(self):
        with self.assertRaises(ValueError): app.validate_config({'services': [self.service] * 2})

    def test_blank_name(self): self.invalid(name=' ')
    def test_unsupported_protocol(self): self.invalid(url='ftp://example.com')
    def test_missing_hostname(self): self.invalid(url='https:///path')
    def test_bad_port(self): self.invalid(url='https://example.com:99999')
    def test_malformed_url_syntax(self):
        for url in ('https://example.com:', 'https://example.com/%zz', 'https://example.com\\path'):
            with self.subTest(url=url): self.invalid(url=url)
    def test_bad_host(self): self.invalid(url='https://-bad.example')
    def test_url_whitespace(self): self.invalid(url='https://example.com/a b')
    def test_credentials(self): self.invalid(url='https://user:secret@example.com')
    def test_fragment(self): self.invalid(url='https://example.com/#part')
    def test_zero_timeout(self): self.invalid(timeout=0)
    def test_bool_timeout(self): self.invalid(timeout=True)
    def test_infinite_timeout(self): self.invalid(timeout=float('inf'))

    def test_success_and_elapsed(self):
        row = self.row()
        self.assertTrue(row['success'])
        self.assertEqual(row['response_time_ms'], 25)
        self.assertIn('+00:00', row['timestamp'])

    def test_http_failure(self):
        row = self.row(503)
        self.assertEqual(row['status_code'], 503)
        self.assertFalse(row['success'])

    def test_redirect_is_failure(self): self.assertFalse(self.row(302)['success'])

    def test_transport_arguments(self):
        calls = []
        app.check_service(self.service, lambda *args: calls.append(args) or 204)
        self.assertEqual(calls, [(self.service['url'], 2)])

    def test_connection_and_timeout(self):
        for exception in (ConnectionError('secret'), TimeoutError('secret')):
            with self.subTest(exception=exception):
                def fail(*args): raise exception
                row = app.check_service(self.service, fail)
                self.assertFalse(row['success'])
                self.assertIsNone(row['status_code'])
                self.assertEqual(row['error'], type(exception).__name__)

    def test_invalid_transport_status(self):
        self.assertEqual(self.row(999)['error'], 'ValueError')

    def test_real_transport_options(self):
        session = MagicMock()
        session.get.return_value.__enter__.return_value.status_code = 204
        fake_requests = MagicMock()
        fake_requests.Session.return_value.__enter__.return_value = session
        with patch.dict('sys.modules', requests=fake_requests):
            self.assertEqual(http_get(self.service['url'], 2), 204)
        session.get.assert_called_once_with(self.service['url'], timeout=2, allow_redirects=False, stream=True)
        self.assertFalse(session.trust_env)

    def test_empty_database(self):
        self.assertEqual(app.history(self.db, 10), [])
        self.assertEqual(app.latest(self.db), [])

    def test_roundtrip(self):
        row = self.row()
        app.save_result(self.db, row)
        self.assertEqual(app.history(self.db, 1), [row])

    def test_history_order_and_limit(self):
        old, new = self.row(200), self.row(500)
        old['timestamp'], new['timestamp'] = '2026-01-01T00:00:00+00:00', '2026-01-02T00:00:00+00:00'
        for row in (new, old): app.save_result(self.db, row)
        self.assertEqual(app.history(self.db, 1), [new])

    def test_latest_multiple_and_tie(self):
        first = self.row()
        failed = dict(first, status_code=500, success=False)
        other = dict(first, name='other')
        for row in (first, failed, other): app.save_result(self.db, row)
        self.assertEqual(app.latest(self.db), [failed, other])

    def test_invalid_limit(self):
        with self.assertRaises(ValueError): app.history(self.db, 0)

    def test_json_export(self):
        row = self.row()
        self.assertEqual(json.loads(app.export_json([row])), [row])

    def test_csv_export_escaping(self):
        row = dict(self.row(), name='a,"b\nc')
        parsed = list(csv.DictReader(io.StringIO(app.export_csv([row]))))
        self.assertEqual(parsed[0]['name'], row['name'])

    def test_empty_exports(self):
        self.assertEqual(json.loads(app.export_json([])), [])
        self.assertEqual(list(csv.DictReader(io.StringIO(app.export_csv([])))), [])

    def cli(self, argv, transport=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = app.main(argv, transport=transport)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_check_status_history_export(self):
        config = Path(self.tmp.name) / 'config.json'
        config.write_text(json.dumps({'services': [self.service]}))
        code, output, _ = self.cli(['check', '--config', str(config), '--database', self.db], lambda *args: 200)
        self.assertEqual(code, 0)
        self.assertIn('UP', output)
        self.assertIn('Recent 1 checks: 1 successful', self.cli(['status', '--database', self.db])[1])
        report = Path(self.tmp.name) / 'report.csv'
        self.assertEqual(self.cli(['history', '--database', self.db, '--format', 'csv', '--output', str(report)])[0], 0)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(report.read_text())))), 1)

    def test_cli_invalid_and_empty(self):
        self.assertEqual(self.cli(['check', '--config', '/nonexistent'])[0], 2)
        self.assertIn('No history', self.cli(['history', '--database', self.db])[1])
        self.assertEqual(self.cli(['history', '--database', self.db, '--limit', '0'])[0], 2)
        self.assertEqual(self.cli([])[0], 2)

    def test_cli_continues_after_failure(self):
        config = Path(self.tmp.name) / 'config.json'
        config.write_text(json.dumps({'services': [self.service, dict(self.service, name='other')]}))
        def transport(url, timeout):
            if len(calls) == 0:
                calls.append(1)
                raise TimeoutError()
            return 200
        calls = []
        self.assertEqual(self.cli(['check', '--config', str(config), '--database', self.db], transport)[0], 1)
        self.assertEqual(len(app.history(self.db, 10)), 2)

    def test_terminal_report_escapes_controls_preserves_json(self):
        from service_monitor.reports import text_report
        row = dict(self.row(), name='api\x1b[2J\nforged\x85line')
        report = text_report([row])
        self.assertNotIn('\x1b', report)
        self.assertNotIn('\x85', report)
        self.assertEqual(len(report.splitlines()), 2)
        self.assertEqual(json.loads(app.export_json([row]))[0]['name'], row['name'])

    def test_report_cannot_overwrite_database_or_alias(self):
        import os
        app.save_result(self.db, self.row())
        original = Path(self.db).read_bytes()
        alias = Path(self.tmp.name) / 'alias'
        os.link(self.db, alias)
        for output in (self.db, str(alias)):
            self.assertEqual(self.cli(['history', '--database', self.db, '--output', output])[0], 2)
            self.assertEqual(Path(self.db).read_bytes(), original)

    def test_report_cannot_overwrite_configuration_before_check(self):
        config = Path(self.tmp.name) / 'config.json'
        config.write_text(json.dumps({'services': [self.service]}))
        original = config.read_bytes()
        calls = []
        code, _, _ = self.cli(['check', '--config', str(config), '--database', self.db,
                              '--output', str(config)], lambda *args: calls.append(args) or 200)
        self.assertEqual(code, 2)
        self.assertFalse(calls)
        self.assertEqual(config.read_bytes(), original)

    def test_load_malformed_json(self):
        config = Path(self.tmp.name) / 'config.json'
        config.write_text('{')
        with self.assertRaises(ValueError): load_config(config)

    def test_database_failure(self):
        self.assertEqual(self.cli(['status', '--database', self.tmp.name])[0], 2)


if __name__ == '__main__':
    unittest.main()
