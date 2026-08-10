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

        try:
            input_stream = io.BytesIO(target_image_bytes)
            img = Image.open(input_stream)
            img_width, img_height = img.size

            if img_width < 3 or img_height < 3:
                await ctx.send("❌ 圖片尺寸過小，無法切割。")
                return

            cell_width = img_width / 3
            cell_height = img_height / 3
            
            # 設定內縮像素 (Padding)，去除邊緣鄰近表情包的雜訊
            padding_x = 12  # 左右內縮像素
            padding_y = 12  # 上下內縮像素

            cropped_emote_files = []

            for row in range(3):
                for col in range(3):
                    # 計算基礎座標並加入內縮邊界
                    left = round(col * cell_width) + padding_x
                    top = round(row * cell_height) + padding_y
                    right = round((col + 1) * cell_width) - padding_x
                    bottom = round((row + 1) * cell_height) - padding_y

                    # 確保座標不超出合理範圍
                    left = max(0, left)
                    top = max(0, top)
                    right = min(img_width, right)
                    bottom = min(img_height, bottom)

                    emote_img = img.crop((left, top, right, bottom))

                    output_stream = io.BytesIO()
                    emote_img.save(output_stream, format="PNG")
                    output_stream.seek(0)

                    filename = f"emote_{row + 1}_{col + 1}.png"
                    file = discord.File(output_stream, filename=filename)
                    cropped_emote_files.append(file)

            await ctx.send("✅ **精確切割完成！**（已去除邊界重疊圖案）：")
            await ctx.send(files=cropped_emote_files)

        except Exception as e:
            await ctx.send(f"❌ 切割失敗：{e}")

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
