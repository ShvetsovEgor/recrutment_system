import json
import os
import threading
import uuid
from collections.abc import Sequence, Mapping
from datetime import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file

from database import db
from ocr_utils import ocr_pdf, process_resume_with_gpt


def calculate_matching_score(candidate, vacancy, return_details=False):
    """Расчет скора соответствия кандидата и вакансии с использованием YandexGPT (только через scoring, с отладкой)"""
    try:
        from langchain_community.llms import YandexGPT
        import json
        import re
        YANDEX_API_KEY = os.environ.get("YANDEXGPT_API_KEY")
        YANDEX_FOLDER_ID = os.environ.get("YANDEXGPT_FOLDER_ID")
        YANDEX_MODEL = os.environ.get("YANDEXGPT_MODEL")
        GPT = YandexGPT(
            api_key=YANDEX_API_KEY,
            folder_id=YANDEX_FOLDER_ID,
            model=YANDEX_MODEL,
            temperature=0
        )
        def scoring(candidate_data, vacancy_data):
            prompt = f"""
            Сравни определенные поля json вакансии с такими же полями json в резюме и оцени соответствие характеристики от 1 до 10.
            Оценка производится по полям: "age", ("location" и "relocation" (в одно поле)), "work_experience","education","skills","skills_technologies","languages", "desired_position","employment_type","desired_salary".
            Ответ представь в виде json c ключами-характеристиками ("age","location","position","employment_type", "desired_salary","work_exp","education","skills","skills_tech","languages") и полями оценка("score") и обоснование("reason").
            Самое важное условие : Если какое-то поле пропущено или не указано, или имеет значение NULL, или "" ставь -1 в "score" и не оценивай (навыки которых нет в вакансии, но есть у кандидата и который помогут в профессиональной деятельности-это хорошо).
            А также дай общее обоснование оценок, характеристику и вопросы на собеседование для кандидата в ключе "final_score" в поле "reason" (не забудь создать поле "score" в "final_score" со значением 0).
            Вакансия:
            {json.dumps(vacancy_data, ensure_ascii=False)}
            Резюме:
            {json.dumps(candidate_data, ensure_ascii=False)}
            """
            print("[YandexGPT] PROMPT:\n", prompt)
            ans = GPT.invoke(prompt)
            ans = ans.replace("```", '')
            print("[YandexGPT] RESPONSE:\n", ans)
            try:
                return json.loads(ans)
            except json.JSONDecodeError:
                match = re.search(r'"score"\s*:\s*(\d+(?:\.\d+)?)', ans)
                if match:
                    return {"final_score": {"score": float(match.group(1))}}
                match2 = re.search(r'(\d{1,3}(?:\.\d+)?)', ans)
                if match2:
                    return {"final_score": {"score": float(match2.group(1))}}
                return {"final_score": {"score": 0}}
            except Exception:
                return {"final_score": {"score": 0}}
        candidate_data = {
            "age": candidate.get('age_range', ''),
            "location": candidate.get('location', ''),
            "relocation": candidate.get('relocation', False),
            "work_experience": candidate.get('work_experience', ''),
            "education": candidate.get('education_level', ''),
            "education_specialization": candidate.get('education_specialization', ''),
            "skills": candidate.get('skills', []),
            "languages": candidate.get('languages', []),
            "desired_position": candidate.get('desired_position', ''),
            "employment_type": candidate.get('employment_type', ''),
            "desired_salary": candidate.get('desired_salary', '')
        }
        vacancy_data = {
            "title": vacancy.get('title', ''),
            "company": vacancy.get('company', ''),
            "location": vacancy.get('location', ''),
            "description": vacancy.get('description', ''),
            "requirements": vacancy.get('requirements', []),
            "salary_min": vacancy.get('salary_min', ''),
            "salary_max": vacancy.get('salary_max', '')
        }
        job_requirements = scoring(candidate_data, vacancy_data)
        score = 0
        detailed_scores = {}
        overall_assessment = ''
        interview_questions = []
        # Парсим подробные оценки, если они есть
        if job_requirements:
            # Итоговый скор
            if "final_score" in job_requirements and "score" in job_requirements["final_score"]:
                score = job_requirements["final_score"]["score"]
            # Общая оценка
            if "final_score" in job_requirements and "reason" in job_requirements["final_score"]:
                overall_assessment = job_requirements["final_score"]["reason"]
            # Вопросы на собеседование
            if "final_score" in job_requirements and "interview_questions" in job_requirements["final_score"]:
                interview_questions = job_requirements["final_score"]["interview_questions"]
            # Детальные оценки по полям
            for key in ["age","location","work_exp","education","skills","skills_tech","languages"]:
                if key in job_requirements:
                    raw_score = job_requirements[key].get('score', 0)
                    # Приводим к диапазону 0-1, если score > 1 (GPT возвращает 0-10)
                    val = raw_score / 10 if raw_score > 1 else raw_score
                    # Если значение отрицательное, не учитываем его
                    detailed_scores[f'{key}_score'] = val if val >= 0 else None
        try:
            score = float(score)
        except Exception:
            score = 0
        # Если финальный скор > 1, делим на 10 (GPT возвращает 0-10)
        score = score / 10 if score > 1 else score
        if return_details:
            return score, detailed_scores, overall_assessment, interview_questions
        return score
    except ImportError:
        print("[YandexGPT] ImportError: langchain_community.llms.YandexGPT не установлен")
        if return_details:
            return 0, {}, '', []
        return 0
    except Exception as e:
        print(f"[YandexGPT] Ошибка: {e}")
        if return_details:
            return 0, {}, '', []
        return 0


def calculate_matching_score_fallback(candidate, vacancy):
    """Fallback метод расчета скора без GPT"""
    detailed_scores = {}
    comments = {}

    # Сравнение навыков кандидата с требованиями вакансии
    if candidate.get('skills') and vacancy.get('requirements'):
        candidate_skills = candidate['skills']
        vacancy_requirements = vacancy['requirements']
        matching_skills = set(candidate_skills) & set(vacancy_requirements)
        missing_skills = set(vacancy_requirements) - set(candidate_skills)
        skills_score = len(matching_skills) / max(len(vacancy_requirements), 1)
        detailed_scores['skills_score'] = skills_score
        if matching_skills:
            comments['skills_comment'] = f"Совпадающие навыки: {', '.join(matching_skills)}"
        if missing_skills:
            comments['skills_comment'] = comments.get('skills_comment', '') + f". Отсутствуют: {', '.join(missing_skills)}"
        if not matching_skills and not missing_skills:
            comments['skills_comment'] = "Нет совпадающих навыков"
    else:
        detailed_scores['skills_score'] = 0
        comments['skills_comment'] = "Нет данных о навыках или требованиях"

    # Сравнение опыта работы
    if candidate.get('work_experience') and vacancy.get('description'):
        candidate_exp = candidate['work_experience']
        vacancy_desc = vacancy['description']
        from rapidfuzz import fuzz
        experience_score = fuzz.token_sort_ratio(candidate_exp, vacancy_desc) / 100
        detailed_scores['experience_score'] = experience_score
        if experience_score > 0.7:
            comments['experience_comment'] = "Опыт работы хорошо соответствует требованиям"
        elif experience_score > 0.4:
            comments['experience_comment'] = "Опыт работы частично соответствует требованиям"
        else:
            comments['experience_comment'] = "Опыт работы слабо соответствует требованиям"
    else:
        detailed_scores['experience_score'] = 0
        comments['experience_comment'] = "Нет данных об опыте работы"

    # Сравнение должности
    if candidate.get('desired_position') and vacancy.get('title'):
        candidate_pos = candidate['desired_position']
        vacancy_title = vacancy['title']
        from rapidfuzz import fuzz
        position_score = fuzz.token_sort_ratio(candidate_pos, vacancy_title) / 100
        detailed_scores['position_score'] = position_score
        if position_score > 0.8:
            comments['position_comment'] = "Должности полностью совпадают"
        elif position_score > 0.6:
            comments['position_comment'] = "Должности частично совпадают"
        else:
            comments['position_comment'] = "Должности не совпадают"
    else:
        detailed_scores['position_score'] = 0
        comments['position_comment'] = "Нет данных о должности"

    # Сравнение зарплаты
    if candidate.get('desired_salary') and vacancy.get('salary_min') and vacancy.get('salary_max'):
        try:
            candidate_salary = float(candidate['desired_salary'])
            vacancy_min = float(vacancy['salary_min'])
            vacancy_max = float(vacancy['salary_max'])
            if vacancy_min <= candidate_salary <= vacancy_max:
                detailed_scores['salary_score'] = 1.0
                comments['salary_comment'] = f"Ожидания по зарплате ({candidate_salary}) входят в диапазон вакансии ({vacancy_min}-{vacancy_max})"
            else:
                if candidate_salary < vacancy_min:
                    salary_score = max(0, 1 - (vacancy_min - candidate_salary) / max(vacancy_min, 1))
                    comments['salary_comment'] = f"Ожидания по зарплате ({candidate_salary}) ниже минимальных ({vacancy_min})"
                else:
                    salary_score = max(0, 1 - (candidate_salary - vacancy_max) / max(candidate_salary, 1))
                    comments['salary_comment'] = f"Ожидания по зарплате ({candidate_salary}) выше максимальных ({vacancy_max})"
                detailed_scores['salary_score'] = salary_score
        except Exception:
            detailed_scores['salary_score'] = 0
            comments['salary_comment'] = "Ошибка при сравнении зарплаты"
    else:
        detailed_scores['salary_score'] = 0
        comments['salary_comment'] = "Нет данных о зарплате"

    # Сравнение образования
    if candidate.get('education_level') and vacancy.get('requirements'):
        education_score = 0.5  # Базовый скор
        if candidate.get('education_level') in ['bachelor', 'master', 'phd', 'бакалавр', 'магистр', 'кандидат наук']:
            education_score = 0.8
        detailed_scores['education_score'] = education_score
        comments['education_comment'] = f"Уровень образования: {candidate.get('education_level', 'не указан')}"
    else:
        detailed_scores['education_score'] = 0
        comments['education_comment'] = "Нет данных об образовании"

    # Сравнение местоположения
    if candidate.get('location') and vacancy.get('location'):
        from rapidfuzz import fuzz
        location_score = fuzz.token_sort_ratio(candidate['location'], vacancy['location']) / 100
        detailed_scores['location_score'] = location_score
        if location_score > 0.8:
            comments['location_comment'] = "Местоположения совпадают"
        elif candidate.get('relocation'):
            comments['location_comment'] = "Кандидат готов к переезду"
        else:
            comments['location_comment'] = "Местоположения не совпадают, переезд не рассматривается"
    else:
        detailed_scores['location_score'] = 0
        comments['location_comment'] = "Нет данных о местоположении"

    # Итоговый скор — среднее по всем полям
    if detailed_scores:
        overall_score = sum(detailed_scores.values()) / len(detailed_scores)
    else:
        overall_score = 0.5

    # Формируем общую оценку
    if overall_score > 0.8:
        overall_assessment = "Отличное соответствие кандидата требованиям вакансии"
    elif overall_score > 0.6:
        overall_assessment = "Хорошее соответствие кандидата требованиям вакансии"
    elif overall_score > 0.4:
        overall_assessment = "Удовлетворительное соответствие кандидата требованиям вакансии"
    else:
        overall_assessment = "Слабое соответствие кандидата требованиям вакансии"

    # Генерируем вопросы для собеседования
    interview_questions = []
    if detailed_scores.get('skills_score', 0) < 0.7:
        interview_questions.append("Расскажите о вашем опыте работы с технологиями, которые требуются в вакансии")
    if detailed_scores.get('experience_score', 0) < 0.6:
        interview_questions.append("Опишите ваш опыт работы в аналогичных проектах")
    if detailed_scores.get('salary_score', 0) < 0.8:
        interview_questions.append("Обсудите ваши ожидания по зарплате и возможности компромисса")
    if detailed_scores.get('location_score', 0) < 0.5:
        interview_questions.append("Обсудите возможность переезда или удаленной работы")

    # Сохраняем детальный результат в БД
    detailed_result = {
        'skills_score': detailed_scores.get('skills_score', 0),
        'skills_comment': comments.get('skills_comment', ''),
        'experience_score': detailed_scores.get('experience_score', 0),
        'experience_comment': comments.get('experience_comment', ''),
        'position_score': detailed_scores.get('position_score', 0),
        'position_comment': comments.get('position_comment', ''),
        'salary_score': detailed_scores.get('salary_score', 0),
        'salary_comment': comments.get('salary_comment', ''),
        'education_score': detailed_scores.get('education_score', 0),
        'education_comment': comments.get('education_comment', ''),
        'location_score': detailed_scores.get('location_score', 0),
        'location_comment': comments.get('location_comment', '')
    }
    db.add_matching_result(
        candidate['id'],
        vacancy['id'],
        overall_score,
        detailed_result,
        overall_assessment,
        interview_questions
    )
    return overall_score


app = Flask(__name__)
app.secret_key = 'huntflow_mvp_secret_key'

# Конфигурация
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Создаем папку для загрузок
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# База данных теперь используется вместо JSON файлов


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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


def extract_age(age_str):
    """Извлекает число из строки с возрастом"""
    if not age_str:
        return 0
    try:
        # Пытаемся найти число в строке
        import re
        numbers = re.findall(r'\d+', str(age_str))
        if numbers:
            return int(numbers[0])
        return 0
    except (ValueError, TypeError):
        return 0


def compare_numeric(val1, val2):
    n1, n2 = try_float(val1), try_float(val2)
    if n1 is None or n2 is None:
        return 0.0
    diff = abs(n1 - n2)
    maxv = max(abs(n1), abs(n2), 1)
    return 1.0 - min(diff / maxv, 1.0)


def get_ranked_candidates(vacancy_id, status_filter=None, min_score=0.0):
    candidates = db.get_all_candidates()
    vacancy = db.get_vacancy_by_id(vacancy_id)
    if not vacancy:
        return []
    ranked_candidates = []
    for candidate in candidates:
        if status_filter and candidate.get('status') != status_filter:
            continue
        existing_result = db.get_detailed_matching_result(candidate['id'], vacancy['id'])
        if existing_result:
            score = existing_result['final_score'] / 100.0
        else:
            score = None  # Никогда не вызываем calculate_matching_score (GPT)
        if score is not None and score < min_score:
            continue
        ranked_candidates.append({
            **candidate,
            'matching_score': score,
            'score_percentage': round(score * 100, 1) if score is not None else None
        })
    ranked_candidates.sort(key=lambda x: (x['matching_score'] is not None, x['matching_score']), reverse=True)
    return ranked_candidates


@app.route('/')
def index():
    """Главная страница - дашборд"""
    vacancies = db.get_all_vacancies()
    candidates = db.get_all_candidates()
    stats = db.get_statistics()

    return render_template('index.html', stats=stats, recent_vacancies=vacancies[:5], recent_candidates=candidates[:5])


@app.route('/vacancies')
def vacancies():
    """Список вакансий"""
    vacancies_list = db.get_all_vacancies()
    return render_template('vacancies.html', vacancies=vacancies_list)


@app.route('/vacancies/<int:vacancy_id>')
def vacancy_detail(vacancy_id):
    """Детальная информация о вакансии с ранжированными кандидатами"""
    vacancy = db.get_vacancy_by_id(vacancy_id)

    if not vacancy:
        flash('Вакансия не найдена', 'error')
        return redirect(url_for('vacancies'))

    # Проверяем параметр принудительного пересчета
    force_recalculate = request.args.get('force_recalculate', 'false').lower() == 'true'

    if force_recalculate:
        # Удаляем все существующие результаты матчинга для этой вакансии
        matching_results = db.get_matching_results(vacancy_id=vacancy_id)
        for result in matching_results:
            db.delete_matching_result(result['cv_id'], vacancy_id)

    # Получаем ранжированных кандидатов
    status_filter = request.args.get('status')
    min_score_percent = float(request.args.get('min_score', 0.0))
    min_score = min_score_percent / 100.0  # Конвертируем процент в дробь

    ranked_candidates = get_ranked_candidates(vacancy_id, status_filter, min_score)

    # Получаем результаты матчинга для этой вакансии
    matching_results = db.get_matching_results(vacancy_id=vacancy_id)

    return render_template('vacancy_detail.html',
                           vacancy=vacancy,
                           candidates=ranked_candidates,
                           matching_results=matching_results,
                           status_filter=status_filter,
                           min_score=min_score_percent)


@app.route('/vacancies/<int:vacancy_id>/candidates')
def vacancy_candidates(vacancy_id):
    """Список кандидатов для конкретной вакансии с ранжированием"""
    vacancy = db.get_vacancy_by_id(vacancy_id)

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
        vacancy_id = str(uuid.uuid4())
        vacancy_file = request.files.get('vacancy_file')
        vacancy_file_path = None
        if vacancy_file and allowed_file(vacancy_file.filename):
            file_extension = os.path.splitext(vacancy_file.filename)[1]
            filename = f"{vacancy_id}{file_extension}"
            vacancy_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'vacancies')
            os.makedirs(vacancy_upload_folder, exist_ok=True)
            vacancy_file_path = os.path.join('vacancies', filename).replace('\\', '/')
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], vacancy_file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            vacancy_file.save(full_path)
        structured_requirements = None
        if vacancy_file_path and vacancy_file_path.endswith('.pdf'):
            pdf_full_path = os.path.join(app.config['UPLOAD_FOLDER'], vacancy_file_path)
            txt_filename = f"{vacancy_id}.txt"
            json_filename = f"{vacancy_id}.json"
            txt_output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'vacancies', txt_filename)
            json_output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'vacancies', json_filename)
            os.makedirs(os.path.dirname(txt_output_path), exist_ok=True)
            try:
                ocr_pdf(pdf_full_path, txt_output_path)
                process_resume_with_gpt(txt_output_path, json_output_path, is_vacancy=True)
                if os.path.exists(json_output_path):
                    with open(json_output_path, 'r', encoding='utf-8') as f:
                        structured_requirements = json.load(f)
            except Exception as e:
                print(f"Ошибка при обработке PDF вакансии: {e}")
        # Если structured_requirements не получен — не добавлять вакансию
        if not structured_requirements:
            flash('Не удалось получить структурированные данные вакансии. Проверьте корректность файла или попробуйте позже.', 'error')
            return redirect(url_for('new_vacancy'))
        personal_info = structured_requirements.get('personal_info', {})
        job_preferences = structured_requirements.get('job_preferences', {})
        education = structured_requirements.get('education', {})
        work_experience = structured_requirements.get('work_experience', {})
        vacancy_data = {
            'title': request.form.get('title', '').strip(),
            'company': request.form.get('company', '').strip(),
            'description': request.form.get('description', '').strip(),
            'salary_min': request.form.get('salary_min', '').strip(),
            'salary_max': request.form.get('salary_max', '').strip(),
            'vacancy_file_path': vacancy_file_path,
            'age': personal_info.get('age', ''),
            'location': personal_info.get('location', ''),
            'relocation': personal_info.get('relocation', ''),
            'desired_position': job_preferences.get('desired_position', ''),
            'employment_type': job_preferences.get('employment_type', ''),
            'desired_salary': job_preferences.get('desired_salary', 0),
            'education_level': education.get('level', ''),
            'education_specialization': education.get('specialization', ''),
            'work_experience': work_experience,
            'skills': ', '.join(structured_requirements.get('skills', [])),
            'skills_technologies': ', '.join(structured_requirements.get('skills_technologes', [])),
            'languages': structured_requirements.get('languages', [])
        }
        db.create_vacancy(vacancy_data)
        flash('Вакансия успешно добавлена!', 'success')
        return redirect(url_for('index'))
    return render_template('new_vacancy.html')


@app.route('/candidates')
def candidates():
    """Список кандидатов"""
    candidates_list = db.get_all_candidates()
    # Для каждого кандидата подгружаем скор из on_jobs_cvs (если есть вакансия)
    for candidate in candidates_list:
        vacancy_id = candidate.get('job_id') or candidate.get('vacancy_id')
        if vacancy_id:
            result = db.get_detailed_matching_result(candidate['id'], vacancy_id)
            if result and 'final_score' in result:
                candidate['matching_score'] = result['final_score'] / 100.0
            else:
                candidate['matching_score'] = None
        else:
            candidate['matching_score'] = None
    return render_template('candidates.html', candidates=candidates_list)


@app.route('/candidates/new', methods=['GET', 'POST'])
def new_candidate():
    """Добавление нового кандидата"""
    if request.method == 'POST':
        # Генерируем уникальный ID для кандидата
        candidate_id = str(uuid.uuid4())

        # Обработка загрузки файла
        resume_file = request.files.get('resume')
        resume_path = None

        if resume_file and allowed_file(resume_file.filename):
            # Получаем расширение файла
            file_extension = os.path.splitext(resume_file.filename)[1]
            # Создаем имя файла с ID
            filename = f"{candidate_id}{file_extension}"
            # Создаем подпапку для резюме
            resume_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'resume')
            os.makedirs(resume_upload_folder, exist_ok=True)
            resume_path = os.path.join('resume', filename).replace('\\', '/')
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            resume_file.save(full_path)

        # Обрабатываем PDF файл через OCR, если он загружен
        structured_resume_data = None
        if resume_path and resume_path.endswith('.pdf'):
            pdf_full_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_path)
            # Сохраняем txt в папку resume с ID
            txt_filename = f"{candidate_id}.txt"
            json_filename = f"{candidate_id}.json"
            txt_output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resume', txt_filename)
            json_output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resume', json_filename)
            os.makedirs(os.path.dirname(txt_output_path), exist_ok=True)
            try:
                ocr_pdf(pdf_full_path, txt_output_path)

                # Обрабатываем текст через GPT для извлечения структурированных данных
                process_resume_with_gpt(txt_output_path, json_output_path, is_vacancy=False)

                # Читаем результат обработки
                if os.path.exists(json_output_path):
                    with open(json_output_path, 'r', encoding='utf-8') as f:
                        structured_resume_data = json.load(f)
            except Exception as e:
                print(f"Ошибка при обработке PDF резюме: {e}")

        # Фоновая обработка PDF и создание JSON (для совместимости)
        def background_ocr_and_gpt(pdf_path, txt_path, json_path):
            try:
                ocr_pdf(pdf_path, txt_path)
                process_resume_with_gpt(txt_path, json_path, is_vacancy=False)
            except Exception as e:
                print(f"Ошибка при обработке PDF: {e}")

        if resume_path and resume_path.endswith('.pdf'):
            pdf_full_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_path)
            # Используем ID для именования TXT и JSON файлов
            txt_filename = f"{candidate_id}.txt"
            json_filename = f"{candidate_id}.json"
            txt_output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resume', txt_filename)
            json_output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resume', json_filename)
            # Создаем папку если не существует
            os.makedirs(os.path.dirname(txt_output_path), exist_ok=True)
            threading.Thread(target=background_ocr_and_gpt, args=(pdf_full_path, txt_output_path, json_output_path),
                             daemon=True).start()

        # Обработка навыков
        skills_raw = request.form.get('skills', '').strip()
        skills = [s for s in skills_raw.split('\n') if s.strip()] if skills_raw else []

        # Обработка языков
        language_names = request.form.getlist('language_names[]')
        language_levels = request.form.getlist('language_levels[]')
        languages = []
        for i in range(len(language_names)):
            if language_names[i] and language_levels[i]:
                languages.append({
                    'name': language_names[i],
                    'level': language_levels[i]
                })

        # Используем структурированные данные из PDF, если они доступны
        if structured_resume_data:
            # Извлекаем данные из структурированного JSON
            personal_info = structured_resume_data.get('personal_info', {})
            job_preferences = structured_resume_data.get('job_preferences', {})
            education = structured_resume_data.get('education', {})
            work_experience = structured_resume_data.get('work_experience', [])
            contacts = structured_resume_data.get('contacts', {})
            candidate_data = {
                'name': personal_info.get('name', request.form.get('name', '').strip()),
                'age': extract_age(personal_info.get('age')),
                'location': personal_info.get('location', request.form.get('location', '')),
                'relocation': personal_info.get('relocation', request.form.get('relocation') == 'true'),
                'phone': contacts.get('phone', request.form.get('phone', '').strip()),
                'email': contacts.get('email', request.form.get('email', '').strip()),
                'telegram': contacts.get('telegram', request.form.get('telegram', '').strip()),
                'portfolio': contacts.get('portfolio', request.form.get('portfolio', '').strip()),
                'desired_position': job_preferences.get('desired_position', request.form.get('desired_position', '')),
                'employment_type': job_preferences.get('employment_type', request.form.get('employment_type', '')),
                'desired_salary': job_preferences.get('desired_salary',
                                                      float(request.form.get('desired_salary', 0) or 0)),
                'organization': education.get('organization', ''),
                'education_level': education.get('level', request.form.get('education_level', '')),
                'year_of_end': education.get('year_of_end', 0),
                'education_specialization': education.get('specialization',
                                                          request.form.get('education_specialization', '')),
                'work_experience': work_experience,
                'skills': ', '.join(structured_resume_data.get('skills', [])),
                'skills_technologies': ', '.join(structured_resume_data.get('skills_technologies', [])),
                'languages': structured_resume_data.get('languages', languages),
                'resume_path': resume_path,
                'job_id': int(request.form.get('vacancy_id', 0)) if request.form.get('vacancy_id') else None
            }
        else:
            # Используем данные из формы
            candidate_data = {
                'name': request.form.get('name', '').strip(),
                'age': extract_age(request.form.get('age_range')),
                'location': request.form.get('location', ''),
                'relocation': request.form.get('relocation') == 'true',
                'phone': request.form.get('phone', '').strip(),
                'email': request.form.get('email', '').strip(),
                'telegram': request.form.get('telegram', '').strip(),
                'portfolio': request.form.get('portfolio', '').strip(),
                'desired_position': request.form.get('desired_position', ''),
                'employment_type': request.form.get('employment_type', ''),
                'desired_salary': float(request.form.get('desired_salary', 0) or 0),
                'organization': '',
                'education_level': request.form.get('education_level', ''),
                'year_of_end': 0,
                'education_specialization': request.form.get('education_specialization', ''),
                'work_experience': [],
                'skills': ', '.join(skills),
                'skills_technologies': '',
                'languages': languages,
                'resume_path': resume_path,
                'job_id': int(request.form.get('vacancy_id', 0)) if request.form.get('vacancy_id') else None
            }

        # Создаем кандидата в базе данных
        new_candidate_id = db.create_candidate(candidate_data)
        # Если указан vacancy_id — сразу рассчитываем скор и заполняем on_jobs_cvs
        vacancy_id = candidate_data.get('job_id')
        if vacancy_id:
            candidate_obj = db.get_candidate_by_id(new_candidate_id)
            vacancy_obj = db.get_vacancy_by_id(vacancy_id)
            if candidate_obj and vacancy_obj:
                # Получаем score и подробные данные
                score, detailed_scores, overall_assessment, interview_questions = calculate_matching_score(candidate_obj, vacancy_obj, return_details=True)
                db.add_matching_result(
                    candidate_obj['id'],
                    vacancy_obj['id'],
                    score,
                    detailed_scores,
                    overall_assessment,
                    interview_questions
                )
        flash('Обработка файла запущена. Результат появится через несколько минут.', 'info')
        return redirect(url_for('index'))  # Перенаправляем на главную страницу

    vacancies = db.get_all_vacancies()
    return render_template('new_candidate.html', vacancies=vacancies)


@app.route('/candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
def edit_candidate(candidate_id):
    """Редактирование кандидата"""
    candidate = db.get_candidate_by_id(candidate_id)
    if not candidate:
        flash('Кандидат не найден', 'error')
        return redirect(url_for('candidates'))

    if request.method == 'POST':
        # Обработка загрузки файла
        resume_file = request.files.get('resume')
        resume_path = candidate.get('resume_path')

        if resume_file and allowed_file(resume_file.filename):
            # Получаем расширение файла
            file_extension = os.path.splitext(resume_file.filename)[1]
            # Создаем имя файла с ID
            filename = f"{candidate_id}{file_extension}"
            # Создаем подпапку для резюме
            resume_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'resume')
            os.makedirs(resume_upload_folder, exist_ok=True)
            resume_path = os.path.join('resume', filename).replace('\\', '/')
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            resume_file.save(full_path)

        # Обработка навыков
        skills_raw = request.form.get('skills', '').strip()
        skills = [s for s in skills_raw.split('\n') if s.strip()] if skills_raw else []

        # Обработка языков
        language_names = request.form.getlist('language_names[]')
        language_levels = request.form.getlist('language_levels[]')
        languages = []
        for i in range(len(language_names)):
            if language_names[i].strip():
                languages.append({
                    'name': language_names[i].strip(),
                    'level': language_levels[i] if i < len(language_levels) else 'basic'
                })

        candidate_data = {
            'name': request.form.get('name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'telegram': request.form.get('telegram', '').strip(),
            'portfolio': request.form.get('portfolio', '').strip(),
            'age_range': request.form.get('age_range', ''),
            'location': request.form.get('location', '').strip(),
            'relocation': request.form.get('relocation') == 'on',
            'desired_position': request.form.get('desired_position', '').strip(),
            'employment_type': request.form.get('employment_type', ''),
            'desired_salary': request.form.get('desired_salary', '').strip(),
            'work_experience': request.form.get('work_experience', '').strip(),
            'education_level': request.form.get('education_level', ''),
            'education_specialization': request.form.get('education_specialization', '').strip(),
            'skills': skills,
            'languages': languages,
            'resume_path': resume_path,
            'status': request.form.get('status', 'new'),
            'vacancy_id': request.form.get('vacancy_id', '')
        }

        if db.update_candidate(candidate_id, candidate_data):
            flash('Кандидат успешно обновлен', 'success')
            return redirect(url_for('candidate_detail', candidate_id=candidate_id))
        else:
            flash('Ошибка при обновлении кандидата', 'error')

    # Получаем список вакансий для выбора
    vacancies = db.get_all_vacancies()

    return render_template('edit_candidate.html', candidate=candidate, vacancies=vacancies)


@app.route('/candidates/<int:candidate_id>')
def candidate_detail(candidate_id):
    candidate = db.get_candidate_by_id(candidate_id)
    matching_score = None
    if candidate:
        vacancy_id = candidate.get('job_id') or candidate.get('vacancy_id')
        if vacancy_id:
            result = db.get_detailed_matching_result(candidate['id'], vacancy_id)
            if result and 'final_score' in result:
                matching_score = result['final_score'] / 100.0
    return render_template('candidate_detail.html', candidate=candidate, matching_score=matching_score)


@app.route('/api/match/<int:candidate_id>/<int:vacancy_id>')
def api_match(candidate_id, vacancy_id):
    """API для сравнения кандидата и вакансии"""
    candidate = db.get_candidate_by_id(candidate_id)
    vacancy = db.get_vacancy_by_id(vacancy_id)

    if not candidate or not vacancy:
        return jsonify({'error': 'Кандидат или вакансия не найдены'}), 404

    # Проверяем параметр force_recalculate
    force_recalculate = request.args.get('force_recalculate', 'false').lower() == 'true'

    if force_recalculate:
        # Удаляем существующий результат и пересчитываем
        db.delete_matching_result(candidate_id, vacancy_id)

    score = calculate_matching_score(candidate, vacancy)

    # Получаем детальный результат
    detailed_result = db.get_detailed_matching_result(candidate_id, vacancy_id)

    return jsonify({
        'matching_score': score,
        'detailed_result': detailed_result,
        'force_recalculated': force_recalculate
    })


@app.route('/api/vacancies/<int:vacancy_id>/candidates')
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


@app.route('/matching/<int:candidate_id>/<int:vacancy_id>')
def detailed_matching(candidate_id, vacancy_id):
    """Детальный результат матчинга кандидата и вакансии"""
    candidate = db.get_candidate_by_id(candidate_id)
    vacancy = db.get_vacancy_by_id(vacancy_id)

    if not candidate or not vacancy:
        flash('Кандидат или вакансия не найдены', 'error')
        return redirect(url_for('index'))

    # Получаем детальный результат матчинга только из БД
    detailed_result = db.get_detailed_matching_result(candidate_id, vacancy_id)

    return render_template('detailed_matching.html',
                           candidate=candidate,
                           vacancy=vacancy,
                           matching=detailed_result)


@app.route('/vacancies/<int:vacancy_id>/edit', methods=['GET', 'POST'])
def edit_vacancy(vacancy_id):
    """Редактирование вакансии"""
    vacancy = db.get_vacancy_by_id(vacancy_id)
    if not vacancy:
        flash('Вакансия не найдена', 'error')
        return redirect(url_for('vacancies'))

    if request.method == 'POST':
        # Обработка загрузки файла
        vacancy_file = request.files.get('vacancy_file')
        vacancy_file_path = vacancy.get('vacancy_file_path')

        if vacancy_file and allowed_file(vacancy_file.filename):
            # Получаем расширение файла
            file_extension = os.path.splitext(vacancy_file.filename)[1]
            # Создаем имя файла с ID
            filename = f"{vacancy_id}{file_extension}"
            # Создаем подпапку для вакансий
            vacancy_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'vacancies')
            os.makedirs(vacancy_upload_folder, exist_ok=True)
            vacancy_file_path = os.path.join('vacancies', filename).replace('\\', '/')
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], vacancy_file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            vacancy_file.save(full_path)

        requirements_raw = request.form.get('requirements', '').strip()
        requirements = [r for r in requirements_raw.split('\n') if r.strip()] if requirements_raw else []

        vacancy_data = {
            'title': request.form.get('title', '').strip(),
            'company': request.form.get('company', '').strip(),
            'location': request.form.get('location', '').strip(),
            'salary_min': request.form.get('salary_min', '').strip(),
            'salary_max': request.form.get('salary_max', '').strip(),
            'description': request.form.get('description', '').strip(),
            'requirements': requirements,
            'vacancy_file_path': vacancy_file_path,
            'status': request.form.get('status', 'active')
        }

        if db.update_vacancy(vacancy_id, vacancy_data):
            flash('Вакансия успешно обновлена', 'success')
            return redirect(url_for('vacancy_detail', vacancy_id=vacancy_id))
        else:
            flash('Ошибка при обновлении вакансии', 'error')

    return render_template('edit_vacancy.html', vacancy=vacancy)


@app.route('/vacancies/<int:vacancy_id>/file')
def download_vacancy_file(vacancy_id):
    vacancy = db.get_vacancy_by_id(vacancy_id)
    if not vacancy or not vacancy.get('vacancy_file_path'):
        flash('Файл вакансии не найден', 'error')
        return redirect(url_for('vacancies'))
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], vacancy['vacancy_file_path'])
    if not os.path.exists(file_path):
        flash('Файл не найден на сервере', 'error')
        return redirect(url_for('vacancies'))
    if file_path.endswith('.pdf'):
        filename = os.path.basename(file_path).replace('.pdf', '.txt')
        txt_output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'vacancies', filename)
        os.makedirs(os.path.dirname(txt_output_path), exist_ok=True)
        try:
            ocr_pdf(file_path, txt_output_path)
        except Exception:
            pass
    return send_file(file_path, as_attachment=True)


@app.route('/candidates/<int:candidate_id>/resume')
def download_candidate_resume(candidate_id):
    candidate = db.get_candidate_by_id(candidate_id)
    if not candidate:
        flash('Кандидат не найден', 'error')
        return redirect(url_for('candidates'))
    resume_path = candidate.get('resume_path')
    if not resume_path:
        flash('Резюме не загружено', 'error')
        return redirect(url_for('candidates'))
    if not os.path.isabs(resume_path):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_path)
    else:
        file_path = resume_path
    if not os.path.exists(file_path):
        flash('Файл резюме не найден на сервере', 'error')
        return redirect(url_for('candidates'))
    return send_file(file_path, as_attachment=True)


@app.route('/vacancies/<int:vacancy_id>/delete', methods=['DELETE'])
def delete_vacancy(vacancy_id):
    vacancy = db.get_vacancy_by_id(vacancy_id)
    if not vacancy:
        return jsonify({'error': 'Вакансия не найдена'}), 404
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], vacancy['vacancy_file_path'])
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
    # Удаляем из базы данных
    db.delete_vacancy(vacancy_id)
    return jsonify({'success': True})


@app.route('/candidates/<int:candidate_id>/delete', methods=['DELETE'])
def delete_candidate(candidate_id):
    candidate = db.get_candidate_by_id(candidate_id)
    if not candidate:
        return jsonify({'error': 'Кандидат не найден'}), 404
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], candidate.get('resume_path', ''))
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
    # Удаляем из базы данных
    db.delete_candidate(candidate_id)
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
