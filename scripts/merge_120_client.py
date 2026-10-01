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
    if "net.fabricmc.fabric" in text and not (s.startswith(prefix + "particle/") or s.endswith("ShakerOverlay.java")):
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
    needed_states = {"GlasswareHolderBlockEntityRenderState.java", "ShakerBlockEntityRenderState.java", "StorageBlockEntityRenderState.java"}
    for src in state_src.rglob("*.java"):
        if src.name not in needed_states:
            continue
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


# 26.2 changed block tint registration APIs. Preserve the color calculations in NeoForge-compatible helpers;
# registration is bridged by the NeoForge client setup separately.
for relname in [
    "com/github/ysbbbbbb/kaleidoscopetavern/client/render/misc/SignatureCocktailColor.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/client/render/misc/PotionBottleColor.java",
]:
    p = work / relname
    if p.exists():
        t = p.read_text(encoding="utf-8")
        t = t.replace("import net.fabricmc.fabric.api.client.rendering.v1.BlockTintsFactory;\n", "")
        t = t.replace("import it.unimi.dsi.fastutil.ints.IntList;\n", "")
        t = t.replace("implements BlockTintsFactory", "")
        t = re.sub(r"\s*@Override\s*\n\s*public void collect\([\s\S]*?\n\s*}\n}", "\n}", t, count=1)
        p.write_text(t, encoding="utf-8")


# Explicit NeoForge 26.2 bridges for 1.2 client-only features.
(work / "com/github/ysbbbbbb/kaleidoscopetavern/client/render/misc/SignatureCocktailColor.java").write_text("""package com.github.ysbbbbbb.kaleidoscopetavern.client.render.misc;
import com.github.ysbbbbbb.kaleidoscopetavern.blockentity.mixology.SignatureCocktailBlockEntity;
import net.minecraft.client.color.block.BlockTintSource;
import net.minecraft.client.renderer.block.BlockAndTintGetter;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;
public final class SignatureCocktailColor {
 private SignatureCocktailColor() {}
 public static class Block implements BlockTintSource {
  public int color(BlockState state) { return 0xFFFFFFFF; }
  public int colorInWorld(BlockState state, BlockAndTintGetter level, BlockPos pos) {
   if (level.getBlockEntity(pos) instanceof SignatureCocktailBlockEntity be) return 0xFF000000 | (be.getColor() & 0xFFFFFF);
   return 0xFFFFFFFF;
  }
 }
}
""", encoding="utf-8")

(work / "com/github/ysbbbbbb/kaleidoscopetavern/client/render/misc/PotionBottleColor.java").write_text("""package com.github.ysbbbbbb.kaleidoscopetavern.client.render.misc;
import com.github.ysbbbbbb.kaleidoscopetavern.blockentity.brew.PotionBottleBlockEntity;
import net.minecraft.client.color.block.BlockTintSource;
import net.minecraft.client.renderer.block.BlockAndTintGetter;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.item.alchemy.PotionContents;
import net.minecraft.world.level.block.state.BlockState;
public class PotionBottleColor implements BlockTintSource {
 public int color(BlockState state) { return 0xFFFFFFFF; }
 public int colorInWorld(BlockState state, BlockAndTintGetter level, BlockPos pos) {
  if (level.getBlockEntity(pos) instanceof PotionBottleBlockEntity be && !be.getPotionStack().isEmpty()) {
   PotionContents contents = be.getPotionStack().get(DataComponents.POTION_CONTENTS);
   if (contents != null) return 0xFF000000 | (contents.getColor() & 0xFFFFFF);
  }
  return 0xFFFFFFFF;
 }
}
""", encoding="utf-8")

p = work / "com/github/ysbbbbbb/kaleidoscopetavern/client/gui/overlay/ShakerOverlay.java"
if p.exists():
    t = (ref / "com/github/ysbbbbbb/kaleidoscopetavern/client/gui/overlay/ShakerOverlay.java").read_text(encoding="utf-8")
    t = t.replace("import net.fabricmc.api.EnvType;\n", "").replace("import net.fabricmc.api.Environment;\n", "")
    t = t.replace("import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElement;\n", "")
    t = t.replace("import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;\n", "")
    t = t.replace("@Environment(EnvType.CLIENT)\n", "")
    t = t.replace("implements HudElement", "implements net.neoforged.neoforge.client.gui.GuiLayer")
    t = re.sub(r"\n    public static void register\(\) \{[\s\S]*?\n    \}\n", "\n", t, count=1)
    for reg in ["ModBlocks","ModItems"]:
        pat = re.compile(r"\b" + reg + r"\.([A-Z][A-Z0-9_]*)\b(?!\.get\(\))")
        t = pat.sub(lambda m: reg + "." + m.group(1) + ".get()", t)
    p.write_text(t, encoding="utf-8")
