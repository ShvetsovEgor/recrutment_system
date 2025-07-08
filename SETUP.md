# Настройка системы рекрутинга

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Настройка YandexGPT

1. Создайте файл `.env` в корневой папке проекта
2. Добавьте в него следующие переменные:

```
# YandexGPT API Configuration
YANDEX_API_KEY=your_api_key_here
YANDEX_FOLDER_ID=your_folder_id_here
YANDEX_MODEL=yandexgpt-lite

# Flask Configuration
SECRET_KEY=huntflow_mvp_secret_key

# Database Configuration
DATABASE_PATH=recruitment.db
```

### Получение API ключей YandexGPT

1. Зарегистрируйтесь в [Yandex Cloud](https://cloud.yandex.ru/)
2. Создайте платежный аккаунт
3. Создайте сервисный аккаунт
4. Получите API ключ в разделе "Сервисные аккаунты"
5. Получите Folder ID в настройках проекта

## Запуск приложения

```bash
python app.py
```

Приложение будет доступно по адресу: http://localhost:5000

## Функциональность

- **Анализ соответствия**: Система использует YandexGPT для анализа соответствия кандидатов и вакансий
- **Детальная оценка**: Каждое поле оценивается отдельно с комментариями
- **Вопросы для собеседования**: Автоматическая генерация вопросов на основе анализа
- **Fallback режим**: Если GPT недоступен, используется алгоритмический анализ

## Структура проекта

- `app.py` - основной файл приложения
- `database.py` - работа с базой данных
- `config.py` - конфигурация
- `ocr_utils.py` - обработка PDF файлов
- `requirements.txt` - зависимости Python
- `templates/` - HTML шаблоны
- `uploads/` - загруженные файлы 