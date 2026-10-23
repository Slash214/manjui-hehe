def build_prompt(style: str, assets: list[str], action: str, size: str, angle: str, blocking: str) -> str:
    return "\n".join(part.strip() for part in [style, *assets, action, size, angle, blocking] if part.strip())
