# 🔋 White Paper 05: Wireless Power Transmission and Space Solar Power Systems

## Electromagnetic Induction Efficiency and the SPS Technology Pathway

> **Symbol reference**: [SYMBOLOGY.md §I.D](../../SYMBOLOGY.md)

---

## Abstract

Wireless Power Transmission (WPT) via resonant magnetic field coupling represents a key enabling technology in the broader electromagnetic research portfolio associated with astro-fusion applications. This white paper documents the theoretical efficiency model for inductance-relay coil systems, the experimental efficiency measurement protocol, and the technology roadmap toward Space Solar Power System (SPS) satellite experiments — providing context for the non-laboratory electromagnetic datasets catalogued in `data/empirical/`.

---

## 1. WPT Theory: Magnetic Inductive Coupling

### 1.1 Mutual Inductance Model

A two-coil resonant WPT system consists of a transmitter coil (Tx) and a receiver coil (Rx), magnetically coupled through a relay coil (Relay). The power transfer efficiency $\eta_{\rm WPT}$ is:

$$\eta_{\rm WPT} = \frac{P_{\rm load}}{P_{\rm input}} = \frac{k^2 Q_{\rm Tx} Q_{\rm Rx}}{(1 + k^2 Q_{\rm Tx} Q_{\rm Rx})^2}$$

where:

- $k = M / \sqrt{L_{\rm Tx} L_{\rm Rx}}$ is the coupling coefficient ($0 \leq k \leq 1$)
- $M$ is the mutual inductance (H)
- $Q_{\rm Tx}$, $Q_{\rm Rx}$ are the quality factors of transmitter and receiver coils at resonance

### 1.2 Relay Coil Enhancement

Inserting a passive relay coil between Tx and Rx extends the effective transmission range. For a three-coil system, the optimum relay position maximises the effective coupling product $k_{\rm eff}$:

$$k_{\rm eff} = k_{\rm Tx-Relay} \cdot k_{\rm Relay-Rx}$$

### 1.3 Resonance Condition

Maximum efficiency is achieved when all coils operate at the resonant frequency $f_0 = 1/(2\pi\sqrt{LC})$, where $L$ is inductance and $C$ is the compensation capacitor value. Frequency mismatch dramatically reduces $\eta_{\rm WPT}$.

---

## 2. Experimental Efficiency Measurement

| Parameter                   | Measurement Method                 | Equipment           |
| --------------------------- | ---------------------------------- | ------------------- |
| Tx frequency $f_0$          | Network analyzer sweep             | Keysight E5063A     |
| Power input $P_{\rm input}$ | Current × voltage at Tx            | Power meter         |
| Power output $P_{\rm load}$ | Load voltage across $R_{\rm load}$ | Precision voltmeter |
| Coupling $k$                | S-parameter measurement            | VNA, 2-port         |

Expected efficiency at 20 cm coil separation, $Q=200$: $\eta_{\rm WPT} \approx 70$–$85\%$.

---

## 3. Space Solar Power System (SPS) Pathway

| Development Stage          | Description                                   | TRL     |
| -------------------------- | --------------------------------------------- | ------- |
| Ground WPT                 | Lab-scale relay coil efficiency demonstration | TRL 4–5 |
| High-altitude WPT demo     | Balloon-borne Tx to ground Rx                 | TRL 3   |
| Low Earth Orbit (LEO) demo | Satellite-to-ground microwave WPT             | TRL 2–3 |
| Geostationary SPS          | Full-scale solar collector + WPT to rectenna  | TRL 1–2 |

The primary technical challenges for SPS are beam pointing precision (sub-mrad over 35,786 km GEO altitude) and rectenna efficiency at GHz microwave frequencies ($\eta_{\rm rectenna} > 80\%$ target).

---

_SPS experiment plans documented in collaboration with the Chinese First Quasi-axisymmetric Stellarator (CFQS) programme (NIFS / SWJTU joint initiative). Symbol cross-reference: [SYMBOLOGY.md §I.D](../../SYMBOLOGY.md)._
