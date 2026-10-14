# PlumeTrace Brand & Presentation Style Guide

Minimalistic visual identity and graphic design system tailored for the PlumeTrace defence presentation, executive pitch deck, and digital twin dashboard UI.

---

## 1. Visual Philosophy & Design Principles

- **Clean & Minimalistic**: Generous white space, uncluttered slide canvases, structured card layouts, and strong typographic hierarchy.
- **Human-Centric & Grounded**: Balances cutting-edge autonomous robotics with tangible human health and environmental protection.
- **Strictly No Monospace Typography**: All slide typography uses clean, modern, proportional sans-serif typefaces. Code and data tables are styled cleanly without typewriter aesthetics.
- **Pure White Background**: The presentation canvas is strictly **Pure White (`#FFFFFF`)**, ensuring optimal contrast, professional projector rendering, and clean print readability.

---

## 2. Official Color Palette

```text
+---------------------------------------------------------------------------------------------------+
|                                     PLUMETRACE COLOR SYSTEM                                       |
+-------------------+-------------------+-------------------+-------------------+-------------------+
|   MIDNIGHT NAVY   |    RIVER CYAN     |    SKY BREEZE     |    AMBER GOLD     |  TANGERINE ORANGE |
|     #023047       |     #219ebc       |     #8ecae6       |     #ffb703       |     #fb8500       |
|  [PRIMARY TEXT]   |  [PRIMARY BRAND]  | [SECONDARY TINT]  |  [WARNING STATE]  |   [ACUTE ALERT]   |
+-------------------+-------------------+-------------------+-------------------+-------------------+
```

### Primary Palette (Structure & Trust)
| Color Name | Hex Code | RGB | HSL | Functional Role in Slides |
| :--- | :---: | :---: | :---: | :--- |
| **Midnight Navy** | `#023047` | `(2, 48, 71)` | `(200°, 95%, 14%)` | **Primary Text & Structure**: Major slide titles, authoritative headings, high-contrast structural borders, dark card accents. |
| **River Cyan** | `#219ebc` | `(33, 158, 188)` | `(192°, 70%, 43%)` | **Primary Brand & Action**: Subheadings, primary button fills, active links, river flow graphics, primary data series. |

### Secondary Palette (Backgrounds & Soft Hierarchy)
| Color Name | Hex Code | RGB | HSL | Functional Role in Slides |
| :--- | :---: | :---: | :---: | :--- |
| **Sky Breeze** | `#8ecae6` | `(142, 202, 230)` | `(199°, 63%, 73%)` | **Secondary Tint & Depth**: Soft card fills, badge backgrounds, secondary chart bars, subtle divider lines, hover states. |
| **Pure Canvas White** | `#ffffff` | `(255, 255, 255)`| `(0°, 0%, 100%)` | **Mandatory Slide Background**: Guarantees maximum contrast, clean readability, and distraction-free viewing. |
| **Off-White Tint** | `#f8fafc` | `(248, 250, 252)`| `(210°, 40%, 98%)` | **Content Card Fills**: Soft container background for grouping metrics or bullet points without harsh borders. |

### Accent & Alert Palette (Dynamic Triggers & Status)
| Color Name | Hex Code | RGB | HSL | Functional Role in Slides |
| :--- | :---: | :---: | :---: | :--- |
| **Amber Gold** | `#ffb703` | `(255, 183, 3)` | `(43°, 100%, 51%)` | **Warning & Caution**: Yellow state in the Citizen Traffic Light system, cautionary notifications, secondary metric highlights. |
| **Tangerine Orange** | `#fb8500` | `(251, 133, 0)` | `(32°, 100%, 49%)` | **Acute Alert & Call-to-Action**: Red/Orange danger state in Traffic Light app, chemical threshold spikes ($> 0.6\ \text{mg/L}$), key quantitative impact numbers (€ values), urgent callouts. |

---

## 3. Typography Guide (Strictly Sans-Serif)

> [!IMPORTANT]
> **No Monospace Fonts**: Do not use `Courier`, `Consolas`, `Roboto Mono`, or monospace code fonts in presentation slides.

### Recommended Modern Geometric Sans-Serif Typefaces
1. **Inter** *(Google Fonts / Open Source – Top Recommendation)*: Unmatched readability at both micro and display sizes.
2. **Plus Jakarta Sans** *(Google Fonts / Modern Editorial)*: Clean, contemporary European design aesthetic.
3. **DM Sans** or **Montserrat**: Clean geometric forms with excellent weight contrasts.
4. **System Native Alternatives**: `Helvetica Neue`, `SF Pro Display`, `Arial` (when custom fonts cannot be embedded).

### Slide Typographic Hierarchy
| Role | Recommended Size (16:9 Deck) | Weight | Color | Formatting Rules |
| :--- | :---: | :---: | :---: | :--- |
| **Slide Title (Hero)** | 36 – 42 pt | Bold (700) | `#023047` | Sentence case, max 1–2 lines. |
| **Section Category Kicker** | 12 – 14 pt | Bold (700) | `#219ebc` | ALL CAPS, tracked out (+1.5px), placed above slide title. |
| **Section Heading (H2)** | 20 – 24 pt | Semi-Bold (600) | `#023047` | Clean grouping headers. |
| **Body Text / Bullets** | 14 – 16 pt | Regular (400) | `#1e293b` / `#023047` | 1.4–1.5 line height, concise, max 3–4 lines per block. |
| **Giant Metric / Stat Number** | 48 – 64 pt | Extra-Bold (800) | `#fb8500` or `#219ebc` | Paired with a concise 12 pt label below. |
| **Badge / Tag Text** | 10 – 12 pt | Semi-Bold (600) | `#023047` on `#8ecae6` | Rounded pill container with 6px padding. |

---

## 4. Logo Usage & Brand Assets

The official project brand mark is stored at:
- **Primary Logo Asset**: [**`presentation/assets/logo.jpeg`**](assets/logo.jpeg)

```text
[Surfer on Riverbank] + [Dynamic River Waves] + [Robot with Scanner] + [Sun over Pegnitz Valley]
                               PlumeTrace
                            RIVER PROTECTOR
```

### Placement & Application Rules
1. **Title & Closing Slides**: Place the full circular badge logo prominently in the center or left half (height $\approx 250\text{--}300\ \text{px}$).
2. **Content Slides**: Use a compact horizontal version or place the emblem in the top-left or bottom-right header/footer margin (height $\approx 45\text{--}50\ \text{px}$).
3. **Clear Space**: Maintain a minimum clear margin equal to the height of the letter "P" in the PlumeTrace logotype around all sides.
4. **Background Rule**: Always render over a pure white or very light off-white background; avoid placing over dark or busy photographic backgrounds.

---

## 5. UI & Slide Component Styling

### A. The Citizen "Traffic Light" Indicator Component
Use standard rounded status badges on slides introducing the public health app:
- 🟢 **Safe**: `#219ebc` or Emerald `#10b981` pill with white text ("SAFE – Water clear for surfing").
- 🟡 **Caution**: `#ffb703` pill with `#023047` text ("CAUTION – Marginal post-rain flow").
- 🔴 **Hazard**: `#fb8500` pill with white text ("HAZARD – Fecal plume detected, do not enter").

### B. Metric Highlight Cards (Kantian Bento-Box Layout)
- **Container**: White card (`#ffffff`) with subtle 1px border (`#8ecae6` at 40% opacity) or subtle drop shadow (`box-shadow: 0 4px 12px rgba(2, 48, 71, 0.06)`).
- **Border Radius**: 12px to 16px.
- **Padding**: 24px.
- **Top Accent Stripe**: 4px solid line in `#219ebc` (primary) or `#fb8500` (alert).

### C. Data Charts & Graphs
- **Axis & Gridlines**: Muted light cyan `#8ecae6` or cool gray `#cbd5e1`.
- **Primary Line / Bars**: `#219ebc` (River Cyan).
- **Secondary Baseline**: `#023047` (Midnight Navy).
- **Threshold Exceedance Line ($> 0.6\ \text{mg/L}$)**: Dashed bold line in `#fb8500` (Tangerine Orange).
