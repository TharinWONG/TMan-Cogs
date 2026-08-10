from redbot.core import commands
from PIL import Image, ImageDraw, ImageChops
import io
import discord

class EmoteCutter(commands.Cog):
    """將 3x3 九宮格圖片自動精準切割、去雜訊及圖像清理的插件"""

    def __init__(self, bot):
        self.bot = bot

    # ------------------ 1. 原有功能：自動切割圖片 ------------------
    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cutemotes(self, ctx: commands.Context, *, arg: str = None):
        """上傳 3x3 九宮格圖片，自動精準切割成 9 張獨立 Emotes"""
        target_image_bytes = None

        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    target_image_bytes = await attachment.read()
                    break
        elif arg and arg.startswith("http") and arg.lower().endswith((".png", ".jpg", ".jpeg")):
            try:
                async with self.bot.session.get(arg) as response:
                    if response.status == 200:
                        target_image_bytes = await response.read()
            except Exception as e:
                await ctx.send(f"❌ 無法讀取圖片鏈接：{e}")
                return

        if not target_image_bytes:
            await ctx.send("❌ 請上傳一張 3x3 九宮格圖片！")
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
                    left = round(col * cell_width)
                    top = round(row * cell_height)
                    right = round((col + 1) * cell_width)
                    bottom = round((row + 1) * cell_height)

                    crop_top = top + 15 if row > 0 else top
                    cell_img = img.crop((left, crop_top, right, bottom))

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

            await ctx.send("✅ **精確去雜訊切割完成！**")
            await ctx.send(files=cropped_emote_files)

        except Exception as e:
            await ctx.send(f"❌ 切割失敗：{e}")

# ------------------ 2. 微調修正版：精確擦除標籤與分界線 ------------------
    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def cleanemotes(self, ctx: commands.Context, *, arg: str = None):
        """上傳 9 宮格圖，精準抹除頂部 [...] 標籤與灰色分界線（不傷文字）"""
        target_image_bytes = None

        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    target_image_bytes = await attachment.read()
                    break
        elif arg and arg.startswith("http"):
            try:
                async with self.bot.session.get(arg) as response:
                    if response.status == 200:
                        target_image_bytes = await response.read()
            except Exception as e:
                await ctx.send(f"❌ 無法讀取圖片：{e}")
                return

        if not target_image_bytes:
            await ctx.send("❌ 請上傳帶有 `[TAG]` 標籤的九宮格圖片！")
            return

        try:
            input_stream = io.BytesIO(target_image_bytes)
            img = Image.open(input_stream).convert('RGB')
            draw = ImageDraw.Draw(img)
            
            w, h = img.size
            cell_w = w / 3
            cell_h = h / 3

            # 1. 精準擦除 [TAG] 區域（僅覆蓋每格頂部 2.5% 至 7.5% 的標籤文字高度）
            for row in range(3):
                for col in range(3):
                    x1 = col * cell_w
                    y1 = (row * cell_h) + (cell_h * 0.015)  # 稍微下移，完全涵蓋括號
                    x2 = (col + 1) * cell_w
                    y2 = (row * cell_h) + (cell_h * 0.08)   # 縮小覆蓋高度，避免遮到下方文字
                    
                    draw.rectangle([x1, y1, x2, y2], fill=(255, 255, 255))

            # 2. 擦除細線分界線 (縮小邊框寬度至 0.8%，避免切掉左右圖案)
            line_thickness = max(2, int(w * 0.008))
            
            # 垂直線
            draw.rectangle([cell_w - line_thickness, 0, cell_w + line_thickness, h], fill=(255, 255, 255))
            draw.rectangle([cell_w * 2 - line_thickness, 0, cell_w * 2 + line_thickness, h], fill=(255, 255, 255))

            # 水平線
            draw.rectangle([0, cell_h - line_thickness, w, cell_h + line_thickness], fill=(255, 255, 255))
            draw.rectangle([0, cell_h * 2 - line_thickness, w, cell_h * 2 + line_thickness], fill=(255, 255, 255))

            output_stream = io.BytesIO()
            img.save(output_stream, format="PNG")
            output_stream.seek(0)

            file = discord.File(output_stream, filename="cleaned_grid.png")
            await ctx.send("✨ **修正完成！標籤已乾淨抹除且文字完整保留：**", file=file)

        except Exception as e:
            await ctx.send(f"❌ 處理失敗：{e}")
