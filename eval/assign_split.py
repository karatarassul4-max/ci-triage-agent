import hashlib
import json
from pathlib import Path

CASES_DIR = Path('eval/cases')
SALT = 'v1'


def choose_split(case_id):
    digest = hashlib.md5((SALT + case_id).encode('utf-8')).hexdigest()
    number = int(digest, 16)
    if number % 3 == 0:
        return 'dev'
    return 'test'


def main():
    counts = {}
    for path in sorted(CASES_DIR.glob('*.json')):
        case = json.loads(path.read_text(encoding='utf-8'))
        if case['split'] == 'unassigned':
            case['split'] = choose_split(case['id'])
            text = json.dumps(case, ensure_ascii=False, indent=2)
            path.write_text(text, encoding='utf-8')
            print(case['id'], '->', case['split'])
        key = (case['repo_url'], case['split'])
        counts[key] = counts.get(key, 0) + 1
    print()
    for (repo, split), n in sorted(counts.items()):
        print(repo, split, n)


if __name__ == '__main__':
    main()