import re

UZ_NUMBERS = {
    "ноль": 0, "нол": 0, "нуль": 0,
    "бир": 1, "икки": 2, "уч": 3, "тўрт": 4, "беш": 5,
    "олти": 6, "етти": 7, "саккиз": 8, "туғқиз": 9,

    "ўн": 10, "йигирма": 20, "ўттиз": 30, "қирқ": 40,
    "эллик": 50, "олтмиш": 60, "етмиш": 70, "саксон": 80, "тўқсон": 90,

    "юз": 100, "йуз": 100, "юзта": 100,
    "минг": 1000, "млн": 1_000_000, "миллион": 1_000_000,
    "ярим": 500_000
}

RU_NUMBERS = {
    "ноль": 0, "один": 1, "два": 2, "три": 3, "четыре": 4,
    "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9,

    "десять": 10, "двадцать": 20, "тридцать": 30, "сорок": 40,
    "пятьдесят": 50, "шестьдесят": 60, "семьдесят": 70,
    "восемьдесят": 80, "девяносто": 90,

    "сто": 100, "двести": 200, "триста": 300, "четыреста": 400,
    "пятьсот": 500, "шестьсот": 600, "семьсот": 700,
    "восемьсот": 800, "девятьсот": 900,

    "тысяч": 1000, "тысяча": 1000, "тысячи": 1000,
    "млн": 1_000_000, "миллион": 1_000_000,
    "полмиллиона": 500_000
}


def words_to_number(words: list[str], table: dict) -> int:
    total = 0
    current = 0

    for w in words:
        if w not in table:
            continue

        value = table[w]

        # multiplier logic (hundred, thousand, million)
        if value in [100, 1000, 1_000_000]:
            if current == 0:
                current = 1
            current *= value
            total += current
            current = 0
        else:
            current += value

    return total + current


def normalize_text_to_number(text: str) -> int | None:
    """Преобразует узбекские/русские слова в число"""

    # 1) Ищем цифры сразу
    numbers = re.findall(r"\d[\d ]+", text)
    if numbers:
        cleaned = numbers[0].replace(" ", "")
        return int(cleaned)

    # 2) преобразуем текст в слова
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁўқғҳʼ'’]+", text.lower())

    # узбекские
    uz_sum = words_to_number(words, UZ_NUMBERS)

    # русские
    ru_sum = words_to_number(words, RU_NUMBERS)

    final_number = max(uz_sum, ru_sum)

    return final_number if final_number > 0 else None
