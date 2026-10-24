# Native renderer and startup attribution

The bitmap glyphs and VideoOut tile-address mapping in monitor_raster.cpp and
tiled_frame.h are adapted from PS5-Vulkan-Inference src/demo_renderer.cpp at
872cc1264ad8ba5d6b888b092968fa5858a38c58, inherited through Mihawk-99/PS5_Vulkan
from BlackBearReloaded's native application boilerplate. Original copyright and
GPL-3.0-or-later notices are preserved in the adapted files. The license text is
included here. The local native format tool and native CRT also retain their
external source notices and recorded identities. No runtime binary is committed.

native/app/native_crt.cpp is derived from tooling/native/app_crt.cpp at the same
pinned revision. It preserves the original IEEE/platform startup, initializer
order and main-return hook, adding durable records around each initializer.
It retains BlackBearReloaded's copyright and GPL-3.0-or-later license. The build
receipt records the exact original CRT digest alongside the application source.
