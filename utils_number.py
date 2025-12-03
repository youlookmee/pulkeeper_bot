import re

UZ_NUMBERS = {
    "ноль": 0, "нол": 0, "нуль": 0,
    "бир": 1, "икки": 2, "уч": 3, "тўрт": 4, "беш": 5,
    "олти": 6, "етти": 7, "саккиз": 8, "туғқиз": 9,

    "ўн": 10, "йигирма": 20, "ўттиз": 30, "қирқ": 40,
    "эллик": 50, "олтмиш": 60, "етмиш": 70, "саксон": 80, "тўқсон": 90,

    "юз": 100, "йуз": 100, "юзта": 100,
    "минг": 1000, "ming": 1000,
    "млн": 1_000_000, "миллион": 1_000_000, "million": 1_000_000,
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

MULTIPLIERS = {
    "млн": 1_000_000, "million": 1_000_000, "миллион": 1_000_000,
    "тыс": 1000, "тысяча": 1000, "ming": 1000, "минг": 1000
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
    """Поддерживает:
    - 1 млн, 1.5 млн, 30 тыс
    - 1 000 000
    - бир миллион / ikki ming
    """

    text = text.lower().strip()

    # 1) Если цифры + множитель: "1.5 млн", "30 тыс"
    match = re.findall(r"([\d\.,]+)\s*(млн|million|миллион|тыс|ming|минг)", text)
    if match:
        num = match[0][0].replace(",", ".")
        mul = MULTIPLIERS.get(match[0][1], 1)
        return int(float(num) * mul)

    # 2) Просто цифры
    digits = re.findall(r"\d[\d\s]*", text)
    if digits:
        return int(digits[0].replace(" ", ""))

    # 3) Слова (узбек/рус)
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁўқғҳʼ'’]+", text)

    uz_sum = words_to_number(words, UZ_NUMBERS)
    ru_sum = words_to_number(words, RU_NUMBERS)

    final = max(uz_sum, ru_sum)

    return final if final > 0 else None
