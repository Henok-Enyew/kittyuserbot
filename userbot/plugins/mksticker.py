# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~# CatUserBot #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
# Sticker Creation Plugin with Background Removal
# .mkstcr / .makestcr - Create sticker from image with background removed
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#

import os
import tempfile
from io import BytesIO

from PIL import Image
from rembg import remove
from telethon.tl.types import DocumentAttributeSticker, InputStickerSetEmpty

from userbot import catub
from userbot.Config import Config
from userbot.core.managers import edit_delete, edit_or_reply

plugin_category = "tools"


async def _download_image(event, message):
    """Download image from message to temp file."""
    try:
        # Create temp directory if it doesn't exist
        tmp_dir = getattr(Config, 'TMP_DOWNLOAD_DIRECTORY', tempfile.gettempdir())
        os.makedirs(tmp_dir, exist_ok=True)
        
        # Download to temp file
        temp_file = os.path.join(tmp_dir, f"input_{event.id}.jpg")
        await event.client.download_media(message, temp_file)
        return temp_file
    except Exception as e:
        raise Exception(f"Failed to download image: {str(e)}")


async def _remove_background(input_path, output_path):
    """Remove background from image using rembg."""
    try:
        # Read input image
        with open(input_path, 'rb') as f:
            input_data = f.read()
        
        # Remove background
        output_data = remove(input_data)
        
        # Save output
        with open(output_path, 'wb') as f:
            f.write(output_data)
        
        return True
    except Exception as e:
        raise Exception(f"Background removal failed: {str(e)}")


async def _convert_to_sticker(input_path, output_path):
    """Convert image to WebP sticker format (512x512)."""
    try:
        # Open image
        img = Image.open(input_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Resize to fit 512x512 while maintaining aspect ratio
        img.thumbnail((512, 512), Image.Resampling.LANCZOS)
        
        # Create a new 512x512 transparent image
        sticker = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        
        # Paste the resized image in the center
        offset = ((512 - img.width) // 2, (512 - img.height) // 2)
        sticker.paste(img, offset, img)
        
        # Save as WebP
        sticker.save(output_path, 'WEBP', quality=95)
        
        return True
    except Exception as e:
        raise Exception(f"Conversion to sticker format failed: {str(e)}")


@catub.cat_cmd(
    pattern="(?:mkstcr|makestcr)$",
    command=("mkstcr", plugin_category),
    info={
        "header": "Create sticker with background removal",
        "description": (
            "Creates a Telegram sticker from an image with the background automatically removed. "
            "Uses AI to detect and remove the background, then converts to proper sticker format."
        ),
        "usage": [
            "{tr}mkstcr (reply to image)",
            "{tr}makestcr (reply to image)",
        ],
        "examples": [
            "{tr}mkstcr",
            "{tr}makestcr",
        ],
        "note": (
            "Reply to a photo/image to use this command. "
            "The bot will remove the background and create a transparent sticker. "
            "First use may take longer as it downloads the AI model."
        ),
    },
)
async def make_sticker(event):
    """Create sticker from image with background removed."""
    # Check if replying to a message
    if not event.is_reply:
        return await edit_delete(
            event,
            "`Reply to a photo to use this command.`",
            5
        )
    
    # Get replied message
    reply_message = await event.get_reply_message()
    
    # Check if message has photo/image
    if not reply_message.photo and not (reply_message.document and 'image' in reply_message.document.mime_type):
        return await edit_delete(
            event,
            "`This only works on images.`",
            5
        )
    
    # Start processing
    cat_event = await edit_or_reply(event, "`Downloading image...`")
    
    # Temp file paths
    tmp_dir = getattr(Config, 'TMP_DOWNLOAD_DIRECTORY', tempfile.gettempdir())
    input_file = None
    bg_removed_file = None
    sticker_file = None
    
    try:
        # Download image
        input_file = await _download_image(event, reply_message)
        
        # Check file size and resize if too large
        try:
            img = Image.open(input_file)
            width, height = img.size
            max_dimension = max(width, height)
            
            if max_dimension > 2000:
                await cat_event.edit("`Image too large, resizing...`")
                # Resize to max 2000px
                scale = 2000 / max_dimension
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                img.save(input_file)
            img.close()
        except Exception:
            pass  # Continue with original if resize fails
        
        # Remove background
        await cat_event.edit("`Removing background... (this may take a moment)`")
        bg_removed_file = os.path.join(tmp_dir, f"nobg_{event.id}.png")
        await _remove_background(input_file, bg_removed_file)
        
        # Convert to sticker format
        await cat_event.edit("`Converting to sticker format...`")
        sticker_file = os.path.join(tmp_dir, f"sticker_{event.id}.webp")
        await _convert_to_sticker(bg_removed_file, sticker_file)
        
        # Send as sticker
        await cat_event.edit("`Uploading sticker...`")
        await event.client.send_file(
            event.chat_id,
            sticker_file,
            reply_to=reply_message.id,
            attributes=[
                DocumentAttributeSticker(
                    alt="",
                    stickerset=InputStickerSetEmpty()
                )
            ]
        )
        
        # Delete status message
        await cat_event.delete()
        
    except Exception as e:
        error_msg = str(e)
        if "background removal failed" in error_msg.lower():
            await cat_event.edit("`Background removal failed, try a clearer image.`")
        elif "conversion" in error_msg.lower():
            await cat_event.edit("`Failed to convert image to sticker format.`")
        else:
            await cat_event.edit(f"`Error: {error_msg[:200]}`")
    
    finally:
        # Clean up temp files
        for file_path in [input_file, bg_removed_file, sticker_file]:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
