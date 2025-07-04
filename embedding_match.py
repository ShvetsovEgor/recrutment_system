import json
from rapidfuzz import fuzz
from collections.abc import Sequence, Mapping

# --- Настройки и словари ---
LOCATION_SYNONYMS = {
    "питер": "санкт-петербург",
    "спб": "санкт-петербург",
    "санкт-петербург": "санкт-петербург",
    "мск": "москва",
    "москва": "москва"
}

# --- Вспомогательные функции ---
def normalize_location(text):
    t = text.lower().replace("-", " ").replace("ё", "е").strip()
    return LOCATION_SYNONYMS.get(t, t)

def jaccard_similarity(list1, list2):
    set1, set2 = set(list1), set(list2)
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

def flatten_to_list(value):
    # Преобразует вложенные списки/словари в плоский список строк
    if isinstance(value, str):
        return [value]
    elif isinstance(value, Mapping):
        result = []
        for v in value.values():
            result.extend(flatten_to_list(v))
        return result
    elif isinstance(value, Sequence) and not isinstance(value, str):
        result = []
        for v in value:
            result.extend(flatten_to_list(v))
        return result
    elif value is None:
        return []
    else:
        return [str(value)]

def try_float(val):
    try:
        return float(str(val).replace(',', '.').replace(' ', ''))
    except Exception:
        return None

def compare_numeric(val1, val2):
    n1, n2 = try_float(val1), try_float(val2)
    if n1 is None or n2 is None:
        return 0.0
    diff = abs(n1 - n2)
    maxv = max(abs(n1), abs(n2), 1)
    return 1.0 - min(diff / maxv, 1.0)

# --- Основная логика ---
with open('data/resume.json', encoding='utf-8') as f:
    resume = json.load(f)
with open('data/vacancy.json', encoding='utf-8') as f:
    vacancy = json.load(f)

fields = set(resume.keys()) | set(vacancy.keys())
results = {}

for field in fields:
    r_val = resume.get(field)
    v_val = vacancy.get(field)
    if r_val is None or v_val is None:
        continue
    # --- Город ---
    if field in ('location', 'место жительства', 'город', 'расположение'):
        r_loc = normalize_location(str(r_val))
        v_loc = normalize_location(str(v_val))
        score = fuzz.token_sort_ratio(r_loc, v_loc) / 100
    # --- Навыки, языки, требования, обязанности ---
    elif field in ('skills', 'навыки', 'languages', 'языки', 'требования', 'обязанности', 'design_skills', 'design_tools'):
        r_list = flatten_to_list(r_val)
        v_list = flatten_to_list(v_val)
        score = jaccard_similarity(r_list, v_list)
    # --- Числовые поля ---
    elif field in ('age', 'возраст', 'salary', 'зарплата', 'опыт', 'experience'):
        score = compare_numeric(r_val, v_val)
    # --- Остальные (fuzzy) ---
    else:
        score = fuzz.token_sort_ratio(str(r_val), str(v_val)) / 100
    results[field] = score

# Итоговый скор
if results:
    avg_score = sum(results.values()) / len(results)
    for k, v in results.items():
        print(f"Сходство по полю '{k}': {v:.3f}")
    print(f"\nИтоговый средний скор: {avg_score:.3f}")
else:
    print("Нет совпадающих полей для сравнения.") 