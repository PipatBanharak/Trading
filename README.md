# Trading — EA / AI Agent Probability Framework

ระยะที่ 1 เป็นงานค้นคว้า + **data structure** สำหรับคำนวณความน่าจะเป็นที่ EA หรือ AI Trading Agent จะทำกำไรได้อย่างต่อเนื่อง
**ยังไม่มีโค้ด** และข้อมูลทั้งหมดได้จากการอ่านเว็บ โดยไม่ได้ดาวน์โหลดไฟล์ใดๆ กลับมา

## โครงสร้าง

```
docs/
  01_research_findings.md     ผลค้นคว้า: base rate รายย่อย, EA, LLM agent, งานวิจัย overfitting, กลยุทธ์, สกิล
  02_math_framework.md        สูตร F01–F30 (Sharpe→ความน่าจะเป็น, DSR, PBO, MinTRL, Kelly, RoR, Bayes, MC)
  03_probability_analysis.md  ผลวิเคราะห์ scenario, sensitivity, decision gates, ข้อสรุป
data/
  schema.yaml                 Data structure หลัก: entities, enums, formula registry, pipeline (DAG)
  evidence_base.yaml          หลักฐาน (EvidenceRecord) + prior ที่สกัดออกมา
  strategy_catalog.yaml       กลุ่มกลยุทธ์ + prior SR, skew, ความไวต่อต้นทุน, failure modes
  skill_catalog.yaml          สกิล/โมดูล agent ที่มีผลต่อความน่าจะเป็น + สถาปัตยกรรมที่แนะนำ
  scenarios.yaml              ตารางคำนวณล่วงหน้า T1–T14 + ผล scenario
```

## สรุปผลลัพธ์ (ระยะ 3 ปี, vol 10%/ปี)

| แนวทาง | P(บวกรวม) | P(บวก & DD<25%) | P(กำไรทุกปี, ≥65% เดือนบวก, DD<15%) |
|---|---|---|---|
| ซื้อ EA/signal ทั่วไป | 18.8% | 18.6% | 0.4% |
| สร้าง EA เอง ไม่มี validation | 32.9% | 32.5% | 1.3% |
| LLM ตัดสินใจเทรดเอง | 23.1% | 22.9% | 1.0% |
| **Pipeline เข้มงวด + กระจาย + ¼–½ Kelly** | **65.3%** | **64.9%** | **10.4%** |
| ข้างบน + ผ่าน live incubation | 75.1% | 74.8% | 17.8% |

ประเด็นหลัก:
- ถ้าไม่มี edge เลย ก็ยังมีโอกาส 17–28% ที่ผล 3 ปีจะออกมาเป็นบวกเพราะโชค
- "กำไรทุกเดือน" แทบเป็นไปไม่ได้สำหรับระบบที่ซื่อตรง (SR 2 มีโอกาสกำไรครบ 12/12 เดือนแค่ ~1.9%)
- ตัวกำหนดผลลัพธ์คือ **ต้นทุน, จำนวนครั้งที่ลอง (N), ขนาดไม้ และการกระจาย edge** ส่วนความฉลาดของโมเดลมีผลน้อยกว่า
- Martingale/Grid มี ruin เป็นเรื่องของ "เมื่อไร" ไม่ใช่ "ถ้า"

รายละเอียดอยู่ใน [docs/03_probability_analysis.md](docs/03_probability_analysis.md)

> ⚠️ เอกสารนี้เป็นการวิเคราะห์เชิงสถิติเพื่อการศึกษา ไม่ใช่คำแนะนำการลงทุน
> Forex ไม่อยู่ภายใต้การกำกับของ ก.ล.ต. จึงควรตรวจสอบใบอนุญาตของผู้ให้บริการก่อนใช้งานเสมอ
