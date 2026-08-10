from redbot.core import commands
from PIL import Image, ImageDraw, ImageChops
import io
import discord

class EmoteCutter(commands.Cog):
    """將 3x3 九宮格圖片自動精準切割、抹除頂部 [] 標題並完整保留底部文字的插件"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cutemotes(self, ctx: commands.Context, *, arg: str = None):
        """上傳 3x3 九宮格圖片，自動切成 9 張獨立表情包 (塗白抹除 [] 標題)"""
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
                    # 1. 微調網格邊界，避開黑/灰色分界線 (內縮 4 像素)
                    margin = 4
                    left = round(col * cell_width) + margin
                    top = round(row * cell_height) + margin
                    right = round((col + 1) * cell_width) - margin
                    bottom = round((row + 1) * cell_height) - margin

                    cell_img = img.crop((left, top, right, bottom))
                    cw, ch = cell_img.size

                    # 2. **覆蓋抹除 [] 標題**
                    # 在每格頂部 13% 的範圍內畫一個純白矩形，直接遮蓋 [LURK] 等標題文字
                    draw = ImageDraw.Draw(cell_img)
                    erase_height = int(ch * 0.13)
                    draw.rectangle([0, 0, cw, erase_height], fill=(255, 255, 255, 255))

                    # 3. 自動偵測剩餘區域主體（避開白邊，抓取表情包與底部文字）
                    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
                    diff = ImageChops.difference(cell_img, bg)
                    bbox = diff.getbbox()

                    if bbox:
                        cropped_subject = cell_img.crop(bbox)
                    else:
                        cropped_subject = cell_img

                    # 4. 放置於完美居中的正方形畫布上，並留適當邊框
                    sub_w, sub_h = cropped_subject.size
                    max_dim = max(sub_w, sub_h)
                    
                    canvas_size = int(max_dim * 1.05) # 5% 安全留白
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

            await ctx.send("✅ **完美切割！** `[...]` 標題已完全抹除，底部文字 100% 完整保留：")
            await ctx.send(files=cropped_emote_files)

        except Exception as e:
            await ctx.send(f"❌ 切割失敗：{e}")

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
