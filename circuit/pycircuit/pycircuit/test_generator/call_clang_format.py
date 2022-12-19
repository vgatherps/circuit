import subprocess


def call_clang_format(on_content: str) -> str:
    command = ["clang-format"]

    p = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    (outs, errs) = p.communicate(input=str.encode(on_content))

    if p.returncode != 0:
        msg = f"""clang-format failed with returncode {p.returncode}:
        {errs!r}"""
        raise RuntimeError(msg)

    return outs.decode(encoding="utf-8")
