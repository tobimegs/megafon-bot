import json
import re
from pathlib import Path

ADDRESSES_FILE = Path("connected_addresses.json")


def normalize(text: str) -> set:
    """Убирает всё лишнее и возвращает набор слов"""
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    return set(text.split())


def load_addresses():
    if not ADDRESSES_FILE.exists():
        return []
    with open(ADDRESSES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_addresses(addresses):
    with open(ADDRESSES_FILE, "w", encoding="utf-8") as f:
        json.dump(addresses, f, ensure_ascii=False, indent=2)


def add_address(new_address: str) -> bool:
    """Добавляет адрес, если его ещё нет. Возвращает True, если добавили."""
    addresses = load_addresses()
    normalized_new = normalize(new_address)

    for addr in addresses:
        if normalize(addr) == normalized_new:
            return False  # Уже есть

    addresses.append(new_address.strip())
    save_addresses(addresses)
    return True


def is_address_connected(user_input: str) -> bool:
    """Проверяет, подключён ли адрес"""
    addresses = load_addresses()
    user_words = normalize(user_input)

    for addr in addresses:
        if normalize(addr).issubset(user_words):
            return True
    return False
