# Система рекрутинга с YandexGPT

Система автоматического анализа соответствия кандидатов и вакансий с использованием YandexGPT для интеллектуальной оценки.

## Основные возможности

### 🤖 Интеллектуальный анализ с YandexGPT
- **Детальная оценка полей**: Каждое поле кандидата и вакансии анализируется отдельно
- **Взвешенный скор**: Используются веса для разных характеристик (навыки, опыт, зарплата и т.д.)
- **Автоматические комментарии**: GPT генерирует обоснования для каждой оценки
- **Вопросы для собеседования**: Автоматическая генерация релевантных вопросов

### 📊 Анализируемые поля
- **Возраст** (вес: 0.3)
- **Местоположение и готовность к переезду** (вес: 0.6)
- **Должность** (вес: 1.0)
- **Тип занятости** (вес: 0.8)
- **Ожидаемая зарплата** (вес: 0.6)
- **Опыт работы** (вес: 0.7)
- **Образование** (вес: 0.8)
- **Навыки** (вес: 1.0)
- **Технические навыки** (вес: 1.0)
- **Языки** (вес: 0.5)

### 🔄 Fallback режим
Если YandexGPT недоступен, система автоматически переключается на алгоритмический анализ:
- Сравнение навыков через коэффициент Жаккара
- Fuzzy matching для текстовых полей
- Числовое сравнение для зарплат

## Архитектура

### Функция `calculate_matching_score`
```python
def calculate_matching_score(candidate, vacancy):
    """Расчет скора соответствия с использованием YandexGPT"""
```

**Входные данные:**
- `candidate`: Данные кандидата из БД
- `vacancy`: Данные вакансии из БД

**Процесс:**
1. Подготовка данных для GPT
2. Отправка промпта в YandexGPT
3. Парсинг JSON ответа
4. Расчет взвешенного скора
5. Сохранение результатов в БД

### Промпт для YandexGPT
```python
prompt = f"""
Сравни определенные поля json вакансии с таким же полями json в резюме и оцени соответствие характеристики от 1 до 10.
Оценка производится по полям: "age", ("location" and "relocation" (в одно поле)), "work_experience","education","skills","skills_technologies","languages", "desired_position","employment_type","desired_salary".
Ответ представь в виде json c ключами-характеристиками ("age","location","position","employment_type", "desired_salary","work_exp","education","skills","skills_tech","languages") и полями оценка("score") и обоснование("reason").
Самое важное условие : Если какое-то поле пропущено или не указано, или имеет значение NULL, или "" ставь -1 в "score" и не оценивай (навыки которых нет в вакансии, но есть у кандидата и который помогут в профессиональной деятельности-это хорошо).
А также дай общее обоснование оценок, характеристику и вопросы на собеседование для кандидата в ключе "final_score" в поле "reason" (не забудь создать поле "score" в "final_score" со значением 0).
"""
```

### Расчет итогового скора
```python
weights = [0.3, 0.6, 1, 0.8, 0.6, 0.7, 0.8, 1, 1, 0.5, 0]
fields = ["age", "location", "position", "employment_type", "desired_salary", 
         "work_exp", "education", "skills", "skills_tech", "languages"]

fs = 0  # Сумма взвешенных скоров
fm = 0  # Сумма весов

for i, field in enumerate(fields):
    if field in job_requirements and job_requirements[field]["score"] != -1:
        score = job_requirements[field]["score"] / 10.0  # Нормализация к 0-1
        fs += score * weights[i]
        fm += weights[i]

overall_score = fs / fm if fm > 0 else 0.5
```

## Конфигурация

### Переменные окружения
Создайте файл `.env`:
```env
# YandexGPT API Configuration
YANDEX_API_KEY=your_api_key_here
YANDEX_FOLDER_ID=your_folder_id_here
YANDEX_MODEL=yandexgpt-lite

# Flask Configuration
SECRET_KEY=huntflow_mvp_secret_key

# Database Configuration
DATABASE_PATH=recruitment.db
```

### Установка зависимостей
```bash
pip install -r requirements.txt
```

## API Endpoints

### `/api/match/<candidate_id>/<vacancy_id>`
Получение скора соответствия кандидата и вакансии

**Ответ:**
```json
{
    "matching_score": 0.85,
    "detailed_result": {
        "skills_score": 0.9,
        "skills_comment": "Отличное соответствие навыков",
        "experience_score": 0.8,
        "experience_comment": "Опыт работы хорошо соответствует требованиям",
        // ... другие поля
    }
}
```

### `/api/vacancies/<vacancy_id>/candidates`
Получение ранжированных кандидатов для вакансии

**Параметры:**
- `status`: Фильтр по статусу кандидата
- `min_score`: Минимальный скор (в процентах)

## База данных

### Таблица `matching_results`
```sql
CREATE TABLE matching_results (
    id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    vacancy_id TEXT NOT NULL,
    score REAL NOT NULL,
    detailed_scores JSON,
    overall_assessment TEXT,
    interview_questions JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies(id)
);
```

## Использование

### 1. Настройка API ключей
```bash
# Создайте файл .env с вашими ключами
cp .env.example .env
# Отредактируйте .env файл
```

### 2. Запуск приложения
```bash
python app.py
```

### 3. Использование API
```python
import requests

# Получение скора соответствия
response = requests.get('http://localhost:5000/api/match/candidate_id/vacancy_id')
score = response.json()['matching_score']

# Получение ранжированных кандидатов
response = requests.get('http://localhost:5000/api/vacancies/vacancy_id/candidates')
candidates = response.json()['candidates']
```

## Преимущества реализации

1. **Интеллектуальный анализ**: GPT понимает контекст и нюансы
2. **Детальная оценка**: Каждое поле анализируется отдельно
3. **Автоматические комментарии**: Обоснования для каждой оценки
4. **Вопросы для собеседования**: Релевантные вопросы на основе анализа
5. **Fallback режим**: Работает даже без GPT
6. **Взвешенный скор**: Учитывает важность разных характеристик
7. **Сохранение результатов**: Все результаты сохраняются в БД

## Мониторинг и логирование

Система логирует:
- Успешные запросы к GPT
- Ошибки парсинга JSON
- Переключения на fallback режим
- Время выполнения анализа

## Производительность

- **Время анализа**: 2-5 секунд на кандидата
- **Fallback режим**: 0.1-0.5 секунды
- **Кэширование**: Результаты сохраняются в БД
- **Асинхронность**: Анализ не блокирует UI 