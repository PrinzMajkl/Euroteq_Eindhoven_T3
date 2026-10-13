# Local Stakeholder Framework: Authorities & Citizens in Nuremberg

Strategic stakeholder architecture categorizing the PlumeTrace Digital Twin ecosystem into two primary groups: **Local Authorities** (Primary) and **Citizens & Recreators** (Secondary). All environmental pressures (urban CSOs, Knoblauchsland agriculture, drought/hypoxia) are channeled directly through municipal oversight.

---

## 1. Stakeholder Hierarchy

```text
+---------------------------------------------------------------------------------------------------+
|                                 STAKEHOLDER ARCHITECTURE                                          |
+---------------------------------------------------------------------------------------------------+
|                                PRIMARY STAKEHOLDERS: LOCAL AUTHORITIES                            |
|  - WWA Nürnberg (Wasserwirtschaftsamt Nürnberg)           --> River reach monitoring & enforcement|
|  - SUN (Stadtentwässerung und Umweltanalytik Nürnberg)     --> Municipal sewer network & CSOs      |
|  - LfU (Bayerisches Landesamt für Umwelt)                 --> Bavarian statewide water regulation |
|  - Gesundheitsamt Nürnberg (Public Health Department)     --> Recreational water safety advisories|
+---------------------------------------------------------------------------------------------------+
|                           SECONDARY STAKEHOLDERS: CITIZENS & RECREATORS                           |
|  - Fuchslochwelle river surfers                                                                   |
|  - Pegnitzauen park visitors, swimmers, waders, dog owners                                        |
|  - Recreational water sports clubs & anglers                                                      |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Primary Stakeholders: Local Authorities & Current vs. Improved Data

### A. WWA Nürnberg (*Wasserwirtschaftsamt Nürnberg*)
- **Official Role**: Regional State Water Management Office responsible for hydrological monitoring, river ecological status (EU WFD), flood protection, and emergency point-source pollution tracking along the Pegnitz.
- **Current Baseline (What they measure now)**:
  - **Static River Gauges (GKD Bayern)**: Single-point monitoring stations (e.g., Pegnitz-Doos, Nürnberg gauge) tracking water discharge ($m^3/s$), water temperature, and electrical conductivity.
  - **Manual Grab Sampling (*Schöpfproben*)**: Physical collection of water samples taken by field technicians at fixed intervals (typically monthly or bi-weekly).
- **The Bottleneck**:
  - Point stations only detect what flows directly past their probe; they cannot pinpoint where upstream an unmapped discharge occurred.
  - Manual grab sampling completely misses transient 2-to-4-hour Combined Sewer Overflows (CSOs) triggered by localized summer storm cells.
- **How PlumeTrace Improves It**:
  - Provides **mobile spatial gradient tracing** directly back to the active discharge source.
  - Delivers automated, geolocated statutory alerts in **$< 60\ \text{seconds}$** upon threshold breach ($\text{NH}_3\text{-N} > 0.6\ \text{mg/L}$ under German OGewV).

---

### B. SUN (*Stadtentwässerung und Umweltanalytik Nürnberg*)
- **Official Role**: Municipal drainage, sewer network, and environmental analytics utility of the City of Nuremberg. Manages ~1,500 km of public sewers, wastewater treatment plants (*Klärwerk 1 & 2*), stormwater retention basins (*Regenüberlaufbecken - RÜB*), and CSO relief structures (*Regenüberläufe - RÜ*).
- **Current Baseline (What they measure now)**:
  - **Internal Sewer SCADA Telemetry**: Level sensors and overflow weir trip-counters inside underground retention tanks.
- **The Bottleneck**:
  - They know *if* and *when* an overflow weir spilled, but have **zero visibility into how the pollution plume disperses in the river**, how acute the chemical concentration is, or how long the aquatic reach remains toxic.
  - Capital investment decisions (which multi-million-euro retention basins need expansion) rely on theoretical hydraulic models rather than empirical in-river impact data.
- **How PlumeTrace Improves It**:
  - Generates quantitative **3D In-River Pollution Heatmaps** in Cesium/LOD2 mapping the exact dispersion plume of specific sewer outfalls.
  - Pinpoints which specific outfalls cause the greatest in-stream ecological violations, providing concrete data justification for targeted municipal infrastructure investments.

---

### C. LfU (*Bayerisches Landesamt für Umwelt*)
- **Official Role**: Bavarian State Office for the Environment. Sets statewide environmental thresholds, oversees compliance with the EU Water Framework Directive (WFD), and enforces the German *Oberflächengewässerverordnung* (OGewV).
- **Current Baseline**: Aggregated macrozoobenthos biological surveys, long-term trend statistics, and chemical monitoring networks.
- **How PlumeTrace Improves It**:
  - Feeds high-resolution spatio-temporal data into regional hydrodynamic models, linking upstream agricultural drainage (Knoblauchsland) and urban CSOs with downstream water quality.
  - Verifies compliance with EU ambient water quality indicator SDG 6.3.2.

---

### D. Gesundheitsamt Nürnberg (*City Public Health Department*)
- **Official Role**: Municipal department responsible for public health protection, infectious disease prevention, and recreational water advisories.
- **Current Baseline (What they measure now)**:
  - **Laboratory Petri-Dish Cultures**: Periodic testing for microbiological pathogens (*Escherichia coli*, *intestinal enterococci*).
- **The Bottleneck**:
  - Incubation tests require **24 to 48 hours** to produce results. By the time contamination is confirmed in the laboratory, the acute storm plume has already passed, and surfers or bathers have already been exposed to contaminated water.
- **How PlumeTrace Improves It**:
  - Connects real-time physical chemical sensing ($\text{NH}_3\text{-N}$, $\text{DO}$) to predictive dispersion models, forecasting water safety hours ahead of delayed laboratory cultures.

---

## 3. Secondary Stakeholders: Citizens & Recreators

### The Target Community:
- Urban river surfers at the **Fuchslochwelle** wave in Nuremberg.
- Recreational visitors in the **Pegnitzauen** park corridors.
- Swimmers, children wading in shallow sections, and dog owners.

### The Actionable Interface: Citizen "Traffic Light" App
- Instead of overwhelming the public with chemical metrics ($\text{mg/L}\ \text{NH}_3\text{-N}$ or $\mu\text{S/cm}$), data is translated into an immediate, intuitive visual standard:
  - 🟢 **Green (Safe)**: Water quality meets recreational safety standards.
  - 🟡 **Yellow (Caution)**: Marginal conditions, elevated turbidity or post-storm flow.
  - 🔴 **Red (Hazard - Do Not Enter)**: Active contamination plume detected; high risk of skin/gastrointestinal infection.
- **Strategic Impact**: Establishes a direct public health value proposition that resonates strongly with everyday citizens, local media, and presentation juries.

---

## 4. Unifying Agricultural, Ecological, and Urban Pressures under Municipal Oversight

Rather than treating farmers or fisheries as separate independent clients, their concerns are channeled directly into municipal and authority mandates:
1. **Urban Sewage Overflows**: Governed and remediated by **SUN** using PlumeTrace diagnostic heatmaps.
2. **Agricultural Leaching (Knoblauchsland)**: Monitored and enforced by **WWA Nürnberg** through targeted drainage mouth sampling, replacing blunt blanket bans with empirical point-source evidence.
3. **Drought, Hypoxia & Fish Kills**: Handled by **WWA Nürnberg** and state water managers via automated hypoxic alerts ($\text{DO} < 3\ \text{mg/L}$) that trigger emergency fresh-water discharge from upstream storage systems (Bavarian Danube-Main water transfer / Rothsee reservoir).
