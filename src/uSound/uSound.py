import asyncio
from dotenv import load_dotenv
import os

import yt_dlp

import discord
from discord.ext import commands
from discord import FFmpegPCMAudio, PCMVolumeTransformer

search_data = {}
intents = discord.Intents.default()
queues = {}
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
load_dotenv()
server_ids = os.getenv('DISCORD_SERVER_ID', default='NO_SERVER_ID').split(',')
TOKEN = os.getenv('DISCORD_TOKEN', default='NO_TOKEN')

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn'}

def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

def check_queue(ctx, guild_id):
    queue = get_queue(guild_id)
    if queue:
        next_track = queue.pop(0)
        ctx.voice_client.play(next_track, after=lambda e: check_queue(ctx, guild_id))

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
            search_dict = {}
            for item in info['entries']:
                search_dict[item['title']] = item['url']
            return search_dict


class ButtonWithNumber(discord.ui.Button):
    def __init__(self, label, number, guild_id):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.number = number
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        if self.guild_id not in search_data:
            search_data[self.guild_id] = {}
        search_data[self.guild_id]['selected_number'] = self.number
        search_data[self.guild_id]['event'].set()
        await interaction.response.defer()
        await interaction.delete_original_response()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command(name='connect', guild_ids=server_ids)
async def _connect(ctx: commands.Context):
    if ctx.author.voice is None:
        return await ctx.respond("❌ Никого нет в голосовом канале", ephemeral=True, delete_after=5)
    await ctx.respond("Подключился", ephemeral=True, delete_after=5)
    await ctx.author.voice.channel.connect()

@bot.command(name='disconnect', guild_ids=server_ids)
async def _disconnect(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.respond("❌ Я не подключен ни к какому голосовому каналу!", ephemeral=True, delete_after=5)

    guild_id = ctx.guild.id
    if guild_id in queues:
        queues[guild_id] = []

    await ctx.respond("Отключаюсь", ephemeral=True, delete_after=5)
    await ctx.voice_client.disconnect()

@bot.command(name='play', guild_ids=server_ids)
async def _play(ctx: commands.Context, search: str):
    await ctx.defer(ephemeral=True)

    if not ctx.author.voice:
        return await ctx.respond("❌ Вы не находитесь в голосовом канале!", ephemeral=True, delete_after=5)

    guild_id = ctx.guild.id
    queue = get_queue(guild_id)

    if "yt" in search or "youtube.com" in search or "youtu.be" in search:
        audio, title = await get_audio(search)
    else:
        search_dict = await get_audio(f"ytsearch4:{search}")
        embeds = []
        buttons = []
        count = 1
        result_dict = {}

        for item in search_dict:
            embeds.append(discord.Embed(title=f"{count}.{item}"))
            buttons.append(ButtonWithNumber(label=f"{count}", number=count, guild_id=guild_id))
            result_dict[count] = search_dict[item]
            count += 1

        if guild_id not in search_data:
            search_data[guild_id] = {}
        search_data[guild_id]['event'] = asyncio.Event()

        view = discord.ui.View()
        for button in buttons:
            view.add_item(button)

        await ctx.respond(embeds=embeds, view=view, ephemeral=True, delete_after=30)
        await search_data[guild_id]['event'].wait()
        selected_number = search_data[guild_id]['selected_number']
        audio, title = await get_audio(result_dict[selected_number])


    queue.append(audio)

    if ctx.voice_client is None:
        await ctx.respond(f"▶️ Начинаю проигрывание {title}", ephemeral=True, delete_after=5)
        await ctx.author.voice.channel.connect()
        ctx.voice_client.play(audio, after=lambda e: check_queue(ctx, guild_id))

    elif ctx.voice_client.is_playing():
        await ctx.respond(f"🎵 Трек {title} добавлен в очередь", ephemeral=True, delete_after=5)

    else:
        await ctx.respond(f"▶️ Начинаю проигрывание {title}", ephemeral=True, delete_after=5)
        ctx.voice_client.play(audio, after=lambda e: check_queue(ctx, guild_id))

@bot.command(name='pause', guild_ids=server_ids)
async def _pause(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.respond("❌ Я не подключен ни к какому голосовому каналу!", ephemeral=True, delete_after=5)
    if ctx.voice_client.is_playing():
        await ctx.respond("На паузе", ephemeral=True, delete_after=5)
        ctx.voice_client.pause()

@bot.command(name='resume', guild_ids=server_ids)
async def _resume(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.respond("❌ Я не подключен ни к какому голосовому каналу!", ephemeral=True, delete_after=5)
    if ctx.voice_client.is_paused():
        await ctx.respond("Возобновлено", ephemeral=True, delete_after=5)
        ctx.voice_client.resume()

@bot.command(name='volume', guild_ids=server_ids)
async def _volume(ctx:commands.Context, volume: int):
    await ctx.respond(f"Громкость изменена на {volume}%", ephemeral=True, delete_after=5)
    ctx.voice_client.source.volume = volume / 100

@bot.command(name='skip', guild_ids=server_ids)
async def _skip(ctx: commands.Context):
    if ctx.voice_client is None:
        return await ctx.respond("❌ Я не подключен ни к какому голосовому каналу!", ephemeral=True, delete_after=5)
    await ctx.respond("⏭️ Трек пропущен", ephemeral=True, delete_after=5)
    ctx.voice_client.stop()

@bot.command(name='clear', guild_ids=server_ids)
async def _clear_queue(ctx: commands.Context):
    guild_id = ctx.guild.id
    if guild_id in queues:
        queues[guild_id] = []
    await ctx.respond("🗑️ Очередь очищена", ephemeral=True, delete_after=5)

@bot.command(name='stop', guild_ids=server_ids)
async def _stop(ctx: commands.Context):
    guild_id = ctx.guild.id

    if ctx.voice_client is None:
        await ctx.respond("❌ Бот не в голосовом канале", ephemeral=True, delete_after=5)
    else:
        if guild_id in queues:
            queues[guild_id] = []
        await ctx.voice_client.disconnect()
        await ctx.respond("⏹️ Воспроизведение остановлено, бот отключён", ephemeral=True, delete_after=5)

def main():
    bot.run(TOKEN)

if "__main__" == __name__:
    main()