from pathlib import Path
import shutil, re

root = Path(__file__).resolve().parents[1]
work = root / "work"
base = root / "upstream-official-26.1.2"
feature = root / "upstream-official-1.21.1"
ref = root / "upstream-refabricated-26.2"

# Preserve the proven NeoForge 26.2 scaffold, then layer only 1.2.0 feature files.
if not work.exists():
    raise SystemExit("work/ missing: run scripts/prepare_port.py first")

# 1.2.0 assets/data: preserve original visual identity.
for sub in ["assets", "data"]:
    src = feature / "src/main/resources" / sub
    dst = work / "src/main/resources" / sub
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)

for name in ["pack.mcmeta"]:
    src = feature / "src/main/resources" / name
    if src.exists():
        shutil.copy2(src, work / "src/main/resources" / name)

# Overlay the Refabricated 26.2 resource conversion last. The original 1.2 assets
# use pre-26.2 item/model resource layouts; the 26.2 reference keeps the same
# Tavern artwork/content while supplying Minecraft 26.2-compatible JSON paths.
for sub in ["assets", "data"]:
    src = ref / "src/main/resources" / sub
    dst = work / "src/main/resources" / sub
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)

ref_pack = ref / "src/main/resources/pack.mcmeta"
if ref_pack.exists():
    shutil.copy2(ref_pack, work / "src/main/resources/pack.mcmeta")

base_java = base / "src/main/java"
feature_java = feature / "src/main/java"
work_java = work / "src/main/java"

base_rel = {p.relative_to(base_java) for p in base_java.rglob("*.java")}
feature_rel = {p.relative_to(feature_java) for p in feature_java.rglob("*.java")}
added = sorted(feature_rel - base_rel)

# First fast pass: merge every 1.2 common/server feature class.
# Client/compat/datagen are deliberately moved to the next compile gate so that
# common registration/gameplay errors are isolated first, not hidden in renderer noise.
skip_prefixes = ("com/github/ysbbbbbb/kaleidoscopetavern/client/",
                 "com/github/ysbbbbbb/kaleidoscopetavern/compat/",
                 "com/github/ysbbbbbb/kaleidoscopetavern/datagen/")

merged = []
for rel in added:
    srel = rel.as_posix()
    if srel.startswith(skip_prefixes):
        continue
    src = feature_java / rel
    dst = work_java / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")

    # Mechanical 26.2 name migrations that are safe across the new classes.
    text = text.replace("net.minecraft.resources.ResourceLocation", "net.minecraft.resources.Identifier")
    text = text.replace("ResourceLocation.fromNamespaceAndPath", "Identifier.fromNamespaceAndPath")
    text = text.replace("ResourceLocation.parse", "Identifier.parse")
    text = text.replace("ItemInteractionResult", "InteractionResult")
    text = text.replace("net.minecraft.world.InteractionResult", "net.minecraft.world.InteractionResult")
    text = text.replace("PASS_TO_DEFAULT_BLOCK_INTERACTION", "PASS")
    text = text.replace("applyInstantenousEffect", "applyInstantaneousEffect")
    # 26.2 accessor is a method.
    text = re.sub(r"\.isClientSide(?!\s*\()", ".isClientSide()", text)
    # 26.2 riding overload used by the already-proven scaffold.
    text = re.sub(r"\.startRiding\(([^;\n]+),\s*true\);", r".startRiding(\1, true, true);", text)

    dst.write_text(text, encoding="utf-8")
    merged.append(srel)

# Bring the 1.2 registry declarations that do not overwrite ModBlocks/ModItems yet.
# These three are small and retain NeoForge DeferredRegister architecture.
mod_effects = work_java / "com/github/ysbbbbbb/kaleidoscopetavern/init/ModEffects.java"
if mod_effects.exists():
    t = mod_effects.read_text(encoding="utf-8")
    t = t.replace(
        "import com.github.ysbbbbbb.kaleidoscopetavern.effect.BaseEffect;\n"
        "import com.github.ysbbbbbb.kaleidoscopetavern.effect.GrassStealthEffect;\n"
        "import com.github.ysbbbbbb.kaleidoscopetavern.effect.HighHeelsEffect;\n"
        "import com.github.ysbbbbbb.kaleidoscopetavern.effect.VisionEffect;",
        "import com.github.ysbbbbbb.kaleidoscopetavern.effect.*;"
    )
    marker = '    DeferredHolder<MobEffect, MobEffect> BLOODY_MARY = EFFECTS.register("bloody_mary", () -> new BaseEffect(0xF73A36));'
    extra = marker + '''
    DeferredHolder<MobEffect, MobEffect> ARDENT_HEAT = EFFECTS.register("ardent_heat", () -> new ArdentHeatEffect(0xFF6B35));
    DeferredHolder<MobEffect, MobEffect> LONG_REACH = EFFECTS.register("long_reach", () -> new LongReachEffect(0x8B6914));
    DeferredHolder<MobEffect, MobEffect> TOMB_RAIDER = EFFECTS.register("tomb_raider", () -> new BaseEffect(0xDAA520));
    DeferredHolder<MobEffect, MobEffect> XP_DRAIN = EFFECTS.register("xp_drain", () -> new XpDrainEffect(0x7CFC00));
    DeferredHolder<MobEffect, MobEffect> UPSIDE_DOWN = EFFECTS.register("upside_down", () -> new UpsideDownEffect(0x9B59B6));
    DeferredHolder<MobEffect, MobEffect> ZENITH = EFFECTS.register("zenith", () -> new ZenithEffect(0x87CEEB));
    DeferredHolder<MobEffect, MobEffect> SHRIEK_ATTACK = EFFECTS.register("shriek_attack", () -> new ShriekAttackEffect(0x0D4C4A));'''
    if "ARDENT_HEAT" not in t:
        t = t.replace(marker, extra)
    mod_effects.write_text(t, encoding="utf-8")

# Use the 26.2 Refabricated implementations only for the new recipe trio; they
# provide the current Minecraft recipe API without replacing NeoForge loader code.
for relstr in [
    "com/github/ysbbbbbb/kaleidoscopetavern/crafting/container/SimpleInput.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/crafting/recipe/ShakerRecipe.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/crafting/serializer/ShakerRecipeSerializer.java",
]:
    src = ref / "src/main/java" / relstr
    dst = work_java / relstr
    if src.exists():
        txt = src.read_text(encoding="utf-8")
        txt = txt.replace("com.github.ysbbbbbb.kaleidoscopetavern.util.neo.RecipeMatcher",
                          "net.neoforged.neoforge.common.util.RecipeMatcher")
        # NeoForge registry holders are suppliers.
        txt = re.sub(r"ModRecipes\.SHAKER_SERIALIZER(?!\.get\()", "ModRecipes.SHAKER_SERIALIZER.get()", txt)
        txt = re.sub(r"ModRecipes\.SHAKER_RECIPE(?!\.get\()", "ModRecipes.SHAKER_RECIPE.get()", txt)
        txt = re.sub(r"ModRecipes\.SHAKER_RECIPE_CATEGORY(?!\.get\()", "ModRecipes.SHAKER_RECIPE_CATEGORY.get()", txt)
        # Replace Fabric direct recipe-book registration with the DeferredRegister entry.
        txt = re.sub(
            r"return Registry\.register\(BuiltInRegistries\.RECIPE_BOOK_CATEGORY, Identifier\.fromNamespaceAndPath\(KaleidoscopeTavern\.MOD_ID, \"shaker\"\), new RecipeBookCategory\(\)\);",
            "return ModRecipes.SHAKER_RECIPE_CATEGORY.get();",
            txt
        )
        txt = txt.replace("import net.minecraft.core.Registry;\n", "")
        txt = txt.replace("import net.minecraft.core.registries.BuiltInRegistries;\n", "")
        txt = txt.replace("import net.minecraft.resources.Identifier;\n", "")
        txt = txt.replace("import com.github.ysbbbbbb.kaleidoscopetavern.KaleidoscopeTavern;\n", "")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(txt, encoding="utf-8")

mod_recipes = work_java / "com/github/ysbbbbbb/kaleidoscopetavern/init/ModRecipes.java"
if mod_recipes.exists():
    t = mod_recipes.read_text(encoding="utf-8")
    if "ShakerRecipe" not in t:
        t = t.replace(
            "import com.github.ysbbbbbb.kaleidoscopetavern.crafting.recipe.PressingTubRecipe;",
            "import com.github.ysbbbbbb.kaleidoscopetavern.crafting.recipe.PressingTubRecipe;\n"
            "import com.github.ysbbbbbb.kaleidoscopetavern.crafting.recipe.ShakerRecipe;\n"
            "import com.github.ysbbbbbb.kaleidoscopetavern.crafting.serializer.ShakerRecipeSerializer;"
        )
    if "SHAKER_SERIALIZER" not in t:
        t = t.replace(
            '    Supplier<RecipeSerializer<BarrelRecipe>> BARREL_SERIALIZER = RECIPE_SERIALIZERS.register("barrel", () -> BarrelRecipe.SERIALIZER);',
            '    Supplier<RecipeSerializer<BarrelRecipe>> BARREL_SERIALIZER = RECIPE_SERIALIZERS.register("barrel", () -> BarrelRecipe.SERIALIZER);\n'
            '    Supplier<RecipeSerializer<ShakerRecipe>> SHAKER_SERIALIZER = RECIPE_SERIALIZERS.register("shaker", () -> new RecipeSerializer<>(ShakerRecipeSerializer.codec(), ShakerRecipeSerializer.streamCodec()));'
        )
        t = t.replace(
            '    Supplier<RecipeType<BarrelRecipe>> BARREL_RECIPE = RECIPE_TYPES.register("barrel", () -> RecipeType.simple(KaleidoscopeTavern.modLoc("barrel")));',
            '    Supplier<RecipeType<BarrelRecipe>> BARREL_RECIPE = RECIPE_TYPES.register("barrel", () -> RecipeType.simple(KaleidoscopeTavern.modLoc("barrel")));\n'
            '    Supplier<RecipeType<ShakerRecipe>> SHAKER_RECIPE = RECIPE_TYPES.register("shaker", () -> RecipeType.simple(KaleidoscopeTavern.modLoc("shaker")));'
        )
        t = t.replace(
            '    Supplier<RecipeBookCategory> BARREL_RECIPE_CATEGORY = RECIPE_BOOK_CATEGORIES.register("barrel", RecipeBookCategory::new);',
            '    Supplier<RecipeBookCategory> BARREL_RECIPE_CATEGORY = RECIPE_BOOK_CATEGORIES.register("barrel", RecipeBookCategory::new);\n'
            '    Supplier<RecipeBookCategory> SHAKER_RECIPE_CATEGORY = RECIPE_BOOK_CATEGORIES.register("shaker", RecipeBookCategory::new);'
        )
    mod_recipes.write_text(t, encoding="utf-8")

# Mark this build as a real 1.2 merge attempt.
gp = work / "gradle.properties"
if gp.exists():
    t = gp.read_text(encoding="utf-8")
    t = re.sub(r"(?m)^mod_version=.*$", "mod_version=1.2.0-neoforge+mc26.2-fastmerge", t)
    gp.write_text(t, encoding="utf-8")

summary = [
    "Fast 1.2.0 merge pass",
    f"new common/server Java files merged: {len(merged)}",
    "full official 1.2 assets/data overlaid",
    "client/compat/datagen intentionally held for next compile gate",
]
(root / "merged-files.txt").write_text("\n".join(summary + merged) + "\n", encoding="utf-8")
print("\n".join(summary))
