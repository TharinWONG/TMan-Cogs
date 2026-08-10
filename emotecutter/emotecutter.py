from redbot.core import commands
from PIL import Image
import io
import discord

class EmoteCutter(commands.Cog):
    """將 3x3 九宮格圖片自動切割成 9 張獨立 Emotes 的插件"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cutemotes(self, ctx: commands.Context, *, arg: str = None):
        """上傳 3x3 九宮格圖片並輸入此指令，自動切成 9 張表情包"""
        target_image_bytes = None

        # 讀取使用者上傳的圖片附件
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
            await ctx.send("❌ 請上傳一張 3x3 九宮格圖片，或提供圖片鏈接！")
            return

        # 記憶體內進行圖片切割
        try:
            input_stream = io.BytesIO(target_image_bytes)
            img = Image.open(input_stream)
            img_width, img_height = img.size

            if img_width < 3 or img_height < 3:
                await ctx.send("❌ 圖片尺寸過小，無法切割。")
                return

            cell_width = img_width // 3
            cell_height = img_height // 3
            cropped_emote_files = []

            for row in range(3):
                for col in range(3):
                    left = col * cell_width
                    top = row * cell_height
                    right = (col + 1) * cell_width
                    bottom = (row + 1) * cell_height

                    emote_img = img.crop((left, top, right, bottom))

                    output_stream = io.BytesIO()
                    emote_img.save(output_stream, format="PNG")
                    output_stream.seek(0)

                    filename = f"emote_{row + 1}_{col + 1}.png"
                    file = discord.File(output_stream, filename=filename)
                    cropped_emote_files.append(file)

            await ctx.send("✅ **切割完成！** 以下是 9 張獨立表情包：")
            await ctx.send(files=cropped_emote_files)

        except Exception as e:
            await ctx.send(f"❌ 切割失敗：{e}")

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
