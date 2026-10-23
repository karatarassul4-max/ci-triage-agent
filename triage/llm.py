import json
import os
import time
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq, RateLimitError

load_dotenv()
client = Groq(api_key=os.environ['GROQ_API_KEY'])

USAGE_FILE = Path('usage.jsonl')
TOKENS_PER_MINUTE = 8000
DAILY_LIMIT = 180_000


class BudgetExceeded(Exception):
    pass


def tokens_used_today(model):
    if not USAGE_FILE.exists():
        return 0
    today = date.today().isoformat()
    total = 0
    for line in USAGE_FILE.read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        if row['date'] == today and row['model'] == model:
            total += row['total_tokens']
    return total


def call_model(model, messages, tools=None, max_retries=5, **kwargs):
    if tokens_used_today(model) >= DAILY_LIMIT:
        raise BudgetExceeded('Дневной лимит токенов исчерпан для ' + model)

    params = dict(model=model, messages=messages, **kwargs)
    if tools:
        params['tools'] = tools

    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(**params)
            break
        except RateLimitError as error:
            wait = 20
            header = error.response.headers.get('retry-after')
            if header:
                wait = float(header) + 1
            print('Ошибка 429, жду', wait, 'сек')
            time.sleep(wait)
    else:
        raise RuntimeError('Не удалось получить ответ после повторов')

    usage = resp.usage
    row = {
        'date': date.today().isoformat(),
        'model': model,
        'prompt_tokens': usage.prompt_tokens,
        'completion_tokens': usage.completion_tokens,
        'total_tokens': usage.total_tokens,
    }
    with USAGE_FILE.open('a', encoding='utf-8') as f:
        f.write(json.dumps(row) + '\n')

    time.sleep(usage.total_tokens / TOKENS_PER_MINUTE * 60)
    return resp