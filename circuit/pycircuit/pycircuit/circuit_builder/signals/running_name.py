_NAME_COUNTER: int = 0


def get_novel_name(prefix: str) -> str:
    global _NAME_COUNTER

    rval = f"{prefix}{_NAME_COUNTER}"
    _NAME_COUNTER += 1
    return rval
