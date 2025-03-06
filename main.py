import os
import discord
from discord.ext import commands
from discord import app_commands, ui
from flask import Flask
import threading
import random
import string

# ตั้งค่า Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "บอทรายงาน Discord กำลังทำงานอยู่!"

def run_flask():
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

# ใช้ Intents.all() เพื่อให้บอทมีสิทธิ์เข้าถึงทุกอย่าง
intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents, activity=None)

# ตั้งค่า Channel ID และ Role ID ที่ใช้ในระบบ
REPORT_CHANNEL_ID = 1333073139562709002
LOG_CHANNEL_ID = 1333392202939760690
MOD_ROLE_ID = 1330887708100399135
NOTIFY_ROLE_ID = 1330887708100399135

# สร้างรหัสเคสแบบสุ่ม
def generate_case_id():
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{random.randint(1000000000000, 9999999999999)}-{random_part}"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name="/report เพื่อรายงาน"
            )
        )
    except Exception as e:
        print(f"Error syncing commands: {e}")




async def send_dm_notification(user: discord.User, caseclass ConfirmView(ui.View):
    def __init__(self, case_id: str):
        super().__init__(timeout=None)
        self.case_id = case_id

    @ui.button(label="ยืนยัน", style=discord.ButtonStyle.green, emoji="✅", custom_id="confirm_report")
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        try:
            # ตรวจสอบว่า interaction อยู่ในเซิร์ฟเวอร์
            if interaction.guild is None:
                await interaction.response.send_message("คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์!", ephemeral=True)
                return

            # ตรวจสอบสิทธิ์ role
            role = interaction.guild.get_role(MOD_ROLE_ID)
            if role is None or role not in interaction.user.roles:
                await interaction.response.send_message("คุณไม่มีสิทธิ์ยืนยันรายงานนี้", ephemeral=True)
                return

            # ตอบกลับ interaction ก่อนแก้ไขข้อความ
            await interaction.response.defer()

            # ส่งข้อความไปยังช่อง log
            log_channel = bot.get_channel(LOG_CHANNEL_ID)
            if log_channel is None:
                log_channel = await bot.fetch_channel(LOG_CHANNEL_ID)

            embed = discord.Embed(
                description=f"ได้รับการอนุมัติโดย: {interaction.user.mention}\nID รายงาน: **{self.case_id}**",
                color=0x6287f5
            )
            await log_channel.send(embed=embed)

            # แจ้งผู้ใช้ที่รายงาน (จัดการข้อผิดพลาดหากส่ง DM ไม่สำเร็จ)
            try:
                original_embed = interaction.message.embeds[0]
                reported_user_id = original_embed.fields[1].value.split("**")[1]  # ดึงไอดีผู้ใช้จาก embed
                reported_user = await bot.fetch_user(reported_user_id)
                await send_report_processed_notification(reported_user, self.case_id, interaction.user)
            except discord.Forbidden:
                print(f"ไม่สามารถส่ง DM ไปยังผู้ใช้ {reported_user_id} ได้ เนื่องจากผู้ใช้ปิดการรับข้อความจากบอทหรือเซิร์ฟเวอร์")
            except Exception as e:
                print(f"เกิดข้อผิดพลาดในการส่ง DM: {e}")

            # ลบปุ่มออก
            self.clear_items()
            await interaction.message.edit(view=self)

            # แจ้งผู้กดปุ่มว่ายืนยันเรียบร้อยแล้ว
            await interaction.followup.send("ยืนยันรายงานเรียบร้อยแล้ว", ephemeral=True)
        except Exception as e:
            print(f"Error in ConfirmView: {e}")
            await interaction.followup.send("เกิดข้อผิดพลาดในการยืนยันรายงาน", ephemeral=True)_id: str, reported_id: str, reason: str):
    try:
        embed = discord.Embed(
            title="รายงานของคุณได้รับการสร้างขึ้นแล้ว",
            description=(
                "ขอบคุณสำหรับการรายงานของคุณ จะมีผู้ดูแลระบบดูแลเรื่องนี้\n\n"
                f"**รหัสรายงาน:**\n{case_id}\n\n"
                f"**ผู้เล่นที่รายงาน:**\n{user.mention}\n\n"
                f"**ไอดีผู้เล่นที่โดนรายงาน:**\n{reported_id}\n\n"
                f"**เหตุผล:**\n{reason}\n\n"
                "คุณจะได้รับแจ้งทันทีเมื่อรายงานของคุณได้รับการประมวลผลแล้ว"
            ),
            color=0x6287f5
        )
        await user.send(embed=embed)
    except discord.Forbidden:
        print(f"ไม่สามารถส่ง DM ไปยัง {user.name} ได้ เนื่องจากผู้ใช้ปิดการรับข้อความจากบอทหรือเซิร์ฟเวอร์")

async def send_report_processed_notification(user: discord.User, case_id: str, moderator: discord.Member):
    try:
        embed = discord.Embed(
            title=f"อัปเดตรายงานของคุณ #{case_id}",
            description=(
                "รายงานของคุณได้รับการจัดการแล้ว\n\n"
                f"**อนุมัติโดย:**\n{moderator.mention}\n\n"
                "ขอบคุณสำหรับการรายงาน"
            ),
            color=0x6287f5
        )
        await user.send(embed=embed)
    except discord.Forbidden:
        print(f"ไม่สามารถส่ง DM ไปยัง {user.name} ได้ เนื่องจากผู้ใช้ปิดการรับข้อความจากบอทหรือเซิร์ฟเวอร์")

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
    app_commands.Choice(name="คำหยาบคาย", value="คำหยาบคาย"),
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

    report_channel = bot.get_channel(REPORT_CHANNEL_ID)
    if report_channel is None:
        report_channel = await bot.fetch_channel(REPORT_CHANNEL_ID)

    # สร้างรหัสเคส
    case_id = generate_case_id()

    # สร้าง embed สำหรับห้องรายงาน
    embed = discord.Embed(title="รายงานใหม่", color=0x6287f5)
    embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
    embed.add_field(name="รหัสรายงาน", value=f"**{case_id}**", inline=False)
    embed.add_field(name="รายงานโดย", value=interaction.user.mention, inline=False)
    embed.add_field(name="ไอดีผู้เล่นที่โดนรายงาน", value=f"**{id}**", inline=False)
    embed.add_field(name="เหตุผล", value=f"**{reason}**", inline=False)
    embed.set_image(url=profile.url)

    # ส่ง embed ไปยังห้องรายงาน
    view = ConfirmView(case_id)
    await report_channel.send(content=f"<@&{NOTIFY_ROLE_ID}> มีรายงานใหม่!", embed=embed, view=view)

    # ส่งภาพหลักฐาน (ถ้ามี)
    attachments = [img1, img2, img3, img4]
    for img in attachments:
        if img:
            await report_channel.send(file=await img.to_file())

    # ส่ง DM แจ้งเตือนผู้ใช้
    await send_dm_notification(interaction.user, case_id, id, reason)

@bot.tree.command(name="help", description="แสดงวิธีการรายงาน")
async def help(interaction: discord.Interaction):
    if interaction.user.id == 770227564442026024:
        embed = discord.Embed(
            title="สวัสดีค่ะคุณโชค",
            description=(
                "คุณต้องการแบนใครคะ ตอนนี้ sare security of chok พร้อมแล้ว\n"
                "และตอนนี้จะรับคำสั่งแค่คุณโชค ให้ตบหัวพ่อมันเลยไหม aura\n\n"
                "เพื่อ chok snow\n\n"
                "ไฮ โชค"
            ),
            color=0x6287f5
        )
    else:
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

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("กรุณาตั้งค่า Environment Variable: DISCORD_TOKEN")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    bot.run(TOKEN)
