# Система обработки вакансий и резюме

Эта система автоматически обрабатывает вакансии и резюме в формате PDF, извлекает из них структурированную информацию и оценивает соответствие кандидатов требованиям вакансий.

## Функциональность

1. **OCR обработка PDF**: Конвертация PDF файлов в текст с помощью Yandex OCR API
2. **Извлечение структурированных данных**: Преобразование текста вакансий и резюме в JSON формат
3. **Оценка соответствия**: Автоматическая оценка соответствия резюме требованиям вакансии
4. **Сохранение в базу данных**: Все данные сохраняются в SQLite базу данных

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Настройте переменные окружения:
```bash
export YANDEXGPT_API_KEY="ваш_api_ключ"
export YANDEXGPT_FOLDER_ID="ваш_folder_id"
export YANDEXGPT_MODEL="yandexgpt-lite"
export YANDEXGPT_OCR_API_KEY="ваш_ocr_api_ключ"
export YANDEXGPT_OCR_FOLDER_ID="ваш_ocr_folder_id"
```

## Использование

### Основная функция

```python
from recruitment_processor import process_recruitment

# Обработка вакансии и резюме
result = process_recruitment("path/to/vacancy.pdf", "path/to/resume.pdf")

print(f"Финальная оценка: {result['final_score']}%")
```

### Пример использования

Запустите файл `example_usage.py`:

```bash
python example_usage.py
```

## Структура базы данных

### Таблица `vacancies`
- `id` - уникальный идентификатор
- `title` - название должности
- `personal_info` - персональная информация (JSON)
- `job_preferences` - предпочтения по работе (JSON)
- `work_experience` - требуемый опыт
- `education` - требования к образованию (JSON)
- `skills` - требуемые навыки (JSON)
- `skills_technologies` - требуемые технологии (JSON)
- `languages` - требуемые языки (JSON)
- `raw_text` - исходный текст
- `created_at` - дата создания

### Таблица `resumes`
- `id` - уникальный идентификатор
- `name` - имя кандидата
- `personal_info` - персональная информация (JSON)
- `job_preferences` - предпочтения по работе (JSON)
- `work_experience` - опыт работы (JSON)
- `education` - образование (JSON)
- `skills` - навыки (JSON)
- `skills_technologies` - технологии (JSON)
- `languages` - языки (JSON)
- `contacts` - контакты (JSON)
- `raw_text` - исходный текст
- `created_at` - дата создания

### Таблица `evaluations`
- `id` - уникальный идентификатор
- `vacancy_id` - ID вакансии
- `resume_id` - ID резюме
- Оценки по критериям (age_score, location_score, etc.)
- Обоснования оценок (age_reason, location_reason, etc.)
- `final_score` - финальная оценка
- `final_reason` - общее заключение
- `created_at` - дата создания

## Критерии оценки

Система оценивает соответствие по следующим критериям:
1. **Возраст** (age)
2. **Местоположение и переезд** (location)
3. **Должность** (position)
4. **Тип занятости** (employment_type)
5. **Желаемая зарплата** (desired_salary)
6. **Опыт работы** (work_exp)
7. **Образование** (education)
8. **Навыки** (skills)
9. **Технологии** (skills_tech)
10. **Языки** (languages)

## Формат выходных данных

### JSON вакансии
```json
{
  "personal_info": {
    "age": "25-35 лет",
    "location": "Москва",
    "relocation": "возможен"
  },
  "job_preferences": {
    "desired_position": "Python разработчик",
    "employment_type": "полная занятость",
    "desired_salary": 150000
  },
  "work_experience": "от 2 лет",
  "education": {
    "level": "высшее",
    "specialization": "информационные технологии"
  },
  "skills": ["Python", "Django", "SQL"],
  "skills_technologes": ["Git", "Docker", "PostgreSQL"],
  "languages": [
    {
      "name": "английский",
      "level": "B2"
    }
  ]
}
```

### JSON резюме
```json
{
  "personal_info": {
    "name": "Иванов Иван Иванович",
    "age": "28",
    "location": "Москва",
    "relocation": "не требуется"
  },
  "job_preferences": {
    "desired_position": "Python разработчик",
    "employment_type": "полная занятость",
    "desired_salary": 140000
  },
  "work_experience": [
    {
      "company": "ООО Технологии",
      "period": "2021-2023",
      "duration": "2 года",
      "position": "Python разработчик",
      "responsibilities": ["разработка веб-приложений", "работа с базой данных"]
    }
  ],
  "education": {
    "organization": "МГУ",
    "level": "высшее",
    "year_of_end": 2021,
    "specialization": "информационные технологии"
  },
  "skills": ["Python", "Django", "SQL", "JavaScript"],
  "skills_technologes": ["Git", "Docker", "PostgreSQL", "Redis"],
  "languages": [
    {
      "name": "английский",
      "level": "B1"
    }
  ],
  "contacts": {}
}
```

## Обработка ошибок

Система включает обработку следующих ошибок:
- Файлы не найдены
- Ошибки OCR API
- Ошибки парсинга JSON
- Ошибки базы данных

## Требования

- Python 3.7+
- Yandex Cloud API ключ
- Доступ к YandexGPT API
- Доступ к Yandex OCR API 