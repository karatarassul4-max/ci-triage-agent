import json
import sys
from pathlib import Path

METRICS = ['category_correct', 'file_hit', 'file_precision', 'file_recall']


def mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def load_rows(split):
    result = {}
    for path in sorted(Path('eval/results').glob('*_' + split + '.jsonl')):
        variant = path.stem.rsplit('_', 1)[0]
        lines = path.read_text(encoding='utf-8').splitlines()
        result[variant] = [json.loads(line) for line in lines]
    return result


def load_categories():
    categories = {}
    for path in Path('eval/cases').glob('*.json'):
        case = json.loads(path.read_text(encoding='utf-8'))
        categories[case['id']] = case['category']
    return categories


def print_table(title, rows_by_variant):
    print(title)
    print('вариант  n  ok  ' + '  '.join(METRICS) + '  токенов/кейс')
    for variant, rows in rows_by_variant.items():
        if not rows:
            continue
        ok = sum(1 for r in rows if r['status'] == 'ok')
        cells = [format(mean([r[m] for r in rows]), '.2f') for m in METRICS]
        tokens = mean([r['total_tokens'] for r in rows])
        print(variant, len(rows), ok, '  '.join(cells), round(tokens))
    print()


def main(split):
    data = load_rows(split)
    categories = load_categories()
    print_table('=== ВСЕ КЕЙСЫ (' + split + ')', data)
    for category in ['code_bug', 'flaky_test', 'dependency', 'config']:
        part = {}
        for variant, rows in data.items():
            part[variant] = [r for r in rows if categories.get(r['case_id']) == category]
        print_table('=== КАТЕГОРИЯ ' + category, part)


if __name__ == '__main__':
    main(sys.argv[1])