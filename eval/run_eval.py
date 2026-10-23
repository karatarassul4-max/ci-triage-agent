import json
import sys
from pathlib import Path

from triage.baseline import run_variant
from triage.llm import BudgetExceeded

RESULTS_DIR = Path('eval/results')


def load_cases(split):
    cases = []
    for path in sorted(Path('eval/cases').glob('*.json')):
        case = json.loads(path.read_text(encoding='utf-8'))
        if case['split'] == split:
            cases.append(case)
    return cases


def main(variant_name, split, limit=None):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / (variant_name + '_' + split + '.jsonl')

    done = set()
    if out_file.exists():
        for line in out_file.read_text(encoding='utf-8').splitlines():
            done.add(json.loads(line)['case_id'])

    count = 0
    for case in load_cases(split):
        if case['id'] in done:
            continue
        if limit is not None and count >= limit:
            break
        try:
            result = run_variant(variant_name, case)
        except BudgetExceeded as error:
            print('Остановка:', error)
            break
        with out_file.open('a', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
        print(case['id'], variant_name, result['status'], 'токенов:', result['total_tokens'])
        count += 1


if __name__ == '__main__':
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    main(sys.argv[1], sys.argv[2], limit)