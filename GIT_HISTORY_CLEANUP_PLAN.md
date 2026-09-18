# Git History Cleanup Plan

> เอกสารนี้เป็นแผนและคำสั่งตัวอย่างเท่านั้น ยังไม่ควรรันจนกว่าเจ้าของ repository และสมาชิกทีมจะยืนยันร่วมกัน

## 1. สำรอง Repository

สร้าง mirror clone แยกจาก working repository ปัจจุบัน และเก็บสำรองในตำแหน่งที่ไม่เปิดเผยต่อสาธารณะ

```bash
git clone --mirror <private-repository-url> pj_pct-backup.git
```

## 2. Rotate Secret ก่อนล้าง History

ยกเลิกและสร้างค่าใหม่สำหรับ:

- SMTP/Gmail App Password
- Database password
- Django secret key
- First-admin setup token หากเคยนำไปใช้งาน

ห้ามถือว่าการ rewrite history ทำให้ secret เดิมกลับมาปลอดภัย เพราะอาจมี clone, cache หรือ log ภายนอกอยู่แล้ว

## 3. ติดตั้ง git-filter-repo

```bash
python -m pip install git-filter-repo
```

ควรทำงานบน clone ใหม่ที่สะอาดและตรวจ remote ให้ถูกต้องก่อนทุกครั้ง

## 4. นำไฟล์ต้องห้ามออกจากทุก Commit

```bash
git filter-repo --path .env --path media/ --path debug.log --invert-paths
```

สำหรับ credential ที่เคย hard-code ในไฟล์อื่น ให้สร้าง `replacements.txt` ไว้นอก repository โดยใส่ค่าจริงเดิมและ replacement ตามรูปแบบของ `git filter-repo --replace-text` ห้าม commit ไฟล์นี้

```bash
git filter-repo --replace-text C:/secure-location/replacements.txt
```

ต้องครอบคลุม Django secret key, database username/password และ secret อื่นที่พบจาก secret scanner

## 5. ตรวจทุก Branch และ Tag

```bash
git branch --all
git tag --list
git log --all -- .env media debug.log
```

ตรวจว่าไม่มี blob หรือ path ต้องห้ามหลงเหลือใน ref อื่น

## 6. Verify หลัง Rewrite

```bash
git log --all -- .env media debug.log
git rev-list --objects --all
```

จากนั้นรัน secret scanner เช่น Gitleaks หรือ TruffleHog กับทุก branch และ tag โดยไม่แสดงค่า secret เต็มในรายงาน

## 7. Force Push หลังเจ้าของยืนยันเท่านั้น

```bash
git push --force --all origin
git push --force --tags origin
```

คำสั่งนี้เปลี่ยนประวัติร่วมกันของทีม ต้องได้รับการยืนยันก่อนรันและต้องแจ้งสมาชิกทุกคน

## 8. ให้สมาชิกทีม Re-clone

หลัง force-push สมาชิกทีมควรสำรองงานที่ยังไม่ commit แล้ว clone repository ใหม่ เพื่อป้องกัน commit เก่านำ secret หรือ media กลับเข้ามาอีก

## เกณฑ์ก่อนเปิด Public

- Secret เดิมถูก revoke/rotate แล้ว
- `.env`, `media/` และ `debug.log` ไม่อยู่ใน history ทุก ref
- Secret scanner ไม่พบ credential จริง
- Repository ใช้ `.env.example` ที่ไม่มีค่าจริง
- สมาชิกทีมยืนยันว่าไม่มี branch หรือ tag เก่าที่ต้องเก็บเป็นสาธารณะ
