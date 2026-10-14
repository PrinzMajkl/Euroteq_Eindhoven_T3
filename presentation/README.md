# Presentation Directory Index

This directory contains slide decks, visual brand assets, pitch outlines, rehearsal scripts, and vector PDF exports for the EuroTeQ Track 3 project **PlumeTrace** (Autonomous Digital Twin for River Water Protection).

---

## Deliverables & Slides

| File / Asset | Description |
| :--- | :--- |
| **[`plumetrace_presentation.pdf`](plumetrace_presentation.pdf)** | **Vector 16:9 PDF Slide Deck** covering Sections 1, 2, and 3 (7 slides). Pixel-perfect vector typography, clean card layout, official logo, and strict 5-color palette. |
| **[`plumetrace_deck.pptx`](plumetrace_deck.pptx)** | **Editable PowerPoint Presentation (16:9)** covering Sections 1, 2, and 3 (7 slides). Fixed layout with crisp 3.5% corner radius, left-aligned text, larger fonts, and embedded Speaker Notes. |
| **[`deck_preview.html`](deck_preview.html)** | **Interactive 16:9 Presentation Viewer** for all 7 slides. Features step-by-step click reveal animations (`Space` / `→`), fullscreen mode (`F`), and toggleable Speaker Notes drawer (`N`). |
| **[`generate_deck.py`](generate_deck.py)** | Standalone Python script using `python-pptx` to build and export the native PowerPoint presentation. |
| **[`export_pdf.py`](export_pdf.py)** | Standalone Python Playwright script to re-export `deck_preview.html` to a 16:9 vector PDF with one command. |
| **[`test_presentation_section_1_and_2.md`](test_presentation_section_1_and_2.md)** | Detailed spoken scripts and outline for early slides. |
| **[`brand_style_guide.md`](brand_style_guide.md)** | Graphic identity manual: Calibri typography, 5-color palette, no emojis/mdashes, and card layout guidelines. |
| **[`slides_brainstorm.md`](slides_brainstorm.md)** | Presentation master outline, talking points, and Q&A defense preparation across all 6 rubric sections. |
| **[`assets/logo.jpeg`](assets/logo.jpeg)** | Official PlumeTrace circular brand emblem (Pegnitz river waves, surfer, autonomous surface robot, and sun). |

---

## Rubric Breakdown (7 Slides)

- **Section 1: Title Slide (Max 1 Slide)**
  - **Slide 1**: *PlumeTrace: Autonomous Water Protection for the Pegnitz River* (Circular logo, title, subtitle).
- **Section 2: Context and Challenge (Max 3 Slides)**
  - **Slide 2**: *Why Pegnitz* (Public Health, Sewer Overflows, Knoblauchsland Agriculture, Heat & Drought).
  - **Slide 3**: *Current Monitoring* (Municipal parameters vs The Sampling Gap & undetected plumes).
  - **Slide 4**: *Key Stakeholders* (Current pain points of Water Authorities vs Citizens & Surfers).
- **Section 3: Technical Solution (Max 3 Slides)**
  - **Slide 5**: *System Architecture* (Physical TurtleBot3 platform, Gazebo simulation mirror, Cesium LOD2 3D digital twin).
  - **Slide 6**: *Autonomous Closed Loop* (4D adaptive retasking, dual obstacle cloud, fault-tolerant edge buffer).
  - **Slide 7**: *Why Mobile Robotics?* (Gradient tracing, municipal asset intelligence, 3D corridor mapping, economics).
