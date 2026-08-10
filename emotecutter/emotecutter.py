from redbot.core import commands
from PIL import Image, ImageChops
import io
import discord

class EmoteCutter(commands.Cog):
    """將 3x3 九宮格圖片自動精準切割、去頂部標題與分界線的插件"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cutemotes(self, ctx: commands.Context, *, arg: str = None):
        """上傳 3x3 九宮格圖片，自動切成 9 張獨立表情包 (自動去除分界線與 [] 標題)"""
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
                    # 1. 計算基礎網格座標
                    left = round(col * cell_width)
                    top = round(row * cell_height)
                    right = round((col + 1) * cell_width)
                    bottom = round((row + 1) * cell_height)

                    # 2. **去除 [] 標題與分界線處理**
                    # 頂部向下裁切 7.5% 的高度（完美避開 [LURK] 等頂部標題與橫向分界線）
                    crop_top_offset = int(cell_height * 0.075) 
                    
                    # 左右與底部微調 8 像素（切掉豎向分界線與底線殘影）
                    border_offset = 8 

                    crop_left = left + border_offset
                    crop_top = top + crop_top_offset
                    crop_right = right - border_offset
                    crop_bottom = bottom - border_offset

                    cell_img = img.crop((crop_left, crop_top, crop_right, crop_bottom))

                    # 3. **保留原有的邊界探測與去背景邏輯**
                    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
                    diff = ImageChops.difference(cell_img, bg)
                    bbox = diff.getbbox()

                    if bbox:
                        cropped_subject = cell_img.crop(bbox)
                    else:
                        cropped_subject = cell_img

                    # 4. **保留原有的等比例居中畫布**
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

            await ctx.send("✅ **切割完成！**（已自動去除 [] 標題與灰色分界線）：")
            await ctx.send(files=cropped_emote_files)

        except Exception as e:
            await ctx.send(f"❌ 切割失敗：{e}")

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
