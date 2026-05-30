import asyncio

from dotenv import load_dotenv

import yt_dlp

import os
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio, PCMVolumeTransformer

intents = discord.Intents.default()
track_queue = []
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
load_dotenv()
server_id = os.getenv('DISCORD_SERVER_ID', default='NO_SERVER_ID')
TOKEN = os.getenv('DISCORD_TOKEN', default='NO_TOKEN')

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn'}

def check_queue(ctx):
    if track_queue:
        next_track = track_queue.pop(0)
        ctx.voice_client.play(next_track, after=lambda e: check_queue(ctx))

async def get_audio(url):
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'extract_flat': 'in_playlist',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'entries' not in info:
            audio_url = info.get('url')
            title = info.get('title')
            return PCMVolumeTransformer(FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS), volume=0.05), title
        else:
            aboba = info['entries']
            search_dict = {}
            for item in info['entries']:
                search_dict[item['title']] = [item['url'], item['thumbnails'][0]['url']]
            # info = ydl.extract_info(info['entries'][0].get('url'), download=False)
            # audio_url = info.get('url')
            # title = info.get('title')
            return search_dict


class ButtonWithNumber(discord.ui.Button):
    def __init__(self, label, number, callback_handler):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.number = number
        self.callback_handler = callback_handler

    async def callback(self, interaction: discord.Interaction):
        await self.callback_handler(interaction, self.number)

button_pressed_event = asyncio.Event()
selected_number = None

async def handle_button_press(interaction, number):
    global selected_number
    selected_number = number
    await interaction.response.defer()
    await interaction.delete_original_response()
    button_pressed_event.set()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.slash_command(name='connect', guild_ids=[server_id])
async def _connect(ctx: commands.Context):
    if ctx.author.voice is None:
        return await ctx.respond("Никого нет в голосовом канале", ephemeral=True, delete_after=5)
    await ctx.respond("Подключился", ephemeral=True, delete_after=5)
    await ctx.author.voice.channel.connect()

@bot.slash_command(name='disconnect', guild_ids=[server_id])
async def _disconnect(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.respond("Я не подключен ни к какому голосовому каналу!", ephemeral=True, delete_after=5)
    await ctx.respond("Отключаюсь", ephemeral=True, delete_after=5)
    await ctx.voice_client.disconnect()

@bot.slash_command(name='play', guild_ids=[server_id])
async def _play(ctx: commands.Context, search: str):
    await ctx.defer(ephemeral=True)

    if "yt" in search or "youtube" in search:
        audio, title = await get_audio(search)
    else:
        search_dict = await get_audio(f"ytsearch4:{search}")
        embeds = []
        buttons = []
        count = 1
        result_dict = {}
        for item in search_dict:
            embeds.append(discord.Embed(title=f"{count}.{item}"))
            buttons.append(ButtonWithNumber(label=f"{count}", number=count, callback_handler=handle_button_press))
            result_dict[count] = search_dict[item][0]
            count += 1
        view = discord.ui.View()
        for button in buttons:
            view.add_item(button)
        await ctx.respond(embeds=embeds, view=view, ephemeral=True, delete_after=30)
        await button_pressed_event.wait()
        audio, title = await get_audio(result_dict[selected_number])

    track_queue.append(audio)

    if ctx.voice_client is None:
        await ctx.respond(f"Начинаю проигрывание {title}", ephemeral=True, delete_after=5)
        await ctx.author.voice.channel.connect()
        ctx.voice_client.play(audio, after=lambda e: check_queue(ctx))

    elif ctx.voice_client.is_playing():
        await ctx.respond(f"Трек {title} добавлен в очередь", ephemeral=True, delete_after=5)

    else:
        await ctx.respond(f"Начинаю проигрывание {title}", ephemeral=True, delete_after=5)
        ctx.voice_client.play(audio, after=lambda e: check_queue(ctx))

@bot.slash_command(name='pause', guild_ids=[server_id])
async def _pause(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.respond("Я не подключен ни к какому голосовому каналу!", ephemeral=True, delete_after=5)
    if ctx.voice_client.is_playing():
        await ctx.respond("На паузе", ephemeral=True, delete_after=5)
        ctx.voice_client.pause()

@bot.slash_command(name='resume', guild_ids=[server_id])
async def _resume(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.respond("Я не подключен ни к какому голосовому каналу!", ephemeral=True, delete_after=5)
    if ctx.voice_client.is_paused():
        await ctx.respond("Возобновлено", ephemeral=True, delete_after=5)
        ctx.voice_client.resume()

@bot.slash_command(name='volume', guild_ids=[server_id])
async def _volume(ctx:commands.Context, volume: int):
    await ctx.respond(f"Громкость изменена на {volume}%", ephemeral=True, delete_after=5)
    ctx.voice_client.source.volume = volume / 100

@bot.slash_command(name='skip', guild_ids=[server_id])
async def _skip(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.respond("Я не подключен ни к какому голосовому каналу!", ephemeral=True, delete_after=5)
    await ctx.respond("Проускаю", ephemeral=True, delete_after=5)
    ctx.voice_client.stop()

bot.run(TOKEN)
