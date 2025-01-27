import os
import discord
from discord.ext import commands
from discord import app_commands, ui

# ใช้ Intents.all() เพื่อให้บอทมีสิทธิ์เข้าถึงทุกอย่าง
intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents, activity=None)

# ตั้งค่า Channel ID และ Role ID ที่ใช้ในระบบ
REPORT_CHANNEL_ID = 1333073139562709002  # ห้องที่ส่งรายงาน
LOG_CHANNEL_ID = 1333392202939760690   # ห้อง Log
MOD_ROLE_ID = 1330887708100399135           # บทบาทที่สามารถยืนยันรายงานได้

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name="/report เพื่อรายงานผู้เล่น"
            )
        )
    except Exception as e:
        print(e)

class ConfirmView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="ยืนยัน", style=discord.ButtonStyle.green, emoji="✅", custom_id="confirm_report")
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        role = interaction.guild.get_role(MOD_ROLE_ID)
        if role not in interaction.user.roles:
            await interaction.response.send_message("คุณไม่มีสิทธิ์ยืนยันรายงานนี้", ephemeral=True)
            return

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(
            description=f"ได้รับการอนุมัติโดย: {interaction.user.mention}\nID: **{interaction.message.embeds[0].fields[1].value}**",
            color=0x6287f5
        )
        await log_channel.send(embed=embed)
        await interaction.response.send_message("ยืนยันรายงานเรียบร้อยแล้ว", ephemeral=True)

@bot.tree.command(name="report", description="รายงานผู้เล่น")
@app_commands.describe(
    id="ID ผู้กระทำความผิด",
    reason="เหตุผลที่รายงาน",
    profile="โปรไฟล์ของผู้การทำความผิด",
    img1="รูปรายงานแชท",
    img2="รูปรายงานแชท 2",
    img3="รูปรายงานแชท 3",
    img4="รูปรายงานแชท 4"
)
async def report(
    interaction: discord.Interaction,
    id: str,
    reason: str,
    profile: discord.Attachment,
    img1: discord.Attachment = None,
    img2: discord.Attachment = None,
    img3: discord.Attachment = None,
    img4: discord.Attachment = None
):
    await interaction.response.send_message("รายงานสำเร็จ!", ephemeral=True)

    # ห้องที่ส่งรายงาน (ใช้ ID เดิม)
    report_channel = bot.get_channel(REPORT_CHANNEL_ID)
    
    # สร้าง Embed สำหรับรายงาน
    embed = discord.Embed(
        title="รายงาน",
        color=0x6287f5
    )
    embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
    embed.add_field(name="รายงานโดย", value=interaction.user.mention, inline=False)
    embed.add_field(name="ไอดี", value=f"**{id}**", inline=False)
    embed.add_field(name="สาเหตุ", value=f"**{reason}**", inline=False)
    embed.add_field(name="โปรไฟล์", value=f"[ภาพโปรไฟล์]({profile.url})", inline=False)

    # รวบรวมรูปภาพที่แนบมา
    attachments = []
    if img1: attachments.append(img1.url)
    if img2: attachments.append(img2.url)
    if img3: attachments.append(img3.url)
    if img4: attachments.append(img4.url)

    # ส่งรายงานไปยังห้องที่กำหนด
    view = ConfirmView()
    await report_channel.send(
        content="\n".join(attachments) if attachments else None,
        embed=embed,
        view=view
    )

@bot.tree.command(name="help", description="แสดงวิธีการรายงาน")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="คู่มือการรายงาน",
        description="ใช้คำสั่ง `/report` เพื่อรายงานผู้เล่นที่ไม่ปฏิบัติตามกฎ\n",
        color=0x6287f5
    )
    embed.add_field(
        name="วิธีการใช้",
        value=(
            "1. พิมพ์ `/report` ในช่องแชท\n"
            "2. ระบุ ID ผู้เล่นที่ต้องการรายงาน\n"
            "3. เลือกเหตุผลการรายงาน\n"
            "4. แนบภาพหลักฐานตามที่กำหนด\n"
            "5. กดส่งรายงาน"
        ),
        inline=False
    )
    embed.add_field(
        name="📌 ข้อควรระวัง",
        value="กรุณาแนบหลักฐานให้ครบถ้วนและตรวจสอบข้อมูลให้ถูกต้อง",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# อ่านโทเคนจาก Environment Variable
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("กรุณาตั้งค่า Environment Variable: DISCORD_TOKEN")

# สั่งให้บอทเริ่มทำงาน
bot.run(TOKEN)
