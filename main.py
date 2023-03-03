from pyVinted import Vinted
import discord
import json
from discord.ext import commands, tasks
import logging
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")

logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
logging.basicConfig(level=logging.INFO)

with open("vinted.json") as json_file:
    config = json.load(json_file)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(intents=intents)


def write_config():
    with open("vinted.json", "w") as outfile:
        jsonSerialized = json.dumps(config, indent=4)
        outfile.write(jsonSerialized)


@bot.slash_command(name="subscribe", description="Subscribe à une recherche Vinted")
async def subscribe(ctx, name, url, channel: discord.TextChannel):
    await ctx.defer()
    config["searches"].append(
        {
            "id": config["lastID"] + 1,
            "userID": ctx.author.id,
            "name": name,
            "url": url,
            "channelID": channel.id,
            "lastSearch": 0,
        }
    )
    config["lastID"] = config["lastID"] + 1
    write_config()
    await ctx.followup.send(
        f"Bien compris, je me met à chercher Vinted. Tu seras prévenu sur <#{channel.id}>"
    )


@bot.slash_command(name="unsubscribe", description="Unsubscribe à une recherche Vinted")
async def unsubscribe(ctx, id: discord.Option(int)):
    await ctx.defer()
    config["searches"][:] = (
        search for search in config["searches"] if search["id"] != id
    )
    write_config()
    await ctx.followup.send(f"Bien compris, je supprime cette recherche.")


@bot.slash_command(name="list", description="Liste les recherches Vinted enregistrées")
async def list_command(ctx):
    await ctx.defer()
    r = list()
    for search in config["searches"]:
        if ctx.author.id == search["userID"]:
            r.append(search)

    if not r:
        await ctx.followup.send(
            f"Tu n'as pas d'abonnement actif. Utilise la commande /subscribe pour t'abonner à une recherche !"
        )
    else:
        await ctx.followup.send(f"{len(r)} abonnements actifs !")
        for i in r:
            embed = discord.Embed()
            embed.add_field(name="ID", value=i["id"], inline=False)
            embed.add_field(name="URL", value=i["url"], inline=False)
            bot_channel = i["channelID"]
            embed.add_field(
                name="Salon",
                value=f"<#{bot_channel}>",
                inline=False,
            )
            await ctx.send(embed=embed)


@tasks.loop(seconds=5)
async def sync_vinted():
    vinted = Vinted()
    for search in config["searches"]:
        logging.info(f"Searching for {search['url']}")
        items = vinted.items.search(search["url"])
        itemsOrdered = sorted(items, key=lambda d: d.raw_timestamp, reverse=True)

        for item in itemsOrdered:
            if item.raw_timestamp <= search["lastSearch"]:
                break
            else:
                search["lastSearch"] = itemsOrdered[0].raw_timestamp
                write_config()
            channel = bot.get_channel(int(search["channelID"]))
            embed = discord.Embed(title=item.title)
            embed.url = item.url
            embed.set_image(url=item.photo)
            embed.add_field(name="Prix:", value=f"{item.price}{item.currency}")
            embed.add_field(name="Taille:", value=f"{item.size_title}")
            embed.add_field(name="Marque:", value=f"{item.brand_title}")
            embed.set_footer(text=f"{item.created_at_ts}")

            buttonDetails = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                url=item.url,
                emoji="🔎",
                label="Détails",
            )
            buttonBuy = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                url=f"https://www.vinted.fr/transaction/buy/new?source_screen=item&transaction%5Bitem_id%5D={item.id}",
                emoji="💸",
                label="Acheter",
            )
            buttonProfil = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                url=f"https://www.vinted.fr/member/{item.raw_data['user']['id']}-{item.raw_data['user']['login']}",
                emoji="🪪",
                label="Profil",
            )
            view = discord.ui.View(buttonDetails, buttonBuy, buttonProfil)
            await channel.send(embed=embed, view=view)


@bot.event
async def on_ready():
    # LOOPS THROUGH ALL THE GUILD / SERVERS THAT THE BOT IS ASSOCIATED WITH.
    for guild in bot.guilds:
        logging.info(f"🔗 Connecté sur {guild.name} en tant que {bot.user} !")

    logging.info(f"Launching task sync_vinted")
    sync_vinted.start()


bot.run(BOT_TOKEN)
