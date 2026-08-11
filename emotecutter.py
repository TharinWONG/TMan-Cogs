from redbot.core import commands
from PIL import Image, ImageChops
import io
import discord

class EmoteCutter(commands.Cog):
    """將 3x3 九宮格圖片自動精準切割並去雜訊的插件"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cutemotes(self, ctx: commands.Context, *, arg: str = None):
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
                    # 1. 基礎網格切割，並向內微調去除鄰居大面積重疊
                    left = round(col * cell_width)
                    top = round(row * cell_height)
                    right = round((col + 1) * cell_width)
                    bottom = round((row + 1) * cell_height)

                    # 針對頂部殘影微調：如果是第 2、3 列，頂部多裁掉 15 像素以切斷上一排殘影
                    crop_top = top + 15 if row > 0 else top
                    
                    cell_img = img.crop((left, crop_top, right, bottom))

                    # 2. 自動去白色背景並取得主體 Bounding Box
                    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
                    diff = ImageChops.difference(cell_img, bg)
                    bbox = diff.getbbox()

                    if bbox:
                        # 裁切出只有主體（含文字）的區域
                        cropped_subject = cell_img.crop(bbox)
                    else:
                        cropped_subject = cell_img

                    # 3. 將主體等比例縮放，放入完美的正方形畫布中
                    sub_w, sub_h = cropped_subject.size
                    max_dim = max(sub_w, sub_h)
                    
                    # 留出 10% 邊界Margin，防止文字貼邊
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

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
