TREND = {
    "up": "صعودی",
    "down": "نزولی",
    "mixed": "مخلوط",
    "range": "رنج",
    "unclear": "نامشخص",
    "aligned_up": "هم‌جهت صعودی",
    "aligned_down": "هم‌جهت نزولی",
    "conflict": "تعارض تایم‌فریم",
}

PATTERN = {
    "doji": "دوجی",
    "pin_bull": "پین صعودی",
    "pin_bear": "پین نزولی",
    "engulf_bull": "اینگالف صعودی",
    "engulf_bear": "اینگالف نزولی",
}

GROUP = {
    "metals": "فلزات",
    "energy": "انرژی",
    "index": "شاخص",
    "crypto": "کریپتو",
    "fx": "ارز",
    "other": "سایر",
}


def fa_trend(key: str | None) -> str:
    return TREND.get(key or "", key or "نامشخص")


def fa_pattern(key: str) -> str:
    return PATTERN.get(key, key)


def fa_group(key: str) -> str:
    return GROUP.get(key, key)
