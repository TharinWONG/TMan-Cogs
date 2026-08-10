from redbot.core import commands
from PIL import Image, ImageChops
import io
import discord

class EmoteCutter(commands.Cog):
    """將 3x3 九宮格圖片自動精準切割，並支援超輕量去背的插件"""

    def __init__(self, bot):
        self.bot = bot

    def _remove_white_background(self, img: Image.Image, threshold: int = 240) -> Image.Image:
        """
        純原生 PIL 超快去背法：將接近純白色的像素轉為透明
        threshold: 240 代表 RGB 三色均大於 240 的淺白背景都會被過濾成透明
        """
        img = img.convert("RGBA")
        datas = img.getdata()

        new_data = []
        for item in datas:
            # item 格式為 (R, G, B, A)
            if item[0] >= threshold and item[1] >= threshold and item[2] >= threshold:
                new_data.append((255, 255, 255, 0))  # 變透明
            else:
                new_data.append(item)

        img.putdata(new_data)
        return img

    async def _process_emotes(self, ctx, remove_bg: bool = False, arg: str = None):
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

        status_msg = await ctx.send("⏳ **正在處理圖片中...**")

        try:
            input_stream = io.BytesIO(target_image_bytes)
            img = Image.open(input_stream).convert('RGBA')
            img_width, img_height = img.size

            cell_width = img_width / 3
            cell_height = img_height / 3
            cropped_emote_files = []

            for row in range(3):
                for col in range(3):
                    # 1. 基礎網格切割 (頂部微調 15 像素除上一排殘影)
                    left = round(col * cell_width)
                    top = round(row * cell_height)
                    right = round((col + 1) * cell_width)
                    bottom = round((row + 1) * cell_height)

                    crop_top = top + 15 if row > 0 else top
                    cell_img = img.crop((left, crop_top, right, bottom))

                    # 2. 自動去白色背景邊界並取得主體 Bounding Box
                    bg = Image.new('RGBA', cell_img.size, (255, 255, 255, 255))
                    diff = ImageChops.difference(cell_img, bg)
                    bbox = diff.getbbox()

                    cropped_subject = cell_img.crop(bbox) if bbox else cell_img

                    # 3. 如果開啟去背，使用原生超快色彩過濾去背
                    if remove_bg:
                        cropped_subject = self._remove_white_background(cropped_subject, threshold=235)

                    # 4. 放入正方形畫布
                    sub_w, sub_h = cropped_subject.size
                    max_dim = max(sub_w, sub_h)
                    canvas_size = int(max_dim * 1.1)

                    bg_color = (0, 0, 0, 0) if remove_bg else (255, 255, 255, 255)
                    final_canvas = Image.new('RGBA', (canvas_size, canvas_size), bg_color)
                    
                    paste_x = (canvas_size - sub_w) // 2
                    paste_y = (canvas_size - sub_h) // 2
                    final_canvas.paste(cropped_subject, (paste_x, paste_y), cropped_subject)

                    output_stream = io.BytesIO()
                    final_canvas.save(output_stream, format="PNG")
                    output_stream.seek(0)

                    filename = f"emote_{row + 1}_{col + 1}.png"
                    file = discord.File(output_stream, filename=filename)
                    cropped_emote_files.append(file)

            await status_msg.delete()
            msg = "✅ **極速去背與切割完成！**" if remove_bg else "✅ **精確切割完成！**"
            await ctx.send(msg)
            await ctx.send(files=cropped_emote_files)

        except Exception as e:
            try:
                await status_msg.delete()
            except Exception:
                pass
            await ctx.send(f"❌ 處理失敗：{e}")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def cutemotes(self, ctx: commands.Context, *, arg: str = None):
        """[原指令] 自動切割 9 宮格表情包 (保留背景)"""
        await self._process_emotes(ctx, remove_bg=False, arg=arg)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def cutemotesbg(self, ctx: commands.Context, *, arg: str = None):
        """[新指令] 自動切割 9 宮格表情包，並極速轉換為透明 PNG (零崩潰)"""
        await self._process_emotes(ctx, remove_bg=True, arg=arg)

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
