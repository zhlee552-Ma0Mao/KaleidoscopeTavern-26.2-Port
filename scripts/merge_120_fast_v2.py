from pathlib import Path
import shutil, re

root = Path(__file__).resolve().parents[1]
work = root / "work"
base = root / "upstream-official-26.1.2"
feature = root / "upstream-official-1.21.1"
ref = root / "upstream-refabricated-26.2"
wj = work / "src/main/java"
bj = base / "src/main/java"
fj = feature / "src/main/java"
rj = ref / "src/main/java"

base_rel = {p.relative_to(bj) for p in bj.rglob("*.java")}
feature_rel = {p.relative_to(fj) for p in fj.rglob("*.java")}
added = sorted(feature_rel - base_rel)
skip = (
    "com/github/ysbbbbbb/kaleidoscopetavern/client/",
    "com/github/ysbbbbbb/kaleidoscopetavern/compat/",
    "com/github/ysbbbbbb/kaleidoscopetavern/datagen/",
)

# Replace newly-added 1.2 common classes with the Refabricated 26.2 equivalent
# when it is loader-neutral. This keeps NeoForge registration architecture while
# borrowing only the current Minecraft 26.2 method signatures.
for rel in added:
    s = rel.as_posix()
    if s.startswith(skip):
        continue
    rs = rj / rel
    if not rs.exists():
        continue
    txt = rs.read_text(encoding="utf-8")
    if "net.fabricmc." in txt:
        continue

    # NeoForge's registries in our scaffold are DeferredHolder/Supplier based.
    # Refabricated's are direct values, so unwrap only the registry families
    # whose call sites require the concrete registered object.
    for prefix in [
        "ModBlocks", "ModItems", "ModDataComponents",
        "ModSounds", "ModParticles", "ModRecipes"
    ]:
        txt = re.sub(
            rf"\b{prefix}\.([A-Z][A-Z0-9_]*)(?!\.get\(\))",
            rf"{prefix}.\1.get()",
            txt
        )

    dst = wj / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(txt, encoding="utf-8")

# Refabricated carries small NeoForge-derived compatibility helpers rewritten for
# 26.2's ValueInput/ValueOutput APIs. They are loader-neutral and avoid depending
# on the removed legacy ItemStackHandler NBT signatures.
neo_util = rj / "com/github/ysbbbbbb/kaleidoscopetavern/util/neo"
if neo_util.exists():
    for src in neo_util.glob("*.java"):
        txt = src.read_text(encoding="utf-8")
        if "net.fabricmc." in txt:
            continue
        dst = wj / "com/github/ysbbbbbb/kaleidoscopetavern/util/neo" / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(txt, encoding="utf-8")

# Drink effect reload listener is pure Minecraft API in the 26.2 reference.
for relstr in [
    "com/github/ysbbbbbb/kaleidoscopetavern/datamap/data/DrinkEffectData.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/datamap/resources/DrinkEffectDataReloadListener.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/util/CocktailEffectHelper.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/item/ShakerItem.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/crafting/recipe/ShakerRecipe.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/block/brew/PotionBottleBlock.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/block/mixology/GlasswareBlock.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/api/client/IModelModifyRotationAfterBake.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/api/entity/PlayerExtraData.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/effect/ArdentHeatEffect.java",
]:
    src = rj / relstr
    if src.exists():
        dst = wj / relstr
        dst.parent.mkdir(parents=True, exist_ok=True)
        txt = src.read_text(encoding="utf-8")
        for prefix in ["ModBlocks", "ModItems", "ModDataComponents", "ModSounds", "ModParticles", "ModRecipes"]:
            txt = re.sub(rf"\b{prefix}\.([A-Z][A-Z0-9_]*)(?!\.get\(\))", rf"{prefix}.\1.get()", txt)
        dst.write_text(txt, encoding="utf-8")

# Pull only missing helper methods/fields from the 26.2 reference utilities.
# Copying the whole utility classes would replace NeoForge-specific ItemStackHandler types.
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/util/ItemUtils.java"
src = rj / "com/github/ysbbbbbb/kaleidoscopetavern/util/ItemUtils.java"
if p.exists() and src.exists():
    t = p.read_text(encoding="utf-8")
    rt = src.read_text(encoding="utf-8")
    if "giveItemToPlayer(Player player, ItemStack stack)" not in t:
        start = rt.index("    public static void giveItemToPlayer(Player player, ItemStack stack)")
        end = rt.index("    public static ItemStack insertItem(", start)
        t = t.rsplit("}", 1)[0] + "\n" + rt[start:end] + "}\n"
        p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/util/ColorUtils.java"
src = rj / "com/github/ysbbbbbb/kaleidoscopetavern/util/ColorUtils.java"
if p.exists() and src.exists():
    # ColorUtils is loader-neutral; unlike ItemUtils it does not alter NeoForge inventory types.
    p.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/item/BottleBlockItem.java"
src = rj / "com/github/ysbbbbbb/kaleidoscopetavern/item/BottleBlockItem.java"
if p.exists() and src.exists():
    t = p.read_text(encoding="utf-8")
    rt = src.read_text(encoding="utf-8")
    if "isValidForShaker(ItemStack stack)" not in t:
        start = rt.index("    public static boolean isValidForShaker(ItemStack stack)")
        end = rt.index("\n    public ", start + 5)
        t = t[:t.rfind("}")] + "\n" + rt[start:end] + "\n}\n"
        p.write_text(t, encoding="utf-8")

# Complete imports/constants needed by the selectively copied 1.2 helper methods.
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/util/ItemUtils.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    imports = """import com.github.ysbbbbbb.kaleidoscopetavern.util.neo.IItemHandler;
import com.github.ysbbbbbb.kaleidoscopetavern.util.neo.PlayerMainInvWrapper;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.level.Level;
"""
    if "util.neo.IItemHandler" not in t:
        t = t.replace("package com.github.ysbbbbbb.kaleidoscopetavern.util;\n",
                      "package com.github.ysbbbbbb.kaleidoscopetavern.util;\n\n" + imports)
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/item/BottleBlockItem.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "MIN_BREW_LEVEL_FOR_SHAKER" not in t.split("public static boolean isValidForShaker", 1)[0]:
        t = t.replace('public static final String BREW_LEVEL_KEY = "BrewLevel";',
                      'public static final String BREW_LEVEL_KEY = "BrewLevel";\n    public static final int MIN_BREW_LEVEL_FOR_SHAKER = 4;')
    p.write_text(t, encoding="utf-8")

# ShakerBlockEntity uses NeoForge's ItemStackHandler; use NeoForge's matching helper.
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/blockentity/mixology/ShakerBlockEntity.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "ItemHandlerHelper" not in t:
        t = t.replace("import net.neoforged.neoforge.items.ItemStackHandler;",
                      "import net.neoforged.neoforge.items.ItemStackHandler;\nimport net.neoforged.neoforge.items.ItemHandlerHelper;")
    t = t.replace("ItemUtils.insertItemStacked(storage, copy, false)",
                  "ItemHandlerHelper.insertItemStacked(storage, copy, false)")
    p.write_text(t, encoding="utf-8")

# Finish helper compatibility without replacing NeoForge classes.
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/util/ItemUtils.java"
src = rj / "com/github/ysbbbbbb/kaleidoscopetavern/util/ItemUtils.java"
if p.exists() and src.exists():
    t = p.read_text(encoding="utf-8")
    rt = src.read_text(encoding="utf-8")
    if "public static ItemStack insertItem(IItemHandler" not in t:
        start = rt.index("    public static ItemStack insertItem(IItemHandler")
        end = rt.rfind("\n}")
        t = t.rsplit("}", 1)[0] + "\n" + rt[start:end] + "\n}\n"
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/item/BottleBlockItem.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "public static final int MIN_BREW_LEVEL_FOR_SHAKER" not in t:
        idx = t.index("public class BottleBlockItem") + len("public class BottleBlockItem")
        brace = t.index("{", idx)
        t = t[:brace+1] + "\n    public static final int MIN_BREW_LEVEL_FOR_SHAKER = 4;" + t[brace+1:]
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/blockentity/mixology/ShakerBlockEntity.java"
if p.exists():
    t = p.read_text(encoding="utf-8").replace(
        "ItemHandlerHelper.insertItemStacked(storage, copy, false)",
        "net.neoforged.neoforge.items.ItemHandlerHelper.insertItemStacked(storage, copy, false)")
    p.write_text(t, encoding="utf-8")

# Compatibility accessors keep legacy NeoForge resolver code working on the 26.2 data model.
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/datamap/data/DrinkEffectData.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "entriesForLevel(int brewLevel)" not in t:
        pos = t.index("\n    /**", t.index("public record DrinkEffectData"))
        compat = """
    public List<Entry> entriesForLevel(int brewLevel) {
        if (effects.isEmpty()) return List.of();
        int index = Math.max(0, Math.min(brewLevel, effects.size()) - 1);
        return effects.get(index);
    }

"""
        t = t[:pos] + "\n" + compat + t[pos:]
    if "durationTicks()" not in t:
        marker2 = "    public record Entry(Holder<MobEffect> effect, int duration, int amplifier, float probability) {"
        t = t.replace(marker2, marker2 + "\n        public int durationTicks() { return duration * 20; }")
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/network/message/DrinkEffectSyncS2CMessage.java"
if p.exists():
    t = p.read_text(encoding="utf-8").replace("data.item().value()", "data.item()")
    p.write_text(t, encoding="utf-8")

# Small 26.2 compatibility fixes that preserve the NeoForge implementation.
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/init/register/DatapackReloadListenerEvent.java"
if p.exists():
    t = p.read_text(encoding="utf-8").replace("AddReloadListenerEvent", "AddServerReloadListenersEvent")
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/datamap/data/DrinkEffectData.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "DIRECT_CODEC" not in t:
        pos = t.index("public static final Codec<DrinkEffectData> CODEC")
        t = t[:pos] + "public static final Codec<DrinkEffectData> DIRECT_CODEC = CODEC;\n    " + t[pos:]
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/event/VanillaBottlePlaceEvent.java"
if p.exists():
    t = p.read_text(encoding="utf-8").replace(
        "InteractionResult.sidedSuccess(level.isClientSide())",
        "(level.isClientSide() ? InteractionResult.SUCCESS : InteractionResult.SUCCESS_SERVER)")
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/block/AbstractStorageBlock.java"
if p.exists():
    t = p.read_text(encoding="utf-8").replace(
        "drink.makeThrownPotion(level, shootPos.x(), shootPos.y(), shootPos.z(), brewLevel, null, movement);",
        "drink.makeThrownPotion(level, shootPos.x(), shootPos.y(), shootPos.z(), brewLevel, null);")
    p.write_text(t, encoding="utf-8")

# Complete focused compatibility shims discovered by CI.
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/datamap/data/DrinkEffectData.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace("public static final Codec<DrinkEffectData> DIRECT_CODEC = CODEC;\n    public static final Codec<DrinkEffectData> CODEC",
                  "public static final Codec<DrinkEffectData> CODEC")
    if "public static final Codec<DrinkEffectData> DIRECT_CODEC = CODEC;" not in t:
        needle = ").apply(instance, DrinkEffectData::new));"
        t = t.replace(needle, needle + "\n\n    public static final Codec<DrinkEffectData> DIRECT_CODEC = CODEC;", 1)
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/init/register/DatapackReloadListenerEvent.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace("event.addListener(new DrinkEffectDataReloadListener());",
                  'event.addListener(net.minecraft.resources.Identifier.fromNamespaceAndPath("kaleidoscope_tavern", "drink_effect"), new DrinkEffectDataReloadListener());')
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/block/brew/BottleBlock.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "SIMPLE_BOTTLE_SHAPE" not in t:
        cls = t.index("{", t.index("public class BottleBlock"))
        t = t[:cls+1] + "\n    public static final net.minecraft.world.phys.shapes.VoxelShape SIMPLE_BOTTLE_SHAPE = net.minecraft.world.level.block.Block.box(5, 0, 5, 11, 10, 11);" + t[cls+1:]
    if "static BottleBlock simpleBottle" not in t:
        pos = t.rfind("}")
        t = t[:pos] + "\n    public static BottleBlock simpleBottle(net.minecraft.world.level.block.state.BlockBehaviour.Properties properties) {\n        return new BottleBlock(properties, false);\n    }\n" + t[pos:]
    p.write_text(t, encoding="utf-8")

# Final focused 1.2 compatibility batch.
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/config/GeneralConfig.java"
src = feature / "src/main/java/com/github/ysbbbbbb/kaleidoscopetavern/config/GeneralConfig.java"
if p.exists() and src.exists():
    p.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/block/brew/PotionBottleBlock.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace("super(properties, BottleBlock.SIMPLE_BOTTLE_SHAPE);", "super(properties, false);")
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/blockentity/mixology/ShakerBlockEntity.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    old = "net.neoforged.neoforge.items.ItemHandlerHelper.insertItemStacked(storage, copy, false);"
    new = """for (int slot = 0; slot < storage.getSlots() && !copy.isEmpty(); slot++) {
            copy = storage.insertItem(slot, copy, false);
        }"""
    t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")

p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/blockentity/deco/IncenseBlockEntity.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    old = "zombieVillager.startConverting(null, 60);"
    new = """try {
                    var method = zombieVillager.getClass().getDeclaredMethod("startConverting", java.util.UUID.class, int.class);
                    method.setAccessible(true);
                    method.invoke(zombieVillager, null, 60);
                } catch (ReflectiveOperationException exception) {
                    throw new IllegalStateException("Unable to start zombie villager conversion", exception);
                }"""
    t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")

# Do not globally rewrite registry references: some references are already concrete
# values or appear in declarations. Targeted copied classes above are adapted separately.

# Remove package-level annotations deleted from Minecraft 26.2.
for relstr in [
    "com/github/ysbbbbbb/kaleidoscopetavern/block/package-info.java",
    "com/github/ysbbbbbb/kaleidoscopetavern/block/mixology/package-info.java",
]:
    p = wj / relstr
    if p.exists():
        txt = p.read_text(encoding="utf-8")
        txt = txt.replace("@MethodsReturnNonnullByDefault\n", "")
        txt = txt.replace("import net.minecraft.MethodsReturnNonnullByDefault;\n", "")
        p.write_text(txt, encoding="utf-8")

# ---------- NeoForge 26.2 registry additions ----------

# Data components
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/init/ModDataComponents.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "DrinkEffectData" not in t:
        t = t.replace(
            "import com.github.ysbbbbbb.kaleidoscopetavern.KaleidoscopeTavern;",
            "import com.github.ysbbbbbb.kaleidoscopetavern.KaleidoscopeTavern;\n"
            "import com.github.ysbbbbbb.kaleidoscopetavern.datamap.data.DrinkEffectData;\n"
            "import com.github.ysbbbbbb.kaleidoscopetavern.item.ShakerItem;"
        )
        t = t.replace("import java.util.function.Supplier;", "import java.util.List;\nimport java.util.function.Supplier;")
    if "SHAKER_RESULT" not in t:
        insert = '''
    public static final Supplier<DataComponentType<ShakerItem.Result>> SHAKER_RESULT = DATA_COMPONENT_TYPES.register("shaker_result", () ->
            DataComponentType.<ShakerItem.Result>builder()
                    .persistent(ShakerItem.Result.CODEC)
                    .networkSynchronized(ShakerItem.Result.STREAM_CODEC)
                    .build());

    public static final Supplier<DataComponentType<List<DrinkEffectData.Entry>>> SIGNATURE_COCKTAIL_EFFECTS = DATA_COMPONENT_TYPES.register("signature_cocktail_effects", () ->
            DataComponentType.<List<DrinkEffectData.Entry>>builder()
                    .persistent(Codec.list(DrinkEffectData.Entry.ENTRY_CODEC))
                    .networkSynchronized(DrinkEffectData.Entry.STREAM_CODEC.apply(ByteBufCodecs.list()))
                    .build());

    public static final Supplier<DataComponentType<Integer>> SIGNATURE_COCKTAIL_COLOR = DATA_COMPONENT_TYPES.register("signature_cocktail_color", () ->
            DataComponentType.<Integer>builder()
                    .persistent(Codec.INT)
                    .networkSynchronized(ByteBufCodecs.VAR_INT)
                    .build());
'''
        t = t.rsplit("}", 1)[0] + insert + "}\n"
    p.write_text(t, encoding="utf-8")

# Particles
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/init/ModParticles.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "SAKURA_INCENSE_PARTICLE" not in t:
        insert = '''
    Supplier<SimpleParticleType> SAKURA_INCENSE_PARTICLE = PARTICLES.register("sakura_incense", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> PINE_INCENSE_PARTICLE = PARTICLES.register("pine_incense", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> GINKGO_INCENSE_PARTICLE = PARTICLES.register("ginkgo_incense", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> SPORE_INCENSE_PARTICLE = PARTICLES.register("spore_incense", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> CATNIP_INCENSE_PARTICLE = PARTICLES.register("catnip_incense", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> SNOW_INCENSE_PARTICLE = PARTICLES.register("snow_incense", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> BUTTERFLY_INCENSE_PARTICLE = PARTICLES.register("butterfly_incense", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> FIREFLY_INCENSE_PARTICLE = PARTICLES.register("firefly_incense", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> PINE_INCENSE_LARGE_PARTICLE = PARTICLES.register("pine_incense_large", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> GINKGO_INCENSE_LARGE_PARTICLE = PARTICLES.register("ginkgo_incense_large", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> CATNIP_INCENSE_LARGE_PARTICLE = PARTICLES.register("catnip_incense_large", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> SNOW_INCENSE_LARGE_PARTICLE = PARTICLES.register("snow_incense_large", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> BUTTERFLY_INCENSE_LARGE_PARTICLE = PARTICLES.register("butterfly_incense_large", () -> new SimpleParticleType(false));
    Supplier<SimpleParticleType> FIREFLY_INCENSE_LARGE_PARTICLE = PARTICLES.register("firefly_incense_large", () -> new SimpleParticleType(false));
'''
        t = t.rsplit("}", 1)[0] + insert + "}\n"
    p.write_text(t, encoding="utf-8")

# Sounds
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/init/ModSounds.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "SHAKER_SHAKING" not in t:
        marker = '    public static final Supplier<SoundEvent> EFFECT_VISION = registerSound("effect.vision");'
        t = t.replace(marker, marker + '''
    public static final Supplier<SoundEvent> HOLDER_POP = registerSound("block.holder.pop");
    public static final Supplier<SoundEvent> SHAKER_SHAKING = registerSound("item.shaker.shaking");
    public static final Supplier<SoundEvent> SHAKER_END = registerSound("item.shaker.end");''')
    p.write_text(t, encoding="utf-8")

# Tags needed by new storage/mixology/effects.
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/init/tag/TagMod.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "COCKTAIL_INGREDIENT" not in t:
        insert = '''
    TagKey<Block> CAN_GROW_GRAPE = blockTag("can_grow_grape");
    TagKey<Block> CAN_GROW_ICE_GRAPE = blockTag("can_grow_ice_grape");
    TagKey<Block> CAN_GROW_GOLD_GRAPE = blockTag("can_grow_gold_grape");
    TagKey<Block> ARDENT_HEAT_BREAKABLE = blockTag("ardent_heat_breakable");

    TagKey<Item> BAR_CABINET_IRREGULAR = itemTag("bar_cabinet_irregular");
    TagKey<Item> CELLAR_CABINET_BLOCKLIST = itemTag("cellar_cabinet_blocklist");
    TagKey<Item> TILTED_RACK_BLOCKLIST = itemTag("tilted_rack_blocklist");
    TagKey<Item> CIRCULAR_RACK_BLOCKLIST = itemTag("circular_rack_blocklist");
    TagKey<Item> HOLDER_BLOCKLIST = itemTag("holder_blocklist");
    TagKey<Item> COCKTAIL_INGREDIENT = itemTag("cocktail_ingredient");
    TagKey<Item> COCKTAIL_INGREDIENT_BLACK = itemTag("cocktail_ingredient/black");
    TagKey<Item> COCKTAIL_INGREDIENT_DARK_BLUE = itemTag("cocktail_ingredient/dark_blue");
    TagKey<Item> COCKTAIL_INGREDIENT_DARK_GREEN = itemTag("cocktail_ingredient/dark_green");
    TagKey<Item> COCKTAIL_INGREDIENT_DARK_AQUA = itemTag("cocktail_ingredient/dark_aqua");
    TagKey<Item> COCKTAIL_INGREDIENT_DARK_RED = itemTag("cocktail_ingredient/dark_red");
    TagKey<Item> COCKTAIL_INGREDIENT_DARK_PURPLE = itemTag("cocktail_ingredient/dark_purple");
    TagKey<Item> COCKTAIL_INGREDIENT_GOLD = itemTag("cocktail_ingredient/gold");
    TagKey<Item> COCKTAIL_INGREDIENT_GRAY = itemTag("cocktail_ingredient/gray");
    TagKey<Item> COCKTAIL_INGREDIENT_DARK_GRAY = itemTag("cocktail_ingredient/dark_gray");
    TagKey<Item> COCKTAIL_INGREDIENT_BLUE = itemTag("cocktail_ingredient/blue");
    TagKey<Item> COCKTAIL_INGREDIENT_GREEN = itemTag("cocktail_ingredient/green");
    TagKey<Item> COCKTAIL_INGREDIENT_AQUA = itemTag("cocktail_ingredient/aqua");
    TagKey<Item> COCKTAIL_INGREDIENT_RED = itemTag("cocktail_ingredient/red");
    TagKey<Item> COCKTAIL_INGREDIENT_LIGHT_PURPLE = itemTag("cocktail_ingredient/light_purple");
    TagKey<Item> COCKTAIL_INGREDIENT_YELLOW = itemTag("cocktail_ingredient/yellow");
    TagKey<Item> COCKTAIL_INGREDIENT_WHITE = itemTag("cocktail_ingredient/white");
    TagKey<EntityType<?>> TOMB_RAIDER_DISARMABLE = entityTag("tomb_raider_disarmable");
'''
        pos = t.index("    static TagKey<Item> itemTag")
        t = t[:pos] + insert + "\n" + t[pos:]
    p.write_text(t, encoding="utf-8")

# Blocks and block entities
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/init/ModBlocks.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    t = t.replace(
        "import com.github.ysbbbbbb.kaleidoscopetavern.block.deco.*;",
        "import com.github.ysbbbbbb.kaleidoscopetavern.block.deco.*;\n"
        "import com.github.ysbbbbbb.kaleidoscopetavern.block.mixology.*;"
    )
    t = t.replace(
        "import com.github.ysbbbbbb.kaleidoscopetavern.blockentity.deco.BarStoolBlockEntity;\n"
        "import com.github.ysbbbbbb.kaleidoscopetavern.blockentity.deco.ChalkboardBlockEntity;\n"
        "import com.github.ysbbbbbb.kaleidoscopetavern.blockentity.deco.SandwichBlockEntity;",
        "import com.github.ysbbbbbb.kaleidoscopetavern.blockentity.deco.*;\n"
        "import com.github.ysbbbbbb.kaleidoscopetavern.blockentity.mixology.*;"
    )
    if "net.minecraft.core.particles.ParticleTypes;" not in t:
        t = t.replace("import net.minecraft.core.registries.BuiltInRegistries;",
                      "import net.minecraft.core.particles.ParticleTypes;\nimport net.minecraft.core.registries.BuiltInRegistries;\nimport net.minecraft.core.registries.Registries;")
        t = t.replace("import net.minecraft.world.item.DyeColor;",
                      "import net.minecraft.resources.Identifier;\nimport net.minecraft.resources.ResourceKey;\nimport net.minecraft.world.item.DyeColor;")
        t = t.replace("import net.minecraft.world.level.block.Block;",
                      "import net.minecraft.world.level.block.Block;\nimport net.minecraft.world.level.block.state.BlockBehaviour;")
    if "EMPTY_GLASSWARE = BLOCKS.register" not in t:
        fields = '''
    // 1.2.0 mixology/deco/storage additions
    DeferredBlock<Block> EMPTY_GLASSWARE = BLOCKS.register("empty_glassware", id -> new GlasswareBlock(props(id)));
    DeferredBlock<Block> GLASSWARE_HOLDER = BLOCKS.register("glassware_holder", id -> new GlasswareHolderBlock(props(id)));
    DeferredBlock<Block> SIGNATURE_COCKTAIL = BLOCKS.register("signature_cocktail", id -> new SignatureCocktailBlock(props(id)));
    DeferredBlock<Block> MYSTERY_COCKTAIL = BLOCKS.register("mystery_cocktail", id -> new MysteryCocktailBlock(props(id)));
    DeferredBlock<Block> WHITE_LADY = BLOCKS.register("white_lady", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> EMERALD = BLOCKS.register("emerald", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> BRASS_HEART = BLOCKS.register("brass_heart", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> GODFATHER = BLOCKS.register("godfather", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> GRASSHOPPER = BLOCKS.register("grasshopper", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> SCREWDRIVER = BLOCKS.register("screwdriver", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> MOJITO = BLOCKS.register("mojito", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> ALLIUM_GARDEN = BLOCKS.register("allium_garden", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> DEPTH_CHARGE = BLOCKS.register("depth_charge", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> NETHER_SPECIAL = BLOCKS.register("nether_special", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> BLOODY_MARY = BLOCKS.register("bloody_mary", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> SCULK_SPECIAL = BLOCKS.register("sculk_special", id -> new CocktailBlock(props(id)));
    DeferredBlock<Block> POTION_BOTTLE = BLOCKS.register("potion_bottle", id -> new PotionBottleBlock(props(id)));
    DeferredBlock<Block> XP_BOTTLE = BLOCKS.register("xp_bottle", id -> BottleBlock.simpleBottle(props(id)));
    DeferredBlock<Block> BELL_PENDANT_LAMP = BLOCKS.register("bell_pendant_lamp", id -> new PendantLampBlock(props(id)));
    DeferredBlock<Block> YELLOW_PENDANT_LAMP = BLOCKS.register("yellow_pendant_lamp", id -> new PendantLampBlock(props(id)));
    DeferredBlock<Block> BLUE_PENDANT_LAMP = BLOCKS.register("blue_pendant_lamp", id -> new PendantLampBlock(props(id)));
    DeferredBlock<Block> SAKURA_INCENSE = BLOCKS.register("sakura_incense", id -> new IncenseBlock(props(id), () -> ModParticles.SAKURA_INCENSE_PARTICLE.get(), () -> ParticleTypes.CHERRY_LEAVES));
    DeferredBlock<Block> PINE_INCENSE = BLOCKS.register("pine_incense", id -> new IncenseBlock(props(id), () -> ModParticles.PINE_INCENSE_PARTICLE.get(), () -> ModParticles.PINE_INCENSE_LARGE_PARTICLE.get()));
    DeferredBlock<Block> GINKGO_INCENSE = BLOCKS.register("ginkgo_incense", id -> new IncenseBlock(props(id), () -> ModParticles.GINKGO_INCENSE_PARTICLE.get(), () -> ModParticles.GINKGO_INCENSE_LARGE_PARTICLE.get()));
    DeferredBlock<Block> SPORE_INCENSE = BLOCKS.register("spore_incense", id -> new IncenseBlock(props(id), () -> ModParticles.SPORE_INCENSE_PARTICLE.get(), () -> ParticleTypes.SPORE_BLOSSOM_AIR));
    DeferredBlock<Block> CATNIP_INCENSE = BLOCKS.register("catnip_incense", id -> new IncenseBlock(props(id), () -> ModParticles.CATNIP_INCENSE_PARTICLE.get(), () -> ModParticles.CATNIP_INCENSE_LARGE_PARTICLE.get()));
    DeferredBlock<Block> SNOW_INCENSE = BLOCKS.register("snow_incense", id -> new IncenseBlock(props(id), () -> ModParticles.SNOW_INCENSE_PARTICLE.get(), () -> ModParticles.SNOW_INCENSE_LARGE_PARTICLE.get()));
    DeferredBlock<Block> BUTTERFLY_INCENSE = BLOCKS.register("butterfly_incense", id -> new IncenseBlock(props(id), () -> ModParticles.BUTTERFLY_INCENSE_PARTICLE.get(), () -> ModParticles.BUTTERFLY_INCENSE_LARGE_PARTICLE.get()));
    DeferredBlock<Block> FIREFLY_INCENSE = BLOCKS.register("firefly_incense", id -> new IncenseBlock(props(id), () -> ModParticles.FIREFLY_INCENSE_PARTICLE.get(), () -> ModParticles.FIREFLY_INCENSE_LARGE_PARTICLE.get(), -0.67, 5.33));
    DeferredBlock<Block> CELLAR_CABINET = BLOCKS.register("cellar_cabinet", id -> new CellarCabinetBlock(props(id)));
    DeferredBlock<Block> TILTED_RACK = BLOCKS.register("tilted_rack", id -> new TiltedRackBlock(props(id)));
    DeferredBlock<Block> CIRCULAR_RACK = BLOCKS.register("circular_rack", id -> new CircularRackBlock(props(id)));
    DeferredBlock<Block> HOLDER = BLOCKS.register("holder", id -> new HolderBlock(props(id)));
    DeferredBlock<Block> SHAKER = BLOCKS.register("shaker", id -> new ShakerBlock(props(id)));

'''
        t = t.replace("    // BlockEntity\n", fields + "    // BlockEntity\n")

    if "CELLAR_CABINET_BE = BLOCK_ENTITIES.register" not in t:
        extra = '''
    Supplier<BlockEntityType<CellarCabinetBlockEntity>> CELLAR_CABINET_BE = BLOCK_ENTITIES.register(
            "cellar_cabinet", () -> new BlockEntityType<>(CellarCabinetBlockEntity::new, CELLAR_CABINET.get()));
    Supplier<BlockEntityType<TiltedRackBlockEntity>> TILTED_RACK_BE = BLOCK_ENTITIES.register(
            "tilted_rack", () -> new BlockEntityType<>(TiltedRackBlockEntity::new, TILTED_RACK.get()));
    Supplier<BlockEntityType<CircularRackBlockEntity>> CIRCULAR_RACK_BE = BLOCK_ENTITIES.register(
            "circular_rack", () -> new BlockEntityType<>(CircularRackBlockEntity::new, CIRCULAR_RACK.get()));
    Supplier<BlockEntityType<HolderBlockEntity>> HOLDER_BE = BLOCK_ENTITIES.register(
            "holder", () -> new BlockEntityType<>(HolderBlockEntity::new, HOLDER.get()));
    Supplier<BlockEntityType<ShakerBlockEntity>> SHAKER_BE = BLOCK_ENTITIES.register(
            "shaker", () -> new BlockEntityType<>(ShakerBlockEntity::new, SHAKER.get()));
    Supplier<BlockEntityType<SignatureCocktailBlockEntity>> SIGNATURE_COCKTAIL_BE = BLOCK_ENTITIES.register(
            "signature_cocktail", () -> new BlockEntityType<>(SignatureCocktailBlockEntity::new, SIGNATURE_COCKTAIL.get()));
    Supplier<BlockEntityType<GlasswareHolderBlockEntity>> GLASSWARE_HOLDER_BE = BLOCK_ENTITIES.register(
            "glassware_holder", () -> new BlockEntityType<>(GlasswareHolderBlockEntity::new, GLASSWARE_HOLDER.get()));
    Supplier<BlockEntityType<PotionBottleBlockEntity>> POTION_BOTTLE_BE = BLOCK_ENTITIES.register(
            "potion_bottle", () -> new BlockEntityType<>(PotionBottleBlockEntity::new, POTION_BOTTLE.get()));
    Supplier<BlockEntityType<IncenseBlockEntity>> INCENSE_BE = BLOCK_ENTITIES.register(
            "incense", () -> new BlockEntityType<>(IncenseBlockEntity::new,
                    SAKURA_INCENSE.get(), PINE_INCENSE.get(), GINKGO_INCENSE.get(), SPORE_INCENSE.get(),
                    CATNIP_INCENSE.get(), SNOW_INCENSE.get(), BUTTERFLY_INCENSE.get(), FIREFLY_INCENSE.get()));

    static BlockBehaviour.Properties props(Identifier id) {
        return BlockBehaviour.Properties.of().setId(ResourceKey.create(Registries.BLOCK, id));
    }
'''
        t = t.rsplit("}", 1)[0] + extra + "}\n"
    p.write_text(t, encoding="utf-8")

# Items
p = wj / "com/github/ysbbbbbb/kaleidoscopetavern/init/ModItems.java"
if p.exists():
    t = p.read_text(encoding="utf-8")
    if "DeferredItem<Item> SHAKER =" not in t:
        insert = '''
    // 1.2.0 items
    DeferredItem<Item> BELL_PENDANT_LAMP = ITEMS.register("bell_pendant_lamp", id -> new BlockItem(ModBlocks.BELL_PENDANT_LAMP.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> YELLOW_PENDANT_LAMP = ITEMS.register("yellow_pendant_lamp", id -> new BlockItem(ModBlocks.YELLOW_PENDANT_LAMP.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> BLUE_PENDANT_LAMP = ITEMS.register("blue_pendant_lamp", id -> new BlockItem(ModBlocks.BLUE_PENDANT_LAMP.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> CELLAR_CABINET = ITEMS.register("cellar_cabinet", id -> new BlockItem(ModBlocks.CELLAR_CABINET.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> TILTED_RACK = ITEMS.register("tilted_rack", id -> new BlockItem(ModBlocks.TILTED_RACK.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> CIRCULAR_RACK = ITEMS.register("circular_rack", id -> new BlockItem(ModBlocks.CIRCULAR_RACK.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> HOLDER = ITEMS.register("holder", id -> new BlockItem(ModBlocks.HOLDER.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> EMPTY_GLASSWARE = ITEMS.register("empty_glassware", id -> new GlasswareBlockItem(ModBlocks.EMPTY_GLASSWARE.get(), itemProps(id)));
    DeferredItem<Item> SIGNATURE_COCKTAIL = ITEMS.register("signature_cocktail", id -> new SignatureCocktailBlockItem(ModBlocks.SIGNATURE_COCKTAIL.get(), itemProps(id)));
    DeferredItem<Item> MYSTERY_COCKTAIL = ITEMS.register("mystery_cocktail", id -> new CocktailBlockItem(ModBlocks.MYSTERY_COCKTAIL.get(), itemProps(id)));
    DeferredItem<Item> WHITE_LADY = ITEMS.register("white_lady", id -> new CocktailBlockItem(ModBlocks.WHITE_LADY.get(), itemProps(id)));
    DeferredItem<Item> EMERALD = ITEMS.register("emerald", id -> new CocktailBlockItem(ModBlocks.EMERALD.get(), itemProps(id)));
    DeferredItem<Item> BRASS_HEART = ITEMS.register("brass_heart", id -> new CocktailBlockItem(ModBlocks.BRASS_HEART.get(), itemProps(id)));
    DeferredItem<Item> GODFATHER = ITEMS.register("godfather", id -> new CocktailBlockItem(ModBlocks.GODFATHER.get(), itemProps(id)));
    DeferredItem<Item> GRASSHOPPER = ITEMS.register("grasshopper", id -> new CocktailBlockItem(ModBlocks.GRASSHOPPER.get(), itemProps(id)));
    DeferredItem<Item> SCREWDRIVER = ITEMS.register("screwdriver", id -> new CocktailBlockItem(ModBlocks.SCREWDRIVER.get(), itemProps(id)));
    DeferredItem<Item> MOJITO = ITEMS.register("mojito", id -> new CocktailBlockItem(ModBlocks.MOJITO.get(), itemProps(id)));
    DeferredItem<Item> ALLIUM_GARDEN = ITEMS.register("allium_garden", id -> new CocktailBlockItem(ModBlocks.ALLIUM_GARDEN.get(), itemProps(id)));
    DeferredItem<Item> DEPTH_CHARGE = ITEMS.register("depth_charge", id -> new CocktailBlockItem(ModBlocks.DEPTH_CHARGE.get(), itemProps(id)));
    DeferredItem<Item> NETHER_SPECIAL = ITEMS.register("nether_special", id -> new CocktailBlockItem(ModBlocks.NETHER_SPECIAL.get(), itemProps(id)));
    DeferredItem<Item> BLOODY_MARY = ITEMS.register("bloody_mary", id -> new CocktailBlockItem(ModBlocks.BLOODY_MARY.get(), itemProps(id)));
    DeferredItem<Item> SCULK_SPECIAL = ITEMS.register("sculk_special", id -> new CocktailBlockItem(ModBlocks.SCULK_SPECIAL.get(), itemProps(id)));
    DeferredItem<Item> SHAKER = ITEMS.register("shaker", id -> new ShakerItem(itemProps(id)));
    DeferredItem<Item> GLASSWARE_HOLDER = ITEMS.register("glassware_holder", id -> new BlockItem(ModBlocks.GLASSWARE_HOLDER.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> SAKURA_INCENSE = ITEMS.register("sakura_incense", id -> new BlockItem(ModBlocks.SAKURA_INCENSE.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> PINE_INCENSE = ITEMS.register("pine_incense", id -> new BlockItem(ModBlocks.PINE_INCENSE.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> GINKGO_INCENSE = ITEMS.register("ginkgo_incense", id -> new BlockItem(ModBlocks.GINKGO_INCENSE.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> SPORE_INCENSE = ITEMS.register("spore_incense", id -> new BlockItem(ModBlocks.SPORE_INCENSE.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> CATNIP_INCENSE = ITEMS.register("catnip_incense", id -> new BlockItem(ModBlocks.CATNIP_INCENSE.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> SNOW_INCENSE = ITEMS.register("snow_incense", id -> new BlockItem(ModBlocks.SNOW_INCENSE.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> BUTTERFLY_INCENSE = ITEMS.register("butterfly_incense", id -> new BlockItem(ModBlocks.BUTTERFLY_INCENSE.get(), itemProps(id).useBlockDescriptionPrefix()));
    DeferredItem<Item> FIREFLY_INCENSE = ITEMS.register("firefly_incense", id -> new BlockItem(ModBlocks.FIREFLY_INCENSE.get(), itemProps(id).useBlockDescriptionPrefix()));

    static Item.Properties itemProps(net.minecraft.resources.Identifier id) {
        return new Item.Properties().setId(ResourceKey.create(Registries.ITEM, id));
    }
'''
        t = t.rsplit("}", 1)[0] + insert + "}\n"
    p.write_text(t, encoding="utf-8")

print("Applied fast merge v2: 26.2 reference classes + NeoForge registry additions")
