# 🚀 Discord Report Bot

บอทสำหรับรายงานผู้เล่นใน Discord ด้วย **Python + Discord.py + Flask**  
รองรับการทำงานบนเซิร์ฟเวอร์คลาวด์และให้ผู้ดูแลสามารถยืนยันรายงานผ่านปุ่ม ✅  

---

## 📌 คำอธิบายโดยรวม
บอทนี้ทำหน้าที่:
1. เปิดเซิร์ฟเวอร์ **Flask** เพื่อแสดงสถานะของบอท  
2. ให้ผู้ใช้สามารถรายงานผู้เล่นผ่านคำสั่ง **`/report`**  
3. ให้ผู้ดูแลสามารถยืนยันรายงานผ่านปุ่ม **"ยืนยัน"**  
4. มีคำสั่ง **`/help`** สำหรับให้ข้อมูลเกี่ยวกับการใช้งาน  

---

## 🛠️ เทคโนโลยีที่ใช้
- **[discord.py](https://discordpy.readthedocs.io/en/stable/)** - สร้างบอท Discord  
- **[Flask](https://flask.palletsprojects.com/)** - รองรับ Web Hosting  
- **Threading** - รัน Flask และ Discord bot พร้อมกัน  

---

## 📂 โครงสร้างหลักของโค้ด

### 1️⃣ ตั้งค่า Flask
```python
app = Flask(__name__)

@app.route('/')
def home():
    return "บอทรายงาน Discord กำลังทำงานอยู่!"

✅ สร้างเซิร์ฟเวอร์ Flask
✅ หน้า / จะแสดงสถานะ "บอทรายงาน Discord กำลังทำงานอยู่!"


```
---

2️⃣ ตั้งค่าบอท Discord
```python
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, activity=None)

✅ ใช้ Intents.all() เพื่อให้บอทเข้าถึงทุกกิจกรรม
✅ คำสั่งบอทเริ่มต้นด้วย !
```

---

3️⃣ กำหนดค่า Channel ID & Role ID
```python
REPORT_CHANNEL_ID = 1333073139562709002  # ห้องรายงาน
LOG_CHANNEL_ID = 1333392202939760690     # ห้องบันทึก
MOD_ROLE_ID = 1330887708100399135        # บทบาทผู้ดูแล
NOTIFY_ROLE_ID = 1330887708100399135     # บทบาทแจ้งเตือน

✅ กำหนดช่องทางการแจ้งเตือนและบทบาทที่เกี่ยวข้อง
```

---

4️⃣ เมื่อบอทออนไลน์
```python
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} commands")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="/report เพื่อรายงานผู้เล่น"
        )
    )
```
✅ แสดงข้อความ "Logged in as ..." เมื่อล็อกอินสำเร็จ
✅ ซิงค์คำสั่ง /report และ /help
✅ ตั้งสถานะบอทให้แสดง "กำลังดู /report เพื่อรายงานผู้เล่น"

---

5️⃣ คำสั่ง /report (รายงานผู้เล่น)
```python
@bot.tree.command(name="report", description="รายงานผู้เล่น")
@app_commands.describe(
    id="ID ผู้กระทำความผิด",
    reason="เหตุผลที่รายงาน",
    profile="โปรไฟล์ของผู้กระทำความผิด",
    img1="รูปรายงานแชท",
    img2="รูปรายงานแชท 2",
    img3="รูปรายงานแชท 3",
    img4="รูปรายงานแชท 4"
)
```
✅ รายงานผู้เล่นที่ละเมิดกฎ
✅ รองรับการแนบ หลักฐานภาพถ่าย (สูงสุด 4 รูป)

---

```python
6️⃣ ฝังรายงานลงในช่องแชท

embed = discord.Embed(
    title="รายงาน",
    color=0x6287f5
)
embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
embed.add_field(name="รายงานโดย", value=interaction.user.mention, inline=False)
embed.add_field(name="ไอดี", value=f"**{id}**", inline=False)
embed.add_field(name="สาเหตุ", value=f"**{reason}**", inline=False)
embed.set_image(url=profile.url)
```
✅ ฝัง Embed แสดงรายละเอียดรายงาน
✅ แนบรูปโปรไฟล์ของผู้ถูกรายงาน


---

7️⃣ ปุ่ม "ยืนยัน" สำหรับผู้ดูแล
```python
class ConfirmView(ui.View):
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
        self.clear_items()
        await interaction.message.edit(view=self)
```
✅ ปุ่ม "ยืนยัน" สำหรับผู้ดูแล
✅ รายงานที่ยืนยันจะถูกบันทึกลง LOG Channel


---

8️⃣ คำสั่ง /help (แสดงวิธีรายงาน)
```python
@bot.tree.command(name="help", description="แสดงวิธีการรายงาน")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="คู่มือการรายงาน",
        description="ใช้คำสั่ง `/report` เพื่อรายงานผู้เล่นที่ไม่ปฏิบัติตามกฎ\n",
        color=0x6287f5
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)
```
✅ แสดง คู่มือการใช้งานคำสั่ง /report


---

9️⃣ รัน Flask และบอทพร้อมกัน
```python
def run_bot():
    bot.run(TOKEN)

if __name__ == "__main__":
    from threading import Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=8080))
    flask_thread.start()
    run_bot()
```
✅ ใช้ Threading เพื่อให้ Flask และบอททำงานพร้อมกัน
✅ บอทจะอ่าน Token จาก Environment Variable


---

🚀 วิธีติดตั้ง

1️⃣ ตั้งค่า DISCORD_TOKEN ใน Environment Variable
2️⃣ ติดตั้งไลบรารี
```python
pip install discord.py flask
```
3️⃣ รันบอท
```python
python bot.py
```

---

🎯 สรุป

บอทนี้ช่วยให้สามารถ รายงานผู้เล่นผ่าน Discord ได้ง่าย ๆ พร้อมระบบ ยืนยันรายงาน โดยผู้ดูแล
✅ เพิ่มความสะดวกในการดูแลชุมชน
✅ ลดภาระงานของแอดมิน
✅ ใช้งานง่าย เพียงใช้คำสั่ง /report




