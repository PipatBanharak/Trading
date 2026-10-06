# Trading — EA / AI Agent Probability Framework

โปรเจคนี้ยังอยู่ในขั้นค้นคว้าและออกแบบ data structure/กฎ สำหรับคำนวณความน่าจะเป็นที่ EA หรือ AI Trading Agent จะทำกำไรได้อย่างต่อเนื่อง ตอนนี้เน้น **BTC และทองคำ (XAUUSD / XAUUSDT)**
**ยังไม่มีโค้ด** และข้อมูลทั้งหมดได้จากการอ่านเว็บ โดยไม่ได้ดาวน์โหลดไฟล์หรือข้อมูลราคาใดๆ กลับมา

## โครงสร้าง

```
docs/
  01_research_findings.md        ผลค้นคว้า: base rate รายย่อย, EA, LLM agent, overfitting, กลยุทธ์, สกิล
  02_math_framework.md           สูตร F01–F38
  03_probability_analysis.md     scenario, sensitivity, decision gates G0–G5
  04_ea_market_survey.md         สำรวจ EA/bot ยอดนิยม (ทอง, BTC): เทคนิค ข้อดีข้อเสีย สิ่งที่ยืม/ห้าม
  05_btc_xau_rule_calculations.md  คำนวณกฎสำหรับ BTC + XAU: ต้นทุนต่อ TF, sizing, DD ladder, execution
data/
  schema.yaml                    Data structure หลัก (v0.2): entities, enums, formula registry, pipeline
  evidence_base.yaml             หลักฐาน + prior
  strategy_catalog.yaml          กลุ่มกลยุทธ์ + prior SR, skew, ต้นทุน, failure modes
  skill_catalog.yaml             สกิล/โมดูล agent + สถาปัตยกรรมที่แนะนำ
  scenarios.yaml                 ตารางคำนวณล่วงหน้า T1–T18
  instruments.yaml               สเปก venue จริง: BTCUSDT perp/spot, BTCUSD CFD, XAUUSD ECN, XAUUSDT perp
  rulebook.yaml                  กฎที่ใช้จริง v0.1 (risk, execution, sleeves, validation, monitoring)
```

## สรุปกฎหลักสำหรับ BTC + XAU (รายละเอียดอยู่ใน `data/rulebook.yaml`)

| หัวข้อ | กฎ |
|---|---|
| กลยุทธ์แกน | Trend ensemble (lookback 14/28/56/112 วัน) แบบ vol-target ใช้ชุดเดียวกันทั้ง BTC และทอง (N = 1 ไม่ optimize) |
| TF ขั้นต่ำ | BTCUSDT / XAUUSDT บน Binance: **H4+** (H1 ได้ถ้าเข้าด้วย maker); ทอง ECN: ต้นทุนต่ำ แต่ช่วงข่าวต้องใช้ H1+ |
| ขนาดไม้ | vol พอร์ต 8% (incubation 4%, เพดาน 10%) ≈ 0.17–0.21 Kelly → notional BTC ~0.12× และทอง ~0.18× ของ equity |
| Cap | BTC ≤ 0.15× (stress crash −40%), ทอง ≤ 0.20× (gap สุดสัปดาห์ 10%), leverage ต่อตำแหน่ง ≤ 2× |
| ขีดจำกัดขาดทุน | รายวัน 1.5% (หยุดเปิดใหม่) / 3% (ปิดทั้งหมด); DD 10% ทบทวน / 15% ลดครึ่ง / 20% หยุด |
| Execution | BTC rebalance 00:20 UTC (หลัง funding) เลี่ยงนาที :00/:15/:30/:45; ทอง 15:30–16:30 UTC; blackout ช่วง rollover และข่าว; XAUUSDT ตรวจ cap ก่อนปิดศุกร์ 21:00 UTC |
| ห้ามใช้ | grid, martingale, DCA safety orders, scalping ที่ TF ต่ำกว่าขั้นต่ำ, ระยะเป็น $ ตายตัว |
| บัญชีขั้นต่ำ | ~$3,000 บน Binance; ทอง ECN CFD เหมาะเมื่อ equity เกิน ~$90k (ขั้นต่ำ 1 oz) |

**ความน่าจะเป็นที่คาด (3 ปี, vol 8%):** P(กำไรรวมเป็นบวก) ≈ **60%** หรือ ~66% ถ้า sleeve สมมติฐานผ่าน validation; CAGR มัธยฐานถ้า edge จริงอยู่ที่ ~3.5–5.5%/ปี บวกดอกเบี้ยของเงินสดที่ไม่ได้ใช้

## ภาพรวมความน่าจะเป็นตามแนวทาง (ระยะ 3 ปี, vol 10%/ปี — จาก doc 03)

| แนวทาง | P(บวกรวม) | P(บวก & DD<25%) | P(กำไรทุกปี, ≥65% เดือนบวก, DD<15%) |
|---|---|---|---|
| ซื้อ EA/signal ทั่วไป | 18.8% | 18.6% | 0.4% |
| สร้าง EA เองโดยไม่มี validation | 32.9% | 32.5% | 1.3% |
| LLM ตัดสินใจเทรดเอง | 23.1% | 22.9% | 1.0% |
| Pipeline เข้มงวด + กระจาย + ¼–½ Kelly | 65.3% | 64.9% | 10.4% |

## ขั้นถัดไป (ต้องได้รับอนุญาต)
1. ดาวน์โหลดข้อมูลราคาในอดีต (BTC, ทอง, funding history) เพื่อ backtest S1 ตาม validation gates
2. ยืนยันค่าธรรมเนียม XAUUSDT หลังหมดโปรโมชัน และ swap ของโบรกเกอร์ทองที่จะใช้
3. เริ่มเขียนโค้ดตาม `data/schema.yaml` และ `data/rulebook.yaml`

> ⚠️ เอกสารนี้เป็นการวิเคราะห์เชิงสถิติเพื่อการศึกษา ไม่ใช่คำแนะนำการลงทุน
> Forex ไม่อยู่ภายใต้การกำกับของ ก.ล.ต. และ XAUUSDT ของ Binance อยู่ภายใต้ ADGM FSRA จึงควรตรวจสอบสถานะการกำกับดูแลก่อนใช้งานเสมอ
