import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

# Output file path
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "plumetrace_presentation.pptx")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.jpeg")

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

# Brand Palette
NAVY = RGBColor(2, 48, 71)        # #023047
CYAN = RGBColor(33, 158, 188)      # #219ebc
SKY = RGBColor(142, 202, 230)      # #8ecae6
GOLD = RGBColor(255, 183, 3)       # #ffb703
ORANGE = RGBColor(251, 133, 0)     # #fb8500
WHITE = RGBColor(255, 255, 255)    # #ffffff
CARD_BG = RGBColor(244, 249, 252)  # #f4f9fc soft tint

FONT_NAME = "Calibri"

def set_background(slide):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = WHITE

def add_slide_header(slide, title_text):
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.733), Inches(0.9))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = title_text
    p.alignment = PP_ALIGN.LEFT
    p.font.name = FONT_NAME
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = NAVY

def add_card(slide, left, top, width, height, title, bullets, subtitle=None, title_size=23, bullet_size=16):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.adjustments[0] = 0.035 # Crisp, subtle corner radius (matches 10px CSS radius, not huge pill!)
    shape.fill.solid()
    shape.fill.fore_color.rgb = CARD_BG
    shape.line.color.rgb = SKY
    shape.line.width = Pt(1.5)
    
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = Inches(0.35)
    tf.margin_right = Inches(0.35)
    tf.margin_top = Inches(0.3)
    tf.margin_bottom = Inches(0.25)
    
    # Title (strictly LEFT aligned)
    p = tf.paragraphs[0]
    p.text = title
    p.alignment = PP_ALIGN.LEFT
    p.font.name = FONT_NAME
    p.font.size = Pt(title_size)
    p.font.bold = True
    p.font.color.rgb = NAVY
    p.space_after = Pt(4 if subtitle else 12)
    p.space_before = Pt(0)
    
    # Subtitle if provided (strictly LEFT aligned)
    if subtitle:
        p_sub = tf.add_paragraph()
        p_sub.text = subtitle
        p_sub.alignment = PP_ALIGN.LEFT
        p_sub.font.name = FONT_NAME
        p_sub.font.size = Pt(14)
        p_sub.font.bold = True
        p_sub.font.color.rgb = CYAN
        p_sub.space_after = Pt(14)
        p_sub.space_before = Pt(0)
        
    # Bullets (strictly LEFT aligned)
    for b in bullets:
        bp = tf.add_paragraph()
        bp.text = f"-  {b}"
        bp.alignment = PP_ALIGN.LEFT
        bp.font.name = FONT_NAME
        bp.font.size = Pt(bullet_size)
        bp.font.color.rgb = NAVY
        bp.space_after = Pt(9)
        bp.space_before = Pt(0)
        
    return shape

def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


# ==========================================================
# SLIDE 1: Title Slide
# ==========================================================
s1 = prs.slides.add_slide(blank_layout)
set_background(s1)

if os.path.exists(LOGO_PATH):
    s1.shapes.add_picture(LOGO_PATH, Inches(1.4), Inches(2.1), width=Inches(3.3), height=Inches(3.3))

s1_tb = s1.shapes.add_textbox(Inches(5.1), Inches(2.3), Inches(7.4), Inches(3.0))
tf1 = s1_tb.text_frame
tf1.word_wrap = True
tf1.vertical_anchor = MSO_ANCHOR.MIDDLE
tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0

p1 = tf1.paragraphs[0]
p1.text = "PlumeTrace"
p1.alignment = PP_ALIGN.LEFT
p1.font.name = FONT_NAME
p1.font.size = Pt(64)
p1.font.bold = True
p1.font.color.rgb = CYAN
p1.space_after = Pt(14)

p2 = tf1.add_paragraph()
p2.text = "Autonomous Water Protection for the Pegnitz River"
p2.alignment = PP_ALIGN.LEFT
p2.font.name = FONT_NAME
p2.font.size = Pt(26)
p2.font.bold = True
p2.font.color.rgb = NAVY

add_notes(s1,
    "Good morning members of the jury and mentors. Today, we present PlumeTrace - an autonomous, "
    "closed-loop Digital Twin system designed to protect urban rivers.\n\n"
    "Across Europe, urban rivers are essential for recreation, drinking water, and ecology. "
    "Yet beneath the surface, they face sudden, unmonitored pollution events that traditional testing completely misses.\n\n"
    "Using the Pegnitz River in Nuremberg as our testbed, we demonstrate how coupling an autonomous "
    "robotic agent with a real-time predictive Digital Twin transforms water quality monitoring from "
    "blind, infrequent sampling into actionable protection."
)


# ==========================================================
# SLIDE 2: Why Pegnitz
# ==========================================================
s2 = prs.slides.add_slide(blank_layout)
set_background(s2)
add_slide_header(s2, "Why Pegnitz")

s2_w = Inches(5.666)
s2_h = Inches(2.45)
s2_top1 = Inches(1.7)
s2_top2 = Inches(4.45)
s2_left1 = Inches(0.8)
s2_left2 = Inches(6.866)

add_card(s2, s2_left1, s2_top1, s2_w, s2_h, "Public Health", [
    "Raw sewage spikes after rainfall",
    "Instant health risk for surfers, waders, and park visitors"
], title_size=22, bullet_size=16)

add_card(s2, s2_left2, s2_top1, s2_w, s2_h, "Sewer Overflows (CSOs)", [
    "1,500 km municipal network overloaded by storms",
    "1.5M - 5M+ EUR cost per retention basin"
], title_size=22, bullet_size=16)

add_card(s2, s2_left1, s2_top2, s2_w, s2_h, "Knoblauchsland Agriculture", [
    "Nitrate leaching into drinking water aquifers",
    "Strict EU limits and compliance pressure"
], title_size=22, bullet_size=16)

add_card(s2, s2_left2, s2_top2, s2_w, s2_h, "Summer Heat and Drought", [
    "Low flow concentrates pollutants",
    "Dissolved oxygen drops < 3 mg/L (fish kills)"
], title_size=22, bullet_size=16)

add_notes(s2,
    "Why the Pegnitz River? Because it represents four urgent pressures colliding in one urban corridor:\n\n"
    "First, Public Health: Surfers at the Fuchslochwelle wave and waders face raw sewage contamination after storms, "
    "creating immediate health risks.\n"
    "Second, Urban Infrastructure: Nuremberg's 1,500 km sewer network overspills during heavy rains. "
    "Modernizing a single retention basin costs between 1.5 and 5 million euros - cities cannot afford to invest blindly.\n"
    "Third, Agriculture: Intensive vegetable farming in Knoblauchsland leaches nitrates into alluvial drinking water aquifers under strict EU penalties.\n"
    "And fourth, Climate Drought: Summer heat reduces river discharge, collapsing oxygen levels below 3 mg/L and killing fish."
)


# ==========================================================
# SLIDE 3: Current Monitoring
# ==========================================================
s3 = prs.slides.add_slide(blank_layout)
set_background(s3)
add_slide_header(s3, "Current Monitoring")

col_w = Inches(5.666)
col_h = Inches(4.15)
top_pos = Inches(1.7)

add_card(s3, Inches(0.8), top_pos, col_w, col_h, "Municipal Authorities", [
    "Temperature, pH, conductivity, turbidity",
    "Dissolved oxygen and nutrients (Nitrate, Phosphate)",
    "Ammonium (NH4+): primary raw sewage tracer"
], subtitle="Stadtentwässerung Nürnberg (SUN) & Wasserwirtschaftsamt (WWA)", title_size=23, bullet_size=17)

add_card(s3, Inches(6.866), top_pos, col_w, col_h, "The Sampling Gap", [
    "Automatic sensors: continuous, but confined to few fixed locations",
    "Manual grab sampling: often only 1x per month (24-48h lab delay)",
    "Convective storm overflows: last only 2 to 4 hours"
], title_size=23, bullet_size=17)

# Bottom Highlight: The Result (Left aligned, subtle 0.035 radius)
res_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(6.1), Inches(11.733), Inches(0.75))
res_box.adjustments[0] = 0.035
res_box.fill.solid()
res_box.fill.fore_color.rgb = CARD_BG
res_box.line.color.rgb = CYAN
res_box.line.width = Pt(1.5)

tf_res = res_box.text_frame
tf_res.word_wrap = True
tf_res.vertical_anchor = MSO_ANCHOR.MIDDLE
tf_res.margin_left = Inches(0.35)
tf_res.margin_right = Inches(0.35)
tf_res.margin_top = Inches(0.1)

p_res = tf_res.paragraphs[0]
p_res.alignment = PP_ALIGN.LEFT
p_res.text = "The Result:  "
p_res.font.name = FONT_NAME
p_res.font.size = Pt(18)
p_res.font.bold = True
p_res.font.color.rgb = ORANGE

run_res = p_res.add_run()
run_res.text = "Plume arrives, causes harm, and clears undetected."
run_res.font.name = FONT_NAME
run_res.font.size = Pt(18)
run_res.font.bold = True
run_res.font.color.rgb = NAVY

add_notes(s3,
    "To address this, we looked at what municipal authorities currently measure.\n\n"
    "In Nuremberg, the drainage service SUN tracks eight standard parameters: temperature, pH, conductivity, turbidity, "
    "dissolved oxygen, and nutrients like ammonium, nitrate, and phosphate. Ammonium is the critical chemical fingerprint of raw sewage.\n\n"
    "The sampling gap is two-fold: automated sensors are confined to a few fixed points, while manual sampling happens as rarely as once a month with days of lab delay. "
    "The result: acute plumes arrive, cause damage, and clear completely undetected."
)


# ==========================================================
# SLIDE 4: Key Stakeholders
# ==========================================================
s4 = prs.slides.add_slide(blank_layout)
set_background(s4)
add_slide_header(s4, "Key Stakeholders")

s4_h = Inches(5.15)
add_card(s4, Inches(0.8), Inches(1.7), col_w, s4_h, "Water Authorities (WWA, SUN)", [
    "Cannot locate pollution origin (fixed stations lack spatial tracking)",
    "Blind infrastructure spending (1.5M - 5M+ EUR per basin without plume data)",
    "Chronic pipe seepage undetected until structural failure",
    "Lab results arrive 24-48 hours too late for emergency action"
], title_size=23, bullet_size=17)

add_card(s4, Inches(6.866), Inches(1.7), col_w, s4_h, "Citizens and Surfers", [
    "Zero real-time visibility into water safety",
    "Unknowingly enter water during toxic overflow events",
    "High risk of gastrointestinal and skin infections",
    "Delayed municipal reports provide no immediate guidance"
], title_size=23, bullet_size=17)

add_notes(s4,
    "This monitoring failure creates acute problems for our two key stakeholder groups today:\n\n"
    "First, Water Authorities like SUN and WWA: They must invest millions of euros into retention basins, "
    "but without spatial plume tracking, they are forced to invest blindly without knowing which overflow pipes cause the greatest damage. "
    "Furthermore, laboratory delays mean they only learn of acute spills days after they have already washed away.\n\n"
    "Second, Citizens and Surfers: People entering the Pegnitz at the Fuchslochwelle or in city parks have zero real-time warning. "
    "They unknowingly expose themselves to acute bacterial contamination because municipal data is either delayed by days or buried in complex chemical reports."
)


# ==========================================================
# SLIDE 5: System Architecture (Technical Solution 1/3)
# ==========================================================
s5 = prs.slides.add_slide(blank_layout)
set_background(s5)
add_slide_header(s5, "System Architecture")

col3_w = Inches(3.644)
col3_gap = Inches(0.4)
s5_h = Inches(5.15)

add_card(s5, Inches(0.8), Inches(1.7), col3_w, s5_h, "Physical Platform", [
    "TurtleBot3 surface robotics testbed",
    "ROS 2 Jazzy onboard computing",
    "LDS-02 LiDAR and overhead tracking",
    "Emulated chemical sensor payload"
], title_size=21, bullet_size=15)

add_card(s5, Inches(0.8) + col3_w + col3_gap, Inches(1.7), col3_w, s5_h, "Simulation Mirror", [
    "Gazebo Harmonic physics engine",
    "Bi-directional ROS-Gazebo bridge",
    "Ghost follower pose tracking",
    "Dynamic obstacle injection"
], title_size=21, bullet_size=15)

add_card(s5, Inches(0.8) + (col3_w + col3_gap) * 2, Inches(1.7), col3_w, s5_h, "3D Digital Twin", [
    "CesiumJS with Bavarian LOD2 3D data",
    "Real-time WebSocket telemetry stream",
    "Geo-referenced pipe outfall health",
    "Interactive urban risk heatmaps"
], title_size=21, bullet_size=15)

add_notes(s5,
    "To solve this, we designed the PlumeTrace System Architecture across three tightly synchronized tiers:\n\n"
    "On the water, our Physical Platform is a robotic surface vessel equipped with ROS 2 Jazzy, 360-degree LiDAR, tracking cameras, and emulated real-time chemical payloads.\n"
    "In the cloud, a Simulation Mirror running Gazebo Harmonic tracks physics and obstacles in real time, validating robot health and sensor sanity.\n"
    "At the command level, our 3D Digital Twin in CesiumJS visualizes Bavarian LOD2 building and river geometry, streaming live WebSocket telemetry to generate actionable heatmaps and asset health scores for city managers."
)


# ==========================================================
# SLIDE 6: Autonomous Closed Loop (Technical Solution 2/3)
# ==========================================================
s6 = prs.slides.add_slide(blank_layout)
set_background(s6)
add_slide_header(s6, "Autonomous Closed Loop")

add_card(s6, Inches(0.8), Inches(1.7), col_w, s4_h, "4D Adaptive Retasking", [
    "Dynamically recomputes waypoints in real time",
    "Chemical Gradient: homes upstream to leaking pipe",
    "Rain Radar: pre-positions robot before storm runoff",
    "Data Freshness: prioritizes unvisited river reaches"
], title_size=23, bullet_size=17)

add_card(s6, Inches(6.866), Inches(1.7), col_w, s4_h, "Safety and Resilience", [
    "Dual obstacle cloud: reroute navigation vs collision stop",
    "Edge buffer: zero data loss during network dropouts",
    "Tri-fold sync: odometry, AMCL, and Gazebo alignment",
    "Dynamic Nav2 goal updates in under 35 seconds"
], title_size=23, bullet_size=17)

add_notes(s6,
    "The core innovation of PlumeTrace is its Autonomous Closed Loop.\n\n"
    "Instead of driving a static patrol line, our system continuously recomputes waypoints based on a 4D objective function: "
    "tracking chemical gradients upstream, anticipating rain runoff via live weather radar, and ensuring older areas are revisited.\n\n"
    "Crucially, we build in industrial resilience: a dual obstacle cloud separates smooth rerouting from emergency collision stops, "
    "while onboard edge buffers guarantee zero telemetry loss even when wireless links drop."
)


# ==========================================================
# SLIDE 7: Why Mobile Robotics? (Technical Solution 3/3)
# ==========================================================
s7 = prs.slides.add_slide(blank_layout)
set_background(s7)
add_slide_header(s7, "Why Mobile Robotics?")

add_card(s7, s2_left1, s2_top1, s2_w, s2_h, "Gradient Tracing", [
    "Tracks concentration gradients upstream",
    "Locates exact leaking pipe instead of diluted mix"
], title_size=22, bullet_size=16)

add_card(s7, s2_left2, s2_top1, s2_w, s2_h, "Asset Intelligence", [
    "Links water chemistry to specific municipal outfall IDs",
    "Direct evidence for multi-million EUR basin upgrades"
], title_size=22, bullet_size=16)

add_card(s7, s2_left1, s2_top2, s2_w, s2_h, "River Corridor Mapping", [
    "LiDAR detects riverbank erosion and sediment build-up",
    "Supports EU renaturation compliance"
], title_size=22, bullet_size=16)

add_card(s7, s2_left2, s2_top2, s2_w, s2_h, "Operational Economics", [
    "One self-cleaning mobile robot replaces 50+ fixed probes",
    "Eliminates biofouling and flood destruction"
], title_size=22, bullet_size=16)

add_notes(s7,
    "Why does mobile robotics decisively outperform traditional fixed monitoring networks?\n\n"
    "First, Gradient Tracing: A static sensor only tells you pollution passed by. A mobile robot follows the plume upstream directly to the faulty outfall pipe.\n"
    "Second, Asset Intelligence: We give water authorities concrete evidence to prioritize multi-million euro infrastructure budgets.\n"
    "Third, Corridor Mapping: LiDAR scans detect physical bank erosion and siltation for EU river renaturation programs.\n"
    "And fourth, Economics: Instead of maintaining hundreds of submerged probes prone to biofouling and flood destruction, one mobile platform delivers continuous, protected spatial coverage."
)

# Save with fallback if locked by PowerPoint
try:
    prs.save(OUTPUT_PATH)
    print(f"Successfully generated PowerPoint presentation at: {OUTPUT_PATH}")
except PermissionError:
    fallback_path = os.path.join(os.path.dirname(__file__), "plumetrace_deck.pptx")
    prs.save(fallback_path)
    print(f"Original file was locked in PowerPoint. Saved updated presentation to: {fallback_path}")
