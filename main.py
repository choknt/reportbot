import os
import discord
from discord.ext import commands
from discord import app_commands, ui
from flask import Flask

# ตั้งค่า Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "บอทรายงาน Discord กำลังทำงานอยู่!"

# ใช้ Intents.all() เพื่อให้บอทมีสิทธิ์เข้าถึงทุกอย่าง
intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents, activity=None)

# ตั้งค่า Channel ID และ Role ID ที่ใช้ในระบบ
REPORT_CHANNEL_ID = 1333073139562709002  # ห้องที่ส่งรายงาน
LOG_CHANNEL_ID = 1333392202939760690     # ห้อง Log
MOD_ROLE_ID = 1330887708100399135        # บทบาทที่สามารถยืนยันรายงานได้
NOTIFY_ROLE_ID = 1330887708100399135     # บทบาทที่ต้องการแจ้งเตือนเมื่อมีรายงานใหม่

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
        # ปิดปุ่มหลังจากกด
        self.clear_items()
        await interaction.message.edit(view=self)

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
@app_commands.choices(reason=[
    app_commands.Choice(name="สแปม/โฆษนา", value="สแปม/โฆษนา"),
    app_commands.Choice(name="การขายบัญชี", value="การขายบัญชี"),
    app_commands.Choice(name="ชื่อที่ไม่เหมาะสม", value="ชื่อที่ไม่เหมาะสม"),
    app_commands.Choice(name="อนาจาร/18+", value="อนาจาร/18+"),
    app_commands.Choice(name="การเมือง", value="การเมือง"),
])
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

    # ฝังรูปภาพโปรไฟล์ขนาดใหญ่ด้านล่าง Embed
    embed.set_image(url=profile.url)

    # รวบรวมรูปภาพที่แนบมา
    attachments = []
    if img1: attachments.append(img1.url)
    if img2: attachments.append(img2.url)
    if img3: attachments.append(img3.url)
    if img4: attachments.append(img4.url)

    # ส่งรายงานไปยังห้องที่กำหนด
    view = ConfirmView()
    await report_channel.send(
        content=f"<@&{NOTIFY_ROLE_ID}> มีรายงานใหม่!",  # แจ้งเตือนบทบาท
        embed=embed,
        view=view
    )

    # ส่งรูปภาพแยก (ถ้ามี)
    if attachments:
        await report_channel.send("\n".join(attachments))

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
    await interaction.response.send_message(embed=embed, ephemeral=False)  # ให้ทุกคนเห็น

# อ่านโทเคนจาก Environment Variable
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("กรุณาตั้งค่า Environment Variable: DISCORD_TOKEN")

# สั่งให้บอทเริ่มทำงาน
def run_bot():
    bot.run(TOKEN)

if __name__ == "__main__":
    # รัน Flask และบอท Discord พร้อมกัน
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=8080))
    flask_thread.start()
    run_bot()
