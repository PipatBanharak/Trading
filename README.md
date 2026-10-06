# Trading — EA / AI Agent Probability Framework

โปรเจคนี้ใช้ค้นคว้า ออกแบบ และ backtest กฎสำหรับคำนวณความน่าจะเป็นที่ EA หรือ AI Trading Agent จะทำกำไรได้อย่างต่อเนื่อง ตอนนี้เน้น **BTC และทองคำ (XAUUSD / XAUUSDT)**
มี backtest ชุดแรกแล้ว (S1) ใช้เฉพาะ Python standard library และข้อมูลราคาผ่านการตรวจความปลอดภัยก่อนใช้ทุกไฟล์ (ดู `docs/06`)

## โครงสร้าง

```
docs/
  01_research_findings.md        ผลค้นคว้า: base rate รายย่อย, EA, LLM agent, overfitting, กลยุทธ์, สกิล
  02_math_framework.md           สูตร F01–F38
  03_probability_analysis.md     scenario, sensitivity, decision gates G0–G5
  04_ea_market_survey.md         สำรวจ EA/bot ยอดนิยม (ทอง, BTC): เทคนิค ข้อดีข้อเสีย สิ่งที่ยืม/ห้าม
  05_btc_xau_rule_calculations.md  คำนวณกฎสำหรับ BTC + XAU: ต้นทุนต่อ TF, sizing, DD ladder, execution
  06_backtest_s1_results.md      ผล backtest S1 + บันทึกการตรวจความปลอดภัยของข้อมูล
  07_binance_futures_setup.md    ใช้ Binance USDⓈ-M futures: ข้อกฎหมายไทย, เงินต้นที่ต้องใช้, ตั้งค่าบัญชี/คำสั่ง, backtest แบบ Binance
  08_mt5_connection.md           เชื่อม MT5: ทางเลือก A–D, สถาปัตยกรรม, ขั้นตอนติดตั้ง, เงินต้นแบบ lot, ต้นทุน swap
live/
  mt5_bridge.py                  bridge Python ↔ MT5 (dry-run เป็นค่าเริ่มต้น, SL ฝั่ง server, risk ladder, blackout)
backtest/
  fetch.py                       ดาวน์โหลดแบบ allowlist + ตรวจไฟล์ (magic bytes, strict CSV, ราคาอ้างอิง, SHA-256)
  engine.py                      จำลอง sleeve S1 (vol target, cap, buffer, ต้นทุน, funding, stop)
  stats.py                       Sharpe, PSR, DSR, MinTRL, MDD, stationary bootstrap
  run_s1.py                      รันการศึกษา S1 ทั้งหมด → results/s1_results.json
tests/                           unit tests 25 ตัว (look-ahead, ต้นทุน, funding, ไฟล์อันตราย, MT5 bridge กับ terminal จำลอง)
results/s1_results.json          ผลลัพธ์ทั้งหมดของ backtest
data/
  schema.yaml                    Data structure หลัก (v0.2): entities, enums, formula registry, pipeline
  evidence_base.yaml             หลักฐาน + prior
  strategy_catalog.yaml          กลุ่มกลยุทธ์ + prior SR, skew, ต้นทุน, failure modes
  skill_catalog.yaml             สกิล/โมดูล agent + สถาปัตยกรรมที่แนะนำ
  scenarios.yaml                 ตารางคำนวณล่วงหน้า T1–T18
  instruments.yaml               สเปก venue จริง: BTCUSDT perp/spot, BTCUSD CFD, XAUUSD ECN, XAUUSDT perp
  rulebook.yaml                  กฎที่ใช้จริง v0.1 (risk, execution, sleeves, validation, monitoring, ผล backtest)
  market_data_manifest.json      ที่มาและ hash ของข้อมูลราคา (ไม่ commit ข้อมูลดิบ)
```

## ผล backtest S1 (docs/06)
| | Sharpe | CAGR | Max DD | หมายเหตุ |
|---|---|---|---|---|
| BTC 2015–2026 | 1.34 | 6.2% | 6.1% | rolling 2 ปี ลดลงเหลือ **0.21 (2025) / 0.05 (2026)** → edge เสื่อม |
| ETH (OOS) | 1.31 | 5.7% | 5.6% | พารามิเตอร์เดิมทั้งหมด |
| ทอง 1972–2026 (รายเดือน) | 0.28 | 0.9% | 10.1% | ต่ำกว่าการถือทองเฉยๆ แต่ correlation กับ BTC ≈ −0.06 |
| พอร์ต 2015–2026 | 1.33 | 6.9% | 4.6% | ไม่มีปีติดลบ (in-sample) |

ความน่าจะเป็นที่ผล 3 ปีข้างหน้าจะเป็นบวก ≈ **72%** (สมมติ 60% ที่ edge ยังเหลือครึ่งหนึ่ง และ 40% ที่หายไปแล้ว) → แนะนำเริ่มที่ **incubation vol 4%**

```
python3 -I backtest/fetch.py --out <โฟลเดอร์นอก repo>      # ดาวน์โหลด + ตรวจความปลอดภัย
python3 -m backtest.run_s1 --data <โฟลเดอร์เดิม> --out results/s1_results.json
python3 -m unittest discover -s tests
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
| Venue | **Binance USDⓈ-M Futures เท่านั้น** (BTCUSDT + XAUUSDT), isolated 2x, one-way, post-only ก่อน, stop ผ่าน Algo order |
| บัญชีขั้นต่ำ | Incubation (vol 4%) ~$7,000 · vol 8% ~$3,400 · leverage จริง 0.01x ต้องใช้ ~$20,000–$40,000 (BTC min notional 100 USDT) |

**ความน่าจะเป็นที่คาด (3 ปี, vol 8%):** P(กำไรรวมเป็นบวก) ≈ **60%** หรือ ~66% ถ้า sleeve สมมติฐานผ่าน validation; CAGR มัธยฐานถ้า edge จริงอยู่ที่ ~3.5–5.5%/ปี บวกดอกเบี้ยของเงินสดที่ไม่ได้ใช้

## ภาพรวมความน่าจะเป็นตามแนวทาง (ระยะ 3 ปี, vol 10%/ปี — จาก doc 03)

| แนวทาง | P(บวกรวม) | P(บวก & DD<25%) | P(กำไรทุกปี, ≥65% เดือนบวก, DD<15%) |
|---|---|---|---|
| ซื้อ EA/signal ทั่วไป | 18.8% | 18.6% | 0.4% |
| สร้าง EA เองโดยไม่มี validation | 32.9% | 32.5% | 1.3% |
| LLM ตัดสินใจเทรดเอง | 23.1% | 22.9% | 1.0% |
| Pipeline เข้มงวด + กระจาย + ¼–½ Kelly | 65.3% | 64.9% | 10.4% |

## ⚠️ ข้อกฎหมาย (ผู้อยู่ในไทย)
Binance.com ไม่มีใบอนุญาต ก.ล.ต. (ช่วงผ่อนผันสิ้นสุด 28 มิ.ย. 2026) และ Binance TH เป็น spot เท่านั้น → ปรึกษาทนายก่อนใช้เงินจริง ทางเลือกที่ถูกกฎหมายคือ TFEX Gold-D / GF10 และ BTC futures ที่คาดว่าจะเปิด (ดู `docs/07` §0)

## ขั้นถัดไป
1. เปิด network host `data.binance.vision`, `data-api.binance.vision`, `prices.lbma.org.uk` เพื่อทดสอบบนข้อมูล perps/XAUUSDT รายชั่วโมงและ funding จริง (ตอนนี้ถูก policy บล็อก)
2. ยืนยันค่าธรรมเนียม XAUUSDT หลังหมดโปรโมชัน และ swap ของโบรกเกอร์ทองที่จะใช้
3. Incubation (G3) ที่ vol 4% เป็นเวลา 6 เดือน

> ⚠️ เอกสารนี้เป็นการวิเคราะห์เชิงสถิติเพื่อการศึกษา ไม่ใช่คำแนะนำการลงทุน
> Forex ไม่อยู่ภายใต้การกำกับของ ก.ล.ต. และ XAUUSDT ของ Binance อยู่ภายใต้ ADGM FSRA จึงควรตรวจสอบสถานะการกำกับดูแลก่อนใช้งานเสมอ
