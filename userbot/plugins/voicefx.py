# Voice changer — reply to a voice note / audio / video with an effect, get a voice note back.
#
#   .vfx chipmunk      .vfx deep      .vfx robot      .vfx list

import asyncio
import os
import shutil
import tempfile

from telethon.tl import types

from userbot import catub

from ..Config import Config
from ..core.managers import edit_delete, edit_or_reply

plugin_category = "fun"

MAX_SECONDS = 300


def _pitch(p: float, speed: float = 1.0) -> str:
    """Shift pitch by factor p, with overall playback speed `speed` (atempo kept within 0.5-2)."""
    tempo = speed / p
    chain = []
    while tempo > 2.0:
        chain.append("atempo=2.0")
        tempo /= 2.0
    while tempo < 0.5:
        chain.append("atempo=0.5")
        tempo /= 0.5
    chain.append(f"atempo={tempo:.4f}")
    return f"asetrate=48000*{p},aresample=48000," + ",".join(chain)


EFFECTS = {
    "chipmunk": ("🐿", _pitch(1.6, 1.1)),
    "baby": ("👶", _pitch(1.35)),
    "deep": ("🧔", _pitch(0.72)),
    "monster": ("👹", _pitch(0.55, 0.9) + ",aecho=0.8:0.6:40:0.3"),
    "robot": ("🤖", "afftfilt=real='hypot(re,im)*sin(0)':imag='hypot(re,im)*cos(0)':win_size=512:overlap=0.75"),
    "alien": ("👽", "vibrato=f=7:d=0.5," + _pitch(1.25)),
    "echo": ("🗣", "aecho=0.8:0.88:120|240:0.45|0.25"),
    "cave": ("🕳", "aecho=0.8:0.9:500|1000|1500:0.4|0.3|0.2"),
    "radio": ("📻", "highpass=f=400,lowpass=f=3200,acrusher=bits=10:mix=0.2,volume=1.6"),
    "phone": ("☎️", "highpass=f=500,lowpass=f=2600,volume=1.5"),
    "drunk": ("🥴", "vibrato=f=3:d=0.8,atempo=0.85"),
    "whisper": (
        "🤫",
        "afftfilt=real='hypot(re,im)*cos((random(0)*2-1)*2*3.14)':"
        "imag='hypot(re,im)*sin((random(1)*2-1)*2*3.14)':win_size=128:overlap=0.8",
    ),
    "fast": ("⏩", "atempo=1.5"),
    "slow": ("🐢", "atempo=0.7"),
    "reverse": ("🔁", "areverse"),
    "bass": ("🔊", "bass=g=14,volume=0.8,alimiter"),
    "8d": ("🎧", "apulsator=hz=0.125"),
}


async def run_ffmpeg(src: str, dst: str, filt: str):
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-vn",
        "-af", filt, "-t", str(MAX_SECONDS), "-ac", "1" if "apulsator" not in filt else "2",
        "-ar", "48000", "-c:a", "libopus", "-b:a", "64k", dst,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    return proc.returncode, err.decode(errors="replace")[-400:]


@catub.cat_cmd(
    pattern=r"vfx(?:\s+(\S+))?$",
    command=("vfx", plugin_category),
    info={
        "header": "Voice changer: reply to a voice note, audio, video or round video.",
        "description": "Sends the result back as a voice note. Max 5 minutes of audio.",
        "usage": ["{tr}vfx <effect>  (reply)", "{tr}vfx list"],
        "examples": ["{tr}vfx chipmunk", "{tr}vfx robot", "{tr}vfx 8d"],
    },
)
async def vfx_cmd(event):
    "Voice changer."
    effect = (event.pattern_match.group(1) or "").lower()
    if not effect or effect == "list" or effect not in EFFECTS:
        listing = "  ".join(f"{icon}`{name}`" for name, (icon, _) in EFFECTS.items())
        head = "" if not effect or effect == "list" else f"Unknown effect `{effect}`.\n\n"
        return await edit_or_reply(event, f"{head}🎙 **Voice effects**\n\n{listing}\n\nReply to audio: `{Config.COMMAND_HAND_LER}vfx robot`")

    reply = await event.get_reply_message()
    if not reply or not reply.media or not (reply.voice or reply.audio or reply.video or reply.video_note or (
        isinstance(reply.media, types.MessageMediaDocument) and (reply.file.mime_type or "").startswith(("audio/", "video/"))
    )):
        return await edit_delete(event, "`Reply to a voice note, audio or video.`", 6)
    if shutil.which("ffmpeg") is None:
        return await edit_delete(event, "`ffmpeg isn't installed on this host.`", 6)

    status = await edit_or_reply(event, f"`{EFFECTS[effect][0]} applying {effect}…`")
    tmp = tempfile.mkdtemp(dir=Config.TMP_DOWNLOAD_DIRECTORY)
    try:
        src = await event.client.download_media(reply.media, file=tmp + os.sep)
        if not src:
            return await status.edit("Couldn't download that file.")
        dst = os.path.join(tmp, f"{effect}.ogg")
        code, err = await run_ffmpeg(src, dst, EFFECTS[effect][1])
        if code != 0 or not os.path.exists(dst):
            return await status.edit(f"ffmpeg failed:\n`{err.strip() or code}`")
        await event.client.send_file(
            event.chat_id, dst, voice_note=True, reply_to=reply.id,
        )
        await status.delete()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
