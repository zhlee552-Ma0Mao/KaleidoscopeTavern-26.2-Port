from pathlib import Path
import shutil, re, sys

root = Path(__file__).resolve().parents[1]
src26 = root / "upstream-official-26.1.2"
src12 = root / "upstream-official-1.21.1"
ref26 = root / "upstream-refabricated-26.2"
work = root / "work"

if work.exists():
    shutil.rmtree(work)
shutil.copytree(src26, work, ignore=shutil.ignore_patterns(".git", ".gradle", "build", "run"))

# Target Minecraft / NeoForge / version.
gp = work / "gradle.properties"
s = gp.read_text(encoding="utf-8")
repls = {
    r"(?m)^minecraft_version=.*$": "minecraft_version=26.2",
    r"(?m)^minecraft_version_range=.*$": "minecraft_version_range=[26.2,26.3)",
    r"(?m)^neo_version=.*$": "neo_version=26.2.0.88",
    r"(?m)^neo_version_range=.*$": "neo_version_range=[26.2,26.3)",
    r"(?m)^mod_version=.*$": "mod_version=1.2.0-neoforge+mc26.2-port-ci",
}
for p,v in repls.items():
    s = re.sub(p,v,s)
gp.write_text(s, encoding="utf-8")

# Update build tooling/deps and isolate runtime/common first.
bg = work / "build.gradle"
s = bg.read_text(encoding="utf-8")
s = re.sub(r"id 'net\.neoforged\.moddev' version '[^']+'",
           "id 'net.neoforged.moddev' version '2.0.147'", s)
s = s.replace("mezz.jei:jei-26.1.2-neoforge-api:29.5.0.26",
              "mezz.jei:jei-26.2-neoforge-api:30.12.0.72")
s = s.replace("mezz.jei:jei-26.1.2-neoforge:29.5.0.26",
              "mezz.jei:jei-26.2-neoforge:30.12.0.72")
s = s.replace("maven.modrinth:jade:26.1.1+neoforge",
              "maven.modrinth:jade:26.2.8+neoforge")
for token in [
    r'^\s*compileOnly "maven\.modrinth:emi:.*"$',
    r'^\s*compileOnly "maven\.modrinth:cloth-config:.*"$',
    r'^\s*compileOnly "maven\.modrinth:architectury-api:.*"$',
    r'^\s*compileOnly "maven\.modrinth:rei:.*"$',
    r'^\s*compileOnly "net\.createmod\.ponder:.*"$',
]:
    s = re.sub(token, lambda m: "// PORT-CI disabled optional dep: " + m.group(0).strip(),
               s, flags=re.M)
s += """
// PORT-CI: common/server-first compilation gate.
tasks.named('compileJava', JavaCompile).configure {
    exclude '**/client/**'
    exclude '**/compat/**'
    exclude '**/datagen/**'
    options.compilerArgs += ['-Xmaxerrs', '500']
}
"""
bg.write_text(s, encoding="utf-8")

off_java = src26 / "src/main/java"
old_java = src12 / "src/main/java"
ref_java = ref26 / "src/main/java"
dst_java = work / "src/main/java"

feature_tokens = [
    "SHAKER","COCKTAIL","CELLAR_CABINET","POTION_BOTTLE",
    "SAKURA_INCENSE","PINE_INCENSE","GINKGO_INCENSE","SPORE_INCENSE",
    "CATNIP_INCENSE","SNOW_INCENSE","BUTTERFLY_INCENSE","FIREFLY_INCENSE",
    "CIRCULAR_RACK","TILTED_RACK","GLASSWARE_HOLDER","PENDANT_LAMP",
    "ARDENT_HEAT","LONG_REACH","SHRIEK_ATTACK","UPSIDE_DOWN","XP_DRAIN",
    "ZENITH","DRINK_EFFECT"
]

def fabric_specific(text:str)->bool:
    return ("net.fabricmc.fabric.api" in text or
            "net.fabricmc.loader.api" in text)

merged=[]
for old in old_java.rglob("*.java"):
    rel = old.relative_to(old_java)
    rels = rel.as_posix()
    if "/client/" in "/" + rels or "/compat/" in "/" + rels or "/datagen/" in "/" + rels:
        continue
    off = off_java / rel
    oldtxt = old.read_text(encoding="utf-8")
    new_feature = not off.exists()
    changed_feature = False
    if off.exists():
        offtxt = off.read_text(encoding="utf-8")
        changed_feature = any(t in oldtxt and t not in offtxt for t in feature_tokens)
    if not (new_feature or changed_feature):
        continue

    ref = ref_java / rel
    out = dst_java / rel
    out.parent.mkdir(parents=True, exist_ok=True)
    if ref.exists():
        txt = ref.read_text(encoding="utf-8")
        if not fabric_specific(txt):
            txt = re.sub(r'(?m)^import net\.fabricmc\.api\.(EnvType|Environment);\n?', '', txt)
            txt = re.sub(r'(?m)^\s*@Environment\(EnvType\.(CLIENT|SERVER)\)\s*\n?', '', txt)
            out.write_text(txt, encoding="utf-8")
            merged.append("REF26 " + rels)
            continue
    out.write_text(oldtxt, encoding="utf-8")
    merged.append("OLD12 " + rels)

# Copy pure util/neo shims from the 26.2 reference when present.
shim_src = ref_java / "com/github/ysbbbbbb/kaleidoscopetavern/util/neo"
shim_dst = dst_java / "com/github/ysbbbbbb/kaleidoscopetavern/util/neo"
if shim_src.exists():
    shim_dst.mkdir(parents=True, exist_ok=True)
    for f in shim_src.glob("*.java"):
        shutil.copy2(f, shim_dst / f.name)
        merged.append("SHIM26 " + f.relative_to(ref_java).as_posix())

# Full 1.2 resources/data.
for sub in ["assets", "data"]:
    src = src12 / "src/main/resources" / sub
    dst = work / "src/main/resources" / sub
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)

for name in ["kaleidoscope_tavern.mixins.json", "pack.mcmeta"]:
    f = src12 / "src/main/resources" / name
    if f.exists():
        shutil.copy2(f, work / "src/main/resources" / name)

# Known 26.2 migrations for cases where old 1.2 source had to be used.
for f in dst_java.rglob("*.java"):
    txt = f.read_text(encoding="utf-8")
    new = txt
    new = new.replace("applyInstantenousEffect", "applyInstantaneousEffect")
    new = new.replace("mc.setScreen(", "mc.gui.setScreen(")
    # Color dye item switch used by old StringLightsBlock.
    if f.name == "StringLightsBlock.java":
        new = re.sub(r'(?s)this\.dyeItem = switch \(dyeColor\) \{.*?\};',
                     'this.dyeItem = Items.DYE.pick(dyeColor);', new, count=1)
    if new != txt:
        f.write_text(new, encoding="utf-8")

(root / "merged-files.txt").write_text("\n".join(merged)+"\n", encoding="utf-8")
print(f"Prepared {work}")
print(f"Merged/replaced {len(merged)} Java files")
