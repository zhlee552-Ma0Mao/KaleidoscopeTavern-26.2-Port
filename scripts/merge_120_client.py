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
    t = t.replace("public void extractRenderState(@NonNull GuiGraphicsExtractor guiGraphics, @NonNull DeltaTracker deltaTracker)", "public void render(@NonNull GuiGraphicsExtractor guiGraphics, @NonNull DeltaTracker deltaTracker)")
    t = re.sub(r"\n    public static void register\(\) \{[\s\S]*?\n    \}\n", "\n", t, count=1)
    for reg in ["ModBlocks","ModItems"]:
        pat = re.compile(r"\b" + reg + r"\.([A-Z][A-Z0-9_]*)\b(?!\.get\(\))")
        t = pat.sub(lambda m: reg + "." + m.group(1) + ".get()", t)
    p.write_text(t, encoding="utf-8")


# Wire the new 1.2 client features into NeoForge's 26.2 client events.
setup = work / "com/github/ysbbbbbb/kaleidoscopetavern/client/init/ClientSetupEvent.java"
st = setup.read_text(encoding="utf-8")
st = st.replace("import com.github.ysbbbbbb.kaleidoscopetavern.client.render.block.*;\n",
"""import com.github.ysbbbbbb.kaleidoscopetavern.client.render.block.*;
import com.github.ysbbbbbb.kaleidoscopetavern.client.gui.overlay.ShakerOverlay;
import com.github.ysbbbbbb.kaleidoscopetavern.client.render.misc.PotionBottleColor;
import com.github.ysbbbbbb.kaleidoscopetavern.client.render.misc.SignatureCocktailColor;
""")
st = st.replace("import net.neoforged.neoforge.client.event.RegisterFluidModelsEvent;\n",
"""import net.neoforged.neoforge.client.event.RegisterFluidModelsEvent;
import net.neoforged.neoforge.client.event.RegisterGuiLayersEvent;
import net.neoforged.neoforge.client.event.RegisterColorHandlersEvent;
import java.util.List;
import static net.neoforged.neoforge.client.gui.VanillaGuiLayers.CROSSHAIR;
""")
needle = "        BlockEntityRenderers.register(ModBlocks.BAR_STOOL_BE.get(), BarStoolBlockEntityRender::new);"
extra = needle + """
        BlockEntityRenderers.register(ModBlocks.CELLAR_CABINET_BE.get(), CellarCabinetBlockEntityRender::new);
        BlockEntityRenderers.register(ModBlocks.TILTED_RACK_BE.get(), TiltedRackBlockEntityRender::new);
        BlockEntityRenderers.register(ModBlocks.CIRCULAR_RACK_BE.get(), CircularRackBlockEntityRender::new);
        BlockEntityRenderers.register(ModBlocks.HOLDER_BE.get(), HolderBlockEntityRender::new);
        BlockEntityRenderers.register(ModBlocks.SHAKER_BE.get(), ShakerBlockEntityRender::new);
        BlockEntityRenderers.register(ModBlocks.GLASSWARE_HOLDER_BE.get(), GlasswareHolderBlockEntityRender::new);"""
st = st.replace(needle, extra)
st = st.rsplit("}",1)[0] + """
    @SubscribeEvent
    public static void onRegisterGuiOverlays(RegisterGuiLayersEvent event) {
        event.registerAbove(CROSSHAIR, KaleidoscopeTavern.modLoc("shaker_overlay"), new ShakerOverlay());
    }

    @SubscribeEvent
    public static void registerBlockColors(RegisterColorHandlersEvent.BlockTintSources event) {
        event.register(List.of(new SignatureCocktailColor.Block()), ModBlocks.SIGNATURE_COCKTAIL.get());
        event.register(List.of(new PotionBottleColor()), ModBlocks.POTION_BOTTLE.get());
    }
}
"""
setup.write_text(st, encoding="utf-8")

particle_registry = work / "com/github/ysbbbbbb/kaleidoscopetavern/client/init/ParticleFactoryRegistry.java"
pt = particle_registry.read_text(encoding="utf-8")
pt = pt.replace("import com.github.ysbbbbbb.kaleidoscopetavern.client.particle.TapDripParticle;\n",
"""import com.github.ysbbbbbb.kaleidoscopetavern.client.particle.TapDripParticle;
import com.github.ysbbbbbb.kaleidoscopetavern.client.particle.IncenseParticle;
import com.github.ysbbbbbb.kaleidoscopetavern.client.particle.IncenseSuspendedParticle;
import com.github.ysbbbbbb.kaleidoscopetavern.client.particle.ButterflyIncenseLargeParticle;
import com.github.ysbbbbbb.kaleidoscopetavern.client.particle.FireflyIncenseLargeParticle;
""")
marker = "        event.registerSpriteSet(ModParticles.LAVA_TAP_DRIP.get(), TapDripParticle.LavaTapDripParticle::new);"
regs = marker + """
        event.registerSpriteSet(ModParticles.SAKURA_INCENSE_PARTICLE.get(), IncenseParticle.Provider::new);
        event.registerSpriteSet(ModParticles.PINE_INCENSE_PARTICLE.get(), IncenseParticle.Provider::new);
        event.registerSpriteSet(ModParticles.GINKGO_INCENSE_PARTICLE.get(), IncenseParticle.Provider::new);
        event.registerSpriteSet(ModParticles.SPORE_INCENSE_PARTICLE.get(), IncenseParticle.Provider::new);
        event.registerSpriteSet(ModParticles.CATNIP_INCENSE_PARTICLE.get(), IncenseParticle.Provider::new);
        event.registerSpriteSet(ModParticles.SNOW_INCENSE_PARTICLE.get(), IncenseParticle.Provider::new);
        event.registerSpriteSet(ModParticles.BUTTERFLY_INCENSE_PARTICLE.get(), IncenseParticle.Provider::new);
        event.registerSpriteSet(ModParticles.FIREFLY_INCENSE_PARTICLE.get(), IncenseParticle.Provider::new);
        event.registerSpriteSet(ModParticles.PINE_INCENSE_LARGE_PARTICLE.get(), IncenseSuspendedParticle.Provider::new);
        event.registerSpriteSet(ModParticles.GINKGO_INCENSE_LARGE_PARTICLE.get(), IncenseSuspendedParticle.Provider::new);
        event.registerSpriteSet(ModParticles.CATNIP_INCENSE_LARGE_PARTICLE.get(), IncenseSuspendedParticle.Provider::new);
        event.registerSpriteSet(ModParticles.SNOW_INCENSE_LARGE_PARTICLE.get(), IncenseSuspendedParticle.Provider::new);
        event.registerSpriteSet(ModParticles.BUTTERFLY_INCENSE_LARGE_PARTICLE.get(), ButterflyIncenseLargeParticle.Provider::new);
        event.registerSpriteSet(ModParticles.FIREFLY_INCENSE_LARGE_PARTICLE.get(), FireflyIncenseLargeParticle.Provider::new);"""
pt = pt.replace(marker, regs)
particle_registry.write_text(pt, encoding="utf-8")
