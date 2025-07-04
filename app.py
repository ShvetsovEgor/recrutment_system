from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid
from rapidfuzz import fuzz
from collections.abc import Sequence, Mapping

app = Flask(__name__)
app.secret_key = 'huntflow_mvp_secret_key'

# Конфигурация
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Создаем папку для загрузок
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Простое хранилище данных (в реальном проекте - база данных)
VACANCIES_FILE = 'data/vacancies.json'
CANDIDATES_FILE = 'data/candidates.json'

# Словарь синонимов для городов
LOCATION_SYNONYMS = {
    "питер": "санкт-петербург",
    "спб": "санкт-петербург",
    "санкт-петербург": "санкт-петербург",
    "мск": "москва",
    "москва": "москва"
}

def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def normalize_location(text):
    t = text.lower().replace("-", " ").replace("ё", "е").strip()
    return LOCATION_SYNONYMS.get(t, t)

def jaccard_similarity(list1, list2):
    set1, set2 = set(list1), set(list2)
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

def flatten_to_list(value):
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

def calculate_matching_score(candidate, vacancy):
    """Расчет скора соответствия кандидата и вакансии"""
    scores = {}
    
    # Сравнение навыков кандидата с требованиями вакансии
    if candidate.get('skills') and vacancy.get('requirements'):
        candidate_skills = candidate['skills']
        vacancy_requirements = vacancy['requirements']
        scores['skills'] = jaccard_similarity(candidate_skills, vacancy_requirements)
    
    # Сравнение опыта
    if candidate.get('experience') and vacancy.get('description'):
        candidate_exp = candidate['experience']
        vacancy_desc = vacancy['description']
        scores['experience'] = fuzz.token_sort_ratio(candidate_exp, vacancy_desc) / 100
    
    # Сравнение должности
    if candidate.get('position') and vacancy.get('title'):
        candidate_pos = candidate['position']
        vacancy_title = vacancy['title']
        scores['position'] = fuzz.token_sort_ratio(candidate_pos, vacancy_title) / 100
    
    # Если есть зарплата в вакансии, можно добавить сравнение ожиданий
    
    # Итоговый скор - среднее по всем полям
    if scores:
        return sum(scores.values()) / len(scores)
    return 0.5  # Базовый скор если нет данных для сравнения

def get_ranked_candidates(vacancy_id, status_filter=None, min_score=0.0):
    """Получение ранжированных кандидатов для вакансии"""
    candidates = load_data(CANDIDATES_FILE)
    vacancies = load_data(VACANCIES_FILE)
    
    vacancy = next((v for v in vacancies if v['id'] == vacancy_id), None)
    if not vacancy:
        return []
    
    ranked_candidates = []
    
    for candidate in candidates:
        # Фильтр по статусу
        if status_filter and candidate.get('status') != status_filter:
            continue
            
        # Расчет скора
        score = calculate_matching_score(candidate, vacancy)
        
        # Фильтр по минимальному скору
        if score < min_score:
            continue
            
        ranked_candidates.append({
            **candidate,
            'matching_score': score,
            'score_percentage': round(score * 100, 1)
        })
    
    # Сортировка по скору (убывание)
    ranked_candidates.sort(key=lambda x: x['matching_score'], reverse=True)
    
    return ranked_candidates

@app.route('/')
def index():
    """Главная страница - дашборд"""
    vacancies = load_data(VACANCIES_FILE)
    candidates = load_data(CANDIDATES_FILE)
    
    stats = {
        'total_vacancies': len(vacancies),
        'total_candidates': len(candidates),
        'active_vacancies': len([v for v in vacancies if v.get('status') == 'active']),
        'recent_candidates': len([c for c in candidates if c.get('created_at', '') > '2024-01-01'])
    }
    
    return render_template('index.html', stats=stats, recent_vacancies=vacancies[:5], recent_candidates=candidates[:5])

@app.route('/vacancies')
def vacancies():
    """Список вакансий"""
    vacancies_list = load_data(VACANCIES_FILE)
    return render_template('vacancies.html', vacancies=vacancies_list)

@app.route('/vacancies/<vacancy_id>')
def vacancy_detail(vacancy_id):
    """Детальная информация о вакансии с ранжированными кандидатами"""
    vacancies = load_data(VACANCIES_FILE)
    vacancy = next((v for v in vacancies if v['id'] == vacancy_id), None)
    
    if not vacancy:
        flash('Вакансия не найдена', 'error')
        return redirect(url_for('vacancies'))
    
    # Получаем ранжированных кандидатов
    status_filter = request.args.get('status')
    min_score_percent = float(request.args.get('min_score', 0.0))
    min_score = min_score_percent / 100.0  # Конвертируем процент в дробь
    
    ranked_candidates = get_ranked_candidates(vacancy_id, status_filter, min_score)
    
    return render_template('vacancy_detail.html', 
                         vacancy=vacancy, 
                         candidates=ranked_candidates,
                         status_filter=status_filter,
                         min_score=min_score_percent)

@app.route('/vacancies/<vacancy_id>/candidates')
def vacancy_candidates(vacancy_id):
    """Список кандидатов для конкретной вакансии с ранжированием"""
    vacancies = load_data(VACANCIES_FILE)
    vacancy = next((v for v in vacancies if v['id'] == vacancy_id), None)
    
    if not vacancy:
        flash('Вакансия не найдена', 'error')
        return redirect(url_for('vacancies'))
    
    # Получаем ранжированных кандидатов
    status_filter = request.args.get('status')
    min_score_percent = float(request.args.get('min_score', 0.0))
    min_score = min_score_percent / 100.0  # Конвертируем процент в дробь
    
    ranked_candidates = get_ranked_candidates(vacancy_id, status_filter, min_score)
    
    return render_template('vacancy_candidates.html', 
                         vacancy=vacancy, 
                         candidates=ranked_candidates,
                         status_filter=status_filter,
                         min_score=min_score_percent)

@app.route('/vacancies/new', methods=['GET', 'POST'])
def new_vacancy():
    """Создание новой вакансии"""
    if request.method == 'POST':
        vacancy = {
            'id': str(uuid.uuid4()),
            'title': request.form['title'],
            'company': request.form['company'],
            'location': request.form['location'],
            'salary_min': request.form.get('salary_min'),
            'salary_max': request.form.get('salary_max'),
            'description': request.form['description'],
            'requirements': request.form['requirements'].split('\n'),
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'candidates_count': 0
        }
        
        vacancies = load_data(VACANCIES_FILE)
        vacancies.append(vacancy)
        save_data(vacancies, VACANCIES_FILE)
        
        flash('Вакансия успешно создана!', 'success')
        return redirect(url_for('vacancies'))
    
    return render_template('new_vacancy.html')

@app.route('/candidates')
def candidates():
    """Список кандидатов"""
    candidates_list = load_data(CANDIDATES_FILE)
    return render_template('candidates.html', candidates=candidates_list)

@app.route('/candidates/new', methods=['GET', 'POST'])
def new_candidate():
    """Добавление нового кандидата"""
    if request.method == 'POST':
        # Обработка загрузки файла
        resume_file = request.files.get('resume')
        resume_path = None
        
        if resume_file and allowed_file(resume_file.filename):
            filename = secure_filename(resume_file.filename)
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume_file.save(resume_path)
        
        candidate = {
            'id': str(uuid.uuid4()),
            'name': request.form['name'],
            'email': request.form['email'],
            'phone': request.form.get('phone'),
            'position': request.form['position'],
            'experience': request.form.get('experience'),
            'skills': request.form['skills'].split('\n'),
            'resume_path': resume_path,
            'status': 'new',
            'created_at': datetime.now().isoformat(),
            'vacancy_id': request.form.get('vacancy_id')
        }
        
        candidates = load_data(CANDIDATES_FILE)
        candidates.append(candidate)
        save_data(candidates, CANDIDATES_FILE)
        
        flash('Кандидат успешно добавлен!', 'success')
        return redirect(url_for('candidates'))
    
    vacancies = load_data(VACANCIES_FILE)
    return render_template('new_candidate.html', vacancies=vacancies)

@app.route('/candidates/<candidate_id>')
def candidate_detail(candidate_id):
    """Детальная информация о кандидате"""
    candidates = load_data(CANDIDATES_FILE)
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    
    if not candidate:
        flash('Кандидат не найден', 'error')
        return redirect(url_for('candidates'))
    
    # Если есть вакансия, сравниваем
    matching_score = None
    if candidate.get('vacancy_id'):
        vacancies = load_data(VACANCIES_FILE)
        vacancy = next((v for v in vacancies if v['id'] == candidate['vacancy_id']), None)
        if vacancy:
            matching_score = calculate_matching_score(candidate, vacancy)
    
    return render_template('candidate_detail.html', candidate=candidate, matching_score=matching_score)

@app.route('/api/match/<candidate_id>/<vacancy_id>')
def api_match(candidate_id, vacancy_id):
    """API для сравнения кандидата и вакансии"""
    candidates = load_data(CANDIDATES_FILE)
    vacancies = load_data(VACANCIES_FILE)
    
    candidate = next((c for c in candidates if c['id'] == candidate_id), None)
    vacancy = next((v for v in vacancies if v['id'] == vacancy_id), None)
    
    if not candidate or not vacancy:
        return jsonify({'error': 'Кандидат или вакансия не найдены'}), 404
    
    score = calculate_matching_score(candidate, vacancy)
    return jsonify({'matching_score': score})

@app.route('/api/vacancies/<vacancy_id>/candidates')
def api_vacancy_candidates(vacancy_id):
    """API для получения ранжированных кандидатов вакансии"""
    status_filter = request.args.get('status')
    min_score_percent = float(request.args.get('min_score', 0.0))
    min_score = min_score_percent / 100.0  # Конвертируем процент в дробь
    
    ranked_candidates = get_ranked_candidates(vacancy_id, status_filter, min_score)
    
    return jsonify({
        'vacancy_id': vacancy_id,
        'candidates': ranked_candidates,
        'total': len(ranked_candidates)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 