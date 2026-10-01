package com.zhlee.ysmcompat.client;

import com.mojang.blaze3d.vertex.PoseStack;
import net.minecraft.client.gui.render.pip.PictureInPictureRenderer;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.state.gui.pip.PictureInPictureRenderState;

@SuppressWarnings({"rawtypes", "unchecked"})
public final class YsmNoopPipRenderer extends PictureInPictureRenderer<PictureInPictureRenderState> {
    private final Class stateClass;

    public YsmNoopPipRenderer(Class<?> stateClass) {
        this.stateClass = stateClass;
    }

    @Override
    protected void renderToTexture(
            PictureInPictureRenderState renderState,
            PoseStack poseStack,
            SubmitNodeCollector submitNodeCollector
    ) {
        // Probe v0.1 intentionally renders nothing.
        // First target: bypass the removed 26.1 BufferSource constructor/API
        // without changing the original YSM jar.
    }

    @Override
    public Class<PictureInPictureRenderState> getRenderStateClass() {
        return (Class<PictureInPictureRenderState>) stateClass;
    }

    @Override
    protected String getTextureLabel() {
        return "ysm_26_2_compat_probe";
    }
}
