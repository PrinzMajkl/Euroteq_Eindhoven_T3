# Local Stakeholder Use Cases: The Pegnitz River Ecosystem

A deep-dive into the four distinct socio-ecological pillars that justify deploying the PlumeTrace Digital Twin on the Pegnitz River in Nuremberg, Bavaria.

---

## 1. The Four Pillar Framework

```text
+---------------------------------------------------------------------------------------------------+
|                                 PEGNITZ RIVER USE-CASE PILLARS                                    |
+----------------------------------+----------------------------------+-----------------------------+
| 1. PUBLIC HEALTH & RECREATION    | 2. URBAN INFRASTRUCTURE (CSOs)   | 3. AGRICULTURE & DRINKING   |
| - Fuchslochwelle river surfers   | - Stormwater sewer overflows     | - Knoblauchsland runoff     |
| - Pegnitzauen parks & waders     | - Hidden/under-capacitated pipes | - Groundwater protection    |
| - "Traffic Light" warning app    | - Municipal investment heatmaps  | - Fertilizer optimization   |
+----------------------------------+----------------------------------+-----------------------------+
|                                4. ECOLOGY & CLIMATE RESILIENCE                                    |
| - Low summer water levels & concentrated toxic pollutants                                         |
| - Acute hypoxia & fish kills                                                                      |
| - Automated alerts triggering upstream reservoir water releases (e.g., Rothsee transfer)          |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Detailed Pillar Profiles

### Pillar 1: Public Health and Urban Recreation
- **The Local Reality**:
  - The Pegnitz flows directly through urban Nuremberg and popular public green corridors (**Pegnitzauen**).
  - High-impact recreational spot: The **Fuchslochwelle**, an artificial river-surfing wave attracting daily surfers, alongside kayakers, dog owners, and families wading along the riverbanks.
- **The Acute Threat**:
  - Unseen fecal and untreated wastewater contamination spikes enter the reach following localized rainfall events, exposing water-sports athletes and citizens to pathogenic risks and skin/gastrointestinal infections.
- **Data Utilization & Digital Twin Role**:
  - The Digital Twin powers a real-time **Dynamic Early Warning System**, predicting when and where water quality deteriorates hours before standard grab-tests could even be processed.
- **Public Communication & Interface**:
  - A citizen-facing mobile app interface based on a simple **"Traffic Light"** indicator:
    - 🟢 **Green**: Safe for recreation.
    - 🟡 **Yellow**: Caution – elevated turbidity / marginal readings.
    - 🔴 **Red**: Danger – active contamination plume detected; do not enter the water.
  - *Strategic Impact*: Shifts the narrative from abstract ecological metrics to **tangible, immediate human health protection**.

---

### Pillar 2: Urban Infrastructure & Stormwater Sewer Systems
- **The Local Reality**:
  - Like many historic European cities, Nuremberg features combined sewer systems carrying both stormwater and domestic wastewater.
- **The Acute Threat**:
  - Sudden, heavy convective storm downpours overload treatment plant capacities, triggering Combined Sewer Overflows (CSOs) that discharge untreated sewage directly into the Pegnitz through relief outfalls.
- **Data Utilization & Digital Twin Role**:
  - The mobile robotic platform measures chemical plumes ($\text{NH}_3\text{-N}$, $\text{DO}$), while the Digital Twin reconstructs the spatial plume gradient back upstream, identifying *which specific outfall pipes* suffer from recurring hydraulic bottlenecks or chronic under-capacity.
- **Authority Communication & Interface**:
  - Deliver high-resolution **Pollution Heatmaps** to municipal utility authorities (*Stadtentwässerung und Umweltanalytik Nürnberg - SUN*) and the *Wasserwirtschaftsamt*.
  - *Strategic Impact*: Replaces guesswork with empirical diagnostic data, enabling city planners to direct multimillion-euro municipal infrastructure modernization budgets to the exact outfalls causing the greatest environmental harm.

---

### Pillar 3: Agriculture & Groundwater Protection (Knoblauchsland)
- **The Local Reality**:
  - The Nuremberg metropolitan region is directly adjacent to the **Knoblauchsland**, one of Germany’s most intensive vegetable-farming and greenhouse agricultural regions.
- **The Acute Threat**:
  - Agricultural runoff containing high concentrations of nitrates, synthetic fertilizers, and pesticide metabolites drains into the Pegnitz reach and infiltrates vulnerable local alluvial groundwater aquifers used for regional drinking water.
- **Data Utilization & Digital Twin Role**:
  - The autonomous system isolates agricultural diffuse runoff plumes from municipal point sources by analyzing specific chemical signatures, measuring exact inflow tributaries and calculating cross-channel dilution.
- **Stakeholder Engagement & Interface**:
  - Constructive dialogue with regional agricultural associations (*Bayerischer Bauernverband*) and the *Wasserwirtschaftsamt*.
  - *Strategic Impact*: Presents the data not as a punitive tool, but as a precision guidance system—empowering farmers to optimize fertilizer application timing and pinpoint field drainage without facing blunt, blanket regulatory bans.

---

### Pillar 4: Climate Change Resilience, Drought & Ecosystem Collapse
- **The Local Reality**:
  - Prolonged summer droughts and climate extremes increasingly lead to critically low discharge levels in the Pegnitz, dramatically reducing the river’s natural dilution capacity.
- **The Acute Threat**:
  - Warmer water temperatures combined with reduced flow cause toxic pollutant concentration spikes and trigger rapid biological oxygen depletion ($\text{DO} < 3\ \text{mg/L}$), precipitating catastrophic mass fish kills.
- **Data Utilization & Digital Twin Role**:
  - Continuous monitoring identifies early hypoxic hotspots and critical biological degradation before massive die-offs occur.
  - Integrates with regional water management telemetry to trigger active hydrological interventions (e.g., regulated flow augmentation from upstream reservoirs via the Bavarian Danube-Main transfer system).
- **Stakeholder Engagement & Interface**:
  - Automated early warning alerts dispatched to regional angling associations (*Fischereiverband*) and nature conservation agencies.
  - *Strategic Impact*: Preserves aquatic biodiversity and generates powerful visual PR evidence demonstrating proactive municipal climate resilience.

---

## 3. The Dual-Dashboard Product Architecture

```text
+---------------------------------------------------------------------------------------------------+
|                               PLUMETRACE USER INTERACTION MODEL                                   |
+---------------------------------------------------+-----------------------------------------------+
| CITIZEN DASHBOARD (Recreation & Public Health)     | REGULATORY / MUNICIPAL PORTAL (Authorities)   |
+---------------------------------------------------+-----------------------------------------------+
| - Target: Fuchslochwelle surfers, dog walkers     | - Target: Wasserwirtschaftsamt, City SUN      |
| - Traffic Light Banner (Green / Yellow / Red)     | - Quantitative Cesium 3D LOD2 Spatial Viewer  |
| - Live Advisory: "Unsafe for water contact today" | - Diagnostic Outfall Capacity Heatmaps        |
| - Push notifications for active CSO plumes        | - Statistical Reports for Infrastructure CAPEX|
+---------------------------------------------------+-----------------------------------------------+
```

---

## 4. Autonomous Closed-Loop Re-Tasking Dynamics

The robot does not follow a blind, static path. The Digital Twin actively commands where the robot must sample next based on an integrated 4-dimensional objective function:

$$\text{Next Target} = f\Big(\text{Data Age } (\tau),\ \text{Concentration Gradient } (\nabla C),\ \text{Weather / Rain Forecast } (W),\ \text{Historical Baseline } (H)\Big)$$

1. **Information Freshness (Data Age $\tau$)**: Drives exploratory waypoints to areas where measurements are stale or unverified.
2. **Chemical Gradient ($\nabla C$)**: Vectors the robot upstream toward increasing $\text{NH}_3\text{-N}$ and decreasing $\text{DO}$ gradients when an acute spike is flagged.
3. **Meteorological & Radar Feeds ($W$)**: Re-allocates patrol focus to specific outfall reaches downstream of intense localized convective storm cells.
4. **Historical Baselines ($H$)**: Compares live readings against long-term seasonal baselines to isolate anomalous behavior from normal background variations.
