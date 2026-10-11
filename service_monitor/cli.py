import argparse
from pathlib import Path
import sqlite3
import sys

from .checks import check_service
from .config import load_config
from .reports import export_csv, export_json, text_report
from .storage import history, latest, save_result


def validate_output_target(args):
    if not args.output:
        return
    output = Path(args.output)
    protected = [Path(args.database)]
    if args.command == 'check':
        protected.append(Path(args.config))
    for source in protected:
        if (output.resolve() == source.resolve()
                or output.exists() and source.exists() and output.samefile(source)):
            raise ValueError('report output must not overwrite configuration or database')


def main(argv=None, transport=None):
    parser = argparse.ArgumentParser(description='Monitor explicitly configured HTTP services.')
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('check', 'status', 'history'):
        command = commands.add_parser(name)
        command.add_argument('--database', default='health.sqlite3')
        command.add_argument('--format', choices=('text', 'json', 'csv'), default='text')
        command.add_argument('--output', help='write report to this file instead of stdout')
        if name == 'check':
            command.add_argument('--config', required=True)
        if name in ('status', 'history'):
            command.add_argument('--limit', type=int, default=100, help='recent summary/history sample size')
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code
    try:
        validate_output_target(args)
        if args.command == 'check':
            results = []
            for service in load_config(args.config):
                result = check_service(service, transport=transport)
                save_result(args.database, result)
                results.append(result)
        elif args.command == 'status':
            recent = history(args.database, args.limit)
            results = latest(args.database)
        else:
            results = history(args.database, args.limit)
        report = {'json': export_json, 'csv': export_csv, 'text': text_report}[args.format](results)
        if args.command == 'status' and args.format == 'text':
            passed = sum(row['success'] for row in recent)
            report += f'Recent {len(recent)} checks: {passed} successful, {len(recent) - passed} failed\n'
        if args.output:
            validate_output_target(args)
            with open(args.output, 'w', encoding='utf-8', newline='') as destination:
                destination.write(report)
        else:
            print(report, end='')
        return 1 if args.command == 'check' and any(not r['success'] for r in results) else 0
    except (OSError, ValueError, sqlite3.Error):
        print('Error: configuration, database, or report operation failed; check paths and input.', file=sys.stderr)
        return 2
