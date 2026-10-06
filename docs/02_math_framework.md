# 02 — กรอบคณิตศาสตร์ (Formula Registry F01–F30)

> ทุกสูตรมี id ตรงกับ `formula_registry` ใน [`data/schema.yaml`](../data/schema.yaml)
> ตัวเลขตัวอย่างคำนวณไว้แล้วใน [`data/scenarios.yaml`](../data/scenarios.yaml)

## สัญลักษณ์
| สัญลักษณ์ | ความหมาย |
|---|---|
| $p, q=1-p$ | โอกาสชนะ/แพ้ต่อไม้ |
| $W, L$ | กำไรเฉลี่ยเมื่อชนะ / ขาดทุนเฉลี่ยเมื่อแพ้ (หน่วย R) |
| $c_R$ | ต้นทุนต่อไม้ (หน่วย R) |
| $SR$ | Sharpe ratio ต่อปี; $\widehat{SR}$ = ค่าที่วัดได้ |
| $T$ | ระยะเวลา (ปี); $n$ = จำนวน observation |
| $\gamma_3, \gamma_4$ | skewness, kurtosis (normal: 0, 3) |
| $N$ | จำนวน trial/configuration ที่ลองทั้งหมด |
| $\Phi, \Phi^{-1}$ | CDF ของ normal มาตรฐาน และ inverse |
| $\gamma_E$ | ค่าคงที่ Euler–Mascheroni ≈ 0.5772 |

---

## A. Edge ต่อไม้

**F01 — Expectancy**
$$E = p\,W - (1-p)\,L$$

**F02 — หักต้นทุน และหา win rate ที่คุ้มทุน**
$$c_R = \frac{\text{spread} + \text{slippage} + \text{commission}}{\text{stop distance}},\qquad E_{net} = E - c_R,\qquad p_{BE} = \frac{L + c_R}{W + L}$$
> ตัวอย่าง (สมมติ): XAUUSD spread+slippage รวม 0.30 USD, stop 3.00 USD → $c_R = 0.1R$
> ถ้าย่อ stop เหลือ 1.00 USD (สไตล์ scalping) → $c_R = 0.3R$ ซึ่งมากกว่า edge ของกลยุทธ์ส่วนใหญ่

---

## B. จาก Sharpe ไปเป็นความน่าจะเป็น

**F03/F04 — โอกาสที่ผลรวมจะเป็นบวกในช่วงเวลา $\Delta t$ (ปี)**
$$P(R_{\Delta t} > 0) \approx \Phi\!\left(SR\sqrt{\Delta t}\right)$$
- รายเดือน: $\Phi(SR/\sqrt{12})$
- "กำไร ≥ k จาก 12 เดือน" ใช้ binomial: $\sum_{i\ge k}\binom{12}{i}p_m^i(1-p_m)^{12-i}$ (ตาราง T2)

**F05 — Sharpe**: $SR = \dfrac{\bar r}{\sigma_r}\sqrt{\text{periods/year}}$ (ถ้า return มี autocorrelation ต้องปรับ เช่นใช้ Lo (2002))

---

## C. ทดสอบว่า edge จริงหรือเป็นแค่โชค

**F06 — t-statistic**: $t \approx SR\sqrt{T}$ → เกณฑ์ **t > 3** (Harvey–Liu–Zhu) หมายความว่า SR 1.0 ต้องมีข้อมูลอย่างน้อย 9 ปี และ SR 2.0 ต้องมีอย่างน้อย 2.25 ปี

**F07 — Probabilistic Sharpe Ratio** (SR ต่อ period และ $n$ คือจำนวน period)
$$PSR(SR^*) = \Phi\!\left(\frac{(\widehat{SR} - SR^*)\sqrt{n-1}}{\sqrt{1 - \gamma_3\widehat{SR} + \frac{\gamma_4 - 1}{4}\widehat{SR}^2}}\right)$$

**F08 — SR สูงสุดที่คาดว่าจะเจอจากโชคล้วน เมื่อลอง N แบบ**
$$SR_0 = \sqrt{V[\widehat{SR}_n]}\left[(1-\gamma_E)\,\Phi^{-1}\!\left(1-\tfrac{1}{N}\right) + \gamma_E\,\Phi^{-1}\!\left(1-\tfrac{1}{Ne}\right)\right]$$
ถ้า trial ต่างกันเพราะ sampling noise อย่างเดียว ใช้ $V[\widehat{SR}] \approx 1/T$ (SR ต่อปี)

**F09 — Deflated Sharpe Ratio**: $DSR = PSR(SR^* = SR_0)$ ผ่านเมื่อ **DSR ≥ 0.95**

**F10 — Minimum Track Record Length**
$$MinTRL = 1 + \left(1 - \gamma_3\widehat{SR} + \frac{\gamma_4-1}{4}\widehat{SR}^2\right)\left(\frac{z_\alpha}{\widehat{SR} - SR^*}\right)^2 \quad\text{(หน่วย period)}$$

**F11 — จำนวน trial ที่เป็นอิสระจริง** (trial ที่ correlated กันนับเป็นหลายตัวไม่ได้)
$$N_{eff} = \frac{(\sum_i \lambda_i)^2}{\sum_i \lambda_i^2},\quad \lambda_i = \text{eigenvalues ของ correlation matrix}$$

**F12 — Minimum Backtest Length**: $MinBTL \approx \left(E[\max_N]/SR_{target}\right)^2$ ปี, โดยประมาณ $\le 2\ln N / SR_{target}^2$

**F13 — Probability of Backtest Overfitting (CSCV)**
1. แบ่ง matrix ผลตอบแทน (T × N trials) เป็น S บล็อก (S คู่ เช่น 16)
2. ทุก combination ที่เลือก S/2 บล็อกเป็น IS และที่เหลือเป็น OOS
3. หา trial ที่ดีที่สุดใน IS แล้วดูอันดับสัมพัทธ์ $\bar\omega$ ของมันใน OOS: $\lambda = \ln\frac{\bar\omega}{1-\bar\omega}$
4. $PBO = P(\lambda \le 0)$ → ผ่านเมื่อ **PBO ≤ 0.2**

**F14 — White Reality Check / Hansen SPA**: bootstrap สถิติ $\max_k \sqrt{n}\,\bar d_k$ (โดย $d_k$ = ผลต่างจาก benchmark) เพื่อทดสอบว่า "ตัวที่ดีที่สุดในทุกตัวที่ลอง" ดีกว่า benchmark จริงหรือไม่

**F15 — False Discovery Rate (Benjamini–Hochberg)**: เรียง p-value จากน้อยไปมาก แล้ว reject ตัวที่ $p_{(i)} \le \frac{i}{m}q$ ใช้เมื่ออยากได้ "หลายกลยุทธ์ที่น่าจะจริง" ไม่ใช่แค่ตัวเดียว

**F16 — Walk-forward efficiency**: $WFE = \dfrac{\text{ann. return OOS}}{\text{ann. return IS}}$ (ควร ≥ 0.5) ส่วน CPCV (Combinatorial Purged CV) ให้การกระจายของ OOS SR แทนที่จะได้ค่าเดียว

**F17 — Haircut SR** (สิ่งที่คาดว่าจะเห็นใน live)
$$SR_{live} \approx SR_{bt}\,(1 - h),\qquad h \in [0.26,\ 0.58]\ \text{(McLean–Pontiff)}$$
ถ้าใช้ DSR แล้ว ให้ใช้ $SR_{bt} - SR_0$ เป็นค่าตั้งต้นที่อนุรักษ์นิยม

---

## D. Bayes — รวม prior เข้ากับหลักฐาน

**F20 — P(edge จริง | ผ่านการทดสอบ)**
$$P(\text{real}\mid\text{pass}) = \frac{\pi\cdot\text{power}}{\pi\cdot\text{power} + \alpha(1-\pi)}$$
โดย $\pi$ = prior จาก [`evidence_base.yaml#priors`](../data/evidence_base.yaml) ส่วน $\alpha$ ต้องเป็นค่า**หลังปรับ multiple testing** แล้ว
> ถ้าลอง N แบบที่ α = 0.05 โดยไม่ปรับ โอกาสเจอ false positive อย่างน้อยหนึ่งตัว = $1-0.95^N$ (N=45 → 90%)

**F21 — Shrinkage ของ SR** (normal–normal conjugate)
$$SR_{post} = \frac{SR_{prior}/\tau^2 + \widehat{SR}\cdot T}{1/\tau^2 + T}$$
โดย $\tau$ = ความไม่แน่นอนของ prior ใช้ทั้งตอน validate และระหว่าง live (อัปเดตทุกเดือน)

---

## E. ขนาดไม้ การรอด และ drawdown

**F22 — Kelly**
- แบบไม้ต่อไม้: $f^* = p - \dfrac{q}{b}$ (b = W/L)
- แบบต่อเนื่อง: $f^* = \mu/\sigma^2$
- Growth ที่ fraction $c$ ของ Kelly: $g(c) = (c - c^2/2)\,SR^2$ → full Kelly ได้ $SR^2/2$, half Kelly ได้ 75% ของค่านั้น
- **โอกาสที่พอร์ตจะลดลงเหลือ x เท่าของระดับปัจจุบัน ณ จุดใดจุดหนึ่งในอนาคต**:
$$P(\text{ลดลงถึง } x) = x^{\,2/c - 1}$$
(full Kelly: โอกาสลดลงครึ่งหนึ่ง = 50%; quarter Kelly: 0.8%)

**F23 — Risk of Ruin** (Brownian approximation, ขนาดไม้คงที่)
$$RoR \approx \exp\!\left(-\frac{2\,E_{net}\,D}{\sigma_R^2}\right),\qquad D = \frac{\text{DD limit}}{\text{risk per trade}}$$
ถ้า $E_{net} \le 0$ → $RoR = 1$ (ระยะยาว)
> กรณีพิเศษ 1:1 payoff (gambler's ruin): $RoR = \left(\frac{q}{p}\right)^{D}$

**F18 — Martingale (เพิ่มไม้เป็น 2 เท่าหลังแพ้ สูงสุด k ครั้ง)**
$$P_{fail/cycle} = q^k,\qquad EV_{cycle} = (1-q^k)\cdot u - q^k\,(2^k-1)\cdot u$$
เมื่อ $q=0.5$ จะได้ EV = 0 พอดี (เกมยุติธรรม) และถ้า $q>0.5$ (มี spread) EV < 0 ส่วนจำนวนรอบที่คาดว่าจะถึง ruin คือ $1/q^k$

**F24 — Two-barrier (prop challenge: ถึง +a ก่อน −b)**
$$P(+a\text{ ก่อน }-b) = \frac{e^{kb} - 1}{e^{kb} - e^{-ka}},\quad k = \frac{2\mu}{\sigma^2};\quad \mu = 0 \Rightarrow \frac{b}{a+b}$$

---

## F. พอร์ตและระบอบตลาด

**F19 — การกระจาย**: $SR_p = SR\sqrt{\dfrac{N}{1 + (N-1)\rho}}$ (ตาราง T11)

**F30 — Fundamental Law of Active Management**: $IR \approx IC\sqrt{BR}$ โดยต้องนับเฉพาะเดิมพันที่เป็นอิสระ

**F25 — Markov regime**: ใช้ transition matrix $P$ หาระยะเวลาคาดหวังของระบอบ $i$ จาก $1/(1-p_{ii})$ และการกระจายระยะยาวจาก $\pi P = \pi$ ส่วน HMM ให้ $P(\text{state}_t \mid \text{data}_{1..t})$ ซึ่งนำไปใช้ปรับขนาดไม้ตาม $SR$ ของแต่ละระบอบได้

**การเสื่อมของ edge (decay)**: $\alpha(t) = \alpha_0 e^{-\lambda t}$ มีครึ่งชีวิต $= \ln 2/\lambda$ จึงควรประเมิน λ จาก rolling SR

---

## G. การเฝ้าระวังขณะ live

**F26 — CUSUM / SPRT**
- CUSUM: $S_t = \max(0,\ S_{t-1} + (k - x_t))$ (x = return รายวันที่ปรับมาตรฐาน) แล้วแจ้งเตือนเมื่อ $S_t > h$
- SPRT: $\Lambda_t = \sum \ln\frac{f_1(x)}{f_0(x)}$ โดย $H_0$: SR = SR_live ที่คาดไว้ และ $H_1$: SR = 0 แล้วหยุดเมื่อ $\Lambda_t > \ln\frac{1-\beta}{\alpha}$

**F27 — Monte Carlo / Bootstrap**: ใช้ stationary block bootstrap กับ return หรือ trade (เก็บ autocorrelation ไว้) และสลับลำดับ trade เพื่อหาการกระจายของ MDD/CAGR → kill switch เมื่อ live DD เกิน percentile ที่ 95–99

**F28 — Calibration ของ AI agent**: Brier score $BS = \frac{1}{n}\sum (p_t - y_t)^2$ โดย $p_t$ = ความน่าจะเป็นที่ agent บอกว่าราคาจะขึ้น และ $y_t \in \{0,1\}$ (ถ้าเดาสุ่มจะได้ 0.25)

---

## H. สมการรวม

**F29 — ความน่าจะเป็นที่จะทำกำไรต่อเนื่อง**
$$P(\text{consistent}) = \sum_k P(\text{state}_k \mid \text{evidence})\cdot P(\text{criteria} \mid SR_k, \sigma, T, \text{sizing})$$
- $P(\text{state}_k \mid \text{evidence})$ มาจาก F20/F21 (edge จริงหรือไม่ และ SR เท่าไร)
- $P(\text{criteria} \mid \cdot)$ มาจาก Monte Carlo (F27) ตาม `ConsistencyCriteria`
- ผลลัพธ์เก็บใน `ProbabilityReport`

```
EvidenceRecord ─► PriorBelief(π) ─┐
StrategySpec ─► BacktestRun* ─► TrialRegistry(N) ─► ValidationReport(DSR,PBO,SPA,MinTRL)
                                                         │
                                          EdgePosterior(P real, SR_live) ◄─┘
                                                         │
                       RiskPlan(c·Kelly, D) ─► RoR, P(DD) │
                                                         ▼
                         ConsistencyCriteria ─► ProbabilityReport ─► LiveMonitor ─┐
                                                         ▲                       │
                                                         └──── Bayes update ◄────┘
```
