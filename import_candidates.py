import json
import os
import re
from datetime import datetime
import uuid

def extract_name_from_filename(filename):
    """Извлекает имя из названия файла"""
    # Убираем расширение .pdf
    name = filename.replace('.pdf', '')
    
    # Обрабатываем специальные случаи
    if name.startswith('Резюме_'):
        name = name.replace('Резюме_', '')
    if name.endswith('-1'):
        name = name[:-2]
    if name.endswith(' (1)'):
        name = name[:-4]
    
    return name

def generate_candidate_data(name, filename):
    """Генерирует данные кандидата на основе имени"""
    # Базовые навыки для UI/UX дизайнеров
    base_skills = [
        "UI/UX дизайн", "Figma", "Adobe Photoshop", "Adobe Illustrator", 
        "прототипирование", "веб-дизайн", "адаптивный дизайн", "дизайн-системы"
    ]
    
    # Дополнительные навыки (случайный выбор для разнообразия)
    additional_skills = [
        "Sketch", "Adobe XD", "InVision", "Principle", "After Effects",
        "пользовательские исследования", "юзабилити", "wireframing",
        "графический дизайн", "брендинг", "логотипы", "иконки",
        "типографика", "цветокоррекция", "анимация", "моушн-дизайн"
    ]
    
    import random
    # Выбираем случайные дополнительные навыки
    selected_additional = random.sample(additional_skills, random.randint(2, 5))
    all_skills = base_skills + selected_additional
    
    # Генерируем случайный опыт
    experience_options = [
        "1 год стажером",
        "2 года в UI/UX дизайне", 
        "3 года в веб-дизайне",
        "4 года в дизайне интерфейсов",
        "5 лет в графическом дизайне",
        "6 месяцев стажером",
        "1.5 года в дизайне"
    ]
    
    # Генерируем случайный статус
    status_options = ["new", "interview", "hired"]
    status_weights = [0.7, 0.2, 0.1]  # 70% новых, 20% на собеседовании, 10% принятых
    
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": f"{name.lower().replace(' ', '.').replace('ё', 'e').replace('а', 'a').replace('и', 'i').replace('о', 'o').replace('у', 'u').replace('ы', 'y').replace('э', 'e').replace('ю', 'yu').replace('я', 'ya')}@email.com",
        "phone": f"+7 (999) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}",
        "position": random.choice([
            "UI/UX Дизайнер",
            "Дизайнер интерфейсов", 
            "UX/UI Дизайнер",
            "Веб-дизайнер",
            "Графический дизайнер"
        ]),
        "experience": random.choice(experience_options),
        "skills": all_skills,
        "resume_path": f"ui_ux_designer/{filename}",
        "status": random.choices(status_options, weights=status_weights)[0],
        "created_at": datetime.now().isoformat(),
        "vacancy_id": None
    }

def import_candidates():
    """Импортирует кандидатов из папки ui_ux_designer"""
    candidates_dir = "ui_ux_designer"
    candidates_file = "data/candidates.json"
    
    if not os.path.exists(candidates_dir):
        print(f"Папка {candidates_dir} не найдена!")
        return
    
    # Получаем список PDF файлов
    pdf_files = [f for f in os.listdir(candidates_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print("PDF файлы не найдены в папке ui_ux_designer")
        return
    
    print(f"Найдено {len(pdf_files)} резюме для импорта")
    
    # Создаем данные кандидатов
    candidates = []
    
    for filename in pdf_files:
        name = extract_name_from_filename(filename)
        candidate_data = generate_candidate_data(name, filename)
        candidates.append(candidate_data)
        print(f"Добавлен кандидат: {name}")
    
    # Сохраняем в файл
    with open(candidates_file, 'w', encoding='utf-8') as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Импортировано {len(candidates)} кандидатов в {candidates_file}")
    print("Теперь можно запустить приложение и увидеть всех кандидатов!")

if __name__ == "__main__":
    import_candidates() 