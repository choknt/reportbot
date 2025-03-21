import os
import discord
from discord.ext import commands
from discord import app_commands, ui
from flask import Flask
import threading
import random
import string
from pymongo import MongoClient
from datetime import datetime
import logging

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ตั้งค่า Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "บอทรายงาน Discord กำลังทำงานอยู่!"

def run_flask():
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, activity=None)

# ตั้งค่า Channel ID และ Role ID
REPORT_CHANNEL_ID = 1333073139562709002
LOG_CHANNEL_ID = 1333392202939760690
MOD_ROLE_ID = 1330887708100399135
NOTIFY_ROLE_ID = 1330887708100399135

# Role ID สำหรับแรงค์
NEW_REPORTER_ROLE = 67557444
EXPERIENCED_REPORTER_ROLE = 87565453
VETERAN_REPORTER_ROLE = 987765

# เชื่อมต่อ MongoDB
mongo_url = os.getenv("MONGO_URL")
try:
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    client.server_info()  # ทดสอบการเชื่อมต่อ
    db = client["discord_bot"]
    ranks_collection = db["ranks"]
    logging.info("Connected to MongoDB successfully")
except Exception as e:
    logging.error(f"Failed to connect to MongoDB: {e}")
    raise

# ฟังก์ชันจัดการแรงค์
def update_rank(user_id, guild):
    try:
        user_data = ranks_collection.find_one({"user_id": str(user_id)}) or {"reports": 0}
        reports = user_data["reports"] + 1
        ranks_collection.update_one(
            {"user_id": str(user_id)},
            {"$set": {"reports": reports, "last_updated": datetime.utcnow()}},
            upsert=True
        )
        if reports <= 5:
            rank, role_id = "ผู้ใช้ใหม่ (New Reporter)", NEW_REPORTER_ROLE
        elif 6 <= reports <= 20:
            rank, role_id = "ผู้รายงานที่เชี่ยวชาญ (Experienced Reporter)", EXPERIENCED_REPORTER_ROLE
        else:
            rank, role_id = "ผู้รายงานระดับสูง (Veteran Reporter)", VETERAN_REPORTER_ROLE
        return rank, role_id
    except Exception as e:
        logging.error(f"Error updating rank for user {user_id}: {e}")
        return "ผู้ใช้ใหม่ (New Reporter)", NEW_REPORTER_ROLE

def get_rank(user_id):
    try:
        user_data = ranks_collection.find_one({"user_id": str(user_id)}) or {"reports": 0}
        return {"reports": user_data["reports"]}
    except Exception as e:
        logging.error(f"Error getting rank for user {user_id}: {e}")
        return {"reports": 0}

def get_all_ranks():
    try:
        ranks = {}
        for user_data in ranks_collection.find():
            ranks[user_data["user_id"]] = {"reports": user_data["reports"]}
        return ranks
    except Exception as e:
        logging.error(f"Error getting all ranks: {e}")
        return {}

async def update_user_role(guild, user_id, new_role_id):
    member = guild.get_member(int(user_id))
    if not member:
        logging.warning(f"Member {user_id} not found in guild")
        return
    
    rank_roles = [NEW_REPORTER_ROLE, EXPERIENCED_REPORTER_ROLE, VETERAN_REPORTER_ROLE]
    roles_to_remove = [role for role in rank_roles if role != new_role_id]
    
    try:
        for role_id in roles_to_remove:
            role = guild.get_role(role_id)
            if role and role in member.roles:
                await member.remove_roles(role)
        
        new_role = guild.get_role(new_role_id)
        if new_role and new_role not in member.roles:
            await member.add_roles(new_role)
        logging.info(f"Updated roles for {user_id} to role {new_role_id}")
    except Exception as e:
        logging.error(f"Error updating role for {user_id}: {e}")

def generate_case_id():
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{random.randint(1000000000000, 9999999999999)}-{random_part}"

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        logging.info(f"Synced {len(synced)} commands")
        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name="/report เพื่อรายงาน"
            )
        )
    except Exception as e:
        logging.error(f"Error syncing commands: {e}")

class ConfirmView(ui.View):
    def __init__(self, case_id: str, reporter_id: int):
        super().__init__(timeout=None)
        self.case_id = case_id
        self.reporter_id = reporter_id

    @ui.button(label="ยืนยัน", style=discord.ButtonStyle.green, emoji="✅", custom_id="confirm_report")
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        try:
            if interaction.guild is None:
                await interaction.response.send_message("คำสั่งนี้ใช้ได้เฉพาะในเซิร์ฟเวอร์!", ephemeral=True)
                return

            role = interaction.guild.get_role(MOD_ROLE_ID)
            if role is None or role not in interaction.user.roles:
                await interaction.response.send_message("คุณไม่มีสิทธิ์ยืนยันรายงานนี้", ephemeral=True)
                return

            await interaction.response.defer()

            log_channel = bot.get_channel(LOG_CHANNEL_ID) or await bot.fetch_channel(LOG_CHANNEL_ID)
            embed = discord.Embed(
                description=f"ได้รับการอนุมัติโดย: {interaction.user.mention}\nID รายงาน: **{self.case_id}**",
                color=0x6287f5
            )
            await log_channel.send(embed=embed)

            try:
                reported_user = await bot.fetch_user(self.reporter_id)
                await send_report_processed_notification(reported_user, self.case_id, interaction.user)
            except discord.Forbidden:
                logging.warning(f"Cannot send DM to user {self.reporter_id}")
            except Exception as e:
                logging.error(f"Error sending DM: {e}")

            self.clear_items()
            await interaction.message.edit(view=self)
            await interaction.followup.send("ยืนยันรายงานเรียบร้อยแล้ว", ephemeral=True)
        except Exception as e:
            logging.error(f"Error in ConfirmView: {e}")
            await interaction.followup.send("เกิดข้อผิดพลาดในการยืนยันรายงาน", ephemeral=True)

async def send_dm_notification(user: discord.User, case_id: str, reported_id: str, reason: str, rank: str):
    try:
        embed = discord.Embed(
            title="รายงานของคุณได้รับการสร้างขึ้นแล้ว",
            description=(
                f"**รหัสรายงาน:**\n{case_id}\n\n"
                f"**ผู้เล่นที่รายงาน:**\n{user.mention}\n\n"
                f"**ไอดีผู้เล่นที่โดนรายงาน:**\n{reported_id}\n\n"
                f"**เหตุผล:**\n{reason}\n\n"
                f"**ระดับปัจจุบันของคุณ:**\n{rank}\n\n"
                "ดูผลได้ที่ <#1333073139562709002>"
            ),
            color=0x6287f5
        )
        await user.send(embed=embed)
    except discord.Forbidden:
        logging.warning(f"Cannot send DM to {user.name}")

async def send_report_processed_notification(user: discord.User, case_id: str, moderator: discord.Member):
    try:
        embed = discord.Embed(
            title=f"อัปเดตรายงานของคุณ #{case_id}",
            description=(
                "รายงานของคุณได้รับการจัดการแล้ว\n\n"
                f"**อนุมัติโดย:**\n{moderator.mention}\n\n"
                "ขอบคุณสำหรับการช่วยเหลือ!"
            ),
            color=0x6287f5
        )
        await user.send(embed=embed)
    except discord.Forbidden:
        logging.warning(f"Cannot send DM to {user.name}")

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
    try:
        await interaction.response.send_message("รายงานสำเร็จ!", ephemeral=True)

        report_channel = bot.get_channel(REPORT_CHANNEL_ID) or await bot.fetch_channel(REPORT_CHANNEL_ID)
        case_id = generate_case_id()
        embed = discord.Embed(title="รายงานใหม่", color=0x6287f5)
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
        embed.add_field(name="รหัสรายงาน", value=f"**{case_id}**", inline=False)
        embed.add_field(name="รายงานโดย", value=interaction.user.mention, inline=False)
        embed.add_field(name="ไอดีผู้เล่นที่โดนรายงาน", value=f"**{id}**", inline=False)
        embed.add_field(name="เหตุผล", value=f"**{reason}**", inline=False)
        embed.set_image(url=profile.url)

        rank, role_id = update_rank(interaction.user.id, interaction.guild)
        await update_user_role(interaction.guild, interaction.user.id, role_id)

        view = ConfirmView(case_id, interaction.user.id)
        await report_channel.send(content=f"<@&{NOTIFY_ROLE_ID}> มีรายงานใหม่!", embed=embed, view=view)

        attachments = [img1, img2, img3, img4]
        for img in attachments:
            if img:
                await report_channel.send(file=await img.to_file())

        await send_dm_notification(interaction.user, case_id, id, reason, rank)
    except Exception as e:
        logging.error(f"Error in report command: {e}")
        await interaction.followup.send("เกิดข้อผิดพลาดในการส่งรายงาน", ephemeral=True)

@bot.tree.command(name="rank", description="ดูอันดับการรายงาน")
async def rank(interaction: discord.Interaction):
    try:
        ranks = get_all_ranks()
        if not ranks:
            await interaction.response.send_message("ยังไม่มีข้อมูลอันดับการรายงาน", ephemeral=True)
            return

        sorted_ranks = sorted(ranks.items(), key=lambda x: x[1]["reports"], reverse=True)
        top_10 = sorted_ranks[:10]

        embed = discord.Embed(
            title="🏆 อันดับผู้รายงานยอดเยี่ยม",
            color=0x6287f5,
            timestamp=datetime.utcnow()
        )

        for i, (user_id, data) in enumerate(top_10, 1):
            try:
                user = await bot.fetch_user(int(user_id))
                user_display = f"{user.name}#{user.discriminator}"
            except:
                user_display = f"User ID: {user_id}"
            
            reports = data["reports"]
            if reports <= 5:
                rank = "ผู้ใช้ใหม่"
            elif 6 <= reports <= 20:
                rank = "ผู้รายงานที่เชี่ยวชาญ"
            else:
                rank = "ผู้รายงานระดับสูง"

            embed.add_field(
                name=f"#{i} - {user_display}",
                value=f"ระดับ: {rank} | รายงาน: {data['reports']}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        logging.error(f"Error in rank command: {e}")
        await interaction.response.send_message("เกิดข้อผิดพลาดในการดึงอันดับ", ephemeral=True)

# คำสั่ง help และ gce_staff คงเดิมตามโค้ดต้นฉบับ

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
 
@bot.tree.command(name="gce_staff", description="สำหรับพนักงานของ galacticcore ")  
async def gce_staff(interaction: discord.Interaction):  
   user = interaction.user  
   guild_source = bot.get_guild(1219836401902813296)  # เซิร์ฟเวอร์ต้นทาง  
   guild_target = bot.get_guild(1329694920046280747)  # เซิร์ฟเวอร์เป้าหมาย  
 
   if not guild_source or not guild_target:  
       await interaction.response.send_message("ไม่สามารถเข้าถึงเซิร์ฟเวอร์ที่กำหนดได้", ephemeral=True)  
       return  
 
   member_source = guild_source.get_member(user.id)  
   member_target = guild_target.get_member(user.id)  
 
   if not member_source:  
       await interaction.response.send_message("คุณไม่ได้อยู่ในเซิร์ฟเวอร์ต้นทาง", ephemeral=True)  
       return  
 
   role_required = guild_source.get_role(1351916781572329544)  
   role_to_give = guild_target.get_role(1351918569562181673)  
 
   if not role_required or not role_to_give:  
       await interaction.response.send_message("ไม่พบบทบาทที่กำหนดในเซิร์ฟเวอร์", ephemeral=True)  
       return  
 
   if role_required not in member_source.roles:  
       await interaction.response.send_message("คุณไม่มีบทบาทที่จำเป็นในเซิร์ฟเวอร์", ephemeral=True)  
       return  
 
   if not member_target:  
       await interaction.response.send_message("คุณไม่ได้เป็นพนักงานของเรา", ephemeral=True)  
       return

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("กรุณาตั้งค่า Environment Variable: DISCORD_TOKEN")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    bot.run(TOKEN)