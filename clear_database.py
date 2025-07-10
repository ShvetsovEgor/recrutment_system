import sqlite3
import os

def clear_database(db_path='recruitment_system.db'):
    """
    Очищает все данные из базы данных, сохраняя структуру таблиц.
    
    Args:
        db_path (str): Путь к файлу базы данных
    """
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print(f"Найдено таблиц: {len(tables)}")
        
        # Отключаем проверку внешних ключей для ускорения очистки
        cursor.execute("PRAGMA foreign_keys=OFF;")
        
        # Очищаем каждую таблицу
        for table in tables:
            table_name = table[0]
            if table_name != 'sqlite_sequence':  # Пропускаем системную таблицу
                try:
                    cursor.execute(f"DELETE FROM {table_name};")
                    print(f"Очищена таблица: {table_name}")
                except Exception as e:
                    print(f"Ошибка при очистке таблицы {table_name}: {e}")
        
        # Сбрасываем автоинкрементные счетчики
        cursor.execute("DELETE FROM sqlite_sequence;")
        
        # Включаем обратно проверку внешних ключей
        cursor.execute("PRAGMA foreign_keys=ON;")
        
        # Сохраняем изменения
        conn.commit()
        
        print("\nБаза данных успешно очищена!")
        
        # Показываем статистику
        print("\nСтатистика после очистки:")
        for table in tables:
            table_name = table[0]
            if table_name != 'sqlite_sequence':
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                print(f"  {table_name}: {count} записей")
        
    except Exception as e:
        print(f"Ошибка при очистке базы данных: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def clear_specific_tables(db_path='recruitment_system.db', table_names=None):
    """
    Очищает только указанные таблицы.
    
    Args:
        db_path (str): Путь к файлу базы данных
        table_names (list): Список имен таблиц для очистки
    """
    if table_names is None:
        table_names = [
            'jobs', 'cvs', 'preferences', 'job_personal_info', 'cv_personal_info',
            'languages', 'job_work_experience', 'cv_work_experience', 'job_education',
            'cv_education', 'job_skills', 'cv_skills', 'job_skills_technologies',
            'cv_skills_technologies'
        ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"Очистка указанных таблиц: {', '.join(table_names)}")
        
        # Отключаем проверку внешних ключей
        cursor.execute("PRAGMA foreign_keys=OFF;")
        
        for table_name in table_names:
            try:
                cursor.execute(f"DELETE FROM {table_name};")
                print(f"Очищена таблица: {table_name}")
            except Exception as e:
                print(f"Ошибка при очистке таблицы {table_name}: {e}")
        
        # Сбрасываем автоинкрементные счетчики
        cursor.execute("DELETE FROM sqlite_sequence;")
        
        # Включаем обратно проверку внешних ключей
        cursor.execute("PRAGMA foreign_keys=ON;")
        
        conn.commit()
        print("\nУказанные таблицы успешно очищены!")
        
    except Exception as e:
        print(f"Ошибка при очистке таблиц: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--specific":
            # Очистка только основных таблиц системы подбора
            clear_specific_tables()
        elif sys.argv[1] == "--help":
            print("Использование:")
            print("  python clear_database.py          # Очистить все таблицы")
            print("  python clear_database.py --specific # Очистить только таблицы системы подбора")
            print("  python clear_database.py --help    # Показать эту справку")
        else:
            print("Неизвестный аргумент. Используйте --help для справки.")
    else:
        # Очистка всех таблиц
        print("ВНИМАНИЕ: Это действие удалит ВСЕ данные из базы данных!")
        response = input("Продолжить? (y/N): ")
        
        if response.lower() in ['y', 'yes', 'да']:
            clear_database()
        else:
            print("Операция отменена.") 