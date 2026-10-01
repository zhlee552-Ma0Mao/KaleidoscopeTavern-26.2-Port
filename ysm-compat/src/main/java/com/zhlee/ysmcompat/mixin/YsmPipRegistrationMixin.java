package com.zhlee.ysmcompat.mixin;

import com.zhlee.ysmcompat.client.YsmNoopPipRenderer;
import net.minecraft.client.renderer.state.gui.pip.PictureInPictureRenderState;
import net.neoforged.neoforge.client.event.RegisterPictureInPictureRenderersEvent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "com.elfmcys.yesstevemodel.oooo0o0oo00O0O0O0ooo0000", remap = false)
public abstract class YsmPipRegistrationMixin {
    private static final String YSM_PIP_STATE =
            "com.elfmcys.yesstevemodel.oo0o0OOoOo0O000OoO00o00o";

    @SuppressWarnings({"rawtypes", "unchecked"})
    @Inject(
            method = "OO0OoO00ooOOo0o00O000OoO",
            at = @At("HEAD"),
            cancellable = true,
            remap = false
    )
    private static void ysmCompat$replaceOldPipRegistration(
            RegisterPictureInPictureRenderersEvent event,
            CallbackInfo ci
    ) {
        try {
            Class<?> rawStateClass = Class.forName(YSM_PIP_STATE, false,
                    YsmPipRegistrationMixin.class.getClassLoader());

            if (!PictureInPictureRenderState.class.isAssignableFrom(rawStateClass)) {
                throw new IllegalStateException("YSM PiP state no longer implements PictureInPictureRenderState");
            }

            Class stateClass = rawStateClass;
            event.register(stateClass, () -> new YsmNoopPipRenderer(stateClass));
            System.out.println("[YSM 26.2 Compat] replaced legacy BufferSource PiP registration");
            ci.cancel();
        } catch (Throwable t) {
            System.err.println("[YSM 26.2 Compat] probe failed while replacing PiP registration");
            t.printStackTrace();
        }
    }
}
