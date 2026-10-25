import json
import sys
from pathlib import Path


def main(variant, split):
    cases = {}
    for path in Path('eval/cases').glob('*.json'):
        case = json.loads(path.read_text(encoding='utf-8'))
        cases[case['id']] = case
    path = Path('eval/results') / (variant + '_' + split + '.jsonl')
    for line in path.read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        case = cases[row['case_id']]
        print('==', row['case_id'], row['status'], 'tokens:', row['total_tokens'])
        print('   gold files :', case['gold_files'], '| gold category:', case['category'])
        if row.get('error'):
            print('   error      :', row['error'])
        pred = row['prediction']
        if pred:
            print('   pred files :', pred.get('root_cause_files'), 'hit:', row['file_hit'])
            print('   category   :', pred.get('category'), 'confidence:', pred.get('confidence'))
            print('   explanation:', str(pred.get('explanation'))[:200])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])