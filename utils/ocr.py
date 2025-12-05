# utils/ocr.py
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime
from typing import Optional, Dict, Any

# --- Настройка ключевых слов для подсказки суммы ---
AMOUNT_HINT_WORDS = [
    "итого", "итог", "оплата", "сум", "сумма", "total", "amount", "paid", "опл",
    "общая", "итого:", "всего", "одобрено", "payment", "amount:"
]

DATE_PATTERNS = [
    r"\b(\d{2}[./-]\d{2}[./-]\d{4})\b",  # 02.12.2025 or 02/12/2025 or 02-12-2025
    r"\b(\d{4}[./-]\d{2}[./-]\d{2})\b",  # 2025-12-02
    r"\b(\d{2}[./-]\d{2}[./-]\d{2})\b",  # 02.12.25 (less reliable)
]

# merchant heuristics: lines in top of the check, uppercase words, brand tokens
MERCHANT_TOKENS = ["ООО", "ИП", "UZCARD", "PAY", "TERMINAL", "POS", "SHOP", "STORE"]


def clean_text(text: str) -> str:
    """Небольшая нормализация текста, сохраняем перевод строки."""
    if not text:
        return ""
    # Нормализуем пробелы и одинаковые кавычки
    text = text.replace("\r", "\n")
    # Заменим неразрывные пробелы
    text = text.replace("\u00A0", " ")
    # Уберём пустые ведущие/закрывающие пробелы в строках
    lines = [ln.strip() for ln in text.splitlines()]
    # Уберём повторяющиеся пустые строки
    new_lines = []
    for ln in lines:
        if ln == "" and (not new_lines or new_lines[-1] == ""):
            continue
        new_lines.append(ln)
    return "\n".join(new_lines).strip()


def _normalize_number_token(token: str) -> Optional[str]:
    """
    Приводит найденный числовой токен к стандартной форме:
    - убирает пробелы-разделители тысяч
    - заменяет запятую на точку для дробной части
    Возвращает строку, пригодную для Decimal или None.
    """
    if not token:
        return None
    # Удаляем валютные буквы внутри токена
    token = token.strip()
    # Уберём любые буквы, кроме цифр и . ,
    token = re.sub(r"[^\d\.,]", "", token)
    if token == "":
        return None

    # Если есть несколько точек/запятых — попробуем определить формат
    # Сначала удаляем пробелы
    token_no_spaces = token.replace(" ", "").replace("\u00A0", "")
    # Если есть запятая и точка — вероятно разделитель тысяч точка, дробная запятая или наоборот.
    # Упростим: заменим запятую на точку, и если больше одной точки — удалим все кроме последней
    token2 = token_no_spaces.replace(",", ".")
    # Удаляем все точки кроме последней (например "5.000.000.00" -> "5000000.00")
    parts = token2.split(".")
    if len(parts) > 2:
        frac = parts[-1]
        intpart = "".join(parts[:-1])
        token2 = intpart + "." + frac
    # Уберём ведущие нули (но оставим "0.xx")
    token2 = token2.lstrip()
    if re.fullmatch(r"\d+\.", token2):  # "5000000." -> "5000000"
        token2 = token2[:-1]
    if re.fullmatch(r"\.", token2):
        return None
    return token2


def _find_number_candidates(text: str):
    """
    Находим кандидатов — числа в тексте. Возвращаем список (raw_token, line, start_pos)
    """
    candidates = []
    # Ищем числа с возможными разделителями: пробел/точка/запятая
    # Также найдем числа с валютой рядом
    pattern = re.compile(r"(?:(?:\d{1,3}(?:[ .\u00A0]\d{3})+(?:[.,]\d+)?|\d+[.,]\d+|\d+))")
    for m in pattern.finditer(text):
        raw = m.group(0)
        # получаем строку, в которой число находится
        start = m.start()
        # line extraction
        prev_newline = text.rfind("\n", 0, start)
        next_newline = text.find("\n", start)
        if prev_newline == -1:
            line_start = 0
        else:
            line_start = prev_newline + 1
        if next_newline == -1:
            line_end = len(text)
        else:
            line_end = next_newline
        line = text[line_start:line_end]
        candidates.append((raw, line, start))
    return candidates


def _score_candidate(raw: str, line: str, text: str) -> float:
    """
    Простейшая эвристика выбора лучшей суммы.
    - +2 если рядом есть слово из AMOUNT_HINT_WORDS в line
    - +1 если raw имеет точку или запятую (т.е. дробная часть или разделитель тысяч)
    - +1 если длина числа >= 5 (высокие суммы более вероятны)
    - +0.5 если рядом слово 'сум' или 'uzs'
    """
    score = 0.0
    low_line = line.lower()
    low_text = text.lower()
    for w in AMOUNT_HINT_WORDS:
        if w in low_line:
            score += 2.0
        elif w in low_text[max(0, line.__len__()-50):line.__len__()+50]:
            score += 1.0
    # prefer formatted numbers (with separators) or decimals
    if re.search(r"[ \.\u00A0,]", raw):
        score += 1.0
    # longer numbers (>=5 digits) get a boost
    digits_only = re.sub(r"[^\d]", "", raw)
    if len(digits_only) >= 5:
        score += 1.0
    # small boost if currency mention
    if re.search(r"(сум|uzs|sum|UZS)", line, re.IGNORECASE):
        score += 0.5
    return score


def _parse_decimal_from_token(token: str) -> Optional[Decimal]:
    norm = _normalize_number_token(token)
    if not norm:
        return None
    try:
        d = Decimal(norm)
        return d
    except InvalidOperation:
        return None


def _pick_best_amount(candidates, full_text: str) -> Optional[Decimal]:
    """
    Выбираем лучший кандидат по score; если несколько близки — берём максимальную сумму.
    """
    scored = []
    for raw, line, pos in candidates:
        val = _parse_decimal_from_token(raw)
        if val is None:
            continue
        score = _score_candidate(raw, line, full_text)
        scored.append((score, val, raw, line, pos))
    if not scored:
        return None
    # Сортируем по score desc, value desc
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    # Возвращаем сумму лучшего
    best = scored[0]
    return best[1]


def _extract_date(text: str) -> Optional[str]:
    """Пытаемся найти дату в тексте, возвращаем строку в ISO (YYYY-MM-DD) если найдено."""
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            s = m.group(1)
            # Преобразуем в нормальную дату
            for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d.%m.%y", "%d/%m/%y"):
                try:
                    dt = datetime.strptime(s, fmt)
                    return dt.date().isoformat()
                except Exception:
                    continue
            # если не смогли распарсить — вернем сырой s
            return s
    return None


def _extract_merchant(text: str) -> Optional[str]:
    """
    Простая эвристика для продавца:
    берем первые 3-5 строк текста и ищем "заглавные" строки или строки с MERCHANT_TOKENS.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    top_lines = lines[:6]
    # Попробуем найти строки с токенами
    for ln in top_lines:
        for tok in MERCHANT_TOKENS:
            if tok.lower() in ln.lower():
                return ln
    # иначе возьмём самую короткую заглавную строку (логотип типа U Z C A R D)
    for ln in top_lines:
        # если строка в основном в верхнем регистре и длиннее 2 символов
        letters = re.sub(r"[^A-Za-zА-Яа-яЁё0-9]", "", ln)
        if letters.isupper() and len(letters) >= 2:
            return ln
    # иначе первая непустая строка как fallback
    return top_lines[0] if top_lines else None


def extract_from_receipt(ocr_text: str) -> Dict[str, Any]:
    """
    Основная функция — принимает текст (результат OCR),
    возвращает dict:
    {
      "amount": Decimal | None,
      "currency": "UZS"|"RUB"|... | None,
      "date": "YYYY-MM-DD" | raw_date | None,
      "merchant": str | None,
      "description": str | None,
      "raw_text": normalized_text
    }
    """
    normalized = clean_text(ocr_text or "")
    result = {
        "amount": None,
        "currency": None,
        "date": None,
        "merchant": None,
        "description": None,
        "raw_text": normalized
    }

    if not normalized:
        return result

    # 1) Попытка извлечь дату
    date_found = _extract_date(normalized)
    if date_found:
        result["date"] = date_found

    # 2) Находим числовые кандидаты
    candidates = _find_number_candidates(normalized)
    # Выбираем лучший
    amount = _pick_best_amount(candidates, normalized)
    if amount is not None:
        result["amount"] = amount
        # Попробуем определить валюту: поиск рядом с лучшим raw
        # Найдем raw of chosen by matching value string
        # Но проще: проверим наличие слов "сум", "UZS", "руб", "RUB" в тексте
        low = normalized.lower()
        if "сум" in low or "uzs" in low:
            result["currency"] = "UZS"
        elif "руб" in low or "rub" in low:
            result["currency"] = "RUB"
        elif "$" in normalized or "usd" in low:
            result["currency"] = "USD"

    # 3) Merchant heuristic
    merchant = _extract_merchant(normalized)
    if merchant:
        result["merchant"] = merchant

    # 4) Description — попытаемся взять строку с ключевыми словами рядом с amount
    # Найдём строк, где встречается слово из AMOUNT_HINT_WORDS
    lines = normalized.splitlines()
    desc = None
    for ln in lines:
        for w in AMOUNT_HINT_WORDS:
            if w in ln.lower() and any(ch.isdigit() for ch in ln):
                desc = ln
                break
        if desc:
            break
    # fallback: если нет — берем вторую строку после merchant (если есть)
    if not desc and merchant:
        try:
            idx = lines.index(merchant)
            if idx + 1 < len(lines):
                desc = lines[idx + 1]
        except ValueError:
            desc = None

    result["description"] = desc

    return result


# --------------------
# Пример использования (локально)
# --------------------
if __name__ == "__main__":
    sample = """
    UZCARD
    ОПЛАТА
    5 000 000.00 Сум
    ОДОБРЕНО
    Дата: 02.12.2025 15:47:03
    """
    out = extract_from_receipt(sample)
    print(out)
