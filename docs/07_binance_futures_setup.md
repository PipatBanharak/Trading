# 07 — ใช้ Binance USDⓈ-M Futures (BTCUSDT + XAUUSDT)

> ผลตัวเลขอยู่ใน [`results/s1_results.json`](../results/s1_results.json) → `binance_futures`
> กฎที่แก้แล้วอยู่ใน [`data/rulebook.yaml`](../data/rulebook.yaml) และสเปกอยู่ใน [`data/instruments.yaml`](../data/instruments.yaml)

---

## 0. ⚠️ ข้อกฎหมายสำหรับผู้อยู่ในประเทศไทย (อ่านก่อน)
- **พระราชกฤษฎีกา 2 ฉบับ (มีผล 13 เม.ย. 2025)** กำหนดให้ exchange ต่างประเทศที่ให้บริการคนไทยต้องได้รับอนุญาตจาก ก.ล.ต. และช่วงผ่อนผันสิ้นสุดเมื่อ **28 มิ.ย. 2026**
  - **Binance.com ไม่มีใบอนุญาตในไทย** และคนไทยเข้าใช้ผ่าน IP ไทยไม่ได้
  - Binance TH (Gulf Binance) ที่ได้รับอนุญาตเป็น **spot เท่านั้น** ส่วน derivatives สำหรับรายย่อยยังปิดอยู่
- XAUUSDT ให้บริการโดย Nest Exchange (กำกับโดย ADGM FSRA) ซึ่งระบุว่า "อาจจำกัดตามภูมิภาค"
- ถ้าคุณหรือบริษัทมีถิ่นที่อยู่ในไทย การเทรด futures บน Binance.com **อาจผิดกฎหมายไทย** — ควรปรึกษาทนายก่อน (นี่ไม่ใช่คำแนะนำทางกฎหมาย) และ**โปรเจคนี้จะไม่ช่วยหลบเลี่ยงการบล็อก เช่น VPN**
- **ทางเลือกที่ถูกกฎหมายในไทย** (โค้ดและกฎของเราย้ายไปใช้ได้ เพราะออกแบบให้ไม่ผูกกับ venue):
  - TFEX **Gold-D (GD)**: ทอง 100 กรัม (3.2148 oz) ราคาเป็น USD/oz, tick $0.10
  - TFEX **GF10**: ทอง 10 บาท
  - TFEX **BTC futures**: คาดว่าจะเปิดครึ่งหลังปี 2026 – ต้นปี 2027

แหล่งที่มา: [brokerth](https://brokerth.com/en/thailand-extraterritorial-crypto-law-post-june28-2026-en/), [Tilleke & Gibbins](https://www.tilleke.com/insights/thailand-issues-new-royal-decrees-regulate-cryptocurrency-and-digital-tokens/), [The Block: TFEX crypto futures](https://www.theblock.co/news/regulation/2026-01-22-thailand-crypto-etf-futures-386650), [TFEX Gold-D spec](https://www.tfex.co.th/en/products/goldd-spec.html)

---

## 1. สเปกสัญญาที่ใช้
| | BTCUSDT perp | XAUUSDT perp (TradFi) |
|---|---|---|
| ราคา (ต.ค. 2026) | ~$85,600 | ~$4,130 |
| Min qty / **min notional** | 0.001 BTC / **100 USDT** | 0.001 oz / **5 USDT** |
| ค่าธรรมเนียม (VIP0) | maker 0.02%, taker 0.05% (จ่ายด้วย BNB ลด 10%) | โปรโมชันหมดแล้ว (26 พ.ค. 2026); สมมติ maker 0.02%, taker 0.04% — **ต้องตรวจในบัญชี** |
| Funding | ทุก 8 ชม. (00/08/16 UTC); ส่วนดอกเบี้ยฐาน ≈ 0.01%/8h ≈ 10.95%/ปี | ทุก 4 ชม., cap ±2%/รอบ |
| เวลาเทรด | 24/7 | **24/5** — หยุด ศ. 21:00 → อา. 21:00 UTC (ไม่มี trade, liquidation หรือ funding) |
| Leverage สูงสุด | สูงตามขั้นของ notional | 50x |

---

## 2. เงินต้นที่ต้องใช้ (คำถาม: ที่ leverage 0.01)

> **บน Binance ตั้ง "leverage" ต่ำกว่า 1x ไม่ได้** (ตัวเลข leverage ที่ตั้งในหน้าเทรดมีผลแค่ margin ที่วางและราคา liquidation)
> leverage จริงของพอร์ตคือ **notional ÷ equity** ซึ่งเราควบคุมผ่านขนาดไม้
> ตารางนี้คิดที่ leverage จริง 0.01x = ถือสถานะมูลค่า 1% ของเงินต้นเมื่อสัญญาณเต็ม

### 2.1 Leverage จริง 0.01x ต่อสินทรัพย์
| | ขั้นต่ำ: เปิดได้แค่ไม้เต็ม | **ขั้นต่ำที่ใช้กฎได้** (สัญญาณ ½ = 0.005x ต้อง ≥ min notional) | สะดวก (ปรับทีละ 0.25U) |
|---|---|---|---|
| **BTCUSDT** (min 100 USDT) | **$10,000** | **$20,000** | $40,000 |
| **XAUUSDT** (min 5 USDT) | $500 | **$1,000** | $2,000 |
| รวมทั้งสองตัว | $10,500 | **$21,000** | $42,000 |

ถ้า "0.01x" หมายถึง **leverage รวมทั้งพอร์ต** (แบ่งตาม 1/vol: BTC 40% = 0.004x, ทอง 60% = 0.006x):
- BTC ต้องใช้ **$50,000** สำหรับสัญญาณ ½ ($25,000 ถ้าเปิดได้แค่ไม้เต็ม)
- ทองต้องใช้ $1,667

### 2.2 ผลตอบแทนที่คาดได้ที่ 0.01x (คิดจากผล backtest ต่อหน่วย notional)
| | in-sample | ถ้า edge เหลือครึ่งเดียว | บนเงิน $20,000 / ปี |
|---|---|---|---|
| BTC | 0.67%/ปี | 0.33%/ปี | ~$67–$134 |
| ทอง | 0.04%/ปี | 0.02%/ปี | ~$4–$8 |

→ ที่ 0.01x ผลตอบแทน**น้อยกว่าดอกเบี้ยเงินฝาก**: ปลอดภัยมาก แต่เหมาะแค่ทดสอบระบบ (เช่นใช้กับ testnet หรือช่วงทดลองเงินจริงสั้นๆ) ไม่ใช่ใช้สร้างผลตอบแทน

### 2.3 เทียบกับระดับใน rulebook
| ระดับ | Leverage จริง BTC / ทอง | Equity ขั้นต่ำ (สัญญาณ ½) | แนะนำ (ปรับทีละ 0.25U) |
|---|---|---|---|
| 0.01x | 0.01 / 0.01 | $20,000 | $40,000 |
| **Incubation (vol 4%)** | 0.06 / 0.09 | $3,337 | **~$7,000** |
| Start (vol 8%) | 0.12 / 0.18 | $1,669 | ~$3,400 |
| Max (vol 10%) | 0.15 / 0.20 | $1,335 | ~$2,700 |

BTC เป็นตัวกำหนดเงินขั้นต่ำเพราะ min notional 100 USDT ส่วนทองแทบไม่มีข้อจำกัด

### 2.4 ถ้าหมายถึง "0.01 lot" แบบ MT5
- 0.01 BTC ≈ $856 → ต้องมี equity $7,142 (vol 8%) หรือ $14,284 (incubation) จึงจะเป็นขนาดที่กฎกำหนด
- ทองบน Binance ไม่มี lot 1 oz บังคับ (สั่งได้ทีละ 0.001 oz) แต่ถ้าถือ 1 oz ด้วยเงิน $10,000 จะเท่ากับ leverage จริง **0.41x** ซึ่ง**เกินเพดาน 0.20x ของ rulebook**

### 2.5 Margin และ liquidation (isolated, MMR สมมติ 0.4%)
| ตั้ง leverage | Margin ต่อไม้ $100 | ราคาต้องวิ่งสวนเท่าไรถึงโดน liquidate |
|---|---|---|
| 1x | $100 | ~99.6% |
| **2x (เพดาน rulebook)** | $50 | **~49.6%** |
| 5x | $20 | ~19.6% |

---

## 3. Backtest แบบ Binance เท่านั้น (BTCUSDT perp + XAUUSDT perp)
- ต้นทุน XAUUSDT 0.035%/ข้าง
- funding ของทองยังไม่มีข้อมูลจริง จึงทดสอบ 3 สมมติฐาน

| Funding ทอง (สมมติ) | Sharpe ทอง (ปรับแล้ว) | พอร์ต CAGR | พอร์ต Sharpe | Max DD | P(บวก 3 ปี) ถ้า edge เหลือครึ่ง | P(บวก 3 ปี) รวม* |
|---|---|---|---|---|---|---|
| ±5%/ปี สมมาตร | 0.25 | 6.66% | 1.28 | 4.9% | 87.8% | ~71% |
| ±10.95%/ปี สมมาตร (ค่าฐาน Binance) | 0.23 | 6.38% | 1.23 | 5.2% | 86.5% | ~70% |
| **long จ่าย 10.95%, short ไม่ได้รับ** | **0.01** | 5.78% | 1.12 | 5.3% | 83.7% | ~69% |

\* ให้น้ำหนัก 60% ว่า edge เหลือครึ่งหนึ่ง และ 40% ว่า edge หายไปแล้ว

**ข้อสรุป:**
- ถ้า funding ของ XAUUSDT เก็บจากฝั่ง long เป็นหลัก **edge ของทองหายหมด**
- จึงตั้งกฎ: ถ้า funding เฉลี่ย 30 วันที่ฝั่ง long จ่ายเกิน 8%/ปี และฝั่ง short ไม่ได้รับเท่ากัน → หยุดฝั่ง long ของทอง และพิจารณาใช้ TFEX Gold-D แทน

---

## 4. ตั้งค่าบัญชีและคำสั่ง (spec สำหรับขั้นเขียน bot)
| หัวข้อ | ค่าที่ใช้ |
|---|---|
| บัญชี | sub-account แยกสำหรับ bot; margin เป็น USDT; ปิด Multi-Assets mode |
| Position mode | One-way |
| Margin mode / leverage ที่ตั้ง | Isolated, **2x** ทั้งสองสัญญา (เป็นเพดาน ไม่ใช่ขนาดไม้) |
| เข้าไม้ / rebalance | LIMIT + `timeInForce=GTX` (post-only) → ถ้าไม่ fill ใน 10 นาที ใช้ LIMIT IOC ราคาห่างไม่เกิน 0.10% (ไม่ใช้ MARKET) |
| Stop ป้องกัน | Algo order: `POST /fapi/v1/algoOrder`, `STOP_MARKET`, `reduceOnly` หรือ `closePosition`, `workingType=MARK_PRICE`, `priceProtect=true` — ตั้งแต่ 9 ธ.ค. 2025 Binance ย้าย conditional order ไป Algo Service แล้ว และ endpoint เดิมจะตอบ error −4120 |
| ข้อมูลอ้างอิง | `exchangeInfo` (filter min qty/notional), `leverageBracket` (MMR), `fundingInfo` (รอบ funding) — ตรวจทุกวัน (เข้ากับกฎ `venue_change_watch`) |
| เวลา | BTC 00:20 UTC (หลัง funding) เลี่ยงนาที :00/:15/:30/:45; ทอง 15:30–16:30 UTC จ.–ศ.; หยุดเปิดไม้ใหม่ของทองหลัง ศ. 20:30 UTC |
| ความปลอดภัย API | key สิทธิ์ **Futures trade เท่านั้น ห้ามเปิด withdrawal**, จำกัด IP whitelist, เก็บ key นอก repo (env/secret manager), หมุน key ทุก 90 วัน |
| ทดสอบ | Testnet (`testnet.binancefuture.com`) 1 เดือนเพื่อทดสอบการทำงาน → เงินจริงที่ vol 4% เป็นเวลา 6 เดือน (G3) *ถ้าข้อกฎหมายในข้อ 0 อนุญาต* |

---

## 5. ข้อมูลที่ยังต้องใช้
ถ้าจะทดสอบบนราคา perps จริง (รวม basis และ funding จริงของ BTCUSDT/XAUUSDT รายชั่วโมง) ต้องเปิด host `data.binance.vision` ใน network policy ของ environment (ไฟล์มี `.CHECKSUM` ให้ตรวจ SHA-256 ได้)
