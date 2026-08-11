from .emotecutter import EmoteCutter

async def setup(bot):
    await bot.add_cog(EmoteCutter(bot))