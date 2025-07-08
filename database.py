import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any


class DatabaseManager:
    def __init__(self, db_path: str = 'recruitment_system.db'):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Получает соединение с базой данных"""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Инициализирует базу данных, создает таблицы если их нет"""
        with self.get_connection() as conn:
            # Таблица preferences (общая для вакансий и резюме)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    desired_position TEXT,
                    employment_type TEXT,
                    desired_salary INTEGER
                )
            """)

            # Таблицы для вакансий (jobs)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_personal_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    age TEXT,
                    location TEXT,
                    relocation TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_education (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    specialization TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_work_experience (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    duration TEXT,
                    position TEXT,
                    responsibilities TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    company TEXT,
                    description TEXT,
                    salary_min INTEGER,
                    salary_max INTEGER,
                    status TEXT DEFAULT 'active',
                    vacancy_file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    candidates_count INTEGER DEFAULT 0,
                    fk_jpi_id INTEGER,
                    fk_p_id INTEGER,
                    fk_jwe_id INTEGER,
                    fk_je_id INTEGER,
                    skills TEXT,
                    skills_technologies TEXT,
                    FOREIGN KEY (fk_jpi_id) REFERENCES job_personal_info (id),
                    FOREIGN KEY (fk_p_id) REFERENCES preferences (id),
                    FOREIGN KEY (fk_jwe_id) REFERENCES job_work_experience (id),
                    FOREIGN KEY (fk_je_id) REFERENCES job_education (id)
                )
            """)

            # Таблицы для кандидатов (cvs)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cv_personal_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    age INTEGER,
                    location TEXT,
                    relocation TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS cv_education (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cv_id INTEGER NOT NULL,
                    organization TEXT,
                    level TEXT,
                    year_of_end INTEGER,
                    specialization TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS cv_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT,
                    email TEXT,
                    telegram TEXT,
                    portfolio TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS cv_work_experience (
                    cv_id INTEGER NOT NULL,
                    company TEXT,
                    period TEXT,
                    duration TEXT,
                    position TEXT,
                    responsibilities TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS cvs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT DEFAULT 'new',
                    resume_path TEXT,
                    job_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fk_cpi_id INTEGER,
                    fk_p_id INTEGER,
                    fk_ce_id INTEGER,
                    fk_cc_id INTEGER,
                    skills TEXT,
                    skills_technologies TEXT,
                    FOREIGN KEY (fk_cpi_id) REFERENCES cv_personal_info (id),
                    FOREIGN KEY (fk_p_id) REFERENCES preferences (id),
                    FOREIGN KEY (fk_ce_id) REFERENCES cv_education (id),
                    FOREIGN KEY (fk_cc_id) REFERENCES cv_contacts (id),
                    FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE SET NULL
                )
            """)

            # Таблицы для языков (Many to Many)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS languages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    level TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS on_jobs_languages (
                    job_id INTEGER NOT NULL,
                    language_id INTEGER NOT NULL,
                    FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
                    FOREIGN KEY (language_id) REFERENCES languages (id) ON DELETE CASCADE
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS on_cvs_languages (
                    cv_id INTEGER NOT NULL,
                    language_id INTEGER NOT NULL,
                    FOREIGN KEY (cv_id) REFERENCES cvs (id) ON DELETE CASCADE,
                    FOREIGN KEY (language_id) REFERENCES languages (id) ON DELETE CASCADE
                )
            """)

            # Таблица для матчинга
            conn.execute("""
                CREATE TABLE IF NOT EXISTS on_jobs_cvs (
                    job_id INTEGER NOT NULL,
                    cv_id INTEGER NOT NULL,
                    age INTEGER,
                    location INTEGER,
                    work_exp INTEGER,
                    education INTEGER,
                    skills INTEGER,
                    skills_tech INTEGER,
                    languages INTEGER,
                    final_score REAL,
                    overall_assessment TEXT,
                    interview_questions TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
                    FOREIGN KEY (cv_id) REFERENCES cvs (id) ON DELETE CASCADE,
                    UNIQUE (job_id, cv_id)
                )
            """)

            # Таблица для файлов
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id VARCHAR(36) PRIMARY KEY,
                    entity_id INTEGER NOT NULL,
                    entity_type VARCHAR(20) NOT NULL,
                    file_type VARCHAR(20) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    original_filename VARCHAR(255),
                    file_size BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Создаем индексы
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cvs_status ON cvs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cvs_job_id ON cvs(job_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_on_jobs_cvs_job_id ON on_jobs_cvs(job_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_on_jobs_cvs_cv_id ON on_jobs_cvs(cv_id)")

    # Методы для работы с вакансиями (jobs)
    def get_all_vacancies(self) -> List[Dict]:
        """Получает все вакансии с полной информацией"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    j.id, j.title, j.company, j.description, j.salary_min, j.salary_max,
                    j.status, j.vacancy_file_path, j.created_at, j.updated_at,
                    j.skills, j.skills_technologies,
                    p.desired_position, p.employment_type, p.desired_salary,
                    jpi.age, jpi.location, jpi.relocation,
                    je.level as education_level, je.specialization as education_specialization,
                    jwe.duration, jwe.position, jwe.responsibilities
                FROM jobs j
                LEFT JOIN preferences p ON j.fk_p_id = p.id
                LEFT JOIN job_personal_info jpi ON j.fk_jpi_id = jpi.id
                LEFT JOIN job_education je ON j.fk_je_id = je.id
                LEFT JOIN job_work_experience jwe ON j.fk_jwe_id = jwe.id
                ORDER BY j.created_at DESC
            """)
            rows = cursor.fetchall()
            
            vacancies = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                vacancy = dict(zip(columns, row))
                # Получаем языки для вакансии
                vacancy['languages'] = self._get_job_languages(vacancy['id'])
                # Конвертируем навыки из строки в список
                if vacancy.get('skills'):
                    vacancy['requirements'] = [skill.strip() for skill in vacancy['skills'].split(',') if skill.strip()]
                else:
                    vacancy['requirements'] = []
                vacancies.append(vacancy)
            
            return vacancies

    def get_vacancy_by_id(self, vacancy_id: int) -> Optional[Dict]:
        """Получает вакансию по ID с полной информацией"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    j.id, j.title, j.company, j.description, j.salary_min, j.salary_max,
                    j.status, j.vacancy_file_path, j.created_at, j.updated_at,
                    j.skills, j.skills_technologies,
                    p.desired_position, p.employment_type, p.desired_salary,
                    jpi.age, jpi.location, jpi.relocation,
                    je.level as education_level, je.specialization as education_specialization,
                    jwe.duration, jwe.position, jwe.responsibilities
                FROM jobs j
                LEFT JOIN preferences p ON j.fk_p_id = p.id
                LEFT JOIN job_personal_info jpi ON j.fk_jpi_id = jpi.id
                LEFT JOIN job_education je ON j.fk_je_id = je.id
                LEFT JOIN job_work_experience jwe ON j.fk_jwe_id = jwe.id
                WHERE j.id = ?
            """, (vacancy_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                vacancy = dict(zip(columns, row))
                vacancy['languages'] = self._get_job_languages(vacancy['id'])
                # Конвертируем навыки из строки в список
                if vacancy.get('skills'):
                    vacancy['requirements'] = [skill.strip() for skill in vacancy['skills'].split(',') if skill.strip()]
                else:
                    vacancy['requirements'] = []
                return vacancy
            
            return None

    def create_vacancy(self, vacancy_data: Dict) -> int:
        """Создает новую вакансию"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Создаем preferences
            cursor.execute("""
                INSERT INTO preferences (desired_position, employment_type, desired_salary)
                VALUES (?, ?, ?)
            """, (
                vacancy_data.get('desired_position', ''),
                vacancy_data.get('employment_type', ''),
                vacancy_data.get('desired_salary', 0)
            ))
            preferences_id = cursor.lastrowid
            
            # Создаем job_personal_info
            cursor.execute("""
                INSERT INTO job_personal_info (age, location, relocation)
                VALUES (?, ?, ?)
            """, (
                vacancy_data.get('age', ''),
                vacancy_data.get('location', ''),
                vacancy_data.get('relocation', '')
            ))
            personal_info_id = cursor.lastrowid
            
            # Создаем job_education
            cursor.execute("""
                INSERT INTO job_education (level, specialization)
                VALUES (?, ?)
            """, (
                vacancy_data.get('education_level', ''),
                vacancy_data.get('education_specialization', '')
            ))
            education_id = cursor.lastrowid
            
            # Создаем job_work_experience
            cursor.execute("""
                INSERT INTO job_work_experience (duration, position, responsibilities)
                VALUES (?, ?, ?)
            """, (
                vacancy_data.get('work_experience', ''),
                vacancy_data.get('position', ''),
                vacancy_data.get('responsibilities', '')
            ))
            work_experience_id = cursor.lastrowid
            
            # Создаем основную запись вакансии
            cursor.execute("""
                INSERT INTO jobs (
                    title, company, description, salary_min, salary_max,
                    status, vacancy_file_path, created_at,
                    fk_p_id, fk_jpi_id, fk_je_id, fk_jwe_id,
                    skills, skills_technologies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vacancy_data.get('title', ''),
                vacancy_data.get('company', ''),
                vacancy_data.get('description', ''),
                vacancy_data.get('salary_min', 0),
                vacancy_data.get('salary_max', 0),
                'active',
                vacancy_data.get('vacancy_file_path', ''),
                datetime.now().isoformat(),
                preferences_id,
                personal_info_id,
                education_id,
                work_experience_id,
                vacancy_data.get('skills', ''),
                vacancy_data.get('skills_technologies', '')
            ))
            
            job_id = cursor.lastrowid
            
            conn.commit()
            
            # Добавляем языки (в отдельной транзакции)
            if vacancy_data.get('languages'):
                self._add_job_languages(job_id, vacancy_data['languages'])
            
            return job_id

    def _get_job_languages(self, job_id: int) -> List[Dict]:
        """Получает языки для вакансии"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.name, l.level
                FROM languages l
                JOIN on_jobs_languages ojl ON l.id = ojl.language_id
                WHERE ojl.job_id = ?
            """, (job_id,))
            rows = cursor.fetchall()
            return [{'id': row[0], 'name': row[1], 'level': row[2]} for row in rows]

    def _add_job_languages(self, job_id: int, languages: List[Dict]):
        """Добавляет языки к вакансии"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for lang in languages:
                # Создаем или получаем язык
                cursor.execute("""
                    INSERT OR IGNORE INTO languages (name, level)
                    VALUES (?, ?)
                """, (lang.get('name', ''), lang.get('level', '')))
                
                if cursor.lastrowid == 0:
                    # Язык уже существует, получаем его ID
                    cursor.execute("""
                        SELECT id FROM languages WHERE name = ? AND level = ?
                    """, (lang.get('name', ''), lang.get('level', '')))
                    lang_id = cursor.fetchone()[0]
                else:
                    lang_id = cursor.lastrowid
                
                # Связываем с вакансией
                cursor.execute("""
                    INSERT OR IGNORE INTO on_jobs_languages (job_id, language_id)
                    VALUES (?, ?)
                """, (job_id, lang_id))
            conn.commit()

    # Методы для работы с кандидатами (cvs)
    def get_all_candidates(self) -> List[Dict]:
        """Получает всех кандидатов с полной информацией"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    c.id, c.status, c.resume_path, c.job_id, c.created_at, c.updated_at,
                    c.skills, c.skills_technologies,
                    p.desired_position, p.employment_type, p.desired_salary,
                    cpi.name, cpi.age, cpi.location, cpi.relocation,
                    cc.phone, cc.email, cc.telegram, cc.portfolio,
                    ce.organization, ce.level as education_level, ce.year_of_end, ce.specialization as education_specialization
                FROM cvs c
                LEFT JOIN preferences p ON c.fk_p_id = p.id
                LEFT JOIN cv_personal_info cpi ON c.fk_cpi_id = cpi.id
                LEFT JOIN cv_contacts cc ON c.fk_cc_id = cc.id
                LEFT JOIN cv_education ce ON c.fk_ce_id = ce.id
                ORDER BY c.created_at DESC
            """)
            rows = cursor.fetchall()
            
            candidates = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                candidate = dict(zip(columns, row))
                # Получаем языки и опыт работы для кандидата
                candidate['languages'] = self._get_cv_languages(candidate['id'])
                candidate['work_experience'] = self._get_cv_work_experience(candidate['id'])
                # Конвертируем навыки из строки в список
                if candidate.get('skills'):
                    candidate['skills'] = [skill.strip() for skill in candidate['skills'].split(',') if skill.strip()]
                else:
                    candidate['skills'] = []
                candidates.append(candidate)
            
            return candidates

    def get_candidate_by_id(self, candidate_id: int) -> Optional[Dict]:
        """Получает кандидата по ID с полной информацией"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    c.id, c.status, c.resume_path, c.job_id, c.created_at, c.updated_at,
                    c.skills, c.skills_technologies,
                    p.desired_position, p.employment_type, p.desired_salary,
                    cpi.name, cpi.age, cpi.location, cpi.relocation,
                    cc.phone, cc.email, cc.telegram, cc.portfolio,
                    ce.organization, ce.level as education_level, ce.year_of_end, ce.specialization as education_specialization
                FROM cvs c
                LEFT JOIN preferences p ON c.fk_p_id = p.id
                LEFT JOIN cv_personal_info cpi ON c.fk_cpi_id = cpi.id
                LEFT JOIN cv_contacts cc ON c.fk_cc_id = cc.id
                LEFT JOIN cv_education ce ON c.fk_ce_id = ce.id
                WHERE c.id = ?
            """, (candidate_id,))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                candidate = dict(zip(columns, row))
                candidate['languages'] = self._get_cv_languages(candidate['id'])
                candidate['work_experience'] = self._get_cv_work_experience(candidate['id'])
                # Конвертируем навыки из строки в список
                if candidate.get('skills'):
                    candidate['skills'] = [skill.strip() for skill in candidate['skills'].split(',') if skill.strip()]
                else:
                    candidate['skills'] = []
                return candidate
            
            return None

    def create_candidate(self, candidate_data: Dict) -> int:
        """Создает нового кандидата"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Создаем preferences
            cursor.execute("""
                INSERT INTO preferences (desired_position, employment_type, desired_salary)
                VALUES (?, ?, ?)
            """, (
                candidate_data.get('desired_position', ''),
                candidate_data.get('employment_type', ''),
                candidate_data.get('desired_salary', 0)
            ))
            preferences_id = cursor.lastrowid
            
            # Создаем cv_personal_info
            cursor.execute("""
                INSERT INTO cv_personal_info (name, age, location, relocation)
                VALUES (?, ?, ?, ?)
            """, (
                candidate_data.get('name', ''),
                candidate_data.get('age', 0),
                candidate_data.get('location', ''),
                candidate_data.get('relocation', False)
            ))
            personal_info_id = cursor.lastrowid
            
            # Создаем cv_contacts
            cursor.execute("""
                INSERT INTO cv_contacts (phone, email, telegram, portfolio)
                VALUES (?, ?, ?, ?)
            """, (
                candidate_data.get('phone', ''),
                candidate_data.get('email', ''),
                candidate_data.get('telegram', ''),
                candidate_data.get('portfolio', '')
            ))
            contacts_id = cursor.lastrowid
            
            # Создаем cv_education
            cursor.execute("""
                INSERT INTO cv_education (cv_id, organization, level, year_of_end, specialization)
                VALUES (?, ?, ?, ?, ?)
            """, (
                0,  # Временно 0, обновим после создания основной записи
                candidate_data.get('organization', ''),
                candidate_data.get('education_level', ''),
                candidate_data.get('year_of_end', 0),
                candidate_data.get('education_specialization', '')
            ))
            education_id = cursor.lastrowid
            
            # Создаем основную запись кандидата
            cursor.execute("""
                INSERT INTO cvs (
                    status, resume_path, job_id, created_at,
                    fk_p_id, fk_cpi_id, fk_cc_id, fk_ce_id,
                    skills, skills_technologies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'new',
                candidate_data.get('resume_path', ''),
                candidate_data.get('job_id'),
                datetime.now().isoformat(),
                preferences_id,
                personal_info_id,
                contacts_id,
                education_id,
                candidate_data.get('skills', ''),
                candidate_data.get('skills_technologies', '')
            ))
            
            cv_id = cursor.lastrowid
            
            # Обновляем cv_education с правильным cv_id
            cursor.execute("""
                UPDATE cv_education SET cv_id = ? WHERE id = ?
            """, (cv_id, education_id))
            
            conn.commit()
            
            # Добавляем опыт работы (в отдельной транзакции)
            if candidate_data.get('work_experience'):
                self._add_cv_work_experience(cv_id, candidate_data['work_experience'])
            
            # Добавляем языки (в отдельной транзакции)
            if candidate_data.get('languages'):
                self._add_cv_languages(cv_id, candidate_data['languages'])
            
            return cv_id

    def _get_cv_languages(self, cv_id: int) -> List[Dict]:
        """Получает языки для кандидата"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.name, l.level
                FROM languages l
                JOIN on_cvs_languages ocl ON l.id = ocl.language_id
                WHERE ocl.cv_id = ?
            """, (cv_id,))
            rows = cursor.fetchall()
            return [{'id': row[0], 'name': row[1], 'level': row[2]} for row in rows]

    def _get_cv_work_experience(self, cv_id: int) -> List[Dict]:
        """Получает опыт работы для кандидата"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT company, period, duration, position, responsibilities
                FROM cv_work_experience
                WHERE cv_id = ?
            """, (cv_id,))
            rows = cursor.fetchall()
            return [{
                'company': row[0], 'period': row[1], 'duration': row[2],
                'position': row[3], 'responsibilities': row[4]
            } for row in rows]

    def _add_cv_languages(self, cv_id: int, languages: List[Dict]):
        """Добавляет языки к кандидату"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for lang in languages:
                # Создаем или получаем язык
                cursor.execute("""
                    INSERT OR IGNORE INTO languages (name, level)
                    VALUES (?, ?)
                """, (lang.get('name', ''), lang.get('level', '')))
                
                if cursor.lastrowid == 0:
                    # Язык уже существует, получаем его ID
                    cursor.execute("""
                        SELECT id FROM languages WHERE name = ? AND level = ?
                    """, (lang.get('name', ''), lang.get('level', '')))
                    lang_id = cursor.fetchone()[0]
                else:
                    lang_id = cursor.lastrowid
                
                # Связываем с кандидатом
                cursor.execute("""
                    INSERT OR IGNORE INTO on_cvs_languages (cv_id, language_id)
                    VALUES (?, ?)
                """, (cv_id, lang_id))
            conn.commit()

    def _add_cv_work_experience(self, cv_id: int, work_experience: List[Dict]):
        """Добавляет опыт работы к кандидату"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for exp in work_experience:
                # Преобразуем все поля в строку, если это список
                def to_str(val):
                    if isinstance(val, list):
                        return ', '.join(map(str, val))
                    return str(val) if val is not None else ''
                cursor.execute("""
                    INSERT INTO cv_work_experience (cv_id, company, period, duration, position, responsibilities)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    cv_id,
                    to_str(exp.get('company', '')),
                    to_str(exp.get('period', '')),
                    to_str(exp.get('duration', '')),
                    to_str(exp.get('position', '')),
                    to_str(exp.get('responsibilities', ''))
                ))
            conn.commit()

    # Методы для работы с файлами
    def add_file(self, file_data: Dict) -> str:
        """Добавляет файл"""
        file_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO files (id, entity_id, entity_type, file_type, file_path, original_filename, file_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id,
                file_data.get('entity_id'),
                file_data.get('entity_type'),
                file_data.get('file_type'),
                file_data.get('file_path'),
                file_data.get('original_filename'),
                file_data.get('file_size')
            ))
            
            conn.commit()
            return file_id

    def get_files_by_entity(self, entity_id: int, entity_type: str) -> List[Dict]:
        """Получает файлы по entity"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM files 
                WHERE entity_id = ? AND entity_type = ?
                ORDER BY created_at DESC
            """, (entity_id, entity_type))
            rows = cursor.fetchall()
            
            files = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                file_data = dict(zip(columns, row))
                files.append(file_data)
            
            return files

    # Методы для работы с матчингом
    def add_matching_result(self, candidate_id: int, vacancy_id: int, score: float, 
                          detailed_scores: dict = None, overall_assessment: str = None, 
                          interview_questions: list = None) -> str:
        """Добавляет результат матчинга"""
        matching_id = str(uuid.uuid4())
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            interview_questions_json = json.dumps(interview_questions or [], ensure_ascii=False)
            
            cursor.execute("""
                INSERT OR REPLACE INTO on_jobs_cvs (
                    job_id, cv_id, age, location, work_exp, education, 
                    skills, skills_tech, languages, final_score,
                    overall_assessment, interview_questions, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vacancy_id,
                candidate_id,
                (detailed_scores.get('age_score', 0) if detailed_scores else 0) * 100,
                (detailed_scores.get('location_score', 0) if detailed_scores else 0) * 100,
                (detailed_scores.get('work_exp_score', 0) if detailed_scores else 0) * 100,
                (detailed_scores.get('education_score', 0) if detailed_scores else 0) * 100,
                (detailed_scores.get('skills_score', 0) if detailed_scores else 0) * 100,
                (detailed_scores.get('skills_tech_score', 0) if detailed_scores else 0) * 100,
                (detailed_scores.get('languages_score', 0) if detailed_scores else 0) * 100,
                score * 100,  # Конвертируем в проценты для сохранения в БД
                overall_assessment or '',
                interview_questions_json,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            conn.commit()
            return matching_id

    def get_matching_results(self, vacancy_id: int = None, candidate_id: int = None) -> List[Dict]:
        """Получает результаты матчинга"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if vacancy_id:
                cursor.execute("""
                    SELECT * FROM on_jobs_cvs WHERE job_id = ?
                    ORDER BY final_score DESC
                """, (vacancy_id,))
            elif candidate_id:
                cursor.execute("""
                    SELECT * FROM on_jobs_cvs WHERE cv_id = ?
                    ORDER BY final_score DESC
                """, (candidate_id,))
            else:
                cursor.execute("""
                    SELECT * FROM on_jobs_cvs ORDER BY final_score DESC
                """)
            
            rows = cursor.fetchall()
            
            results = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                result = dict(zip(columns, row))
                if result.get('interview_questions'):
                    result['interview_questions'] = json.loads(result['interview_questions'])
                results.append(result)
            
            return results

    def get_detailed_matching_result(self, candidate_id: int, vacancy_id: int) -> Optional[Dict]:
        """Получает детальный результат матчинга"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM on_jobs_cvs 
                WHERE cv_id = ? AND job_id = ?
            """, (candidate_id, vacancy_id))
            row = cursor.fetchone()
            
            if row:
                columns = [description[0] for description in cursor.description]
                result = dict(zip(columns, row))
                if result.get('interview_questions'):
                    result['interview_questions'] = json.loads(result['interview_questions'])
                return result
            
            return None

    def update_matching_result(self, candidate_id: int, vacancy_id: int, 
                             detailed_scores: dict, overall_assessment: str, 
                             interview_questions: list) -> bool:
        """Обновляет результат матчинга"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            interview_questions_json = json.dumps(interview_questions or [], ensure_ascii=False)
            
            cursor.execute("""
                UPDATE on_jobs_cvs SET
                    age = ?, location = ?, work_exp = ?, education = ?,
                    skills = ?, skills_tech = ?, languages = ?,
                    overall_assessment = ?, interview_questions = ?, updated_at = ?
                WHERE cv_id = ? AND job_id = ?
            """, (
                detailed_scores.get('age_score', 0) * 100,
                detailed_scores.get('location_score', 0) * 100,
                detailed_scores.get('work_exp_score', 0) * 100,
                detailed_scores.get('education_score', 0) * 100,
                detailed_scores.get('skills_score', 0) * 100,
                detailed_scores.get('skills_tech_score', 0) * 100,
                detailed_scores.get('languages_score', 0) * 100,
                overall_assessment,
                interview_questions_json,
                datetime.now().isoformat(),
                candidate_id,
                vacancy_id
            ))
            
            conn.commit()
            return cursor.rowcount > 0

    def delete_matching_result(self, candidate_id: int, vacancy_id: int) -> bool:
        """Удаляет результат матчинга"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM on_jobs_cvs 
                WHERE cv_id = ? AND job_id = ?
            """, (candidate_id, vacancy_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_statistics(self) -> Dict:
        """Получает статистику системы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Количество вакансий
            cursor.execute("SELECT COUNT(*) FROM jobs")
            total_vacancies = cursor.fetchone()[0]
            
            # Количество кандидатов
            cursor.execute("SELECT COUNT(*) FROM cvs")
            total_candidates = cursor.fetchone()[0]
            
            # Количество активных вакансий
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE status = 'active'")
            active_vacancies = cursor.fetchone()[0]
            
            # Количество новых кандидатов
            cursor.execute("SELECT COUNT(*) FROM cvs WHERE status = 'new'")
            new_candidates = cursor.fetchone()[0]
            
            # Количество результатов матчинга
            cursor.execute("SELECT COUNT(*) FROM on_jobs_cvs")
            total_matches = cursor.fetchone()[0]
            
            return {
                'total_vacancies': total_vacancies,
                'total_candidates': total_candidates,
                'active_vacancies': active_vacancies,
                'new_candidates': new_candidates,
                'total_matches': total_matches
            }

    def get_candidates_by_vacancy(self, vacancy_id: int) -> List[Dict]:
        """Получает кандидатов для конкретной вакансии"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    c.id, c.status, c.resume_path, c.created_at,
                    c.skills, c.skills_technologies,
                    p.desired_position, p.employment_type, p.desired_salary,
                    cpi.name, cpi.age, cpi.location, cpi.relocation,
                    cc.phone, cc.email, cc.telegram, cc.portfolio,
                    ce.organization, ce.level as education_level, ce.year_of_end, ce.specialization as education_specialization,
                    ojc.final_score, ojc.overall_assessment
                FROM cvs c
                LEFT JOIN preferences p ON c.fk_p_id = p.id
                LEFT JOIN cv_personal_info cpi ON c.fk_cpi_id = cpi.id
                LEFT JOIN cv_contacts cc ON c.fk_cc_id = cc.id
                LEFT JOIN cv_education ce ON c.fk_ce_id = ce.id
                LEFT JOIN on_jobs_cvs ojc ON c.id = ojc.cv_id AND ojc.job_id = ?
                WHERE c.job_id = ?
                ORDER BY ojc.final_score DESC NULLS LAST
            """, (vacancy_id, vacancy_id))
            rows = cursor.fetchall()
            
            candidates = []
            columns = [description[0] for description in cursor.description]
            
            for row in rows:
                candidate = dict(zip(columns, row))
                candidate['languages'] = self._get_cv_languages(candidate['id'])
                candidate['work_experience'] = self._get_cv_work_experience(candidate['id'])
                # Конвертируем навыки из строки в список
                if candidate.get('skills'):
                    candidate['skills'] = [skill.strip() for skill in candidate['skills'].split(',') if skill.strip()]
                else:
                    candidate['skills'] = []
                candidates.append(candidate)
            
            return candidates

    def delete_vacancy(self, vacancy_id: int) -> bool:
        """Удаляет вакансию"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id = ?", (vacancy_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_candidate(self, candidate_id: int) -> bool:
        """Удаляет кандидата"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cvs WHERE id = ?", (candidate_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_vacancy(self, vacancy_id: int, vacancy_data: Dict) -> bool:
        """Обновляет вакансию"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Обновляем основную информацию
            cursor.execute("""
                UPDATE jobs SET
                    title = ?, company = ?, description = ?, salary_min = ?, salary_max = ?,
                    status = ?, vacancy_file_path = ?, updated_at = ?
                WHERE id = ?
            """, (
                vacancy_data.get('title', ''),
                vacancy_data.get('company', ''),
                vacancy_data.get('description', ''),
                vacancy_data.get('salary_min', 0),
                vacancy_data.get('salary_max', 0),
                vacancy_data.get('status', 'active'),
                vacancy_data.get('vacancy_file_path', ''),
                datetime.now().isoformat(),
                vacancy_id
            ))
            
            conn.commit()
            return cursor.rowcount > 0

    def update_candidate(self, candidate_id: int, candidate_data: Dict) -> bool:
        """Обновляет кандидата"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Обновляем основную информацию
            cursor.execute("""
                UPDATE cvs SET
                    status = ?, resume_path = ?, job_id = ?, updated_at = ?
                WHERE id = ?
            """, (
                candidate_data.get('status', 'new'),
                candidate_data.get('resume_path', ''),
                candidate_data.get('job_id'),
                datetime.now().isoformat(),
                candidate_id
            ))
            
            # Обновляем контакты
            cursor.execute("SELECT fk_cc_id FROM cvs WHERE id = ?", (candidate_id,))
            cc_id = cursor.fetchone()[0]
            cursor.execute("""
                UPDATE cv_contacts SET phone = ?, email = ?, telegram = ?, portfolio = ? WHERE id = ?
            """, (
                candidate_data.get('phone', ''),
                candidate_data.get('email', ''),
                candidate_data.get('telegram', ''),
                candidate_data.get('portfolio', ''),
                cc_id
            ))
            
            conn.commit()
            return cursor.rowcount > 0


# Создаем глобальный экземпляр
db = DatabaseManager() 