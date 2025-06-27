import re

def clean_name(name: str) -> str:
    name = re.sub(r"Path:.*", "", name)
    name = re.sub(r"Role filled by", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\[.*?\]", "", name)
    name = re.sub(r"\(.*Path.*?\)", "", name, flags=re.IGNORECASE)
    return name.strip()
