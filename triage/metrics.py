def normalize_path(path):
    p = str(path).replace(chr(92), '/').strip()
    while p.startswith('./'):
        p = p[2:]
    return p


def to_set(paths):
    return {normalize_path(p) for p in paths}


def category_correct(pred_category, gold_category):
    if pred_category == gold_category:
        return 1.0
    return 0.0


def file_hit(pred_files, gold_files):
    if to_set(pred_files) & to_set(gold_files):
        return 1.0
    return 0.0


def file_precision(pred_files, gold_files):
    pred = to_set(pred_files)
    if not pred:
        return 0.0
    return len(pred & to_set(gold_files)) / len(pred)


def file_recall(pred_files, gold_files):
    gold = to_set(gold_files)
    if not gold:
        return 0.0
    return len(to_set(pred_files) & gold) / len(gold)