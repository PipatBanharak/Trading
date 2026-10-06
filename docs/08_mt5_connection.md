# 08 — เชื่อมระบบกับ MetaTrader 5 (MT5)

> โค้ด: [`live/mt5_bridge.py`](../live/mt5_bridge.py) · tests: [`tests/test_mt5_bridge.py`](../tests/test_mt5_bridge.py) (ใช้ terminal จำลอง ไม่มีการส่งคำสั่งจริง)
> ผล backtest แบบ MT5 CFD อยู่ใน [`results/s1_results.json`](../results/s1_results.json) → `mt5_cfd`

---

## 0. ⚠️ ข้อกฎหมายในไทยสำหรับ MT5
- **ธปท.:** ตามกฎหมายควบคุมการแลกเปลี่ยนเงิน ต้องทำธุรกรรมเงินตราต่างประเทศกับผู้ที่ได้รับอนุญาตเท่านั้น และ**ไม่เคยมีการออกใบอนุญาตให้เทรด Forex เพื่อเก็งกำไร** ([ธปท.](https://www.bot.or.th/th/news-and-media/news/news-20220919.html), [InfoQuest](https://www.infoquest.co.th/?p=235723))
  - โบรกเกอร์ MT5 ต่างประเทศที่ให้เทรด CFD ทอง/BTC จึงไม่ได้รับอนุญาตในไทย
- ใช้ MT5 เชื่อมไปที่ Binance ก็**ไม่ได้แก้ปัญหาใบอนุญาต** เพราะคำสั่งยังไปทำที่ Binance.com (ดู docs/07 §0)
- **ทางที่ถูกกฎหมาย:** TFEX ผ่านโบรกเกอร์ไทย MetaQuotes เคยเปิด gateway MT5 ↔ TFEX ([MetaQuotes](https://www.metatrader5.com/en/news/587)) — ควรสอบถามโบรกเกอร์ไทยว่ายังรองรับ MT5 สำหรับ TFEX Gold-D / GF10 อยู่หรือไม่
- โค้ดนี้จึง**ส่งคำสั่งจริงไม่ได้**จนกว่าจะตั้ง `--live` **และ** `MT5_ALLOW_LIVE=1` ด้วยตัวเองหลังตรวจข้อกฎหมายแล้ว

---

## 1. ทางเลือกในการเชื่อม
| ทางเลือก | วิธีทำงาน | ข้อดี | ข้อเสีย | สรุป |
|---|---|---|---|---|
| **A. Python + แพ็กเกจ `MetaTrader5`** (ทางการ) | Python คุยกับ MT5 terminal ที่เปิดอยู่ในเครื่องเดียวกัน (IPC) | ใช้ engine เดียวกับ backtest ตัวเลข live และ backtest จึงตรงกัน, เขียน test ง่าย | ใช้ได้เฉพาะ **Windows** (Linux ต้องใช้ Wine + `mt5linux`), terminal ต้องเปิดตลอด | **แนะนำ** — มีโค้ดแล้ว |
| B. EA ภาษา MQL5 | เขียนกฎใหม่เป็น EA รันใน terminal | รันบน MQL5 VPS ได้, ใช้ Strategy Tester ได้ | ต้องเขียน logic ซ้ำ เสี่ยงที่ผลจะไม่ตรงกับ backtest | ใช้เป็นตัวตรวจทาน (cross-check) ภายหลัง |
| C. MT5 ↔ Binance bridge | custom symbol ดึงราคาจาก Binance + EA ยิง REST API (WebRequest) | ใช้หน้าจอ MT5 กับ Binance ได้ | ต้องให้ API key กับโค้ดของบุคคลที่สาม, Binance ยังเป็นที่ส่งคำสั่งจริง, ข้อมูลอาจไม่ sync | **ไม่แนะนำ** |
| D. MT5 ของ exchange (Bybit TradFi, BingX) | บัญชี MT5 ที่ exchange เปิดเอง | ฝากด้วย USDT ได้ | เป็น CFD ของ exchange นั้น ประเด็นใบอนุญาตเหมือนข้อ 0 | ไม่แนะนำสำหรับผู้อยู่ในไทย |

---

## 2. สถาปัตยกรรมที่แนะนำ (ทางเลือก A)
```
Windows VPS (หรือ Linux + Wine)
 ├─ MT5 terminal (login โบรกเกอร์, เปิด "Algo Trading")
 └─ Task Scheduler/cron ทุก 15 นาที → python -m live.mt5_bridge --once
        ├─ copy_rates_from_pos(H1) → ราคาปิด 00:00 UTC (แปลงจากเวลา server)
        ├─ backtest.engine → สัญญาณ, σ̂, U (สูตรเดียวกับ backtest)
        ├─ risk: daily loss 1.5%/3%, DD ladder 10/15/20%, cap, ช่วงเวลา, ข่าว
        ├─ order_check() ทุกคำสั่ง → order_send() (เฉพาะ live)
        ├─ SL ฝั่ง server (TRADE_ACTION_SLTP) = 4σ รายวัน (ไม่ต่ำกว่า stops level)
        └─ log JSONL ทุกการตัดสินใจ + state (peak equity, day start)
```
- **ทำไมรันทุก 15 นาที:** สัญญาณเปลี่ยนวันละครั้ง แต่ต้องเช็ก circuit breaker ระหว่างวันด้วย
- **ช่วงเวลาที่ส่งคำสั่งได้:**
  - BTC: 00:16–01:00 UTC และเลี่ยง ±3 นาทีรอบ :15/:30/:45
  - ทอง: 15:30–16:30 UTC
- **ทองช่วงสุดสัปดาห์:**
  - ห้ามเปิดความเสี่ยงใหม่หลังวันศุกร์ 20:30 UTC (ปิดหรือลดสถานะได้)
  - ไม่ส่งคำสั่งช่วงตลาดปิดและช่วง rollover 20:45–22:15 UTC

## 3. ขั้นตอนติดตั้ง
1. **เลือกโบรกเกอร์** แล้วตรวจสเปกในหน้า Specification ของ MT5:
   - contract size (XAUUSD มักเป็น 100 oz/lot), lot ขั้นต่ำ/step
   - swap ทั้งสองฝั่ง, filling mode, stops level
   - timezone ของ server (มักเป็น GMT+2/+3)
2. ติดตั้ง MT5 → เปิด **Algo Trading** → เพิ่ม BTCUSD/XAUUSD ใน Market Watch (ถ้าชื่อมี suffix เช่น `XAUUSD.r` ให้แก้ `BridgeConfig.assets`)
3. ติดตั้ง Python บน Windows แล้ว `pip install MetaTrader5` (ยังไม่ได้ติดตั้งในเครื่องนี้ ต้องทำบนเครื่องที่รัน)
4. ตั้ง environment variables (ห้ามใส่ใน repo): `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER` และ `MT5_PATH` ถ้าจำเป็น
5. **บัญชี demo ก่อน:** `python -m live.mt5_bridge --once` (dry-run) แล้วตรวจ `logs/mt5_decisions.jsonl`
6. รันบน demo 1 เดือน → ตรวจว่า log, SL และ blackout ทำงานถูกต้อง
7. เงินจริง (หลังตรวจข้อกฎหมายตามข้อ 0) ใช้ `MT5_ALLOW_LIVE=1 python -m live.mt5_bridge --once --live` ที่ vol 4%

## 4. ฟังก์ชัน MT5 ที่ใช้
| งาน | ฟังก์ชัน / ค่าที่ใช้ |
|---|---|
| เชื่อมต่อ | `initialize(path, login, password, server)`, ตรวจ `terminal_info().trade_allowed` และ `account_info().trade_allowed` |
| สเปกสัญญา | `symbol_select`, `symbol_info` (`trade_contract_size`, `volume_min/step/max`, `filling_mode`, `trade_stops_level`, `point`, `digits`) |
| ราคา | `symbol_info_tick` (bid/ask, เวลา server); `copy_rates_from_pos(sym, TIMEFRAME_H1, 0, n)` |
| เวลา | เวลาใน rates เป็นเวลา server → หา offset จาก `tick.time − UTC now` (ปัดเป็นชั่วโมง) หรือกำหนดเองใน config |
| สถานะ | `positions_get(symbol)` กรองด้วย magic number (ใช้ได้ทั้งบัญชี netting และ hedging) |
| ส่งคำสั่ง | `order_check(req)` (retcode 0 = ผ่าน) → `order_send(req)` (10009 = DONE, 10010 = partial) |
| ลด/ปิด | `TRADE_ACTION_DEAL` ฝั่งตรงข้าม + `position=ticket` (ไม่เกิด hedge โดยไม่ตั้งใจ) |
| Stop | `TRADE_ACTION_SLTP` ใส่ `position`, `sl` |
| Filling | ใช้ IOC ถ้าโบรกเกอร์รองรับ, ไม่งั้น FOK, ไม่งั้น RETURN (อ่านจาก `filling_mode`) |

---

## 5. เงินต้นที่ต้องใช้บน MT5 (lot ขั้นต่ำ 0.01)
> บน MT5 lot ขั้นต่ำ 0.01 = **0.01 BTC (~$856)** และ **1 oz ทอง (~$4,130)**
> ทำให้ต้องใช้เงินต้นสูงกว่า Binance มาก (Binance ซื้อทองได้ทีละ 0.001 oz)

| ระดับ (leverage จริงตอนสัญญาณเต็ม) | BTC ขั้นต่ำ (สัญญาณ ½) | ทอง ขั้นต่ำ (สัญญาณ ½) | ปรับทีละ 0.25U (BTC / ทอง) |
|---|---|---|---|
| **0.01x** | **$171,200** | **$826,000** | $342k / $1.65M |
| Incubation vol 4% (0.06x / 0.09x) | $28,567 | $91,887 | $57k / $184k |
| Start vol 8% (0.12x / 0.18x) | $14,284 | $45,943 | $29k / $92k |
| Max vol 10% (0.15x / 0.20x) | $11,427 | $41,300 | $23k / $83k |

**ตัวอย่างที่ vol 8% (สัญญาณเต็ม, ปัด lot ลง):**
| Equity | BTC | ทอง |
|---|---|---|
| $10,000 | 0.01 lot (0.086x) | **0 lot** (เป้า $1,798 < 1 oz) |
| $20,000 | 0.02 lot (0.086x) | **0 lot** (เป้า $3,596 < 1 oz) |
| $50,000 | 0.07 lot (0.120x) | 0.02 lot (0.165x) |

→ **บน MT5 ทองเป็นตัวกำหนดเงินขั้นต่ำ** ทางเลือกมีดังนี้:
- (ก) หาโบรกเกอร์ที่มีสัญญาทองเล็กกว่า (micro/0.001 lot)
- (ข) เริ่มเฉพาะ BTC ไปก่อน
- (ค) ใช้เงินทุน ≥ ~$46k (vol 8%) หรือ ~$92k (incubation)
- ห้ามปัด lot **ขึ้น** เพราะจะเกิน cap 0.20x ของ rulebook

---

## 6. ต้นทุน CFD บน MT5 (backtest)
- swap ของ crypto CFD มักเก็บ**ทั้งสองฝั่ง** (เช่น −18%/ปี ทั้ง long และ short)
- swap ทองแล้วแต่โบรกเกอร์

| BTC swap | ทอง swap (long/short) | Sharpe ทอง (ปรับแล้ว) | พอร์ต CAGR | พอร์ต Sharpe | Max DD | P(บวก 3 ปี) รวม* |
|---|---|---|---|---|---|---|
| −18% / −18% | −6% / −1% | 0.12 | 5.76% | 1.12 | 5.3% | ~68% |
| −18% / −18% | −3% / 0% | 0.21 | 6.11% | 1.18 | 5.1% | ~69% |
| −10% / −10% | −6% / −1% | 0.12 | 6.26% | 1.20 | 5.1% | ~70% |
| −10% / −10% | −3% / 0% | 0.21 | 6.62% | 1.27 | 4.9% | ~71% |

\* ให้น้ำหนัก 60% ว่า edge เหลือครึ่งหนึ่ง และ 40% ว่า edge หายไปแล้ว

**สรุป:** swap ที่เก็บทั้งสองฝั่งลด Sharpe ของ BTC เพียงเล็กน้อย (1.34 → 1.24) เพราะขนาดสถานะเล็ก แต่ swap ฝั่ง long ของทองกิน edge ของทองไปมาก → **ให้เลือกโบรกเกอร์ที่ swap ทองต่ำ**

---

## 7. ความปลอดภัยของ bridge
- **Dry-run เป็นค่าเริ่มต้น:** สร้างคำสั่งและตรวจด้วย `order_check` แต่ไม่ส่ง
- ส่งจริงต้องยืนยันสองชั้น: `--live` และ `MT5_ALLOW_LIVE=1`
- credential อ่านจาก environment เท่านั้น และไม่มีรหัสผ่านใน repo
- SL เก็บไว้ที่ server ของโบรกเกอร์ จึงยังทำงานแม้ Python หรือเครื่องดับ
- ปัด lot **ลง**เสมอ: ต่ำกว่า lot ขั้นต่ำ → 0 จึงไม่มีทางเกิน cap
- ลด/ปิดด้วย `position=ticket` ทำให้ไม่เกิด hedge ซ้อนในบัญชีแบบ hedging
- ระบบยอม**ลดหรือปิด**ได้เสมอ แต่ห้าม**เพิ่ม**ความเสี่ยงเมื่อ: ขาดทุนรายวัน ≥ 1.5%, หลังศุกร์ 20:30 UTC (ทอง) หรือ DD ladder ทำงาน
- Unit test 10 กรณีกับ terminal จำลอง (รวม test ทั้งหมด 25 ตัวผ่าน)

## 8. ขั้นถัดไป
1. **ยืนยันว่าจะใช้ MT5 แบบไหน:** โบรกเกอร์ CFD (ทางเลือก A, มีโค้ดแล้ว), MT5 → Binance bridge (C) หรือ MT5 → TFEX ผ่านโบรกเกอร์ไทย
2. ส่งสเปก symbol ของโบรกเกอร์จริง (contract size, lot step, swap, เวลา server) มาเพื่อคำนวณเงินต้นและต้นทุนให้ตรง
3. (ทางเลือก) พอร์ตกฎเป็น EA ภาษา MQL5 เพื่อตรวจกับ Strategy Tester ของ MT5 ด้วย tick data จริงของโบรกเกอร์
