"""Restore the two markdown files.

A PowerShell round-trip decoded UTF-8 as cp1251 and re-wrote it as UTF-8, so almost the
whole file is mojibake. The only exception is the marker text inserted in the same
command, which stayed correct Cyrillic; it is masked before the reversal and restored after.
"""

import sys

AD = r"C:\Users\Sonkins\OneDrive\Desktop\AIdriven_HW3_Agents\AIdriven_HW3_Agents\agent-deepseek"
MARKER = "(исх. ред.)"
PLACEHOLDER = "__REDAKCIYA__"


def reverse(text: str) -> str:
    out = bytearray()
    for ch in text:
        if ch == "\u0098":            # cp1251 0x98 is undefined; PowerShell mapped it to C1
            out.append(0x98)
        else:
            out.extend(ch.encode("cp1251"))
    return bytes(out).decode("utf-8")


for name in ("ANALYSIS.md", "REQUIREMENTS.md"):
    path = AD + "\\" + name
    text = open(path, "rb").read().decode("utf-8")

    markers = text.count(MARKER)
    masked = text.replace(MARKER, PLACEHOLDER)
    try:
        restored = reverse(masked)
    except Exception as exc:  # noqa: BLE001
        print(f"{name}: FAILED -> {type(exc).__name__}: {exc}")
        sys.exit(1)

    restored = restored.replace(PLACEHOLDER, MARKER)
    leftover = [m for m in ("Р°", "Рµ", "СЂ", "Рѕ", "Рё", "Рџ") if m in restored]
    ok = "Задание" in restored and not leftover and "\ufffd" not in restored

    print(f"{name}: markers={markers} | cyrillic={'Задание' in restored} | leftover={leftover} | len={len(restored)}")
    if not ok:
        print(f"{name}: NOT WRITTEN")
        sys.exit(1)
    with open(path, "wb") as f:
        f.write(restored.encode("utf-8"))
    print(f"{name}: RESTORED")
