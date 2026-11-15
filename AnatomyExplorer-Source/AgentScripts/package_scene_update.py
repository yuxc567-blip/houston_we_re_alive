"""Replace only scene assets in an existing Unity Web data archive.

Keep the original executable and IL2CPP metadata together. Use only for
scene-only edits with the same Unity version and unchanged runtime fields.
"""
import pathlib
import struct

root = pathlib.Path(__file__).resolve().parents[1]
published = pathlib.Path(r"C:\Users\yuxc5\OneDrive\Documents\GitHub\houston_we_re_alive\anatomy-explorer\Build\LiveServerWeb.data")
original = published.read_bytes()
signature = b"UnityWebData1.0\0"
assert original.startswith(signature)
header_end = struct.unpack_from("<I", original, len(signature))[0]
cursor = len(signature) + 4
entries = []
while cursor < header_end:
    offset, size, name_length = struct.unpack_from("<III", original, cursor)
    cursor += 12
    name = original[cursor:cursor + name_length]
    cursor += name_length
    payload = original[offset:offset + size]
    if name == b"data.unity3d":
        payload = (root / "Library/PlayerDataCache/WebGL/Data/data.unity3d").read_bytes()
    entries.append((name, payload))
assert cursor == header_end
assert sum(name == b"data.unity3d" for name, _ in entries) == 1
header = bytearray(signature + struct.pack("<I", header_end))
offset = header_end
for name, payload in entries:
    header.extend(struct.pack("<III", offset, len(payload), len(name)) + name)
    offset += len(payload)
assert len(header) == header_end
output = root / "Builds/SceneOnlyUpdate/LiveServerWeb.data"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_bytes(header + b"".join(payload for _, payload in entries))
print(f"Packaged scene-only update: {output} ({output.stat().st_size} bytes)")
