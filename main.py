import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import asyncio
import os
import google.generativeai as genai  # Import corrigido do Gemini

# ================= CONFIGURAÇÃO =================

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

CANAL_PAINEL_ID = 1453739353661509673
CANAL_LOGS_ID = 1472725771402346506
CARGO_STAFF_ID = 1453935308302188619
CATEGORIA_TICKETS = None

# ================= GOOGLE GEMINI =================

# Configura a API corretamente
GEMINI_KEY = os.getenv("AIzaSyA_uQCBJ2NacCzgnrSMBN11s6S_HndXWrI")
if not GEMINI_KEY:
    raise RuntimeError("GEMINI_API_KEY não configurada")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")  # Modelo atualizado

# ================= SELECT DO TICKET =================

class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Suporte Geral",
                description="Dúvidas, erros, problemas no servidor ou sugestões",
                emoji="🛠️",
                value="suporte_geral"
            ),
            discord.SelectOption(
                label="Resgatar Sorteio",
                description="Ganhou um sorteio? Resgate seu prêmio aqui!",
                emoji="🎉",
                value="resgatar_sorteio"
            ),
            discord.SelectOption(
                label="Parceria",
                description="Quer fechar parceria com a Embee?",
                emoji="🤝",
                value="parceria"
            ),
            discord.SelectOption(
                label="Dúvidas / Ajuda",
                description="Tire dúvidas rápidas sobre o servidor",
                emoji="❓",
                value="duvidas_ajuda"
            )
        ]

        super().__init__(
            placeholder="📋 Selecione o tipo de suporte...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        tipo_ticket = self.values[0]

        # Verificar se já tem ticket aberto
        existing_ticket = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing_ticket:
            embed_erro = discord.Embed(
                description=f"❌ Você já possui um ticket aberto: {existing_ticket.mention}",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed_erro, ephemeral=True)
            return

        # Mensagem de carregamento
        embed_loading = discord.Embed(
            description="⏳ Criando seu ticket...",
            color=0xFFFF00
        )
        await interaction.response.send_message(embed=embed_loading, ephemeral=True)

        # Definir informações baseadas no tipo
        tipos_info = {
            "suporte_geral": {
                "emoji": "🛠️",
                "nome": "Suporte Geral",
                "cor": 0x3498DB,
                "instrucoes": "**Por favor, descreva detalhadamente:**\n> • Qual é o problema ou dúvida\n> • Quando isso aconteceu\n> • Envie prints se possível\n\n✨ Nossa equipe analisará e responderá em breve!"
            },
            "resgatar_sorteio": {
                "emoji": "🎉",
                "nome": "Resgatar Sorteio",
                "cor": 0xF1C40F,
                "instrucoes": "**Para resgatar seu prêmio:**\n> • Envie o print comprovando que ganhou\n> • Mencione qual foi o sorteio\n> • Aguarde a equipe confirmar e entregar o prêmio\n\n⚠️ Não esqueça de enviar o print!"
            },
            "parceria": {
                "emoji": "🤝",
                "nome": "Parceria",
                "cor": 0x9B59B6,
                "instrucoes": "**Para solicitar parceria, envie:**\n> • Nome do seu servidor\n> • Link de convite permanente\n> • Número de membros\n> • Qual tipo de parceria deseja\n\n🔍 A equipe fará a análise e responderá em breve!"
            },
            "duvidas_ajuda": {
                "emoji": "❓",
                "nome": "Dúvidas / Ajuda",
                "cor": 0x2ECC71,
                "instrucoes": "**Estamos aqui para ajudar!**\n> • Faça sua pergunta de forma clara\n> • Mencione sobre qual sistema/evento é a dúvida\n> • Se for sobre regras, especifique qual\n\n💬 Responderemos o mais rápido possível!"
            }
        }

        info = tipos_info[tipo_ticket]

        # Criar canal do ticket
        staff_role = guild.get_role(CARGO_STAFF_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True, 
                attach_files=True, 
                embed_links=True,
                manage_messages=True
            )

        categoria = guild.get_channel(CATEGORIA_TICKETS) if CATEGORIA_TICKETS else None

        ticket_channel = await guild.create_text_channel(
            name=f"{info['emoji']}-{user.name}",
            overwrites=overwrites,
            category=categoria,
            topic=f"{info['nome']} • {user.name} ({user.id})"
        )

        # Embed do ticket
        embed_ticket = discord.Embed(
            title=f"{info['emoji']} {info['nome']}",
            description=(
                f"╔══════════════════════════════╗\n"
                f"   Olá {user.mention}! Bem-vindo(a)!\n"
                f"╚══════════════════════════════╝\n\n"
                f"{info['instrucoes']}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"⏱️ **Tempo médio de resposta:** 1-2 horas\n"
                f"📌 **Ticket aberto:** {discord.utils.format_dt(discord.utils.utcnow(), style='R')}\n"
                f"🆔 **ID do Ticket:** `{ticket_channel.id}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{staff_role.mention if staff_role else ''} 🔔 **Equipe notificada!**"
            ),
            color=info['cor']
        )
        embed_ticket.set_author(
            name="Sistema de Tickets Embee",
            icon_url=guild.icon.url if guild.icon else None
        )
        embed_ticket.set_thumbnail(url=user.display_avatar.url)
        embed_ticket.set_footer(
            text=f"Ticket de {user.name} • Embee Support",
            icon_url=user.display_avatar.url
        )
        embed_ticket.timestamp = discord.utils.utcnow()

        # Botões de controle
        control_view = View(timeout=None)

        claim_button = Button(
            label="Assumir Ticket",
            style=discord.ButtonStyle.success,
            custom_id="claim_ticket",
            emoji="✋"
        )

        close_button = Button(
            label="Fechar Ticket",
            style=discord.ButtonStyle.danger,
            custom_id="close_ticket",
            emoji="🔒"
        )

        async def claim_callback(inter: discord.Interaction):
            if inter.user.id == user.id:
                embed_erro_claim = discord.Embed(
                    description="❌ Você não pode assumir seu próprio ticket!",
                    color=0xFF0000
                )
                await inter.response.send_message(embed=embed_erro_claim, ephemeral=True)
                return

            embed_claim = discord.Embed(
                title="✋ Ticket Assumido",
                description=f"{inter.user.mention} assumiu este ticket e irá atendê-lo em breve!",
                color=0x00FF00
            )
            embed_claim.set_footer(text=f"Assumido por {inter.user.name}", icon_url=inter.user.display_avatar.url)
            embed_claim.timestamp = discord.utils.utcnow()
            await inter.response.send_message(embed=embed_claim)

            canal_logs = guild.get_channel(CANAL_LOGS_ID)
            if canal_logs:
                embed_log_claim = discord.Embed(
                    title="✋ Ticket Assumido",
                    description=f"**Staff:** {inter.user.mention}\n**Ticket:** {ticket_channel.mention}\n**Dono:** {user.mention}",
                    color=0xFFFF00
                )
                embed_log_claim.set_thumbnail(url=inter.user.display_avatar.url)
                embed_log_claim.timestamp = discord.utils.utcnow()
                await canal_logs.send(embed=embed_log_claim)

        async def close_callback(inter: discord.Interaction):
            embed_close = discord.Embed(
                title="🔒 Fechando Ticket",
                description=(
                    "Este ticket será fechado em **5 segundos**...\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "✨ *Obrigado por entrar em contato com a Embee!*\n"
                    "💬 *Esperamos ter ajudado você!*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=0xFF0000
            )
            embed_close.set_footer(text=f"Fechado por {inter.user.name}", icon_url=inter.user.display_avatar.url)
            await inter.response.send_message(embed=embed_close)

            canal_logs = guild.get_channel(CANAL_LOGS_ID)
            if canal_logs:
                embed_log_close = discord.Embed(
                    title="🔒 Ticket Fechado",
                    color=0xFF0000
                )
                embed_log_close.add_field(name="👤 Fechado por", value=f"{inter.user.mention}", inline=True)
                embed_log_close.add_field(name="🎫 Ticket", value=f"`{ticket_channel.name}`", inline=True)
                embed_log_close.add_field(name="📌 Dono", value=user.mention, inline=True)
                embed_log_close.add_field(name="⏱️ Tempo aberto", value=f"{discord.utils.format_dt(ticket_channel.created_at, style='R')}", inline=False)
                embed_log_close.set_thumbnail(url=inter.user.display_avatar.url)
                embed_log_close.timestamp = discord.utils.utcnow()
                await canal_logs.send(embed=embed_log_close)

            await asyncio.sleep(5)
            await ticket_channel.delete(reason=f"Ticket fechado por {inter.user.name}")

        claim_button.callback = claim_callback
        close_button.callback = close_callback

        control_view.add_item(claim_button)
        control_view.add_item(close_button)

        mention_content = user.mention
        if staff_role:
            mention_content = f"{user.mention} {staff_role.mention}"

        await ticket_channel.send(content=mention_content, embed=embed_ticket, view=control_view)

        canal_logs = guild.get_channel(CANAL_LOGS_ID)
        if canal_logs:
            embed_log = discord.Embed(
                title="📝 Novo Ticket Criado",
                description=f"**Usuário:** {user.mention}\n**Tipo:** {info['nome']}\n**Canal:** {ticket_channel.mention}",
                color=0x00FF00
            )
            embed_log.set_thumbnail(url=user.display_avatar.url)
            embed_log.timestamp = discord.utils.utcnow()
            await canal_logs.send(embed=embed_log)

        embed_sucesso = discord.Embed(
            title="✅ Ticket Criado!",
            description=f"Seu ticket foi criado com sucesso!\n\n**Acesse:** {ticket_channel.mention}",
            color=0x00FF00
        )
        embed_sucesso.set_footer(text="Embee Support System", icon_url=bot.user.display_avatar.url)
        await interaction.edit_original_response(embed=embed_sucesso)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    print(f"🤖 ID: {bot.user.id}")
    print(f"🆓 IA: Hugging Face (Gratuita e SEM CHAVE!)")
    print("-------------------")

    bot.add_view(TicketView())
    await enviar_painel_automatico()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Verificar se o bot foi mencionado
    if bot.user in message.mentions:
        pergunta = message.content.replace(f'<@{bot.user.id}>', '').strip()

        if not pergunta:
            await message.reply("👋 Olá! Me mencione com uma pergunta e eu responderei usando IA!")
            return

        # Mostrar que está digitando
        async with message.channel.typing():
            resposta = await perguntar_ia(pergunta)

            embed_resposta = discord.Embed(
                title="🤖 Resposta da IA",
                description=resposta,
                color=0xFF9D00  # Cor Hugging Face
            )
            embed_resposta.set_footer(
                text=f"Pergunta de {message.author.name} • Powered by Hugging Face",
                icon_url=message.author.display_avatar.url
            )
            embed_resposta.timestamp = discord.utils.utcnow()

            await message.reply(embed=embed_resposta)

    await bot.process_commands(message)

async def enviar_painel_automatico():
    """Envia o painel automaticamente quando o bot ligar"""
    await bot.wait_until_ready()

    canal = bot.get_channel(CANAL_PAINEL_ID)

    if not canal:
        print("❌ Canal não encontrado! Verifique o ID.")
        return

    try:
        async for message in canal.history(limit=50):
            if message.author == bot.user:
                await message.delete()
                await asyncio.sleep(0.5)
    except:
        pass

    embed = discord.Embed(
        title="🎫 Sistema de Suporte Embee",
        description=(
            "╔═══════════════════════════════════╗\n"
            "**Bem-vindo ao atendimento da Embee!**\n"
            "╚═══════════════════════════════════╝\n\n"
            "Estamos aqui para ajudar você com qualquer dúvida ou problema. Selecione a categoria apropriada abaixo para abrir seu ticket.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📋 **CATEGORIAS DISPONÍVEIS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛠️ **» Suporte Geral**\n"
            "> Dúvidas, erros, problemas técnicos ou sugestões\n"
            "> *Descreva o problema e envie prints se possível*\n\n"
            "🎉 **» Resgatar Sorteio**\n"
            "> Ganhou algum sorteio? Resgate aqui!\n"
            "> *Envie o print comprovando seu ganho*\n\n"
            "🤝 **» Parceria**\n"
            "> Quer fazer parceria com a Embee?\n"
            "> *Envie informações do seu servidor*\n\n"
            "❓ **» Dúvidas / Ajuda**\n"
            "> Perguntas rápidas sobre o servidor\n"
            "> *Tire suas dúvidas sobre regras e sistemas*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ **AVISOS IMPORTANTES**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "• Não abra tickets sem necessidade real\n"
            "• Tickets inativos serão fechados automaticamente\n"
            "• Mantenha o respeito com a equipe\n"
            "• Seja claro e objetivo em suas mensagens\n\n"
            "✨ **Obrigado por escolher a Embee!**"
        ),
        color=0xE74C3C
    )

    embed.set_image(url="https://i.pinimg.com/736x/4d/75/97/4d75975c8e4db8e5809275c4521ad645.jpg")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    embed.set_footer(
        text="🎫 Selecione uma categoria no menu abaixo • Embee Support System",
        icon_url=bot.user.display_avatar.url
    )
    embed.set_author(
        name="Sistema de Tickets",
        icon_url=bot.user.display_avatar.url
    )
    embed.timestamp = discord.utils.utcnow()

    await canal.send(embed=embed, view=TicketView())
    print(f"✅ Painel enviado automaticamente em #{canal.name}")

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup_categoria(ctx, categoria_id: int = None):
    """Define a categoria onde os tickets serão criados"""
    global CATEGORIA_TICKETS

    if categoria_id:
        categoria = ctx.guild.get_channel(categoria_id)
        if categoria and isinstance(categoria, discord.CategoryChannel):
            CATEGORIA_TICKETS = categoria_id
            await ctx.send(f"✅ Categoria definida: {categoria.name}")
        else:
            await ctx.send("❌ ID inválido ou não é uma categoria!")
    else:
        await ctx.send("ℹ️ Use: `!setup <ID_DA_CATEGORIA>`")

@bot.command(name="painel")
@commands.has_permissions(administrator=True)
async def reenviar_painel(ctx):
    """Reenvia o painel manualmente"""
    await enviar_painel_automatico()
    await ctx.send("✅ Painel reenviado!")

# Token do bot
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN não configurado")

bot.run(TOKEN)

