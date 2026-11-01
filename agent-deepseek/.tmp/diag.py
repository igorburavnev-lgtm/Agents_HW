import codecs

AD = r"C:\Users\Sonkins\OneDrive\Desktop\AIdriven_HW3_Agents\AIdriven_HW3_Agents\agent-deepseek"
path = AD + r"\ANALYSIS.md"
text = open(path, "rb").read().decode("utf-8")

buf = bytearray()
dec = codecs.getincrementaldecoder("utf-8")("replace")
problems = []
for idx, ch in enumerate(text):
    if ch == "\u0098":
        b = b"\x98"
    else:
        try:
            b = ch.encode("cp1251")
        except UnicodeEncodeError:
            problems.append((idx, ch, "unencodable"))
            continue
    buf.extend(b)

# find invalid utf-8 regions
decoded = bytes(buf).decode("utf-8", "surrogateescape")
bad = [(i, ch) for i, ch in enumerate(decoded) if 0xDC80 <= ord(ch) <= 0xDCFF]
print("invalid byte count:", len(bad))
print("first invalid at decoded index", bad[:5])
for i, ch in bad[:6]:
    start = max(0, i - 40)
    print("context:", repr(decoded[start:i + 20]))
print("unencodable chars:", problems[:5], "count", len(problems))
