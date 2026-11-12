"""Lighthouse journal CLI. No network or agent execution."""
import argparse
import json
import os
import os
from pathlib import Path
from .store import Store
from .observatory import render
from .observatory import render


def main():
    parser = argparse.ArgumentParser(description='Lighthouse local research evidence journal')
    parser.add_argument('--db', default='.lighthouse/lighthouse.db')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init')
    commands.add_parser('status')
    ingest = commands.add_parser('record-envelope')
    ingest.add_argument('file', type=Path)
    experiment = commands.add_parser('record-experiment')
    experiment.add_argument('title')
    experiment.add_argument('source', choices=['genesis','eve','joint','external'])
    experiment.add_argument('file', type=Path)
    verified = commands.add_parser('verify-envelope', help='Cryptographically verify and archive one message')
    verified.add_argument('file', type=Path)
    verified.add_argument('--reviewer', default='manual-hmac-verifier')
    export = commands.add_parser('export', help='Export untrusted exchange bundle')
    export.add_argument('file', type=Path)
    import_cmd = commands.add_parser('import', help='Import untrusted exchange bundle')
    import_cmd.add_argument('file', type=Path)
    observatory = commands.add_parser('observatory', help='Generate offline read-only HTML')
    observatory.add_argument('file', type=Path)
    verified = commands.add_parser('verify-envelope')
    verified.add_argument('file', type=Path)
    verified.add_argument('--reviewer', default='manual-hmac-verifier')
    export = commands.add_parser('export')
    export.add_argument('file', type=Path)
    importer = commands.add_parser('import')
    importer.add_argument('file', type=Path)
    observatory = commands.add_parser('observatory')
    observatory.add_argument('file', type=Path)
    args = parser.parse_args()
    store = Store(args.db)
    store.init()
    if args.command == 'init':
        value = {'database': str(Path(args.db)), 'initialized': True}
    elif args.command == 'status':
        value = store.status()
    elif args.command == 'observatory':
        value = {'output': render(store, args.file)}
    elif args.command == 'export':
        data = store.export_bundle()
        args.file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        value = {'exported': len(data['envelopes']), 'output': str(args.file)}
    else:
        limit = 5000000 if args.command == 'import' else 40000 if args.command == 'record-envelope' else 100000
        if args.file.stat().st_size > limit:
            parser.error('File too large')
        data = json.loads(args.file.read_text(encoding='utf-8'))
        if args.command == 'record-envelope':
            value = store.record_envelope(data)
        elif args.command == 'verify-envelope':
            keys = {
                'genesis': os.getenv('LIGHTHOUSE_GENESIS_SECRET', ''),
                'eve': os.getenv('LIGHTHOUSE_EVE_SECRET', '')
            }
            value = store.record_verified_envelope(data, keys, reviewer=args.reviewer)
        elif args.command == 'import':
            value = store.import_bundle(data)
        else:
            value = {'experiment_id': store.record_experiment(args.title,args.source,data)}
    print(json.dumps(value, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
