import re

def extract_amount(text: str):
    matches = re.findall(r"\b\d[\d\s]{2,}\b", text)
    if not matches:
        return None
    num = matches[-1].replace(" ", "")
    return int(num)


def extract_items(text: str):
    """
    Ищет товарные позиции вида:
    Хлеб 8000
    Молоко 12000
    Pepsi 9000
    """
    lines = text.split("\n")
    items = []

    for line in lines:
        m = re.findall(r"(.+?)\s+(\d{3,})$", line.strip())
        if m:
            name, price = m[0]
            items.append((name.strip(), int(price)))
    return items
