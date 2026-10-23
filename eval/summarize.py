import json
import sys
from pathlib import Path

METRICS = ['category_correct', 'file_hit', 'file_precision', 'file_recall']


def mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def main(split):
    print('вариант  n  ok  ' + '  '.join(METRICS) + '  токенов/кейс')
    for path in sorted(Path('eval/results').glob('*_' + split + '.jsonl')):
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        variant = path.stem.rsplit('_', 1)[0]
        ok = sum(1 for r in rows if r['status'] == 'ok')
        cells = [format(mean([r[m] for r in rows]), '.2f') for m in METRICS]
        tokens = mean([r['total_tokens'] for r in rows])
        print(variant, len(rows), ok, '  '.join(cells), round(tokens))


if __name__ == '__main__':
    main(sys.argv[1])