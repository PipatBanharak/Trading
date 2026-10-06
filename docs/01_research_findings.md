# 01 — ผลการค้นคว้า: EA, AI/LLM Trading Agent และหลักฐานเรื่องความสามารถทำกำไร

> วิธีค้น: อ่านจากเว็บอย่างเดียว ไม่ได้ดาวน์โหลดไฟล์หรือโค้ดใดๆ กลับมา
> ตัวเลขทั้งหมดถูกจัดเก็บเป็น `EvidenceRecord` ใน [`data/evidence_base.yaml`](../data/evidence_base.yaml)
> ระดับคุณภาพหลักฐาน: **A** = peer-reviewed/regulator/ข้อมูลทั้งประชากร, **B** = working paper/benchmark ที่มีระเบียบวิธีชัด, **C** = รายงานอุตสาหกรรม/บล็อก

---

## 1. ภาพรวมแบบสั้น

| คำถาม | คำตอบจากหลักฐาน |
|---|---|
| รายย่อยส่วนใหญ่ทำกำไรได้ไหม | **ไม่** — บัญชี CFD 74–89% ขาดทุน, day trader ที่เทรดนานพอ 97% ขาดทุน และไม่ถึง 1% ที่ทำกำไรได้อย่างคาดการณ์ได้ |
| EA ที่ขายกันทั่วไปมี edge ไหม | ส่วนใหญ่ **ไม่มี** และไม่มีสถิติรวมที่เชื่อถือได้ เพราะ EA ที่ล้มจะถูกถอดออกจากตลาด (survivorship bias) |
| LLM agent เทรดเองแล้วชนะตลาดไหม | ผลการแข่งขันด้วยเงินจริง **ไม่สม่ำเสมอ**: ผลต่างกันมากระหว่างโมเดลและระหว่างรอบ ส่วนใหญ่ขาดทุน และ backtest มักมี look-ahead bias |
| มีกลยุทธ์ที่มีหลักฐานระยะยาวไหม | **มี แต่ Sharpe ต่ำ (~0.3–0.7) และขึ้นกับระบอบตลาด** เช่น trend following กระจายหลายตลาด และ carry ซึ่งเสี่ยง crash |
| อะไรทำให้ backtest หลอกตามากที่สุด | การลองหลายแบบแล้วเลือกตัวที่ดีที่สุด (data snooping), ต้นทุนที่ประเมินต่ำเกิน และช่วงทดสอบที่สั้นเกิน |

---

## 2. อัตราพื้นฐาน (base rate) ของเทรดเดอร์รายย่อย

| หลักฐาน | ตัวเลข | คุณภาพ |
|---|---|---|
| ESMA (EU) — บัญชี CFD รายย่อย | **74–89% ขาดทุน** เฉลี่ยขาดทุน €1,600–€29,000 ต่อคน | A |
| โบรกเกอร์ CFD 28 เจ้า (ตัวเลขที่ต้องเปิดเผย) | ขาดทุน 54–83% เฉลี่ย **76%** ในรอบ 12 เดือน | B |
| Day trader บราซิล (Chague, De-Losso, Giovannetti) | คนที่เทรดเกิน 300 วัน **97% ขาดทุน**, 1.1% ได้มากกว่าค่าแรงขั้นต่ำ, ไม่พบว่าเทรดนานแล้วเก่งขึ้น | A |
| Day trader ไต้หวัน 1992–2006 (Barber, Lee, Liu, Odean) | **< 1%** ทำกำไรได้อย่างคาดการณ์ได้หลังหักค่าธรรมเนียม | A |
| Prop firm challenge (2025–26) | ผ่าน 5–14%; ผู้ซื้อ challenge ได้ payout จริงราว **7%** | C |

**ข้อสรุป:** prior ที่ว่า "คนทั่วไป/EA ทั่วไปมี edge สุทธิที่คงทน" อยู่ที่ราว **1–3%**

---

## 3. EA (Expert Advisor) บน MT4/MT5

**สิ่งที่พบ**
- ไม่มีตัวเลขสาธารณะที่ซื่อตรงว่า EA กี่เปอร์เซ็นต์ทำกำไร เพราะ EA ที่ล้มจะถูกถอดแล้วออกชื่อใหม่ (survivorship) — [MQL5 blog](https://www.mql5.com/en/blogs/post/774530)
- **Martingale/averaging** เป็นสาเหตุหลักที่บัญชีพังในที่สุด สถิติดูดีมาก (win rate สูง) เป็นเวลานานแล้วจบด้วยการล้างพอร์ต
- **การซ่อน drawdown**: signal บางเจ้าฝากเงินเพิ่มเพื่อให้ DD ดูต่ำ ให้ดู *Absolute Gain* เทียบกับ *Gain* — [MQL5 blog](https://www.mql5.com/en/blogs/post/763905)
- ตัวอย่าง EA ที่ซื่อตรงมักมีหน้าตาแบบ win rate ~47%, profit factor ~1.24, DD ~16% คือ**กำไรได้โดยไม่จำเป็นต้องชนะบ่อย** — [MQL5 blog](https://www.mql5.com/en/blogs/post/772467)

**ธงแดงของ EA** (ใช้เป็น checklist ใน `ValidationReport`)
1. กำไรทุกเดือนติดต่อกันนาน (ดูตาราง T2: แม้ SR 2.0 ยังมีโอกาสกำไรครบ 12/12 เดือนแค่ ~1.9%)
2. Win rate > 85% แต่ไม่มี stop loss → grid/martingale
3. Backtest สวยแต่ live สั้นกว่า MinTRL (ตาราง T4)
4. Gain ≫ Absolute Gain หรือมีการฝาก/ถอนบ่อย
5. ไม่บอกว่า optimize ไปกี่ combination (N trials)

---

## 4. AI / LLM Trading Agents (2025–2026)

### 4.1 การแข่งขันด้วยเงินจริง (live)
| Benchmark | ช่วงเวลา/ตลาด | ผล |
|---|---|---|
| **Alpha Arena S1** (Nof1) | 18 ต.ค.–3 พ.ย. 2025, crypto perps (Hyperliquid) | Qwen3 Max ชนะ ~+22%, GPT-5 ≈ −59%, Grok 4 ≈ −58% และโมเดลสหรัฐฯ ตัวอื่นขาดทุนหนักเช่นกัน ([traderank](https://www.traderank.ai/blog/alpha-arena-alternatives-2026), [iweaver](https://www.iweaver.ai/blog/alpha-arena-ai-trader-showdown/)) |
| **Alpha Arena S1.5** | หุ้นสหรัฐฯ, ~$320K, 4 รูปแบบการแข่ง | Mystery model (Grok 4.2) ชนะเฉลี่ย ~+12% และเป็นตัวเดียวที่กำไรครบทุกรายการ ([Forklog](https://forklog.com/en/news/ai-model-grok-4-2-triumphs-in-trading-tournament)) |
| **Prediction Arena** | 57 วัน (ม.ค.–มี.ค. 2026), Kalshi | ทุกโมเดล **−16.0% ถึง −30.8%** ([arXiv 2604.07355](https://arxiv.org/html/2604.07355v1)) |
| **LiveTradeBench** | 21 LLM, live 50 วัน | คะแนน benchmark ทั่วไปไม่ได้ทำนายผลการเทรด และเก่งตลาดหนึ่งไม่ได้แปลว่าเก่งอีกตลาด ([arXiv 2511.03628](https://arxiv.org/html/2511.03628v1)) |
| **AI-Trader** (HKU) | live, ไม่มีการปนเปื้อนข้อมูล | "general intelligence ไม่ได้รับประกันความสำเร็จ" และ**การคุมความเสี่ยง**คือตัวกำหนดความทนทาน ([hyper.ai](https://hyper.ai/en/papers/2512.10971)) |

### 4.2 ปัญหาเชิงระเบียบวิธี
- **Look-ahead / memorization**: LLM จำราคาและข่าวในช่วง training ได้ backtest ก่อน knowledge cutoff จึงดีเกินจริง — [Hedge Fund Alpha](https://hedgefundalpha.com/education/your-llms-alpha-might-be-mere-memorization/), [Look-Ahead-Bench](https://arxiv.org/pdf/2601.13770)
- **FINSABER** (20 ปี, 100+ หุ้น): ข้อได้เปรียบของ LLM ที่เคยรายงานไว้ลดลงมากเมื่อขยายขอบเขต LLM ระวังเกินในตลาดขาขึ้นและกล้าเกินในตลาดขาลง — [arXiv 2505.07078](https://arxiv.org/html/2505.07078v3)
- **Survey Agentic Quant Trading (2026)**: ระบบส่วนใหญ่ยังเน้นแค่หา signal ไม่ได้รวม portfolio/execution/risk ครบ และการพยากรณ์ที่ดีไม่ได้แปลว่าเทรดได้ดีใน live — [HKUST-GZ](https://dsa.hkust-gz.edu.cn/blog/2026/05/29/agentic-quantitative-trading-a-survey-of-workflows-systems-and-evaluation/)
- **Review ล่าสุด (ส.ค. 2026)**: ยังไม่มีสถาปัตยกรรม AI ใดที่แสดง net alpha ที่คงทนข้ามระบอบตลาด — [papers.cool 2609.04917](https://papers.cool/arxiv/2609.04917)
- ผลอย่าง "InvestorAgent + GPT-4.1 ได้ 40.83% บน TSLA, Sharpe 6.47" (Agent Market Arena) มาจาก**ช่วงสั้นและสินทรัพย์เดียว** จึงยังสรุปไม่ได้ว่ามี edge (ดู MinTRL และ DSR)

**ข้อสรุปสำหรับ Agent:** LLM เหมาะเป็น**ผู้ช่วยวิจัย ตัวกรองระบอบ/ข่าว และผู้สรุปรายงาน** มากกว่าเป็นผู้ตัดสินใจซื้อขายเพียงลำพัง → สถาปัตยกรรมที่แนะนำอยู่ใน [`data/skill_catalog.yaml`](../data/skill_catalog.yaml)

---

## 5. งานวิจัยเรื่อง backtest overfitting และการเสื่อมของ edge

| งานวิจัย | ข้อค้นพบ | ใช้ในสูตร |
|---|---|---|
| Bailey, Borwein, López de Prado, Zhu | ลอง >45 แบบบนข้อมูล 5 ปี → เจอ SR=1 จากโชค (SR จริง 0) | F08, F12 |
| Bailey & López de Prado | PSR, **Deflated Sharpe Ratio**, PBO (CSCV) | F07, F09, F13 |
| Harvey, Liu, Zhu (RFS 2016) | ปัจจัยใหม่ควรมี **t > 3.0** | F06 |
| McLean & Pontiff | ผลตอบแทนลด **26% นอก sample, 58% หลังตีพิมพ์** | F17 |
| Bajgrowicz & Scaillet (JFE 2012) | กฎ technical บน DJIA 1897–2011: เลือกกฎที่ดีล่วงหน้าไม่ได้ และกำไรหายเมื่อหักต้นทุน | prior |
| Neely, Weller, Ulrich (JFQA 2009) | กฎ MA/filter ใน FX ทำกำไรจริงช่วง 70s–80s แต่หายไปภายในต้น 90s (Adaptive Markets) | λ decay |
| Futures + White RC/Hansen SPA | กฎที่ดีที่สุดมีนัยสำคัญแค่ **2 จาก 17** สัญญา | F14 |

---

## 6. กลยุทธ์ที่มีหลักฐานระยะยาว (สรุป — รายละเอียดอยู่ใน [`strategy_catalog.yaml`](../data/strategy_catalog.yaml))

| กลุ่ม | หลักฐาน | Skew | ความไวต่อต้นทุน | บทบาทที่แนะนำ |
|---|---|---|---|---|
| Trend following (TSMOM) หลายตลาด | 1880–2016 บวกทุกทศวรรษ แต่ 2010s ได้ ~0.8%/ปี และปี 2022 ได้ +27% | + | ต่ำ | **แกนหลัก** |
| Carry (FX) | ได้ premium แลกกับ crash risk | − | ต่ำ | เสริม |
| Cross-sectional momentum | มีหลักฐาน แต่เสี่ยง momentum crash | − | กลาง | เสริม |
| Mean reversion ระยะสั้น / pairs | เสื่อมลงมากหลังปี 2002 | − | สูง | วิจัย + ตัวกรองระบอบ |
| Breakout intraday / scalping / news | หลักฐานอ่อน ต้นทุนกินกำไร | ± | สูงมาก | หลีกเลี่ยง |
| Grid / Martingale | คณิตศาสตร์บอกว่า ruin แน่นอนในระยะยาว | −−− | — | **ห้ามใช้** |
| LLM ตัดสินใจเองล้วน | live แปรปรวนสูง ส่วนใหญ่ขาดทุน | ? | สูง | ไม่ใช้เป็นผู้ตัดสินใจหลัก |

---

## 7. สกิลที่มีผลต่อความน่าจะเป็นมากที่สุด (เรียงตามลำดับความสำคัญ)

1. **Position sizing / risk of ruin** (SK01) — edge จริงแต่ไม้ใหญ่ไปก็ล้างพอร์ตได้
2. **Cost modeling** (SK02) — ต้นทุน 0.1R ต่อไม้พอที่จะทำให้ edge 0.1R เหลือศูนย์
3. **Research hygiene / บันทึกทุก trial** (SK03) — ตัวแปร N ที่คนมักลืมนับ
4. **Statistical validation** (SK04) — DSR, PBO, SPA, MinTRL
5. **LLM contamination control** (SK12) — เฉพาะ AI agent
6. Edge thesis, diversification, regime awareness, live monitoring/kill switch, data integrity และ discipline

รายละเอียดว่าแต่ละสกิลไปเปลี่ยนตัวแปรไหนในสมการอยู่ใน [`data/skill_catalog.yaml`](../data/skill_catalog.yaml)

---

## 8. บริบทประเทศไทย

- ธุรกิจซื้อขาย Forex **ไม่อยู่ภายใต้การกำกับของ ก.ล.ต.** และ ก.ล.ต. เตือนเรื่องผู้ให้บริการที่ไม่ได้รับอนุญาตและการหลอกลงทุน (สายด่วน 1207 กด 22) — [InfoQuest](https://www.infoquest.co.th/?p=427713)
- ผลคือความเสี่ยงคู่สัญญา (โบรกเกอร์/ผู้ขาย EA) เป็นตัวแปรที่ต้องนับเพิ่ม นอกเหนือจากความเสี่ยงตลาด

---

## แหล่งอ้างอิงหลัก
- ESMA: <https://www.esma.europa.eu/sites/default/files/library/esma35-43-1135_notice_of_pi_decisions_on_cfds_and_binary_options.pdf>
- BrokerChooser (CFD risk warnings): <https://brokerchooser.com/broker-reviews/cmc-markets-review/cfd-risk-warning>
- Day trading Brazil: <https://www.cxoadvisory.com/investing-expertise/day-trading-a-bust/>
- Day trading Taiwan: <https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf>
- Prop firm stats: <https://track360.io/blog/prop-trading-industry-statistics-2026>
- Deflated Sharpe Ratio: <https://papers.ssrn.com/abstract=2460551> · PBO: <https://papers.ssrn.com/abstract=2326253>
- MinBTL/45 configs: <https://www.cxoadvisory.com/?p=23736>
- Harvey-Liu-Zhu: <https://www.nber.org/papers/w20592>
- McLean-Pontiff: <https://ivey.uwo.ca/media/3775549/pontiff.pdf>
- Bajgrowicz-Scaillet: <https://ideas.repec.org/a/eee/jfinec/v106y2012i3p473-491.html>
- Neely-Weller-Ulrich: <https://files.stlouisfed.org/files/htdocs/wp/2006/2006-046.pdf>
- Futures SPA: <https://ageconsearch.umn.edu/record/19039>
- Trend century: <https://www.cxoadvisory.com/momentum-investing/trend-following-with-intrinsic-momentum-over-the-very-long-run>
- CTA 2022: <https://alpha-week.com/2022-cta-index-performance-review>
- Carry crashes: <https://www.nber.org/papers/w14473>
- Pairs trading: <https://alphaarchitect.com/2013/06/pairs-trading-kicks-butt/>
- Martingale: <https://www.luxalgo.com/library/concept/martingale-anti-martingale/>
- Risk of ruin: <https://www.luxalgo.com/library/concept/risk-of-ruin/>
- PSR/MinTRL: <https://portfoliooptimizer.io/blog/the-probabilistic-sharpe-ratio-bias-adjustment-confidence-intervals-hypothesis-testing-and-minimum-track-record-length/>
