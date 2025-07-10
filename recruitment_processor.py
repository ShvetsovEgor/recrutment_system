import os
import base64
import requests
import shutil
import json
import sqlite3
from PyPDF2 import PdfReader, PdfWriter
from dotenv import load_dotenv
from langchain_community.llms import YandexGPT
load_dotenv()
# Конфигурация API
API_KEY = os.getenv('YANDEXGPT_API_KEY')
FOLDER_ID = os.getenv('YANDEXGPT_FOLDER_ID')
MODEL = os.getenv('YANDEXGPT_MODEL')
API_OCR_KEY = os.getenv('YANDEX_OCR_API_KEY')
FOLDER_OCR_ID = os.getenv('YANDEX_OCR_FOLDER_ID')

# Инициализация YandexGPT
GPT = YandexGPT(
    api_key=API_KEY,
    folder_id=FOLDER_ID,
    model=MODEL,
    temperature=0
)

# Заголовки для OCR API


def encode_file(file_path):
    """Кодирует файл в base64 для OCR API"""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def pdf_to_text(pdf_path, output_folder="temp_texts"):
    headers = {
    "Authorization": f"Api-Key {API_OCR_KEY}",
    "x-folder-id": FOLDER_OCR_ID,
    "Content-Type": "application/json"
}
    """Конвертирует PDF в текст с помощью OCR"""
    os.makedirs(output_folder, exist_ok=True)
    
    # Создаем временную папку для страниц
    split_folder = "temp_split_pages"
    os.makedirs(split_folder, exist_ok=True)
    
    try:
        # Читаем PDF
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        
        # Разделяем PDF на страницы
        for i in range(num_pages):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            output_path = os.path.join(split_folder, f"page_{i+1}.pdf")
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
        
        # Обрабатываем каждую страницу через OCR
        full_text = ""
        for i in range(num_pages):
            page_pdf_path = os.path.join(split_folder, f"page_{i+1}.pdf")
            content_base64 = encode_file(page_pdf_path)
            
            data = {
                "mimeType": "application/pdf",
                "languageCodes": ["ru", "en"],
                "content": content_base64,
                "model": "page"
            }
            
            response = requests.post(
                "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                text_from_page = result.get("result", {}).get("textAnnotation", {}).get("fullText", "")
                full_text += text_from_page + "\n"
            else:
                print(f"Ошибка при обработке страницы {i+1}: {response.status_code}")
                print(f"Ответ сервера: {response.text}")

        
        # Сохраняем результат
        filename = os.path.splitext(os.path.basename(pdf_path))[0]
        output_path = os.path.join(output_folder, f"{filename}.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        
        return output_path
        
    finally:
        # Очищаем временные файлы
        if os.path.exists(split_folder):
            shutil.rmtree(split_folder)

def vacancy_to_json(text: str):
    """Преобразует текст вакансии в JSON структуру"""
   
    prompt = f"""
    Ты - HR-специалист. Твоя задача: тебе передают текст вакансии, нужно выделить из него
     требования к кандидату.
    Формат вывода - список JSON, который содержит в себе все навыки и уровень:
    Четкая структура выходных данных, в случае если данные по какой-то шкале не найдены оставь пропуск.
    {{
    "personal_info": {{
      "age": "диапазон возрастов",
      "location": "местоположение",
      "relocation": "возможен переезд или нет"
    }},
    "job_preferences": {{
      "desired_position": "", - должность на которую претендует кандидат
      "employment_type": "", - занятость
      "desired_salary": 0, - предложения по зарплате
    }},
    "work_experience": {{
    "duration": "длительность",
    "position": "занимаемая должность",
    "responsibilities": []}},
    "education": {{
      "level": "уровень образования",
      "specialization": "рекомендуемая специальность",
    }},
    "skills": [список навыков,которые нужны кандидату],
    "skills_technologes": [список стека используемых технологий],
    "languages": [
      {{
        "name": "имя",
        "level": "уровень владения"
      }}
    ],
    }}
    Текст вакансии:
    \"\"\"{text}\"\"\"
    """
    ans = GPT.invoke(prompt)
    ans = ans.replace("```", '')
    
    try:
        return json.loads(ans)
    except json.JSONDecodeError:
        print("Не удалось распарсить JSON вакансии.")
        print(ans)
        return {}

def resume_to_json(text: str):
    """Преобразует текст резюме в JSON структуру"""
    prompt = f"""
    Ты - HR-специалист. Твоя задача: тебе передают текст резюме, нужно выделить из него
     описание кандидата. 
    Формат вывода - список JSON, который содержит в себе все навыки и уровень:
    Четкая структура выходных данных, в случае если данные по какой-то шкале не найдены оставь пропуск.
   {{
    "personal_info": {{
      "name": "фио",
      "age": "возраст",
      "location": "местоположение",
      "relocation": "нужен переезд или нет"
    }},
    "job_preferences": {{
      "desired_position": "", // должность на которую претендует кандидат
      "employment_type": "", // занятость
      "desired_salary": 0 // ожидания по зарплате
    }},
    "work_experience": [
      {{
        "company": "место работы",
        "period": "даты",
        "duration": "длительность",
        "position": "занимаемая должность",
        "responsibilities": []
      }}
    ],
    "education": {{
      "organization": "", // место обучения
      "level": "",// уровень образования,
      "year_of_end": 0, //год окончания
      "specialization": "специальность"
    }},
    "skills": [список навыков кандидата],
    "skills_technologes": [список стека используемых технологий],
    "languages": [
      {{
        "name": "имя",
        "level": "уровень владения"
      }}
    ],
    "contacts": {{}}
  }}
    Текст резюме:
    \"\"\"{text}\"\"\"
    """
    ans = GPT.invoke(prompt)
    ans = ans.replace("```", '')
    
    try:
        return json.loads(ans)
    except json.JSONDecodeError:
        print("Не удалось распарсить JSON резюме.")
        return {}

def scoring(vacancy_json, resume_json):
    """Оценивает соответствие резюме вакансии"""
    
    vacancy_text = json.dumps(vacancy_json, ensure_ascii=False)
    resume_text = json.dumps(resume_json, ensure_ascii=False)
    
    prompt = f"""
    Ты - HR специалист. Сравни совпадающие поля json вакансии с полями json в резюме и оцени соответствие характеристики от 1 до 10.
    Оценка производится по полям: "age", ("location" and "relocation" (в одно поле)), "work_experience"("duration","position","responsibilities" (в одно поле)),"education","skills","skills_technologies","languages", "desired_position","employment_type","desired_salary".
    Ответ представь в виде json c ключами-характеристиками ("age","location","position","employment_type", "desired_salary","work_exp","education","skills","skills_tech","languages") и полями оценка("score") и обоснование("reason").
    Самое важное условие : Если какое-то поле пропущено или не указано, или имеет значение NULL, или "" ставь -1 в "score" и не оценивай (навыки которых нет в вакансии, но есть у кандидата и который помогут в профессиональной деятельности-это хорошо).
    А также дай общее обоснование оценок, характеристику и вопросы на собеседование для кандидата в ключе "final_score" в поле "reason" (не забудь создать поле "score" в "final_score" со значением 0).
    Вакансия:
    \"\"\"{vacancy_text}\"\"\"
    Резюме:
    \"\"\"{resume_text}\"\"\"
    """
    ans = GPT.invoke(prompt)
    ans = ans.replace("```", '')
    
    try:
        scoring_result = json.loads(ans)
        
        # Вычисляем финальную оценку
        weights = [0.3, 0.6, 1, 0.8, 0.6, 0.8, 0.8, 1, 1, 0.5, 0]
        final_score = 0
        max_score = 0
        k = 0
        
        for key in scoring_result:
            if key != "final_score" and scoring_result[key]["score"] != -1:
                final_score += scoring_result[key]["score"] * weights[k]
                max_score += 10 * weights[k]
            k += 1
        
        if max_score > 0:
            scoring_result["final_score"]["score"] = round(final_score / max_score * 100, 1)
        
        return scoring_result
    except json.JSONDecodeError:
        print("Не удалось распарсить JSON оценки.")
        return {}

def save_vacancy_to_db(vacancy_json, raw_text, file_path=None, status='active'):
    """Сохраняет вакансию в базу данных и добавляет запись в job_files"""
    conn = sqlite3.connect('recruitment_system.db')
    cursor = conn.cursor()
    
    # Сохраняем personal_info
    personal_info = vacancy_json.get('personal_info', {})
    cursor.execute('''
        INSERT INTO job_personal_info (age, location, relocation)
        VALUES (?, ?, ?)
    ''', (
        personal_info.get('age', ''),
        personal_info.get('location', ''),
        personal_info.get('relocation', '')
    ))
    personal_info_id = cursor.lastrowid
    
    # Сохраняем preferences
    job_preferences = vacancy_json.get('job_preferences', {})
    cursor.execute('''
        INSERT INTO preferences (desired_position, employment_type, desired_salary)
        VALUES (?, ?, ?)
    ''', (
        job_preferences.get('desired_position', ''),
        job_preferences.get('employment_type', ''),
        job_preferences.get('desired_salary', 0)
    ))
    preferences_id = cursor.lastrowid
    
    # Сохраняем work_experience
    work_exp = vacancy_json.get('work_experience', '')
    cursor.execute('''
        INSERT INTO job_work_experience (duration, position, responsibilities)
        VALUES (?, ?, ?)
    ''', (
        work_exp.get('duration', ''),
        work_exp.get('position', ''),
        json.dumps(work_exp.get('responsibilities', []), ensure_ascii=False),
    ))
    work_exp_id = cursor.lastrowid
    
    # Сохраняем education
    education = vacancy_json.get('education', {})
    cursor.execute('''
        INSERT INTO job_education (level, specialization)
        VALUES (?, ?)
    ''', (
        education.get('level', ''),
        education.get('specialization', '')
    ))
    education_id = cursor.lastrowid
    
    # Сохраняем основную запись вакансии
    cursor.execute('''
        INSERT INTO jobs (fk_jpi_id, fk_p_id, fk_jwe_id, fk_je_id, skills, skills_technologies)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        personal_info_id,
        preferences_id,
        work_exp_id,
        education_id,
        json.dumps(vacancy_json.get('skills', []), ensure_ascii=False),
        json.dumps(vacancy_json.get('skills_technologes', []), ensure_ascii=False)
    ))
    
    job_id = cursor.lastrowid
    
    # Сохраняем языки
    languages = vacancy_json.get('languages', [])
    for lang in languages:
        cursor.execute('''
            INSERT INTO languages (name, level)
            VALUES (?, ?)
        ''', (
            lang.get('name', ''),
            lang.get('level', '')
        ))
        language_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO on_jobs_languages (job_id, language_id)
            VALUES (?, ?)
        ''', (job_id, language_id))
    
    # Добавляем/обновляем запись в job_files
    cursor.execute('INSERT OR REPLACE INTO job_files (job_id, file_path, status) VALUES (?, ?, ?)', (job_id, file_path, status))
    conn.commit()
    conn.close()
    return job_id


def save_resume_to_db(resume_json, raw_text, file_path=None, status='new'):
    """Сохраняет резюме в базу данных и добавляет запись в cv_files"""
    conn = sqlite3.connect('recruitment_system.db')
    cursor = conn.cursor()
    
    # Сохраняем personal_info
    personal_info = resume_json.get('personal_info', {})
    cursor.execute('''
        INSERT INTO cv_personal_info (name, age, location, relocation)
        VALUES (?, ?, ?, ?)
    ''', (
        personal_info.get('name', ''),
        personal_info.get('age', 0),
        personal_info.get('location', ''),
        personal_info.get('relocation', '')
    ))
    personal_info_id = cursor.lastrowid
    
    # Сохраняем preferences
    job_preferences = resume_json.get('job_preferences', {})
    cursor.execute('''
        INSERT INTO preferences (desired_position, employment_type, desired_salary)
        VALUES (?, ?, ?)
    ''', (
        job_preferences.get('desired_position', ''),
        job_preferences.get('employment_type', ''),
        job_preferences.get('desired_salary', 0)
    ))
    preferences_id = cursor.lastrowid
    
    # Сохраняем contacts
    contacts = resume_json.get('contacts', {})
    cursor.execute('''
        INSERT INTO cv_contacts (phone, email, telegram)
        VALUES (?, ?, ?)
    ''', (
        contacts.get('phone', ''),
        contacts.get('email', ''),
        contacts.get('telegram', '')
    ))
    contacts_id = cursor.lastrowid
    
    # Сохраняем основную запись резюме
    cursor.execute('''
        INSERT INTO cvs (fk_cpi_id, fk_p_id, fk_cc_id, skills, skills_technologies)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        personal_info_id,
        preferences_id,
        contacts_id,
        json.dumps(resume_json.get('skills', []), ensure_ascii=False),
        json.dumps(resume_json.get('skills_technologes', []), ensure_ascii=False)
    ))
    
    cv_id = cursor.lastrowid
    
    # Сохраняем education
    education = resume_json.get('education', {})
    cursor.execute('''
        INSERT INTO cv_education (cv_id, organization, level, year_of_end, specialization)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        cv_id,
        education.get('organization', ''),
        education.get('level', ''),
        education.get('year_of_end', 0),
        education.get('specialization', '')
    ))
    
    # Сохраняем work_experience
    work_experience = resume_json.get('work_experience', [])
    for exp in work_experience:
        cursor.execute('''
            INSERT INTO cv_work_experience (cv_id, company, period, duration, position, responsibilities)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            cv_id,
            exp.get('company', ''),
            exp.get('period', ''),
            exp.get('duration', ''),
            exp.get('position', ''),
            json.dumps(exp.get('responsibilities', []), ensure_ascii=False)
        ))
    
    # Сохраняем языки
    languages = resume_json.get('languages', [])
    for lang in languages:
        cursor.execute('''
            INSERT INTO languages (name, level)
            VALUES (?, ?)
        ''', (
            lang.get('name', ''),
            lang.get('level', '')
        ))
        language_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO on_cvs_languages (cv_id, language_id)
            VALUES (?, ?)
        ''', (cv_id, language_id))
    
    # Добавляем/обновляем запись в cv_files
    cursor.execute('INSERT OR REPLACE INTO cv_files (cv_id, file_path, status) VALUES (?, ?, ?)', (cv_id, file_path, status))
    conn.commit()
    conn.close()
    return cv_id

def save_evaluation_to_db(job_id, cv_id, scoring_result):
    """Сохраняет оценку в базу данных"""
    conn = sqlite3.connect('recruitment_system.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO on_jobs_cvs (
            job_id, cv_id, age, location, position, employment_type, desired_salary,
            work_exp, education, skills, skills_tech, languages, final_score,
            age_reason, location_reason, position_reason, employment_type_reason,
            desired_salary_reason, work_exp_reason, education_reason, skills_reason,
            skills_tech_reason, languages_reason, final_score_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        job_id, cv_id,
        scoring_result.get('age', {}).get('score', -1),
        scoring_result.get('location', {}).get('score', -1),
        scoring_result.get('position', {}).get('score', -1),
        scoring_result.get('employment_type', {}).get('score', -1),
        scoring_result.get('desired_salary', {}).get('score', -1),
        scoring_result.get('work_exp', {}).get('score', -1),
        scoring_result.get('education', {}).get('score', -1),
        scoring_result.get('skills', {}).get('score', -1),
        scoring_result.get('skills_tech', {}).get('score', -1),
        scoring_result.get('languages', {}).get('score', -1),
        scoring_result.get('final_score', {}).get('score', 0),
        scoring_result.get('age', {}).get('reason', ''),
        scoring_result.get('location', {}).get('reason', ''),
        scoring_result.get('position', {}).get('reason', ''),
        scoring_result.get('employment_type', {}).get('reason', ''),
        scoring_result.get('desired_salary', {}).get('reason', ''),
        scoring_result.get('work_exp', {}).get('reason', ''),
        scoring_result.get('education', {}).get('reason', ''),
        scoring_result.get('skills', {}).get('reason', ''),
        scoring_result.get('skills_tech', {}).get('reason', ''),
        scoring_result.get('languages', {}).get('reason', ''),
        scoring_result.get('final_score', {}).get('reason', '')
    ))
    
    conn.commit()
    conn.close()

def process_recruitment(vacancy_pdf_path, resume_pdf_path):
    """Основная функция обработки вакансии и резюме"""
    print("=" * 60)
    print("НАЧАЛО ОБРАБОТКИ ВАКАНСИИ И РЕЗЮМЕ")
    print("=" * 60)
    print(f"Вакансия: {vacancy_pdf_path}")
    print(f"Резюме: {resume_pdf_path}")
    print()
    
    # Шаг 1: Конвертируем PDF в текст
    print("ШАГ 1: Конвертация PDF в текст")
    print("-" * 40)
    
    print("1.1. Конвертируем вакансию из PDF в текст...")
    vacancy_text_path = pdf_to_text(vacancy_pdf_path)
    with open(vacancy_text_path, 'r', encoding='utf-8') as f:
        vacancy_text = f.read()
    print(f"Вакансия конвертирована. Размер текста: {len(vacancy_text)} символов")
    
    print("1.2. Конвертируем резюме из PDF в текст...")
    resume_text_path = pdf_to_text(resume_pdf_path)
    with open(resume_text_path, 'r', encoding='utf-8') as f:
        resume_text = f.read()
    print(f"Резюме конвертировано. Размер текста: {len(resume_text)} символов")
    print()
    
    # Шаг 2: Преобразуем в JSON структуры
    print("ШАГ 2: Извлечение структурированных данных")
    print("-" * 40)
    
    print("2.1. Обрабатываем вакансию с помощью YandexGPT...")
    vacancy_json = vacancy_to_json(vacancy_text)
    print("Вакансия обработана и структурирована")
    
    print("2.2. Обрабатываем резюме с помощью YandexGPT...")
    resume_json = resume_to_json(resume_text)
    print("Резюме обработано и структурировано")
    print()
    
    # Шаг 3: Сохраняем в базу данных
    print("ШАГ 3: Сохранение в базу данных")
    print("-" * 40)
    
    print("3.1. Сохраняем вакансию в базу данных...")
    job_id = save_vacancy_to_db(vacancy_json, vacancy_text)
    print(f"Вакансия сохранена с ID: {job_id}")
    
    print("3.2. Сохраняем резюме в базу данных...")
    cv_id = save_resume_to_db(resume_json, resume_text)
    print(f"Резюме сохранено с ID: {cv_id}")
    print()
    
    # Шаг 4: Оцениваем соответствие
    print("ШАГ 4: Оценка соответствия")
    print("-" * 40)
    print("Оцениваем соответствие резюме требованиям вакансии...")
    print(vacancy_json)
    scoring_result = scoring(vacancy_json, resume_json)
    print("Оценка завершена")
    print()
    
    # Шаг 5: Сохраняем оценку
    print("ШАГ 5: Сохранение результатов оценки")
    print("-" * 40)
    print("Сохраняем оценку в базу данных...")
    save_evaluation_to_db(job_id, cv_id, scoring_result)
    print("Оценка сохранена")
    print()
    
    # Шаг 6: Очищаем временные файлы
    print("ШАГ 6: Очистка временных файлов")
    print("-" * 40)
    print("Удаляем временные текстовые файлы...")
    os.remove(vacancy_text_path)
    os.remove(resume_text_path)
    print("Временные файлы удалены")
    print()
    
    # Итоговые результаты
    print("=" * 60)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 60)
    print(f"ID вакансии (jobs): {job_id}")
    print(f"ID резюме (cvs): {cv_id}")
    print(f"Финальная оценка соответствия: {scoring_result.get('final_score', {}).get('score', 0)}%")
    print("=" * 60)
    print("ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО!")
    print("=" * 60)
    
    return {
        'job_id': job_id,
        'cv_id': cv_id,
        'final_score': scoring_result.get('final_score', {}).get('score', 0),
        'scoring_result': scoring_result
    }

def upload_cv(resume_pdf_path, job_id, status='new'):
    """
    Загружает резюме, оценивает его по указанной вакансии и сохраняет все результаты в базу данных.
    :param resume_pdf_path: путь к PDF-файлу резюме
    :param job_id: ID вакансии в базе данных
    :param status: статус резюме (по умолчанию 'new')
    :return: словарь с результатами оценки
    """
    print("=" * 60)
    print("НАЧАЛО ЗАГРУЗКИ И ОЦЕНКИ РЕЗЮМЕ")
    print("=" * 60)
    print(f"Резюме: {resume_pdf_path}")
    print(f"ID вакансии: {job_id}")
    print()

    # Получаем текст вакансии из базы данных
    conn = sqlite3.connect('recruitment_system.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT fk_jpi_id, fk_p_id, fk_jwe_id, fk_je_id, skills, skills_technologies FROM jobs WHERE id = ?
    ''', (job_id,))
    job_row = cursor.fetchone()
    if not job_row:
        print(f"Вакансия с ID {job_id} не найдена!")
        conn.close()
        return None

    # Восстанавливаем JSON вакансии из связанных таблиц
    fk_jpi_id, fk_p_id, fk_jwe_id, fk_je_id, skills_json, skills_technologies_json = job_row
    # personal_info
    cursor.execute('SELECT age, location, relocation FROM job_personal_info WHERE id = ?', (fk_jpi_id,))
    pi = cursor.fetchone()
    personal_info = {"age": pi[0], "location": pi[1], "relocation": pi[2]} if pi else {}
    # job_preferences
    cursor.execute('SELECT desired_position, employment_type, desired_salary FROM preferences WHERE id = ?', (fk_p_id,))
    pr = cursor.fetchone()
    job_preferences = {"desired_position": pr[0], "employment_type": pr[1], "desired_salary": pr[2]} if pr else {}
    # work_experience
    cursor.execute('SELECT duration, position, responsibilities FROM job_work_experience WHERE id = ?', (fk_jwe_id,))
    we = cursor.fetchone()
    work_experience = {"duration": we[0], "position": we[1], "responsibilities": json.loads(we[2])} if we else {}
    # education
    cursor.execute('SELECT level, specialization FROM job_education WHERE id = ?', (fk_je_id,))
    ed = cursor.fetchone()
    education = {"level": ed[0], "specialization": ed[1]} if ed else {}
    # skills, skills_technologes
    skills = json.loads(skills_json) if skills_json else []
    skills_technologes = json.loads(skills_technologies_json) if skills_technologies_json else []
    # languages
    cursor.execute('''
        SELECT l.name, l.level FROM languages l
        JOIN on_jobs_languages ojl ON ojl.language_id = l.id
        WHERE ojl.job_id = ?
    ''', (job_id,))
    languages = [{"name": row[0], "level": row[1]} for row in cursor.fetchall()]
    conn.close()
    vacancy_json = {
        "personal_info": personal_info,
        "job_preferences": job_preferences,
        "work_experience": work_experience,
        "education": education,
        "skills": skills,
        "skills_technologes": skills_technologes,
        "languages": languages
    }

    # 1. Конвертируем PDF резюме в текст
    print("ШАГ 1: Конвертация PDF резюме в текст")
    resume_text_path = pdf_to_text(resume_pdf_path)
    with open(resume_text_path, 'r', encoding='utf-8') as f:
        resume_text = f.read()
    print(f"Резюме конвертировано. Размер текста: {len(resume_text)} символов")
    print()

    # 2. Преобразуем резюме в JSON
    print("ШАГ 2: Извлечение структурированных данных из резюме")
    resume_json = resume_to_json(resume_text)
    print("Резюме обработано и структурировано")
    print()

    # 3. Сохраняем резюме в базу данных
    print("ШАГ 3: Сохранение резюме в базу данных")
    cv_id = save_resume_to_db(resume_json, resume_text, file_path=resume_pdf_path, status=status)
    print(f"Резюме сохранено с ID: {cv_id}")
    print()

    # 4. Оцениваем соответствие
    print("ШАГ 4: Оценка соответствия резюме вакансии")
    scoring_result = scoring(vacancy_json, resume_json)
    print("Оценка завершена")
    print()

    # 5. Сохраняем оценку в базу данных
    print("ШАГ 5: Сохранение результатов оценки")
    save_evaluation_to_db(job_id, cv_id, scoring_result)
    print("Оценка сохранена")
    print()

    # 6. Очищаем временные файлы
    print("ШАГ 6: Очистка временных файлов")
    os.remove(resume_text_path)
    print("Временные файлы удалены")
    print()

    print("=" * 60)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 60)
    print(f"ID вакансии (jobs): {job_id}")
    print(f"ID резюме (cvs): {cv_id}")
    print(f"Финальная оценка соответствия: {scoring_result.get('final_score', {}).get('score', 0)}%")
    print("=" * 60)
    print("ОБРАБОТКА ЗАВЕРШЕНА УСПЕШНО!")
    print("=" * 60)

    return {
        'job_id': job_id,
        'cv_id': cv_id,
        'final_score': scoring_result.get('final_score', {}).get('score', 0),
        'scoring_result': scoring_result
    }

if __name__ == "__main__":
    # Пример использования
    # process_recruitment("path/to/vacancy.pdf", "path/to/resume.pdf")
    pass 