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
held = []

for rel in added:
    s = rel.as_posix()
    if not s.startswith(prefix):
        continue
    rs = ref / rel
    fs = feature / rel
    src = rs if rs.exists() else fs
    text = src.read_text(encoding="utf-8")
    if "net.fabricmc.fabric" in text:
        # Fabric event hooks need the official NeoForge event architecture.
        text = fs.read_text(encoding="utf-8")
    else:
        # Most 26.2 Refabricated client classes only carry Fabric side annotations.
        # Strip those annotations and retain the current 26.2 rendering/model APIs.
        text = re.sub(r"import net\\.fabricmc\\.api\\.(Environment|EnvType);\\n", "", text)
        text = re.sub(r"@Environment\\(EnvType\\.CLIENT\\)\\s*", "", text)
    text = text.replace("net.minecraft.resources.ResourceLocation", "net.minecraft.resources.Identifier")
    text = text.replace("ResourceLocation.fromNamespaceAndPath", "Identifier.fromNamespaceAndPath")
    text = text.replace("ResourceLocation.parse", "Identifier.parse")
    for reg in ["ModBlocks","ModItems","ModDataComponents","ModSounds","ModParticles","ModRecipes"]:
        text = re.sub(rf"\\b{reg}\\.([A-Z][A-Z0-9_]*)\\b(?!\\.get\\(\\))", rf"{reg}.\\1.get()", text)
    dst = work / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    merged.append(s)

with (root / "merged-files.txt").open("a", encoding="utf-8") as f:
    f.write(f"client 1.2 classes merged for gate: {len(merged)}\\n")
    f.write(f"client Fabric-specific classes held for NeoForge adaptation: {len(held)}\\n")
    for s in merged: f.write("CLIENT " + s + "\\n")
    for s in held: f.write("HELD " + s + "\\n")
print("client merged", len(merged), "held", len(held))
