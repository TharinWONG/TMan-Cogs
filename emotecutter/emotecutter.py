from redbot.core import commands
from PIL import Image, ImageDraw, ImageChops
import io
import discord

class EmoteCutter(commands.Cog):
    """將 3x3 九宮格圖片自動精準切割的插件，支援模式選擇"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cutemotes(self, ctx: commands.Context, mode: str = "1", *, url: str = None):
        """
        用法：
        .cutemotes 1 [圖片/連結] - 普通精準切割（預設）
        .cutemotes 2 [圖片/連結] - 無縫去分界線與 [] 標題（文字完整版）
        """
        target_mode = "1"
        if mode in ["1", "2"]:
            target_mode = mode
        else:
            url = mode if not url else f"{mode} {url}"

        target_image_bytes = None

        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    target_image_bytes = await attachment.read()
                    break
        elif url and url.startswith("http") and url.lower().endswith((".png", ".jpg", ".jpeg")):
            try:
                async with self.bot.session.get(url) as response:
                    if response.status == 200:
                        target_image_bytes = await response.read()
            except Exception as e:
                await ctx.send(f"❌ 無法讀取圖片鏈接：{e}")
                return

        if not target_image_bytes:
            await ctx.send("❌ 請上傳一張 3x3 九宮格圖片 (1050x1024)！格式：`.cutemotes 1` 或 `.cutemotes 2`")
            return

        try:
            input_stream = io.BytesIO(target_image_bytes)
            img = Image.open(input_stream).convert('RGBA')
            img_width, img_height = img.size

            cell_width = img_width / 3
            cell_height = img_height / 3
            cropped_emote_files = []

            for row in range(3):
                for col in range(3):
                    cell_img = None

                    # ----------------- 模式 1：普通精準切割 -----------------
                    if target_mode == "1":
                        left = round(col * cell_width)
                        top = round(row * cell_height)
                        right = round((col + 1) * cell_width)
                        bottom = round((row + 1) * cell_height)

                        crop_top = top + 15 if row > 0 else top
                        cell_img = img.crop((left, crop_top, right, bottom))

                    # ----------------- 模式 2：完美去灰線與標題（保護文字） -----------------
                    elif target_mode == "2":
                        # 精準像素偏移：微調避開內部網格灰線，外圍不內縮
                        offset_left = 3 if col > 0 else 0
                        offset_top = 3 if row > 0 else 0
                        offset_right = -3 if col < 2 else 0
                        offset_bottom = -3 if row < 2 else 0

                        left = round(col * cell_width) + offset_left
                        top = round(row * cell_height) + offset_top
                        right = round((col + 1) * cell_width) + offset_right
                        bottom = round((row + 1) * cell_height) + offset_bottom

                        cell_img = img.crop((left, top, right, bottom))
                        cw, ch = cell_img.size

                        # 精準塗白：高度降至 11%，確保只蓋掉頂部 [TITLE]，不壓到表情包與文字
                        draw = ImageDraw.Draw(cell_img)
                        erase_height = int(ch * 0.11)
                        draw.rectangle([0, 0, cw, erase_height], fill=(255, 255, 255, 255))

                    # ----------------- 通用：自動抓取主體與居中畫布 -----------------
                    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
                    diff = ImageChops.difference(cell_img, bg)
                    bbox = diff.getbbox()

                    if bbox:
                        cropped_subject = cell_img.crop(bbox)
                    else:
                        cropped_subject = cell_img

                    sub_w, sub_h = cropped_subject.size
                    max_dim = max(sub_w, sub_h)
                    
                    canvas_size = int(max_dim * 1.1)
                    final_canvas = Image.new('RGBA', (canvas_size, canvas_size), (255, 255, 255, 255))
                    
                    paste_x = (canvas_size - sub_w) // 2
                    paste_y = (canvas_size - sub_h) // 2
                    final_canvas.paste(cropped_subject, (paste_x, paste_y), cropped_subject)

                    output_stream = io.BytesIO()
                    final_canvas.save(output_stream, format="PNG")
                    output_stream.seek(0)

                    filename = f"emote_{row + 1}_{col + 1}.png"
                    file = discord.File(output_stream, filename=filename)
                    cropped_emote_files.append(file)

            msg_suffix = "（模式 2：完美去除灰線與 [] 標題）" if target_mode == "2" else "（模式 1：精準切割）"
            await ctx.send(f"✅ **切割完成！** {msg_suffix}")
            await ctx.send(files=cropped_emote_files)

        except Exception as e:
            await ctx.send(f"❌ 切割失敗：{e}")

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
