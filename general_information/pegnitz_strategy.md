# The "Pegnitz Strategy": Site Selection & Regulatory Framework

Strategic rationale for selecting the Pegnitz River (Nuremberg, Bavaria) over generic global waterways, highlighting geospatial data integration and European regulatory alignment.

---

## 1. Rationale: Why the Pegnitz River?

Switching from generic or unmanaged global river scenarios (e.g., the Yamuna River) to a specific, localized German urban river radically improves the technical feasibility, realism, and stakeholder relevance of the Digital Twin.

```text
+-----------------------------------------------------------------------------------------+
|                                  THE PEGNITZ STRATEGY                                   |
+------------------------------+------------------------------+---------------------------+
|    REALISTIC GEODATA         |   BELIEVABLE CSO SCENARIO    |   REGULATORY ALIGNMENT    |
| - Bavarian LOD2 OpenData     | - Transient storm overflows  | - EU Water Framework Dir. |
| - 3DCityDB & Cesium terrain  | - Localized & time-critical  | - German OGewV            |
| - Real bridge clearances     | - Dissipates before grab-test| - NH3-N > 0.6 mg/L breach |
+------------------------------+------------------------------+---------------------------+
```

### A. Realistic Geospatial Data Availability (Bavarian OpenData)
- **3D City Models (LOD2)**: 3DCityDB and Cesium require high-fidelity geographic and structural geometries. Through the Bavarian State's public OpenData portal (`GeodatenBayern`), the project accesses:
  - Official **LOD2 (Level of Detail 2)** building models with roof shapes.
  - Surveyed **riverbank topographies and digital elevation models (DEM)**.
  - Real-world **bridge clearances, weir locations, and culvert geometries**.
- **Impact**: Elevates the Digital Twin from a theoretical, synthetic sandbox into an operationally grounded geospatial environment.

### B. Believable, Time-Sensitive Pollution Scenario
- Unlike unregulated global rivers that experience continuous, indiscriminate raw sewage discharge, regulated Central European rivers maintain generally stable baseline water quality.
- **The Acute Threat: Combined Sewer Overflows (CSOs)**:
  - During sudden, heavy urban rainfall events, combined storm and wastewater sewers exceed retention capacity.
  - Excess effluent bypasses wastewater treatment plants and discharges directly into the Pegnitz through relief outfalls.
- **Why a Digital Twin is uniquely required**:
  - CSO plumes are **transient, localized, and dynamic**.
  - By the time municipal authorities organize traditional manual grab-sampling, the plume has already diluted and flowed downstream.
  - A mobile autonomous robot coupled with a real-time plume-inverting Digital Twin is the only viable method to detect, follow, and localize the discharge source before it dissipates.

### C. European & German Regulatory Alignment
The Proof of Concept replaces generic metrics with statutory thresholds rooted in European and German environmental law:

| Regulatory Body / Law | Statutory Context | Project Relevance & Threshold |
| :--- | :--- | :--- |
| **EU Water Framework Directive (WFD / 2000/60/EC)** | Mandates "good ecological status" for all European surface water bodies. | Establishes the legal duty to monitor, prevent ecological deterioration, and identify point-source pollution. |
| **Oberflächengewässerverordnung (OGewV)** | German Federal Surface Water Ordinance governing chemical and ecological thresholds. | Sets specific maximum allowable concentrations for priority substances and pollutants. |
| **Ammonia Nitrogen ($\text{NH}_3\text{-N}$) Threshold** | Toxic to freshwater fish species ($LC_{50}$ in salmonids and cyprinids); rapidly depletes dissolved oxygen ($\text{DO}$). | A reading of **$> 0.6\ \text{mg/L}\ \text{NH}_3\text{-N}$** represents an acute statutory violation triggering emergency regulatory response. |

---

## 2. Key Stakeholder Value Proposition

By grounding the solution in the Pegnitz and Bavarian regulatory frameworks, the project delivers immediate utility to regional authorities:
- **Wasserwirtschaftsamt (WWA) Nuremberg**: Receives automated incident alerts within $< 60\ \text{seconds}$ with estimated coordinates of the active outfall.
- **Bayerisches Landesamt für Umwelt (LfU)**: Obtains high-resolution temporal data to update regional hydrological and overflow risk maps.
