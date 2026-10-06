# 04 — สำรวจ EA / Bot ยอดนิยม: ใช้เทคนิคอะไร ข้อดีข้อเสีย และสิ่งที่เรายืมมาใช้

> ขอบเขต: EA ทองคำ (XAUUSD) และ Bitcoin บน MQL5 Market รวมถึง bot คริปโตยอดนิยม (ณ ต.ค. 2026)
> วิธีค้น: อ่านจากผลค้นหาเว็บอย่างเดียว ไม่ได้ดาวน์โหลด EA, set file หรือโค้ดใดๆ (หน้า mql5.com ถูกบล็อกจากเครื่องนี้ จึงใช้ข้อมูลจากรีวิวและผลค้นหาแทน)
> ตัวเลขผลงานทั้งหมดเป็น**ตัวเลขที่ผู้ขายหรือผู้รีวิวรายงาน (คุณภาพ C)** และยังไม่ได้ตรวจสอบโดยอิสระ

---

## 1. ตาราง EA/Bot ที่สำรวจ

### 1.1 EA ทองคำ (XAUUSD)
| EA | เทคนิคหลัก | TF | Grid/Martingale | ผลที่รายงาน | ข้อดี | ข้อเสีย/ความเสี่ยง |
|---|---|---|---|---|---|---|
| **Quantum Queen** | Trend-following หลายกลยุทธ์ย่อย (6 ตัว) + ปรับขนาดไม้ตามความผันผวน | M1 | **มี grid ช่วง drawdown** (ตามรีวิว) | rating 4.98 จากรีวิว 400+, live 20+ เดือน | กระจายกลยุทธ์ย่อย, sizing ตาม vol | grid ซ่อน tail risk, M1 ไวต่อต้นทุน/slippage ช่วงข่าว |
| **The Gold Reaper** | Breakout แนวรับ-ต้านหลาย TF, 9 กลยุทธ์ | หลาย TF | ไม่มี, มี SL ทุกไม้ | บัญชี moderate: กำไร +14.98% แต่ **Max DD 41.66%** | SL ชัด, ไม่มี grid | อัตรากำไรต่อ DD แย่มาก, พารามิเตอร์เยอะ (N สูง) |
| **Turtle-style (เช่น Mad Turtle / Breakout Exit Lab)** | Donchian 20 แท่ง + ตัวกรองเทรนด์, SL 2 ATR, TP 2R | H1–H4 | ไม่มี | backtest 2020–09/2026: PF 1.77, MDD 11.4% ที่ risk 1% | สอดคล้องกับหลักฐาน trend, stop เป็นหน่วย ATR | เป็น backtest ช่วงทองขาขึ้นยาว (regime เดียว) |
| **EA Gold Stuff** | Trend indicator + grid | — | **มี grid** | +265%, DD ~19% (เป็น *balance* DD) | ราคาถูก | balance DD ต่ำกว่า equity DD จริงหลายเท่า |
| **Ghost Scalper 4.0** | Breakout/momentum 4 กลยุทธ์อิสระ เข้าแบบเลือก | — | ไม่ระบุ | — | เลือกเข้าเฉพาะจังหวะ | ข้อมูลยืนยันน้อย |
| **AI Gold Sniper** | Scalping ช่วงผันผวนสูง ทำตลาดด้วยคำว่า "AI" | สั้น | ไม่ระบุ | live ~7 เดือน | ชุมชนใหญ่ | live สั้นกว่า MinTRL มาก, ไวต่อต้นทุน |
| **Gold grid 3 ตัวที่วัดผลแบบซื่อตรง** (MQL5 blog) | Grid | — | grid | **ล้มเหลวทั้ง 3 ตัว**: ตัวหนึ่ง win rate 98.5% จาก 844 ไม้แต่ผลรวม **−23.2%**; ลำดับเดียววันที่ 16 เม.ย. 2025 เสีย $4,425 | — | ระยะ grid ที่ตั้งตาม vol ปี 2023 ใช้ไม่ได้กับ vol ปี 2026 |

### 1.2 EA ยอดนิยมตลาด FX (ใช้เป็นบทเรียนเชิงเทคนิค)
| EA | เทคนิค | ผล/ประเด็น |
|---|---|---|
| **Quantum Emperor** (GBPUSD H1) | ผู้วิเคราะห์อิสระระบุว่าเป็น "martingale-grid ที่ปลอมตัวมา" | ขายดีที่สุดในประวัติ MQL5 (5,000+ ชุด) แต่ **DD 70% เมื่อ มิ.ย. 2024** |
| **Waka Waka** | RSI + Bollinger เป็นจุดเข้า, grid จัดการไม้, ตัวกรองเทรนด์, ระยะ grid ปรับตาม vol | track record ยาว (70+ เดือนกำไร) แต่ DD ~30% และยังเป็น grid |
| **Perceptrader AI** | ให้ AI ตัดสินใจ "ว่าจะเปิด grid เมื่อไร" | แกนกลางยังเป็น grid เดิม |
| **Night Hunter Pro** | Scalping ช่วงตลาดเอเชียที่ vol ต่ำ, SL คงที่, ไม่มี grid | +215% ตั้งแต่ ต.ค. 2020, DD ~30% |

### 1.3 EA / Bot สำหรับ Bitcoin
| ชื่อ | เทคนิค | ข้อสังเกต |
|---|---|---|
| BTC Miner Pro | Time & price analysis, ไม่มี grid/martingale, SL/TP ตั้งได้, โหมด HFT | โหมด HFT บน CFD/perps เจอปัญหาต้นทุน (ดู doc 05) |
| Korrect BTC | Smart Money Concepts (order block, liquidity) + Fibonacci | SMC/ICT ยังไม่มีหลักฐานเชิงวิชาการที่ผ่าน data-snooping test |
| TrendCandleEA (BTC) | M30, ตามเทรนด์และเข้าเมื่อ momentum กลับมาหลังย่อ | แนวคิดสอดคล้องกับ TSMOM แต่ TF สั้น |
| BTC Dominator | Price action 4 โมเดล บน 4 TF | multi-strategy แต่ไม่เปิดเผย N trials |
| SatoshiMind AI | "Multi-agent AI + adaptive ML" | ใช้คำ AI ทางการตลาด ไม่มีรายละเอียดตรวจสอบได้ |
| **Pionex Grid / 3Commas DCA** | Grid ในกรอบราคา; DCA พร้อม "safety orders" ที่เพิ่มไม้เมื่อราคาลง | ผู้ให้บริการอ้าง 15–40%/ปี "ในตลาด sideways" ซึ่ง DCA safety orders ก็คือการเฉลี่ยขาลง (martingale แบบอ่อน) |
| **Freqtrade – NostalgiaForInfinity** | Open-source, 5m–15m, 40–80 คู่เหรียญ, เปิดได้สูงสุด 6 ไม้ | ข้อดีคือโปร่งใสและทำซ้ำได้ ข้อเสียคือ TF สั้น ต้นทุนสูง และมีพารามิเตอร์จำนวนมาก |

---

## 2. วิเคราะห์เทคนิคเชิงคณิตศาสตร์

### 2.1 Grid = การ "ขาย volatility" (short gamma)
P&L ของ grid ที่มีระยะห่าง $g$ และถือ 1 หน่วยต่อชั้น มีค่าประมาณ **(F31)**

$$\text{PnL} \approx \frac{QV - (\Delta P)^2}{2g}$$

โดย $QV$ คือผลรวมกำลังสองของการเคลื่อนไหวทั้งหมด และ $\Delta P$ คือราคาที่เปลี่ยนสุทธิ
- ถ้าราคาเป็น random walk: $E[QV] = E[\Delta P^2]$ → **กำไรคาดหวัง = 0 ก่อนหักต้นทุน**
- ถ้าตลาดแกว่งกลับ (variance ratio < 1) → grid กำไร
- ถ้าตลาดมีเทรนด์ (variance ratio > 1) → grid ขาดทุนเป็นสัดส่วนกับ $\Delta P^2$
- Trend following มีลักษณะตรงข้าม คือ long gamma (กำไรเมื่อ VR > 1)

ตรวจสอบด้วย Monte Carlo (ทอง 1 เดือน, step 1 นาที, ถือชั้นละ 1 oz):
| กรณี | P&L เฉลี่ย | ค่าที่สูตรทำนาย | แย่สุดใน 150 paths |
|---|---|---|---|
| vol ปี 2023 (~$5/ชม.), grid $5 | −$52 (≈0 ภายใน noise) | −$9 | −$4,226 |
| vol ปี 2026 (~$26/ชม.), grid $26 | ≈0 ภายใน noise | ≈0 | −$35,330 |
| vol ปี 2026, grid $26, **เทรนด์ +20%/เดือน** (แบบ ม.ค. 2026) | **−$11,220** | −$11,031 | −$61,252 |

**ทำไม grid ทองถึงพังในปี 2026:** true range ต่อชั่วโมงของทองเพิ่มจาก ~$5 (2022–24) เป็น ~$26 (2026)
- ถ้ายังใช้ระยะ grid $5 ตามค่าที่ตั้งไว้ในปี 2023: การเคลื่อน 3σ ใน 1 เดือน (~$1,075) จะเปิดค้าง ~215 ชั้น และขาดทุนที่ยังไม่ปิดประมาณ $\Delta P^2/2g$ ≈ **$115,000 ต่อ 1 oz/ชั้น**
- ถ้าใช้ระยะ $26: เปิดค้าง ~41 ชั้น ขาดทุนประมาณ $22,000 → **พารามิเตอร์ทุกตัวต้องเป็นหน่วย σ/ATR ไม่ใช่ราคาตายตัว**

### 2.2 Martingale / DCA safety orders
ไม่เปลี่ยนค่า expectancy (F18) แต่ย้ายความเสี่ยงไปไว้ที่หาง → win rate สูงมากจนถึงวันที่ล้างพอร์ต (ดู T8)

### 2.3 Scalping M1–M5
- ทอง (ECN): ต้นทุนเป็น R ต่ำในระบอบ vol ปี 2026 (≈0.02R ที่ M5) แต่ช่วงข่าวสูงขึ้นประมาณ 10 เท่า และหลักฐานว่ามี edge อ่อน
- BTC บน perps (taker): ≈ 0.27R ที่ M5 → **ต้นทุนกิน edge เกือบทั้งหมด** (ดู doc 05 ตาราง C1)

### 2.4 Breakout / Trend (Donchian, MA, TSMOM)
- เป็นเทคนิคเดียวในรายการที่มีหลักฐานวิชาการระยะยาว: TSMOM 1880–2016 และ TSMOM ใน crypto (Liu & Tsyvinski: momentum รายสัปดาห์ของ BTC)
- ข้อเสียคือ win rate ต่ำ (35–55%), DD ยาวช่วง sideways และ backtest ทองช่วง 2020–2026 มีเทรนด์ขาขึ้นเป็นส่วนใหญ่ → ต้องทดสอบทั้งสองทิศและหลายระบอบ

### 2.5 SMC / ICT / Fibonacci / "AI"
- ยังไม่พบหลักฐานที่ผ่านการแก้ data snooping
- "AI" ใน EA ส่วนใหญ่ใช้กำหนดว่าจะเปิด grid หรือใช้เป็นคำทางการตลาด → จัดเป็น `edge_source: none_identified` จนกว่าจะพิสูจน์ได้

---

## 3. สรุป: สิ่งที่ยืมมา vs สิ่งที่ห้าม

| ✅ ยืมมาใช้ | มาจาก | นำไปใช้ใน rulebook |
|---|---|---|
| กลยุทธ์ย่อยหลายตัวรวมกัน **แต่ต้องไม่ correlate กัน และต้องนับ N** | Quantum Queen, Gold Reaper, Ghost Scalper | `sleeves` + `trial_budget` |
| ปรับขนาดไม้ตามความผันผวน / stop เป็นหน่วย ATR | Quantum Queen, Turtle | `vol_targeting`, `protective_stop` |
| พารามิเตอร์ทุกตัวปรับตาม vol (ไม่ใช้ $ ตายตัว) | Waka Waka (ปรับระยะ grid) และบทเรียน vol ทอง 2026 | `all_distances_in_sigma_units` |
| รู้จัก session (เอเชีย/ลอนดอน/NY) | Night Hunter, งานวิจัยเรื่อง session ของทอง | `session_calendar`, hypothesis H2 |
| SL ทุกไม้ ไม่มี grid/martingale | Gold Reaper, Night Hunter, BTC Miner | `banned_techniques` |
| ตัวกรองข่าวและเวลา rollover | Gold EA ทั่วไป | `execution_policy.blackouts` |
| วัดผลด้วย **equity DD** ไม่ใช่ balance DD | บทเรียนจาก Gold Stuff/grid | `monitoring.drawdown_basis: equity` |
| กฎโปร่งใส ทำซ้ำได้ และ log ทุกอย่าง | Freqtrade (open-source) | `TrialRegistry`, `AgentDecisionLog` |

| ⛔ ห้ามใช้ | เหตุผล |
|---|---|
| Grid / grid recovery / hedging grid | short gamma; พังเมื่อมีเทรนด์หรือ vol เปลี่ยน (F31) |
| Martingale, DCA safety orders | ruin แน่นอนในระยะยาว (F18) |
| Scalping M1–M5 บน venue ที่จ่าย taker fee | cost_R ≥ 0.2 (doc 05) |
| Set file ที่ปรับมาเพื่อผ่าน prop firm | optimize เพื่อให้ "ผ่านด่าน" ไม่ใช่เพื่อหา edge และ N สูง |
| เชื่อ backtest ทองช่วง 2020–2026 อย่างเดียว | ทองเป็นขาขึ้นเกือบตลอด (bias ไปฝั่ง long) |

---

## แหล่งข้อมูล
- Quantum Queen / Gold EAs 2026: <https://newyorkcityservers.com/blog/quantum-queen-ea-review>, <https://blodsalgo.com/blog/en/best-eas-gold-trading-2026/>
- Gold Reaper: <https://newyorkcityservers.com/blog/the-gold-reaper-review>
- Quantum Emperor: <https://newyorkcityservers.com/blog/quantum-emperor-review>
- Waka Waka / Night Hunter / Perceptrader: <https://newyorkcityservers.com/blog/waka-waka-ea-review>, <https://newyorkcityservers.com/blog/night-hunter-pro-review>, <https://newyorkcityservers.com/blog/perceptrader-ai-ea-review>
- Gold grid EAs วัดผลแบบซื่อตรง + vol ทอง $5→$26/ชม.: <https://www.mql5.com/en/blogs/post/776032>
- Breakout vs grid ทอง: <https://www.mql5.com/en/blogs/post/774661>
- Gold Stuff และประเด็น balance vs equity DD: <https://newyorkcityservers.com/blog/best-forex-grid-eas-robots-2026>
- BTC EAs: <https://www.mql5.com/en/blogs/post/775423>, <https://www.mql5.com/en/blogs/post/775657>, <https://www.mql5.com/fr/market/product/141384>, <https://www.mql5.com/it/market/product/153735>
- Crypto bots: <https://earnifyhub.com/learning-guides/3commas-vs-pionex-vs-cryptohopper-review-2026>, <https://www.spark.money/tools/ai-crypto-trading-bot-comparison>
- Freqtrade NFI: <https://awesome.ecosyste.ms/projects/959190>
- Turtle-style gold backtest (จากบทสรุปผลค้นหา MQL5 blog เรื่อง Turtle/Breakout EA ทอง — เปิดอ่านต้นฉบับไม่ได้เพราะ mql5.com ถูกบล็อก): <https://www.mql5.com/en/blogs/post/772256>, <https://www.mql5.com/en/blogs/post/776472>
