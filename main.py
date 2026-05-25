from dotenv import load_dotenv
import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
load_dotenv()
server_id = os.getenv('DISCORD_SERVER_ID', default='NO_SERVER_ID')
TOKEN = os.getenv('DISCORD_TOKEN', default='NO_TOKEN')

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith('!hello'):
        await message.channel.send('Hello!')

    await bot.process_commands(message)

@bot.slash_command(name='test_slash_command', guild_ids=[server_id])
async def __test(ctx):
    await ctx.delete()
    await ctx.send("Победа!")

@bot.slash_command(name='join', guild_ids=[server_id])
async def __join(ctx):
    await ctx.delete()
    if ctx.author.voice:
        await ctx.author.voice.channel.connect()
        return

    return await ctx.send("Никого нет в голосовом канале")

@bot.slash_command(name='leave', guild_ids=[server_id])
async def __leave(ctx):
    await ctx.delete()
    for x in bot.voice_clients:
        if (x.guild == ctx.guild):
            await x.disconnect()
            return

    return await ctx.send("Я не подключен ни к какому голосовому каналу!")

bot.run(TOKEN)
