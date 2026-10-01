from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
work = root / "work/src/main/java"
base = root / "upstream-official-26.1.2/src/main/java"
feature = root / "upstream-official-1.21.1/src/main/java"
ref = root / "upstream-refabricated-26.2/src/main/java"

base_rel = {p.relative_to(base) for p in base.rglob("*.java")}
feature_rel = {p.relative_to(feature) for p in feature.rglob("*.java")}
added = sorted(feature_rel - base_rel)
prefix = "com/github/ysbbbbbb/kaleidoscopetavern/client/"
merged = []

for rel in added:
    s = rel.as_posix()
    if not s.startswith(prefix):
        continue
    rs, fs = ref / rel, feature / rel
    text = (rs if rs.exists() else fs).read_text(encoding="utf-8")
    if "net.fabricmc.fabric" in text:
        text = fs.read_text(encoding="utf-8")
    else:
        text = text.replace("import net.fabricmc.api.EnvType;\n", "")
        text = text.replace("import net.fabricmc.api.Environment;\n", "")
        text = text.replace("@Environment(EnvType.CLIENT)\n", "")
    text = text.replace("net.minecraft.resources.ResourceLocation", "net.minecraft.resources.Identifier")
    text = text.replace("ResourceLocation.fromNamespaceAndPath", "Identifier.fromNamespaceAndPath")
    text = text.replace("ResourceLocation.parse", "Identifier.parse")
    for reg in ["ModBlocks","ModItems","ModDataComponents","ModSounds","ModParticles","ModRecipes"]:
        pat = re.compile(r"\\b" + reg + r"\\.([A-Z][A-Z0-9_]*)\\b(?!\\.get\\(\\))")
        text = pat.sub(lambda m: reg + "." + m.group(1) + ".get()", text)
    dst = work / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    merged.append(s)


# 26.2 renderer state classes are new API support files absent from the 1.21.1 tree.
state_src = ref / "com/github/ysbbbbbb/kaleidoscopetavern/client/render/renderstate"
if state_src.exists():
    for src in state_src.rglob("*.java"):
        rel = src.relative_to(ref)
        text = src.read_text(encoding="utf-8")
        if "net.fabricmc.fabric" in text:
            continue
        text = text.replace("import net.fabricmc.api.EnvType;\n", "")
        text = text.replace("import net.fabricmc.api.Environment;\n", "")
        text = text.replace("@Environment(EnvType.CLIENT)\n", "")
        dst = work / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
        merged.append(rel.as_posix())

with (root / "merged-files.txt").open("a", encoding="utf-8") as out:
    out.write("client 1.2 classes merged for gate: " + str(len(merged)) + "\n")
    for s in merged:
        out.write("CLIENT " + s + "\n")
print("client merged", len(merged))
