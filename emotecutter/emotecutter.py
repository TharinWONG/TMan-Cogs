import asyncio
from concurrent.futures import ThreadPoolExecutor
from redbot.core import commands
from PIL import Image, ImageChops
import io
import discord

# 建立線程池，防止 CPU 運算卡死 Bot 主線程
executor = ThreadPoolExecutor(max_workers=2)

class EmoteCutter(commands.Cog):
    """將 3x3 九宮格圖片自動切割，並支援防崩潰去背功能的插件"""

    def __init__(self, bot):
        self.bot = bot

    def _sync_remove_bg(self, img_bytes):
        """在獨立線程中安全執行 rembg"""
        from rembg import remove
        return remove(img_bytes)

    async def _process_emotes(self, ctx, remove_bg: bool = False, arg: str = None):
        """核心處理邏輯 (非同步安全版)"""
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

        status_msg = await ctx.send("⏳ **正在處理圖片中...**" + (" (AI 自動去背運算中，請稍候)" if remove_bg else ""))

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

                    cropped_subject = cell_img.crop(bbox) if bbox else cell_img

                    sub_w, sub_h = cropped_subject.size
                    max_dim = max(sub_w, sub_h)
                    canvas_size = int(max_dim * 1.1)

                    bg_color = (0, 0, 0, 0) if remove_bg else (255, 255, 255, 255)
                    final_canvas = Image.new('RGBA', (canvas_size, canvas_size), bg_color)
                    
                    paste_x = (canvas_size - sub_w) // 2
                    paste_y = (canvas_size - sub_h) // 2
                    final_canvas.paste(cropped_subject, (paste_x, paste_y), cropped_subject)

                    # 如果開啟去背，放到背景線程執行，避免卡死 Bot
                    if remove_bg:
                        img_byte_arr = io.BytesIO()
                        final_canvas.save(img_byte_arr, format='PNG')
                        
                        loop = asyncio.get_running_loop()
                        # 將 AI 運算交給背景 executor
                        nobg_bytes = await loop.run_in_executor(
                            executor, self._sync_remove_bg, img_byte_arr.getvalue()
                        )
                        final_canvas = Image.open(io.BytesIO(nobg_bytes))

                    output_stream = io.BytesIO()
                    final_canvas.save(output_stream, format="PNG")
                    output_stream.seek(0)

                    filename = f"emote_{row + 1}_{col + 1}.png"
                    file = discord.File(output_stream, filename=filename)
                    cropped_emote_files.append(file)

            await status_msg.delete()
            msg = "✅ **去背與切割完成！**" if remove_bg else "✅ **精確切割完成！**"
            await ctx.send(msg)
            await ctx.send(files=cropped_emote_files)

        except Exception as e:
            try:
                await status_msg.delete()
            except Exception:
                pass
            await ctx.send(f"❌ 處理失敗（可能因伺服器記憶體不足）：{e}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cutemotes(self, ctx: commands.Context, *, arg: str = None):
        """[原指令] 自動切割 9 宮格表情包 (保留背景)"""
        await self._process_emotes(ctx, remove_bg=False, arg=arg)

    @commands.command()
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def cutemotesbg(self, ctx: commands.Context, *, arg: str = None):
        """[新指令] 自動切割 9 宮格表情包，並自動去背轉為透明 PNG"""
        await self._process_emotes(ctx, remove_bg=True, arg=arg)

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
