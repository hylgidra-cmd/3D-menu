FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Blender, used headlessly (--background, no display/GPU needed - its own
# Debian package only depends on X11 *client* libraries for dynamic
# linking, not a running X server) to convert a normalized GLB to USDZ for
# iOS Quick Look (utils/glb_to_usdz.py + utils/fix_usdz_textures.py). This
# is the real, only reliable production glTF->USDZ path available - no
# pure-Python library does this; `usd-core` (already in requirements.txt)
# can only read/write USD/USDZ, not import glTF. Blender's glTF importer
# imports numpy from Debian's Python runtime. It is only a recommendation of
# the Blender package, so --no-install-recommends would otherwise leave USDZ
# conversion broken.
# `blender --version` at build time fails the build immediately if the
# headless binary can't even start, instead of discovering that at
# request time in production.
RUN apt-get update \
    && apt-get install -y --no-install-recommends blender python3-numpy \
    && rm -rf /var/lib/apt/lists/* \
    && blender --version
ENV BLENDER_BINARY=/usr/bin/blender

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
