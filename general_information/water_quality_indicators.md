# Municipal Water Quality Indicators: The SUN Monitoring Baseline

Analysis of the 8 standard parameters monitored by the City of Nuremberg's municipal drainage and environmental analytics service (*Stadtentwässerung und Umweltanalytik Nürnberg - SUN*), their diagnostic value, and the critical temporal-frequency bottleneck.

---

## 1. The 8 Core Indicators Monitored by SUN

The municipal monitoring station of the City of Nuremberg (SUN) tracks eight fundamental physico-chemical and nutrient parameters along the Pegnitz River reach:

| # | Parameter | Scientific Unit | Why SUN Measures It | Diagnostic Informational Value & Use |
| :- | :--- | :--- | :--- | :--- |
| **1** | **Water Temperature** | °C | Governs chemical kinetics, biological metabolic rates, and oxygen solubility. | Identifies thermal pollution; essential for calculating the dissociation ratio of non-toxic ammonium ($\text{NH}_4^+$) into toxic ammonia ($\text{NH}_3$). |
| **2** | **pH Value** | pH units (6.5–8.5) | Measures hydrogen ion activity (acidic vs. alkaline balance). | Detects sudden industrial discharges or chemical dumps; controls ammonia toxicity (higher pH exponentially increases toxic un-ionized $\text{NH}_3$). |
| **3** | **Electrical Conductivity** | µS/cm | Quantifies total dissolved ionic solids and mineral salts. | Immediate tracer of ionic surges: road de-icing salt runoff in winter, industrial brine discharges, or high-conductivity domestic wastewater. |
| **4** | **Dissolved Oxygen (DO)** | mg/L | Essential for aerobic aquatic life and fish respiration. | Vital sign of river health. Detects acute hypoxia/anoxia caused by microbial respiration when raw wastewater or organic matter enters the river. |
| **5** | **Turbidity** | NTU / FNU | Optical measurement of suspended particulates and cloudiness. | Rapid optical indicator of wet-weather events: soil erosion, riverbed scouring, treatment plant bypasses, and active sewer pipe overflow plumes. |
| **6** | **Ammonium ($\text{NH}_4^+$) / Ammonia ($\text{NH}_3\text{-N}$)** | mg/L | Signature chemical fingerprint of raw sewage, urine, faeces, and protein breakdown. | **Primary point-source tracer**: Acute indicator of untreated wastewater overflows. Triggers regulatory violation under German OGewV when $> 0.6\ \text{mg/L}$. |
| **7** | **Nitrate ($\text{NO}_3^-$)** | mg/L | Stable oxidized form of dissolved nitrogen. | Tracks chronic diffuse agricultural pollution from the Knoblauchsland; assesses compliance with the EU Nitrates Directive. |
| **8** | **Phosphate ($\text{PO}_4^{3-}$)** | mg/L | Critical limiting nutrient for plant and algal growth. | Diagnoses eutrophication risks; excessive levels fuel algal blooms that cause severe secondary nocturnal oxygen depletion. |

---

## 2. The Fatal Bottleneck: Sampling Frequency vs. Event Duration

Authorities understand *what* each parameter means and *why* it is important. The failure of current water monitoring is **not the chemical parameters, but the sampling frequency and spatial rigidity**.

```text
CONVENTIONAL REGULATORY MONITORING (Manual Grab Sampling):
[Sample Day 1] -------------------- (28 Days of Blindness) -------------------- [Sample Day 29]
                                      ▲
                                      │ 3-Hour Storm Event & Raw CSO Spill (MISSED ENTIRELY)

PLUMETRACE AUTONOMOUS DIGITAL TWIN:
[Continuous Sensing] ──> [Spike Trigger] ──> [Dynamic Plume Tracing] ──> [Source Localized in < 35 s]
```

### The Spatial and Temporal Disconnect:
1. **The Temporal Mismatch**:
   - Severe Combined Sewer Overflows (CSOs) and acute storm runoff pulses are **transient events lasting only 2 to 4 hours**.
   - SUN and WWA perform manual grab sampling (*Schöpfproben*) on a **monthly or bi-weekly schedule**.
   - Statistically, monthly grab sampling has a **near-zero probability** of capturing the peak toxicity of a storm-driven discharge event. By the time a technician takes a sample, the acute plume has diluted and flowed miles downstream.
2. **The Spatial Blind Spot**:
   - Fixed municipal monitoring stations only detect pollution that passes directly over their submerged probes.
   - If an illegal, unmapped, or malfunctioning storm outfall discharges 400 meters upstream or along the opposite riverbank, static probes cannot pinpoint the responsible pipe.
3. **The Incubation Delay**:
   - Microbiological pathogen testing conducted by the *Gesundheitsamt* requires **24 to 48 hours** of laboratory Petri-dish incubation. Warnings are issued days after the public has already been exposed.

---

## 3. How PlumeTrace Bridges the Gap

PlumeTrace does not need to invent new chemical indicators; it provides the **missing spatio-temporal intelligence layer**:
- Uses **Ammonia ($\text{NH}_3\text{-N}$)** and **Dissolved Oxygen ($\text{DO}$)** as rapid, continuous electronic proxies for raw sewage discharge.
- Operates on a **30-second telemetry cycle** instead of a 30-day manual cycle.
- Autonomously traverses the river reach to map the **spatial gradient**, localizing the exact leaking outfall pipe before the plume dissipates.
