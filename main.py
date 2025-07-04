import spacy
import json
from sentence_transformers import SentenceTransformer, util

# Загрузка русской модели spaCy
try:
    nlp = spacy.load('ru_core_news_md')
except OSError:
    print('Модель ru_core_news_md не установлена. Установите её командой: python -m spacy download ru_core_news_md')
    exit(1)

# Загрузка мультиязычной модели для эмбеддингов
sbert_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')


def extract_skills(text):
    doc = nlp(text)
    # Извлекаем все существительные как потенциальные навыки
    skills = set([token.lemma_.lower() for token in doc if token.pos_ == 'NOUN'])
    return list(skills)


def semantic_match(vacancy_text, resume_text, threshold=0.6):
    vacancy_skills = extract_skills(vacancy_text)
    resume_skills = extract_skills(resume_text)

    if not vacancy_skills or not resume_skills:
        return {
            'matching_score': 0.0,
            'matched_skills': [],
            'missing_skills': vacancy_skills,
            'details': {}
        }

    # Получаем эмбеддинги
    vacancy_embs = sbert_model.encode(vacancy_skills, convert_to_tensor=True)
    resume_embs = sbert_model.encode(resume_skills, convert_to_tensor=True)

    # Считаем косинусное сходство
    cosine_scores = util.cos_sim(vacancy_embs, resume_embs)

    matched = []
    missing = []
    details = {}
    for i, v_skill in enumerate(vacancy_skills):
        # Для каждого требования ищем максимальное сходство с любым навыком из резюме
        max_score = float(cosine_scores[i].max())
        best_match_idx = int(cosine_scores[i].argmax())
        best_resume_skill = resume_skills[best_match_idx]
        details[v_skill] = {
            'best_resume_skill': best_resume_skill,
            'similarity': round(max_score, 2)
        }
        if max_score >= threshold:
            matched.append(v_skill)
        else:
            missing.append(v_skill)

    matching_score = round(len(matched) / len(vacancy_skills), 2)
    return {
        'matching_score': matching_score,
        'matched_skills': matched,
        'missing_skills': missing,
        'details': details
    }


if __name__ == '__main__':
    # Пример текстов (замените на свои)
    vacancy = 'Требования: знание Python, опыт работы с базами данных, умение работать в команде.'
    resume = 'Опыт работы: Python, базы данных, командная работа, аналитика.'
    report = semantic_match(vacancy, resume)
    print(json.dumps(report, ensure_ascii=False, indent=2))
