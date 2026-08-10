from redbot.core import commands
from PIL import Image, ImageChops
import io
import discord
import aiohttp

class EmoteCutter(commands.Cog):
    """將 3x3 九宮格圖片自動精準切割、去雜訊及 AI 清理的插件"""

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

    # ------------------ 2. 新功能：AI 抹除分界線與 [] 標籤 ------------------
    @commands.command()
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def cleanemotes(self, ctx: commands.Context, *, arg: str = None):
        """上傳含 [] 標籤與邊框的 9 宮格圖，自動用 AI 提取並去除標籤與分界線"""
        image_url = None

        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    image_url = attachment.url
                    break
        elif arg and arg.startswith("http"):
            image_url = arg

        if not image_url:
            await ctx.send("❌ 請上傳帶有 `[TAG]` 標籤或分界線的九宮格圖片！")
            return

        async with ctx.typing():
            try:
                # 提示詞設計：明確要求移除分界線 (Grid/Lines) 與中括號標籤 ([...])
                prompt = "Remove all grid lines, remove dividing lines, remove top text in brackets like [GREETING], keep the characters and emote text inside, clean solid white background between emotes"
                
                # 使用開放 AI 圖像處理網關進行修圖重構
                encoded_url = java_uri_encode = image_url.replace(":", "%3A").replace("/", "%2F")
                api_url = f"https://image.pollinations.ai/prompt/{prompt}?image={encoded_url}&width=1024&height=1024&nologo=true"

                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url) as resp:
                        if resp.status == 200:
                            cleaned_image_bytes = await resp.read()
                            
                            output_stream = io.BytesIO(cleaned_image_bytes)
                            file = discord.File(output_stream, filename="cleaned_grid.png")
                            
                            await ctx.send("✨ **AI 提純完成！已抹除分界線與 `[...]` 標籤：**", file=file)
                            await ctx.send("💡 *提示：你現在可以對這張生成的圖片使用 `[p]cutemotes` 進行切割！*")
                        else:
                            await ctx.send("❌ AI 處理失敗，請稍後再試。")

            except Exception as e:
                await ctx.send(f"❌ 處理過程中發生錯誤：{e}")

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))
