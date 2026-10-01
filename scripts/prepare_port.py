from pathlib import Path
import shutil, re

root = Path(__file__).resolve().parents[1]
src26 = root / "upstream-official-26.1.2"
work = root / "work"

if work.exists():
    shutil.rmtree(work)
shutil.copytree(src26, work, ignore=shutil.ignore_patterns(".git", ".gradle", "build", "run"))

# Exact target.
gp = work / "gradle.properties"
s = gp.read_text(encoding="utf-8")
for p, v in {
    r"(?m)^minecraft_version=.*$": "minecraft_version=26.2",
    r"(?m)^minecraft_version_range=.*$": "minecraft_version_range=[26.2,26.3)",
    r"(?m)^neo_version=.*$": "neo_version=26.2.0.88",
    r"(?m)^neo_version_range=.*$": "neo_version_range=[26.2,26.3)",
    r"(?m)^mod_version=.*$": "mod_version=1.1.2-neoforge+mc26.2-ci-baseline",
}.items():
    s = re.sub(p, v, s)
gp.write_text(s, encoding="utf-8")

# Current ModDevGradle + 26.2 optional dependencies.
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
    s = re.sub(token, lambda m: "// CI disabled old optional dep: " + m.group(0).strip(), s, flags=re.M)
# Common/server first. This reproduces the already-proven Stage 6 scaffold.
s += """
tasks.named('compileJava', JavaCompile).configure {
    exclude '**/client/**'
    exclude '**/compat/**'
    exclude '**/datagen/**'
    options.compilerArgs += ['-Xmaxerrs', '500']
}
"""
bg.write_text(s, encoding="utf-8")

java_root = work / "src/main/java"

# Known 26.2 API migrations already proven in Stage 6.
f = java_root / "com/github/ysbbbbbb/kaleidoscopetavern/block/deco/StringLightsBlock.java"
if f.exists():
    t = f.read_text(encoding="utf-8")
    t = re.sub(r'(?s)this\.dyeItem = switch \(dyeColor\) \{.*?\};',
               'this.dyeItem = Items.DYE.pick(dyeColor);', t, count=1)
    f.write_text(t, encoding="utf-8")

f = java_root / "com/github/ysbbbbbb/kaleidoscopetavern/effect/BaseEffect.java"
if f.exists():
    t = f.read_text(encoding="utf-8").replace("applyInstantenousEffect", "applyInstantaneousEffect")
    f.write_text(t, encoding="utf-8")

f = java_root / "com/github/ysbbbbbb/kaleidoscopetavern/network/proxy/TextOpenS2CProxy.java"
if f.exists():
    t = f.read_text(encoding="utf-8").replace("mc.setScreen(", "mc.gui.setScreen(")
    f.write_text(t, encoding="utf-8")

(root / "merged-files.txt").write_text(
    "CI baseline: official 26.1.2 NeoForge source -> Minecraft 26.2 / NeoForge 26.2.0.88\n",
    encoding="utf-8"
)
print("Prepared clean 26.2 NeoForge baseline:", work)
