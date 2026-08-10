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
        .cutemotes 2 [圖片/連結] - 抹除頂部 [] 標題與去除分界線模式
        """
        # 1. 判斷第一個參數是否為模式數字，如果不是則當作 URL 處理
        target_mode = "1"
        if mode in ["1", "2"]:
            target_mode = mode
        else:
            # 如果使用者沒輸入模式號碼，直接輸入了 URL
            url = mode if not url else f"{mode} {url}"

        # 2. 獲取圖片 Byte 數據
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
            await ctx.send("❌ 請上傳一張 3x3 九宮格圖片！指令格式：`.cutemotes 1` 或 `.cutemotes 2`")
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

                    # ----------------- 模式 2：去標題與分界線 -----------------
                    elif target_mode == "2":
                        margin_x = 10  # 內縮避開分界線
                        margin_y = 6
                        left = round(col * cell_width) + margin_x
                        top = round(row * cell_height) + margin_y
                        right = round((col + 1) * cell_width) - margin_x
                        bottom = round((row + 1) * cell_height) - margin_y

                        cell_img = img.crop((left, top, right, bottom))
                        cw, ch = cell_img.size

                        # 塗白抹除頂部 [] 標題
                        draw = ImageDraw.Draw(cell_img)
                        erase_height = int(ch * 0.14)
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
                    
                    margin_ratio = 1.1 if target_mode == "1" else 1.05
                    canvas_size = int(max_dim * margin_ratio)
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

            msg_suffix = "（模式 2：已抹除 [] 標題與分界線）" if target_mode == "2" else "（模式 1：精準切割）"
            await ctx.send(f"✅ **切割完成！** {msg_suffix}")
            await ctx.send(files=cropped_emote_files)

        except Exception as e:
            await ctx.send(f"❌ 切割失敗：{e}")

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
