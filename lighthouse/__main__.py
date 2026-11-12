"""Lighthouse journal CLI. No network or agent execution."""
import argparse
import json
from pathlib import Path
from .store import Store


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
    args = parser.parse_args()
    store = Store(args.db)
    store.init()
    if args.command == 'init':
        value = {'database': str(Path(args.db)), 'initialized': True}
    elif args.command == 'status':
        value = store.status()
    else:
        limit = 40000 if args.command == 'record-envelope' else 100000
        if args.file.stat().st_size > limit:
            parser.error('File too large')
        data = json.loads(args.file.read_text(encoding='utf-8'))
        if args.command == 'record-envelope':
            value = store.record_envelope(data)
        else:
            value = {'experiment_id': store.record_experiment(args.title,args.source,data)}
    print(json.dumps(value, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
