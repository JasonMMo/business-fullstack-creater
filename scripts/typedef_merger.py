import re, pathlib
_SERVICES_CLOSE = re.compile(r'(\s*)(</Services>)')

def merge_service(path: pathlib.Path, *, prefixid: str, url: str,
                  cachelevel: str = "session") -> None:
    text = path.read_text(encoding="utf-8")
    if f'prefixid="{prefixid}"' in text:
        return  # idempotent
    entry = (
        f'    <Service prefixid="{prefixid}" type="form" '
        f'url="{url}" cachelevel="{cachelevel}" version=""/>\n'
    )
    new_text, n = _SERVICES_CLOSE.subn(
        lambda m: entry + m.group(1) + m.group(2), text, count=1
    )
    if n != 1:
        raise RuntimeError(f"</Services> not found in {path}")
    path.write_text(new_text, encoding="utf-8")
