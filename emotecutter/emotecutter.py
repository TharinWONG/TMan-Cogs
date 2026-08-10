from redbot.core import commands
from PIL import Image
import io
import discord

class EmoteCutter(commands.Cog):
    """將 3x3 九宮格圖片自動切割成 9 張獨立 Emotes 的插件 (智能縮放文字完整版)"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def cutemotes(self, ctx: commands.Context, *, arg: str = None):
        """上傳 3x3 九宮格圖片，自動切成 9 張完整文字的表情包"""
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
            img = Image.open(input_stream)
            
            # 強制轉換為 RGBA 模式以確保背景處理
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
                
            img_width, img_height = img.size

            if img_width < 3 or img_height < 3:
                await ctx.send("❌ 圖片尺寸過小，無法切割。")
                return

            cell_width = img_width / 3
            cell_height = img_height / 3
            
            cropped_emote_files = []

            for row in range(3):
                for col in range(3):
                    # 1. 執行基礎數學切割 (精確對齊網格，不加 Padding)
                    left = round(col * cell_width)
                    top = round(row * cell_height)
                    right = round((col + 1) * cell_width)
                    bottom = round((row + 1) * cell_height)

                    emote_img = img.crop((left, top, right, bottom))
                    orig_w, orig_h = emote_img.size

                    # 2. **智能縮放處理 (關鍵)**
                    # 建立一個完美的透明正方形畫布 (使用原圖最長邊作為基準)
                    base_size = max(orig_w, orig_h)
                    
                    # 計算縮放比例 (例如整體縮小到基準的 85%，為文字騰出空間)
                    scale_factor = 0.85 
                    
                    new_w = int(orig_w * scale_factor)
                    new_h = int(orig_h * scale_factor)

                    # 縮小圖案 (使用高質量縮放)
                    scaled_img = emote_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                    # 建立透明畫布並將縮小後的圖案垂直居中貼上
                    final_canvas = Image.new('RGBA', (base_size, base_size), (255, 255, 255, 0))
                    paste_x = (base_size - new_w) // 2
                    paste_y = (base_size - new_h) // 2
                    
                    final_canvas.paste(scaled_img, (paste_x, paste_y), scaled_img)

                    # 3. 儲存為 PNG
                    output_stream = io.BytesIO()
                    final_canvas.save(output_stream, format="PNG")
                    output_stream.seek(0)

                    filename = f"emote_{row + 1}_{col + 1}.png"
                    file = discord.File(output_stream, filename=filename)
                    cropped_emote_files.append(file)

            await ctx.send("✅ **切割完成！** 文字已完整保留，圖案已智能居中縮放：")
            await ctx.send(files=cropped_emote_files)

        except Exception as e:
            await ctx.send(f"❌ 切割失敗：{e}")

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
