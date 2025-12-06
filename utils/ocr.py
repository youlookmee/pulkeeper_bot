# utils/ocr.py
import os
import base64
import re
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Вспомогательная функция — извлечь "текст" из ответа Responses API
def _extract_text_from_response(resp):
    # New SDK often exposes .output_text, но делаем защитно
    if hasattr(resp, "output_text") and resp.output_text:
        return resp.output_text

    # Собираем текст из output[].content[]
    parts = []
    out = getattr(resp, "output", None)
    if out:
        for item in out:
            content = item.get("content") if isinstance(item, dict) else getattr(item, "content", None)
            if not content:
                continue
            # content может быть список блоков
            if isinstance(content, list):
                for block in content:
                    t = block.get("text") or block.get("content") or block.get("payload") or None
                    if isinstance(t, str):
                        parts.append(t)
                    elif isinstance(block.get("type"), str) and block.get("type") == "output_text":
                        # fallback
                        txt = block.get("text") or block.get("value") or ""
                        if txt:
                            parts.append(txt)
            elif isinstance(content, str):
                parts.append(content)

    return "\n".join(parts).strip()


def _clean_number_str(s: str) -> float:
    """Преобразует строку с пробелами/точками/запятыми в число."""
    if not s:
        return 0.0
    # удалить все не-цифры кроме точек и запятых
    # сначала заменим запятую на точку, но если внутри есть пробелы — удалим
    s = s.strip()
    s = s.replace("\u00A0", " ")  # nbsp
    # Удаляем всё кроме цифр, пробела, точки, запятой
    s = re.sub(r"[^\d\.,\s]", "", s)
    # Если есть и точка и запятая — считаем что точка дробная, запятая — разделитель тысяч -> удалить запятые
    if "," in s and "." in s:
        s = s.replace(",", "")
    # Если имеются пробелы как разделитель тысяч — удаляем
    s = s.replace(" ", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except:
        # как fallback — возьмём только цифры
        digits = re.sub(r"\D", "", s)
        if digits:
            return float(digits)
        return 0.0


def extract_from_image(image_bytes: bytes, model: str = "gpt-4o-mini"):
    """
    Надёжный OCR через GPT-4o mini Vision (Responses API).
    Возвращает dict:
    {
      "amount": float,
      "category": str,
      "description": str,
      "date": str
    }
    Или None при ошибке.
    """

    # Убедимся что ключ задан
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY not set in environment")
        return None

    try:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{encoded}"

        system_prompt = (
            "Ты — профессиональный OCR ассистент для финансовых чеков. "
            "Верни ТОЛЬКО JSON в формате:\n"
            '{ "amount": 0, "category": "", "description": "", "date": "" }\n\n'
            "Правила:\n"
            "- amount: самое крупное число на чеке в UZS (верни число без разделителей в виде числа).\n"
            "- category: один из [еда, развлечения, покупки, транспорт, прочее, другое].\n"
            "- description: кратко (1-5 слов) о назначении платежа.\n"
            "- date: DD.MM.YYYY или пустая строка.\n"
            "Никакого лишнего текста — только JSON."
        )

        user_inputs = [
            {"type": "input_text", "text": "Извлеки данные с этого чека и верни JSON"},
            {"type": "input_image", "image_url": data_url}
        ]

        # Requests via Responses API
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_inputs}
            ],
            # Маленькие таймауты можно задать, но обычно на стороне SDK.
        )

        raw_text = _extract_text_from_response(resp)
        logger.info("OCR raw from model:\n%s", raw_text)

        if not raw_text:
            logger.warning("OCR: model returned empty text")
            return None

        # Найдём JSON в любом месте ответа
        m = re.search(r"\{[\s\S]*\}", raw_text)
        if not m:
            # Иногда модель может вернуть валидный YAML / ключ: значение — попытаемся извлечь числа
            logger.warning("OCR: JSON not found in model response")
            # fallback: искать числа в raw_text
            numbers = re.findall(r"[\d][\d\s\.,]{2,}", raw_text)
            amount = 0.0
            if numbers:
                # преобразуем и возьмём максимум
                cleaned = []
                for n in numbers:
                    try:
                        val = _clean_number_str(n)
                        cleaned.append(val)
                    except:
                        continue
                if cleaned:
                    amount = max(cleaned)
            return {
                "amount": float(amount),
                "category": "прочее",
                "description": "",
                "date": ""
            }

        json_text = m.group(0)

        try:
            parsed = json.loads(json_text)
        except Exception as e:
            logger.exception("OCR: failed to parse JSON, trying minor fixes: %s", e)
            # попытка убрать одиночные кавычки
            try:
                fixed = json_text.replace("'", "\"")
                parsed = json.loads(fixed)
            except Exception as e2:
                logger.exception("OCR: still failed to parse JSON: %s", e2)
                return None

        # Нормализуем поля
        amount = parsed.get("amount", 0) or 0
        try:
            amount = float(amount)
        except:
            # если строка - попробуем извлечь число
            amount = _clean_number_str(str(amount))

        category = parsed.get("category") or "прочее"
        description = parsed.get("description") or ""
        date = parsed.get("date") or ""

        # safety: если сумма нулевая — попытаемся извлечь из raw_text все числа и взять максимум
        if not amount or amount <= 0:
            numbers = re.findall(r"[\d][\d\s\.,]{2,}", raw_text)
            cleaned = []
            for n in numbers:
                val = _clean_number_str(n)
                if val:
                    cleaned.append(val)
            if cleaned:
                amount = max(cleaned)

        result = {
            "amount": float(amount),
            "category": category,
            "description": description,
            "date": date
        }

        logger.info("OCR result normalized: %s", result)
        return result

    except Exception as exc:
        logger.exception("OCR failed: %s", exc)
        return None
