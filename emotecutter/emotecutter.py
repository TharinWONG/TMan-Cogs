from redbot.core import commands
from PIL import Image
import io
import discord

# 引用同資料夾內的 3D 處理模組
from .emotecutter_3d import process_3d_emote

class EmoteCutter(commands.Cog):
    """3x3 九宮格圖片自動切割套件 (支援普通版與 3D 立體邊框版)"""

    def __init__(self, bot):
        self.bot = bot

    async def _get_image_bytes(self, ctx, arg):
        """讀取圖片的核心共用邏輯"""
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    return await attachment.read()
        elif arg and arg.startswith("http") and arg.lower().endswith((".png", ".jpg", ".jpeg")):
            try:
                async with self.bot.session.get(arg) as response:
                    if response.status == 200:
                        return await response.read()
            except Exception as e:
                await ctx.send(f"❌ 無法讀取圖片鏈接：{e}")
        return None

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cutemotes(self, ctx: commands.Context, *, arg: str = None):
        """[一般版] 上傳 3x3 九宮格圖片，自動精確切割成 9 張獨立表情包"""
        target_bytes = await self._get_image_bytes(ctx, arg)
        if not target_bytes:
            await ctx.send("❌ 請上傳一張 3x3 九宮格圖片！")
            return

        try:
            img = Image.open(io.BytesIO(target_bytes)).convert('RGBA')
            cell_w, cell_h = img.width / 3, img.height / 3
            files = []

            for row in range(3):
                for col in range(3):
                    left, top = round(col * cell_w), round(row * cell_h)
                    right, bottom = round((col + 1) * cell_w), round((row + 1) * cell_h)
                    crop_top = top + 15 if row > 0 else top

                    emote_img = img.crop((left, crop_top, right, bottom))
                    
                    output = io.BytesIO()
                    emote_img.save(output, format="PNG")
                    output.seek(0)
                    files.append(discord.File(output, filename=f"emote_{row+1}_{col+1}.png"))

            await ctx.send("✅ **切割完成！**")
            await ctx.send(files=files)

        except Exception as e:
            await ctx.send(f"❌ 切割失敗：{e}")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cutemotes3d(self, ctx: commands.Context, *, arg: str = None):
        """[3D立體邊框版] 切割圖片並自動加上 3D 浮雕外框與陰影"""
        target_bytes = await self._get_image_bytes(ctx, arg)
        if not target_bytes:
            await ctx.send("❌ 請上傳一張 3x3 九宮格圖片！")
            return

        try:
            img = Image.open(io.BytesIO(target_bytes)).convert('RGBA')
            cell_w, cell_h = img.width / 3, img.height / 3
            files = []

            for row in range(3):
                for col in range(3):
                    left, top = round(col * cell_w), round(row * cell_h)
                    right, bottom = round((col + 1) * cell_w), round((row + 1) * cell_h)
                    crop_top = top + 15 if row > 0 else top

                    cell_crop = img.crop((left, crop_top, right, bottom))
                    
                    # 調用 emotecutter_3d.py 處理 3D 效果
                    final_3d_img = process_3d_emote(cell_crop)

                    output = io.BytesIO()
                    final_3d_img.save(output, format="PNG")
                    output.seek(0)
                    files.append(discord.File(output, filename=f"emote_3d_{row+1}_{col+1}.png"))

            await ctx.send("✅ **3D 邊框切割完成！**")
            await ctx.send(files=files)

        except Exception as e:
            await ctx.send(f"❌ 切割失敗：{e}")

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
