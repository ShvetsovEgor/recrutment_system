import base64
import json
import os
import shutil

import requests
from dotenv import load_dotenv
from langchain_community.llms import YandexGPT
from pypdf import PdfReader, PdfWriter

load_dotenv()

API_KEY = os.environ.get("YANDEX_OCR_API_KEY")
FOLDER_ID = os.environ.get("YANDEX_OCR_FOLDER_ID")


def encode_file(file_path):
    """Кодирует файл в base64 для отправки в API"""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ocr_pdf(pdf_path, output_txt_path):
    """
    Обрабатывает PDF файл через Yandex OCR API и сохраняет результат в текстовый файл
    """
    if not API_KEY or not FOLDER_ID:
        return False
    headers = {
        "Authorization": f"Api-Key {API_KEY}",
        "x-folder-id": FOLDER_ID,
        "Content-Type": "application/json"
    }
    full = ""
    try:
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        os.makedirs("split_pages", exist_ok=True)
        for i in range(num_pages):
            writer = PdfWriter()
            writer.add_page(reader.pages[i])
            output_path = f"split_pages/page_{i + 1}.pdf"
            with open(output_path, "wb") as f_out:
                writer.write(f_out)
        for i in range(num_pages):
            page_pdf_path = f"split_pages/page_{i + 1}.pdf"
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
                full += text_from_page + "\n"
            else:
                return False
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(full)
        return True
    except Exception:
        return False




import dotenv

dotenv.load_dotenv()
dotenv.load_dotenv()

API_KEY = os.environ.get("YANDEXGPT_API_KEY")
FOLDER_ID = os.environ.get("YANDEXGPT_FOLDER_ID")
MODEL = os.environ.get("YANDEXGPT_MODEL")

GPT = YandexGPT(
    api_key=API_KEY,
    folder_id=FOLDER_ID,
    model=MODEL,
    temperature=0
)


def resume_to_json(text: str):
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
  "skills": [],
  "languages": [
    {{
      "name": "имя",
      "level": "уровень владения"
    }}
  ],
  "contacts": {{}}
}}
  Текст резюме:
  "{text}"
  """
    ans = GPT.invoke(prompt)
    ans = ans.replace("```", '')
    try:
        return json.loads(ans)
    except json.JSONDecodeError:
        return []


def vacancy_to_json(text: str):
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
    "work_experience": "требуемый опыт",
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
        return []


def process_resume_with_gpt(txt_path, json_path, is_vacancy=False):
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()
    if is_vacancy:
        job_requirements = vacancy_to_json(text)
    else:
        job_requirements = resume_to_json(text)
    with open(json_path, 'w', encoding="utf-8") as f:
        json.dump(job_requirements, f, indent=4, ensure_ascii=False)
    print(f"Результат сохранён в {json_path}")
