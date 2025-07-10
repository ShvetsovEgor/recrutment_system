from flask import Flask, render_template, send_from_directory, abort, request, redirect, url_for, flash
import sqlite3
import os
import json
import recruitment_processor

app = Flask(__name__, template_folder="templates")
app.secret_key = 'djzfSvkas2351sFAAWji38fjk032uh38f'
DB_PATH = os.path.join(os.path.dirname(__file__), 'recruitment_system.db')

# --- Вспомогательные функции ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_candidates():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT cvs.id, cv_personal_info.name, preferences.desired_position, cv_contacts.email, cv_contacts.phone,
               cv_files.status, cvs.skills, cv_files.file_path,
               (SELECT final_score FROM on_jobs_cvs WHERE cv_id = cvs.id LIMIT 1) as matching_score
        FROM cvs
        LEFT JOIN cv_personal_info ON cvs.fk_cpi_id = cv_personal_info.id
        LEFT JOIN preferences ON cvs.fk_p_id = preferences.id
        LEFT JOIN cv_contacts ON cvs.fk_cc_id = cv_contacts.id
        LEFT JOIN cv_files ON cv_files.cv_id = cvs.id
    ''')
    candidates = []
    for row in cur.fetchall():
        candidates.append({
            'id': row['id'],
            'name': row['name'],
            'desired_position': row['desired_position'],
            'email': row['email'],
            'phone': row['phone'],
            'status': row['status'],
            'skills': json.loads(row['skills']) if row['skills'] else [],
            'resume_path': row['file_path'],
            'matching_score': row['matching_score']
        })
    conn.close()
    return candidates

def get_candidate(candidate_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT cvs.id, cv_personal_info.name, preferences.desired_position, cv_contacts.email, cv_contacts.phone,
               cv_files.status, cvs.skills, cv_files.file_path,
               (SELECT final_score FROM on_jobs_cvs WHERE cv_id = cvs.id LIMIT 1) as matching_score,
               (SELECT job_id FROM on_jobs_cvs WHERE cv_id = cvs.id LIMIT 1) as vacancy_id
        FROM cvs
        LEFT JOIN cv_personal_info ON cvs.fk_cpi_id = cv_personal_info.id
        LEFT JOIN preferences ON cvs.fk_p_id = preferences.id
        LEFT JOIN cv_contacts ON cvs.fk_cc_id = cv_contacts.id
        LEFT JOIN cv_files ON cv_files.cv_id = cvs.id
        WHERE cvs.id = ?
    ''', (candidate_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row['id'],
        'name': row['name'],
        'desired_position': row['desired_position'],
        'email': row['email'],
        'phone': row['phone'],
        'status': row['status'],
        'skills': json.loads(row['skills']) if row['skills'] else [],
        'resume_path': row['file_path'],
        'matching_score': row['matching_score'],
        'vacancy_id': row['vacancy_id']
    }

def get_vacancies():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT jobs.id, preferences.desired_position, job_personal_info.location, preferences.desired_salary,
               COALESCE(job_files.status, 'active') as status, job_files.file_path, jobs.skills
        FROM jobs
        LEFT JOIN preferences ON jobs.fk_p_id = preferences.id
        LEFT JOIN job_personal_info ON jobs.fk_jpi_id = job_personal_info.id
        LEFT JOIN job_files ON job_files.job_id = jobs.id
    ''')
    vacancies = []
    for row in cur.fetchall():
        # Подсчёт количества кандидатов для вакансии
        cur2 = conn.cursor()
        cur2.execute('SELECT COUNT(*) FROM on_jobs_cvs WHERE job_id = ?', (row['id'],))
        candidates_count = cur2.fetchone()[0]
        # Делаем первую букву заглавной, если она строчная
        desired_position = row['desired_position']
        if desired_position and len(desired_position) > 0:
            desired_position = desired_position[0].upper() + desired_position[1:]
        vacancies.append({
            'id': row['id'],
            'desired_position': desired_position,
            'title': desired_position,  # Для корректного отображения в форме
            'location': row['location'],
            'desired_salary': row['desired_salary'],
            'status': row['status'],
            'file_path': row['file_path'],
            'skills': json.loads(row['skills']) if row['skills'] else [],
            'candidates_count': candidates_count
        })
    conn.close()
    return vacancies

def get_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    # Всего вакансий
    cur.execute('SELECT COUNT(*) FROM jobs')
    total_vacancies = cur.fetchone()[0]
    # Активных вакансий (по статусу в job_files или по умолчанию active)
    cur.execute("SELECT COUNT(*) FROM jobs LEFT JOIN job_files ON jobs.id = job_files.job_id WHERE COALESCE(job_files.status, 'active') = 'active'")
    active_vacancies = cur.fetchone()[0]
    # Всего кандидатов
    cur.execute('SELECT COUNT(*) FROM cvs')
    total_candidates = cur.fetchone()[0]
    # Недавно добавленные кандидаты (например, за последние 7 дней, если есть поле created_at, иначе просто последние 5)
    cur.execute('SELECT COUNT(*) FROM cvs')
    recent_candidates = cur.fetchone()[0]  # Можно заменить на более сложную логику, если появится поле created_at
    conn.close()
    return {
        'total_vacancies': total_vacancies,
        'active_vacancies': active_vacancies,
        'total_candidates': total_candidates,
        'recent_candidates': recent_candidates
    }

def get_vacancy(vacancy_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT jobs.id, preferences.desired_position, job_personal_info.location, preferences.desired_salary,
               COALESCE(job_files.status, 'active') as status, job_files.file_path, jobs.skills
        FROM jobs
        LEFT JOIN preferences ON jobs.fk_p_id = preferences.id
        LEFT JOIN job_personal_info ON jobs.fk_jpi_id = job_personal_info.id
        LEFT JOIN job_files ON job_files.job_id = jobs.id
        WHERE jobs.id = ?
    ''', (vacancy_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row['id'],
        'desired_position': row['desired_position'],
        'location': row['location'],
        'desired_salary': row['desired_salary'],
        'status': row['status'],
        'file_path': row['file_path'],
        'skills': json.loads(row['skills']) if row['skills'] else []
    }

def get_candidates_for_vacancy(vacancy_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT cvs.id, cv_personal_info.name, preferences.desired_position, cv_contacts.email, cv_contacts.phone,
               cv_files.status, cvs.skills, cv_files.file_path, on_jobs_cvs.final_score as matching_score
        FROM on_jobs_cvs
        JOIN cvs ON on_jobs_cvs.cv_id = cvs.id
        LEFT JOIN cv_personal_info ON cvs.fk_cpi_id = cv_personal_info.id
        LEFT JOIN preferences ON cvs.fk_p_id = preferences.id
        LEFT JOIN cv_contacts ON cvs.fk_cc_id = cv_contacts.id
        LEFT JOIN cv_files ON cv_files.cv_id = cvs.id
        WHERE on_jobs_cvs.job_id = ?
    ''', (vacancy_id,))
    candidates = []
    for row in cur.fetchall():
        candidates.append({
            'id': row['id'],
            'name': row['name'],
            'desired_position': row['desired_position'],
            'email': row['email'],
            'phone': row['phone'],
            'status': row['status'],
            'skills': json.loads(row['skills']) if row['skills'] else [],
            'resume_path': row['file_path'],
            'matching_score': row['matching_score']
        })
    conn.close()
    return candidates

def init_missing_records():
    """Инициализирует недостающие записи в job_files и cv_files"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Добавляем записи в job_files для вакансий без файлов
    cur.execute('''
        INSERT OR IGNORE INTO job_files (job_id, file_path, status)
        SELECT jobs.id, NULL, 'active'
        FROM jobs
        LEFT JOIN job_files ON jobs.id = job_files.job_id
        WHERE job_files.job_id IS NULL
    ''')
    
    # Добавляем записи в cv_files для кандидатов без файлов
    cur.execute('''
        INSERT OR IGNORE INTO cv_files (cv_id, file_path, status)
        SELECT cvs.id, NULL, 'new'
        FROM cvs
        LEFT JOIN cv_files ON cvs.id = cv_files.cv_id
        WHERE cv_files.cv_id IS NULL
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    init_missing_records()  # Инициализируем недостающие записи
    stats = get_stats()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''SELECT jobs.id, preferences.desired_position, preferences.desired_salary, job_personal_info.location, COALESCE(job_files.status, 'active') as status
                   FROM jobs
                   LEFT JOIN preferences ON jobs.fk_p_id = preferences.id
                   LEFT JOIN job_personal_info ON jobs.fk_jpi_id = job_personal_info.id
                   LEFT JOIN job_files ON job_files.job_id = jobs.id
                   ORDER BY jobs.id DESC LIMIT 5''')
    recent_vacancies = cur.fetchall()
    cur.execute('''SELECT cvs.id, cv_personal_info.name, preferences.desired_position, cv_files.status
                   FROM cvs
                   LEFT JOIN cv_personal_info ON cvs.fk_cpi_id = cv_personal_info.id
                   LEFT JOIN preferences ON cvs.fk_p_id = preferences.id
                   LEFT JOIN cv_files ON cv_files.cv_id = cvs.id
                   ORDER BY cvs.id DESC LIMIT 5''')
    recent_candidates = cur.fetchall()
    conn.close()
    return render_template('index.html', stats=stats, recent_vacancies=recent_vacancies, recent_candidates=recent_candidates)

@app.route('/candidates')
def candidates():
    return render_template('candidates.html', candidates=get_candidates())

@app.route('/candidate/<int:candidate_id>')
def candidate_detail(candidate_id):
    candidate = get_candidate(candidate_id)
    if not candidate:
        abort(404)
    return render_template('candidate_detail.html', candidate=candidate)

@app.route('/vacancies')
def vacancies():
    return render_template('vacancies.html', vacancies=get_vacancies())

@app.route('/new_vacancy', methods=['GET', 'POST'])
def new_vacancy():
    if request.method == 'POST':
        file = request.files.get('vacancy_file')
        status = request.form.get('status', 'active')
        file_path = None
        if file and file.filename:
            upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, file.filename)
            file.save(file_path)
            # --- Парсим PDF и сохраняем вакансию ---
            text_path = recruitment_processor.pdf_to_text(file_path)
            with open(text_path, 'r', encoding='utf-8') as f:
                vacancy_text = f.read()
            vacancy_json = recruitment_processor.vacancy_to_json(vacancy_text)
            job_id = recruitment_processor.save_vacancy_to_db(vacancy_json, vacancy_text)
            # Сохраняем файл и статус
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('INSERT OR REPLACE INTO job_files (job_id, file_path, status) VALUES (?, ?, ?)', (job_id, file_path, status))
            conn.commit()
            conn.close()
            os.remove(text_path)
            flash('Вакансия успешно добавлена!', 'success')
            return redirect(url_for('vacancies'))
        else:
            flash('Загрузите PDF-файл вакансии!', 'danger')
    return render_template('new_vacancy.html')

@app.route('/new_candidate', methods=['GET', 'POST'])
def new_candidate():
    if request.method == 'POST':
        file = request.files.get('resume')
        status = request.form.get('status', 'new')
        vacancy_id = request.form.get('vacancy_id')
        file_path = None
        if file and file.filename:
            upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, file.filename)
            file.save(file_path)
            # --- Используем upload_cv для обработки резюме и привязки к вакансии ---
            if vacancy_id:
                result = recruitment_processor.upload_cv(file_path, int(vacancy_id))
            else:
                # Если вакансия не выбрана, просто сохраняем резюме без оценки
                # Используем save_resume_to_db напрямую
                text_path = recruitment_processor.pdf_to_text(file_path)
                with open(text_path, 'r', encoding='utf-8') as f:
                    resume_text = f.read()
                resume_json = recruitment_processor.resume_to_json(resume_text)
                cv_id = recruitment_processor.save_resume_to_db(resume_json, resume_text)
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('INSERT OR REPLACE INTO cv_files (cv_id, file_path, status) VALUES (?, ?, ?)', (cv_id, file_path, status))
                conn.commit()
                conn.close()
                os.remove(text_path)
            flash('Кандидат успешно добавлен!', 'success')
            return redirect(url_for('candidates'))
        else:
            flash('Загрузите PDF-файл резюме!', 'danger')
    vacancies = get_vacancies()
    return render_template('new_candidate.html', vacancies=vacancies)

@app.route('/download_candidate_resume/<int:candidate_id>')
def download_candidate_resume(candidate_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT file_path FROM cv_files WHERE cv_id = ?', (candidate_id,))
    row = cur.fetchone()
    conn.close()
    if not row or not row['file_path']:
        abort(404)
    file_path = row['file_path']
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/vacancy_candidates/<int:vacancy_id>')
def vacancy_candidates(vacancy_id):
    vacancy = get_vacancy(vacancy_id)
    if not vacancy:
        abort(404)
    candidates = get_candidates_for_vacancy(vacancy_id)
    return render_template('vacancy_candidates.html', vacancy=vacancy, candidates=candidates)

@app.route('/vacancy/<int:vacancy_id>')
def vacancy_detail(vacancy_id):
    vacancy = get_vacancy(vacancy_id)
    if not vacancy:
        abort(404)
    candidates = get_candidates_for_vacancy(vacancy_id)
    return render_template('vacancy_detail.html', vacancy=vacancy, candidates=candidates)

@app.route('/edit_vacancy/<int:vacancy_id>', methods=['GET', 'POST'])
def edit_vacancy(vacancy_id):
    vacancy = get_vacancy(vacancy_id)
    if not vacancy:
        abort(404)
    if request.method == 'POST':
        desired_position = request.form.get('desired_position')
        location = request.form.get('location')
        desired_salary = request.form.get('desired_salary')
        skills = request.form.get('skills')
        file = request.files.get('file')
        status = request.form.get('status')
        file_path = vacancy['file_path']
        if file and file.filename:
            upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, file.filename)
            file.save(file_path)
        conn = get_db_connection()
        cur = conn.cursor()
        # Обновляем preferences
        cur.execute('''UPDATE preferences SET desired_position=?, desired_salary=? WHERE id=(SELECT fk_p_id FROM jobs WHERE id=?)''', (desired_position, desired_salary, vacancy_id))
        # Обновляем job_personal_info
        cur.execute('''UPDATE job_personal_info SET location=? WHERE id=(SELECT fk_jpi_id FROM jobs WHERE id=?)''', (location, vacancy_id))
        # Обновляем skills
        skills_list = [s.strip() for s in (skills or '').split(',') if s.strip()]
        cur.execute('''UPDATE jobs SET skills=? WHERE id=?''', (json.dumps(skills_list, ensure_ascii=False), vacancy_id))
        # Обновляем файл и статус
        cur.execute('''UPDATE job_files SET file_path=?, status=? WHERE job_id=?''', (file_path, status, vacancy_id))
        conn.commit()
        conn.close()
        flash('Вакансия успешно обновлена!', 'success')
        return redirect(url_for('vacancy_detail', vacancy_id=vacancy_id))
    return render_template('edit_vacancy.html', vacancy=vacancy)

@app.route('/edit_candidate/<int:candidate_id>', methods=['GET', 'POST'])
def edit_candidate(candidate_id):
    candidate = get_candidate(candidate_id)
    if not candidate:
        abort(404)
    if request.method == 'POST':
        name = request.form.get('name')
        desired_position = request.form.get('desired_position')
        email = request.form.get('email')
        phone = request.form.get('phone')
        skills = request.form.get('skills')
        file = request.files.get('file')
        status = request.form.get('status')
        file_path = candidate['resume_path']
        if file and file.filename:
            upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, file.filename)
            file.save(file_path)
        conn = get_db_connection()
        cur = conn.cursor()
        # Обновляем personal_info
        cur.execute('''UPDATE cv_personal_info SET name=? WHERE id=(SELECT fk_cpi_id FROM cvs WHERE id=?)''', (name, candidate_id))
        # Обновляем preferences
        cur.execute('''UPDATE preferences SET desired_position=? WHERE id=(SELECT fk_p_id FROM cvs WHERE id=?)''', (desired_position, candidate_id))
        # Обновляем contacts
        cur.execute('''UPDATE cv_contacts SET phone=?, email=? WHERE id=(SELECT fk_cc_id FROM cvs WHERE id=?)''', (phone, email, candidate_id))
        # Обновляем skills
        skills_list = [s.strip() for s in (skills or '').split(',') if s.strip()]
        cur.execute('''UPDATE cvs SET skills=? WHERE id=?''', (json.dumps(skills_list, ensure_ascii=False), candidate_id))
        # Обновляем файл и статус
        cur.execute('''UPDATE cv_files SET file_path=?, status=? WHERE cv_id=?''', (file_path, status, candidate_id))
        conn.commit()
        conn.close()
        flash('Кандидат успешно обновлён!', 'success')
        return redirect(url_for('candidate_detail', candidate_id=candidate_id))
    return render_template('edit_candidate.html', candidate=candidate)

@app.route('/delete_vacancy/<int:vacancy_id>', methods=['POST'])
def delete_vacancy(vacancy_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # Удаляем связанные записи
    cur.execute('DELETE FROM job_files WHERE job_id = ?', (vacancy_id,))
    cur.execute('DELETE FROM on_jobs_languages WHERE job_id = ?', (vacancy_id,))
    cur.execute('DELETE FROM on_jobs_cvs WHERE job_id = ?', (vacancy_id,))
    # Получаем связанные id для preferences, job_personal_info, job_work_experience, job_education
    cur.execute('SELECT fk_p_id, fk_jpi_id, fk_jwe_id, fk_je_id FROM jobs WHERE id = ?', (vacancy_id,))
    row = cur.fetchone()
    if row:
        fk_p_id, fk_jpi_id, fk_jwe_id, fk_je_id = row
        cur.execute('DELETE FROM preferences WHERE id = ?', (fk_p_id,))
        cur.execute('DELETE FROM job_personal_info WHERE id = ?', (fk_jpi_id,))
        cur.execute('DELETE FROM job_work_experience WHERE id = ?', (fk_jwe_id,))
        cur.execute('DELETE FROM job_education WHERE id = ?', (fk_je_id,))
    # Удаляем саму вакансию
    cur.execute('DELETE FROM jobs WHERE id = ?', (vacancy_id,))
    conn.commit()
    conn.close()
    flash('Вакансия удалена!', 'success')
    return redirect(url_for('vacancies'))

@app.route('/delete_candidate/<int:candidate_id>', methods=['POST'])
def delete_candidate(candidate_id):
    vacancy_id = request.form.get('vacancy_id')
    conn = get_db_connection()
    cur = conn.cursor()
    # Удаляем связанные записи
    cur.execute('DELETE FROM cv_files WHERE cv_id = ?', (candidate_id,))
    cur.execute('DELETE FROM on_cvs_languages WHERE cv_id = ?', (candidate_id,))
    cur.execute('DELETE FROM on_jobs_cvs WHERE cv_id = ?', (candidate_id,))
    # Получаем связанные id для preferences, cv_personal_info, cv_contacts
    cur.execute('SELECT fk_p_id, fk_cpi_id, fk_cc_id FROM cvs WHERE id = ?', (candidate_id,))
    row = cur.fetchone()
    if row:
        fk_p_id, fk_cpi_id, fk_cc_id = row
        cur.execute('DELETE FROM preferences WHERE id = ?', (fk_p_id,))
        cur.execute('DELETE FROM cv_personal_info WHERE id = ?', (fk_cpi_id,))
        cur.execute('DELETE FROM cv_contacts WHERE id = ?', (fk_cc_id,))
    # Удаляем образование и опыт работы
    cur.execute('DELETE FROM cv_education WHERE cv_id = ?', (candidate_id,))
    cur.execute('DELETE FROM cv_work_experience WHERE cv_id = ?', (candidate_id,))
    # Удаляем самого кандидата
    cur.execute('DELETE FROM cvs WHERE id = ?', (candidate_id,))
    conn.commit()
    conn.close()
    flash('Кандидат удалён!', 'success')
    if vacancy_id:
        return redirect(url_for('vacancy_candidates', vacancy_id=vacancy_id))
    return redirect(url_for('candidates'))

@app.route('/download_vacancy_file/<int:vacancy_id>')
def download_vacancy_file(vacancy_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT file_path FROM job_files WHERE job_id = ?', (vacancy_id,))
    row = cur.fetchone()
    conn.close()
    if not row or not row['file_path']:
        abort(404)
    file_path = row['file_path']
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/detailed_matching/<int:candidate_id>/<int:vacancy_id>')
def detailed_matching(candidate_id, vacancy_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT * FROM on_jobs_cvs WHERE cv_id = ? AND job_id = ?
    ''', (candidate_id, vacancy_id))
    row = cur.fetchone()
    # Получаем данные кандидата и вакансии для шаблона
    candidate = get_candidate(candidate_id)
    vacancy = get_vacancy(vacancy_id)
    conn.close()
    if not row:
        flash('Нет данных о соответствии для этого кандидата и вакансии.', 'warning')
        return redirect(url_for('candidate_detail', candidate_id=candidate_id))
    # Преобразуем row в dict для передачи как matching
    matching = dict(row)
    return render_template('detailed_matching.html', candidate_id=candidate_id, vacancy_id=vacancy_id, matching=matching, candidate=candidate, vacancy=vacancy)

@app.route('/hire_candidate/<int:candidate_id>', methods=['POST'])
def hire_candidate(candidate_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # Меняем статус на 'Принят'
    cur.execute('UPDATE cv_files SET status=? WHERE cv_id=?', ('Принят', candidate_id))
    # Удаляем из on_jobs_cvs (убрать из рейтинга)
    cur.execute('DELETE FROM on_jobs_cvs WHERE cv_id=?', (candidate_id,))
    conn.commit()
    conn.close()
    flash('Кандидат принят на работу!', 'success')
    return redirect(url_for('candidate_detail', candidate_id=candidate_id))

@app.route('/reject_candidate/<int:candidate_id>', methods=['POST'])
def reject_candidate(candidate_id):
    conn = get_db_connection()
    cur = conn.cursor()
    # Меняем статус на 'Отклонено'
    cur.execute('UPDATE cv_files SET status=? WHERE cv_id=?', ('Отклонено', candidate_id))
    # Удаляем из on_jobs_cvs (убрать из рейтинга)
    cur.execute('DELETE FROM on_jobs_cvs WHERE cv_id=?', (candidate_id,))
    conn.commit()
    conn.close()
    flash('Кандидату отказано. Он убран из рейтинга.', 'warning')
    return redirect(url_for('candidate_detail', candidate_id=candidate_id))

@app.route('/schedule_interview/<int:candidate_id>', methods=['POST'])
def schedule_interview(candidate_id):
    interview_datetime = request.form.get('interview_datetime')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''UPDATE cv_files SET status=?, interview_datetime=? WHERE cv_id=?''',
                ('На собеседовании', interview_datetime, candidate_id))
    conn.commit()
    conn.close()
    flash('Собеседование назначено!', 'success')
    return redirect(url_for('candidate_detail', candidate_id=candidate_id))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)