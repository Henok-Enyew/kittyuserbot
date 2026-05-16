# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Copyright (C) 2020-2023 by TgCatUB@Github.

# This file is part of: https://github.com/TgCatUB/catuserbot
# and is released under the "GNU v3.0 License Agreement".

# Please see: https://github.com/TgCatUB/catuserbot/blob/master/LICENSE
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

FROM catub/core:bullseye

# Working directory 
WORKDIR /userbot

# Timezone
ENV TZ=Asia/Kolkata

## Copy files into the Docker image
COPY . .

# Pre-download rembg model to avoid slow first run
RUN python3 -c "from rembg import new_session; new_session('u2net')" || true

ENV PATH="/home/userbot/bin:$PATH"

CMD ["python3","-m","userbot"]
