from dotenv import load_dotenv

import yt_dlp

import os
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from yt_dlp.extractor import reuters

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
load_dotenv()
server_id = os.getenv('DISCORD_SERVER_ID', default='NO_SERVER_ID')
TOKEN = os.getenv('DISCORD_TOKEN', default='NO_TOKEN')

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn'}
async def get_audio(url):
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        audio_url = ydl.extract_info(url, download=False).get('url')
    return PCMVolumeTransformer(FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS), volume=0.05)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.slash_command(name='connect', guild_ids=[server_id])
async def _connect(ctx: commands.Context):
    if ctx.author.voice is None:
        return await ctx.send("Никого нет в голосовом канале")
    await ctx.respond("Подключился", ephemeral=True)
    await ctx.author.voice.channel.connect()

@bot.slash_command(name='disconnect', guild_ids=[server_id])
async def _disconnect(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.send("Я не подключен ни к какому голосовому каналу!")
    await ctx.respond("Отключаюсь", ephemeral=True)
    await ctx.voice_client.disconnect()

@bot.slash_command(name='play', guild_ids=[server_id])
async def _play(ctx: commands.Context, url: str):
    audio = await get_audio(url)
    await ctx.respond("Начинаю проигрывание", ephemeral=True)
    if ctx.voice_client is None:
        await ctx.author.voice.channel.connect()
        ctx.voice_client.play(audio)
    else:
        ctx.voice_client.play(audio)

@bot.slash_command(name='pause', guild_ids=[server_id])
async def _pause(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.send("Я не подключен ни к какому голосовому каналу!")
    if ctx.voice_client.is_playing():
        await ctx.respond("На паузе", ephemeral=True)
        ctx.voice_client.pause()

@bot.slash_command(name='resume', guild_ids=[server_id])
async def _resume(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.send("Я не подключен ни к какому голосовому каналу!")
    if ctx.voice_client.is_paused():
        await ctx.respond("Возобновлено", ephemeral=True)
        ctx.voice_client.resume()

@bot.slash_command(name='volume', guild_ids=[server_id])
async def _volume(ctx:commands.Context, volume: int):
    await ctx.respond(f"Громкость изменена на {volume}%", ephemeral=True)
    ctx.voice_client.source.volume = volume / 100

bot.run(TOKEN)
