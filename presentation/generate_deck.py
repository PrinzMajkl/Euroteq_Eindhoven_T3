import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "plumetrace_presentation.pptx")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.jpeg")
ICONS_DIR = os.path.join(os.path.dirname(__file__), "assets", "icons")

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

# Brand Palette
NAVY = RGBColor(2, 48, 71)          # #023047
CYAN = RGBColor(33, 158, 188)        # #219ebc
SKY = RGBColor(142, 202, 230)        # #8ecae6
GOLD = RGBColor(255, 183, 3)         # #ffb703
ORANGE = RGBColor(251, 133, 0)       # #fb8500
WHITE = RGBColor(255, 255, 255)      # #ffffff
CARD_BG = RGBColor(244, 249, 252)    # #f4f9fc soft tint
CHIP_BG = RGBColor(235, 244, 250)    # soft tag tint
BORDER_CLR = RGBColor(180, 218, 238) # crisp border

FONT_NAME = "Calibri"

def set_background(slide):
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = WHITE

def add_slide_header(slide, title_text, category_pill=None):
    top_offset = Inches(0.45)
    if category_pill:
        tb_cat = slide.shapes.add_textbox(Inches(0.8), top_offset, Inches(10), Inches(0.32))
        tf_cat = tb_cat.text_frame
        tf_cat.word_wrap = True
        tf_cat.vertical_anchor = MSO_ANCHOR.TOP
        tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_pill.upper()
        p_cat.font.name = FONT_NAME
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.color.rgb = CYAN
        top_offset = Inches(0.72)
    
    tb = slide.shapes.add_textbox(Inches(0.8), top_offset, Inches(11.733), Inches(0.7))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = title_text
    p.alignment = PP_ALIGN.LEFT
    p.font.name = FONT_NAME
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = NAVY

def add_card(slide, left, top, width, height, title, bullets, icon_name=None, tag=None, subtitle=None, chip_text=None, title_size=20, bullet_size=15):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.adjustments[0] = 0.035
    shape.fill.solid()
    shape.fill.fore_color.rgb = CARD_BG
    shape.line.color.rgb = BORDER_CLR
    shape.line.width = Pt(1.5)
    
    # Icon if provided
    has_icon = False
    if icon_name:
        icon_path = os.path.join(ICONS_DIR, f"{icon_name}.png")
        if os.path.exists(icon_path):
            slide.shapes.add_picture(icon_path, left + Inches(0.3), top + Inches(0.24), width=Inches(0.48), height=Inches(0.48))
            has_icon = True

    # Title & Text Box
    text_left = left + Inches(0.88 if has_icon else 0.32)
    text_width = width - Inches(1.15 if has_icon else 0.64)
    
    tb_title = slide.shapes.add_textbox(text_left, top + Inches(0.18), text_width, Inches(0.65))
    tf_t = tb_title.text_frame
    tf_t.word_wrap = True
    tf_t.vertical_anchor = MSO_ANCHOR.TOP
    tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0
    
    if tag:
        p_tag = tf_t.paragraphs[0]
        p_tag.text = tag.upper()
        p_tag.font.name = FONT_NAME
        p_tag.font.size = Pt(10)
        p_tag.font.bold = True
        p_tag.font.color.rgb = CYAN
        p_tag.space_after = Pt(2)
        p_main = tf_t.add_paragraph()
    else:
        p_main = tf_t.paragraphs[0]

    p_main.text = title
    p_main.alignment = PP_ALIGN.LEFT
    p_main.font.name = FONT_NAME
    p_main.font.size = Pt(title_size)
    p_main.font.bold = True
    p_main.font.color.rgb = NAVY
    
    if subtitle:
        p_sub = tf_t.add_paragraph()
        p_sub.text = subtitle
        p_sub.alignment = PP_ALIGN.LEFT
        p_sub.font.name = FONT_NAME
        p_sub.font.size = Pt(13)
        p_sub.font.bold = True
        p_sub.font.color.rgb = CYAN
        p_sub.space_before = Pt(2)

    # Bullets container
    bullets_top = top + Inches(0.92 if (tag or subtitle) else 0.82)
    bullets_height = height - Inches(1.35 if chip_text else 0.92)
    
    tb_b = slide.shapes.add_textbox(left + Inches(0.32), bullets_top, width - Inches(0.64), bullets_height)
    tf_b = tb_b.text_frame
    tf_b.word_wrap = True
    tf_b.vertical_anchor = MSO_ANCHOR.TOP
    tf_b.margin_left = tf_b.margin_top = tf_b.margin_right = tf_b.margin_bottom = 0
    
    for i, b in enumerate(bullets):
        bp = tf_b.paragraphs[0] if i == 0 else tf_b.add_paragraph()
        bp.text = f"-  {b}"
        bp.alignment = PP_ALIGN.LEFT
        bp.font.name = FONT_NAME
        bp.font.size = Pt(bullet_size)
        bp.font.color.rgb = NAVY
        bp.space_after = Pt(6)
        bp.space_before = Pt(0)
        
    # Bottom Chip / Badge if provided
    if chip_text:
        chip = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, 
            left + Inches(0.28), 
            top + height - Inches(0.50), 
            width - Inches(0.56), 
            Inches(0.35)
        )
        chip.adjustments[0] = 0.08
        chip.fill.solid()
        chip.fill.fore_color.rgb = CHIP_BG
        chip.line.color.rgb = SKY
        chip.line.width = Pt(1)
        
        tf_c = chip.text_frame
        tf_c.word_wrap = True
        tf_c.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf_c.margin_left = Inches(0.15)
        tf_c.margin_right = Inches(0.15)
        tf_c.margin_top = tf_c.margin_bottom = 0
        pc = tf_c.paragraphs[0]
        pc.text = chip_text
        pc.alignment = PP_ALIGN.LEFT
        pc.font.name = FONT_NAME
        pc.font.size = Pt(11)
        pc.font.bold = True
        pc.font.color.rgb = CYAN
        
    return shape

def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


# ==========================================================
# SLIDE 1: Title Slide (Section 1 - 1/1)
# ==========================================================
s1 = prs.slides.add_slide(blank_layout)
set_background(s1)

if os.path.exists(LOGO_PATH):
    s1.shapes.add_picture(LOGO_PATH, Inches(1.2), Inches(1.9), width=Inches(3.5), height=Inches(3.5))

s1_tb = s1.shapes.add_textbox(Inches(5.0), Inches(2.1), Inches(7.5), Inches(3.2))
tf1 = s1_tb.text_frame
tf1.word_wrap = True
tf1.vertical_anchor = MSO_ANCHOR.MIDDLE
tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0

p0 = tf1.paragraphs[0]
p0.text = "EUROTEQ ENGINEERING UNIVERSITY | TRACK 3"
p0.alignment = PP_ALIGN.LEFT
p0.font.name = FONT_NAME
p0.font.size = Pt(13)
p0.font.bold = True
p0.font.color.rgb = CYAN
p0.space_after = Pt(8)

p1 = tf1.add_paragraph()
p1.text = "PlumeTrace"
p1.alignment = PP_ALIGN.LEFT
p1.font.name = FONT_NAME
p1.font.size = Pt(64)
p1.font.bold = True
p1.font.color.rgb = CYAN
p1.space_after = Pt(10)

p2 = tf1.add_paragraph()
p2.text = "Autonomous Water Protection for the Pegnitz River"
p2.alignment = PP_ALIGN.LEFT
p2.font.name = FONT_NAME
p2.font.size = Pt(24)
p2.font.bold = True
p2.font.color.rgb = NAVY
p2.space_after = Pt(20)

badge_titles = ["Autonomous River Robotics", "Predictive Digital Twin", "AI & Open Data Interface"]
for i, bt in enumerate(badge_titles):
    bx = Inches(5.0) + Inches(i * 2.45)
    b_shape = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, Inches(4.8), Inches(2.3), Inches(0.42))
    b_shape.adjustments[0] = 0.1
    b_shape.fill.solid()
    b_shape.fill.fore_color.rgb = CARD_BG
    b_shape.line.color.rgb = SKY
    b_shape.line.width = Pt(1)
    tf_b = b_shape.text_frame
    tf_b.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf_b.margin_left = tf_b.margin_right = tf_b.margin_top = tf_b.margin_bottom = 0
    pb = tf_b.paragraphs[0]
    pb.text = bt
    pb.alignment = PP_ALIGN.CENTER
    pb.font.name = FONT_NAME
    pb.font.size = Pt(11)
    pb.font.bold = True
    pb.font.color.rgb = NAVY

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
# SLIDE 2: Why Pegnitz (Section 2 - 1/3)
# ==========================================================
s2 = prs.slides.add_slide(blank_layout)
set_background(s2)
add_slide_header(s2, "Why Pegnitz", category_pill="Context & Problem Statement")

s2_w = Inches(5.666)
s2_h = Inches(2.55)
s2_top1 = Inches(1.55)
s2_top2 = Inches(4.35)
s2_left1 = Inches(0.8)
s2_left2 = Inches(6.866)

add_card(s2, s2_left1, s2_top1, s2_w, s2_h, "Public Health", [
    "Raw sewage spikes after convective rainfall",
    "Instant health risk for surfers, waders, and park visitors"
], icon_name="health", chip_text="Fuchslochwelle Surf Wave  |  Acute Bacterial Risk", title_size=20, bullet_size=15)

add_card(s2, s2_left2, s2_top1, s2_w, s2_h, "Sewer Overflows (CSOs)", [
    "1,500 km municipal network overloaded by storms",
    "1.5M - 5M+ EUR cost per retention basin"
], icon_name="storm_pipe", chip_text="1,500 km Sewer Grid  |  €1.5M - €5M+ CapEx per Basin", title_size=20, bullet_size=15)

add_card(s2, s2_left1, s2_top2, s2_w, s2_h, "Knoblauchsland Agriculture", [
    "Nitrate leaching into drinking water aquifers",
    "Strict EU limits and compliance penalties"
], icon_name="agriculture", chip_text="Alluvial Drinking Aquifers  |  EU Compliance Risk", title_size=20, bullet_size=15)

add_card(s2, s2_left2, s2_top2, s2_w, s2_h, "Summer Heat and Drought", [
    "Low flow concentrates urban pollutants",
    "Dissolved oxygen drops < 3 mg/L causing fish mortality"
], icon_name="drought", chip_text="Oxygen Collapses < 3 mg/L  |  Summer Ecosystem Crisis", title_size=20, bullet_size=15)

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
# SLIDE 3: Current Monitoring (Section 2 - 2/3)
# ==========================================================
s3 = prs.slides.add_slide(blank_layout)
set_background(s3)
add_slide_header(s3, "Current Monitoring", category_pill="The Monitoring Bottleneck")

col_w = Inches(5.666)
col3_h = Inches(3.05)
top_pos = Inches(1.55)

add_card(s3, Inches(0.8), top_pos, col_w, col3_h, "Municipal Authorities", [
    "Temperature, pH, conductivity, turbidity",
    "Dissolved oxygen and nutrients (Nitrate, Phosphate)",
    "Ammonium (NH4+): primary raw sewage tracer"
], icon_name="municipal_sensor", subtitle="Stadtentwässerung Nürnberg (SUN) & WWA", chip_text="Tracked Parameters: pH, Temp, DO, Turbidity, NH4+, NO3-", title_size=21, bullet_size=15)

add_card(s3, Inches(6.866), top_pos, col_w, col3_h, "The Sampling Gap", [
    "Automatic sensors: continuous, but confined to few fixed locations",
    "Manual grab sampling: often only 1x per month (24-48h lab delay)",
    "Convective storm overflows: last only 2 to 4 hours"
], icon_name="sampling_gap", chip_text="Critical Bottleneck: 1x/Month Sampling  |  24-48h Lab Delay", title_size=21, bullet_size=15)

# Temporal Mismatch Infographic
inf_top = Inches(4.8)
inf_w = Inches(11.733)
inf_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), inf_top, inf_w, Inches(1.2))
inf_box.adjustments[0] = 0.035
inf_box.fill.solid()
inf_box.fill.fore_color.rgb = CARD_BG
inf_box.line.color.rgb = BORDER_CLR
inf_box.line.width = Pt(1.5)

tf_i = inf_box.text_frame
tf_i.word_wrap = True
tf_i.vertical_anchor = MSO_ANCHOR.TOP
tf_i.margin_left = Inches(0.3)
tf_i.margin_right = Inches(0.3)
tf_i.margin_top = Inches(0.15)

pi_title = tf_i.paragraphs[0]
pi_title.text = "THE TEMPORAL MISMATCH INFOGRAPHIC"
pi_title.font.name = FONT_NAME
pi_title.font.size = Pt(11)
pi_title.font.bold = True
pi_title.font.color.rgb = CYAN
pi_title.space_after = Pt(6)

p_bar1 = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.1), inf_top + Inches(0.48), Inches(2.2), Inches(0.24))
p_bar1.adjustments[0] = 0.2
p_bar1.fill.solid()
p_bar1.fill.fore_color.rgb = ORANGE
p_bar1.line.fill.background()
tf_b1 = p_bar1.text_frame
tf_b1.vertical_anchor = MSO_ANCHOR.MIDDLE
tf_b1.margin_left = Inches(0.1)
p_b1_txt = tf_b1.paragraphs[0]
p_b1_txt.text = "Storm Overflow: 2-4 Hours"
p_b1_txt.font.name = FONT_NAME
p_b1_txt.font.size = Pt(9.5)
p_b1_txt.font.bold = True
p_b1_txt.font.color.rgb = WHITE

p_bar2 = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(3.6), inf_top + Inches(0.48), Inches(8.6), Inches(0.24))
p_bar2.adjustments[0] = 0.06
p_bar2.fill.solid()
p_bar2.fill.fore_color.rgb = NAVY
p_bar2.line.fill.background()
tf_b2 = p_bar2.text_frame
tf_b2.vertical_anchor = MSO_ANCHOR.MIDDLE
tf_b2.margin_left = Inches(0.15)
p_b2_txt = tf_b2.paragraphs[0]
p_b2_txt.text = "Laboratory Grab Sample Verification Delay: 24 to 48 Hours (Plume Long Cleared)"
p_b2_txt.font.name = FONT_NAME
p_b2_txt.font.size = Pt(9.5)
p_b2_txt.font.bold = True
p_b2_txt.font.color.rgb = WHITE

tb_exp = s3.shapes.add_textbox(Inches(1.1), inf_top + Inches(0.78), Inches(11.1), Inches(0.3))
tf_exp = tb_exp.text_frame
tf_exp.word_wrap = True
tf_exp.margin_left = tf_exp.margin_top = tf_exp.margin_right = tf_exp.margin_bottom = 0
p_exp = tf_exp.paragraphs[0]
p_exp.text = "Static sensors only show that something passed. Laboratory delays mean warnings arrive days after the pollution event has ended."
p_exp.font.name = FONT_NAME
p_exp.font.size = Pt(11.5)
p_exp.font.color.rgb = NAVY

# Bottom Highlight: The Result
res_box = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(6.18), Inches(11.733), Inches(0.68))
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
tf_res.margin_top = Inches(0.08)

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
# SLIDE 4: Key Stakeholders & Challenge Definition (Section 2 - 3/3)
# ==========================================================
s4 = prs.slides.add_slide(blank_layout)
set_background(s4)
add_slide_header(s4, "Key Stakeholders & Challenge", category_pill="Stakeholder Needs & Challenge Framing")

s4_card_h = Inches(3.25)
add_card(s4, Inches(0.8), Inches(1.55), col_w, s4_card_h, "Water Authorities (WWA, SUN)", [
    "Cannot locate pollution origin (fixed stations lack spatial tracking)",
    "Blind infrastructure spending (1.5M - 5M+ EUR per basin without plume data)",
    "Chronic pipe seepage undetected until structural failure",
    "Lab results arrive 24-48 hours too late for emergency action"
], icon_name="authority", tag="Regulatory & Infrastructure", chip_text="High Financial Risk: €1.5M - €5M+ CapEx per Basin  |  Delayed Lab Data", title_size=21, bullet_size=15)

add_card(s4, Inches(6.866), Inches(1.55), col_w, s4_card_h, "Citizens and Surfers", [
    "Zero real-time visibility into water safety",
    "Unknowingly enter water during toxic overflow events",
    "High risk of gastrointestinal and skin infections",
    "Delayed municipal reports provide no immediate guidance"
], icon_name="citizens_surfer", tag="Public Health & Recreation", chip_text="Acute Health Risk: Unwarned Bacterial Exposure  |  No Live Warnings", title_size=21, bullet_size=15)

# Formal Challenge Statement Box (Mandated by DTAS rubric!)
ch_box = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.0), Inches(11.733), Inches(1.85))
ch_box.adjustments[0] = 0.035
ch_box.fill.solid()
ch_box.fill.fore_color.rgb = CARD_BG
ch_box.line.color.rgb = CYAN
ch_box.line.width = Pt(1.5)

tf_ch = ch_box.text_frame
tf_ch.word_wrap = True
tf_ch.vertical_anchor = MSO_ANCHOR.TOP
tf_ch.margin_left = Inches(0.35)
tf_ch.margin_right = Inches(0.35)
tf_ch.margin_top = Inches(0.18)

pch_title = tf_ch.paragraphs[0]
pch_title.text = "FORMAL DTAS CHALLENGE DEFINITION"
pch_title.font.name = FONT_NAME
pch_title.font.size = Pt(11)
pch_title.font.bold = True
pch_title.font.color.rgb = CYAN
pch_title.space_after = Pt(6)

pch_stmt = tf_ch.add_paragraph()
pch_stmt.text = (
    '"How can digital twinning be applied to autonomous systems in order to address the challenge of '
    'detecting and localizing transient Combined Sewer Overflows (CSOs) for the Wasserwirtschaftsamt '
    'and regional environmental authorities?"'
)
pch_stmt.font.name = FONT_NAME
pch_stmt.font.size = Pt(15.5)
pch_stmt.font.bold = True
pch_stmt.font.color.rgb = NAVY
pch_stmt.space_after = Pt(8)

pch_takeaway = tf_ch.add_paragraph()
pch_takeaway.text = "Goal: Replace delayed monthly grab testing with an autonomous closed-loop system connecting physical sensing to predictive action."
pch_takeaway.font.name = FONT_NAME
pch_takeaway.font.size = Pt(12)
pch_takeaway.font.color.rgb = CYAN

add_notes(s4,
    "This monitoring failure creates acute problems for our two key stakeholder groups today:\n\n"
    "First, Water Authorities like SUN and WWA: They must invest millions of euros into retention basins, "
    "but without spatial plume tracking, they are forced to invest blindly without knowing which overflow pipes cause the greatest damage. "
    "Furthermore, laboratory delays mean they only learn of acute spills days after they have already washed away.\n\n"
    "Second, Citizens and Surfers: People entering the Pegnitz at the Fuchslochwelle or in city parks have zero real-time warning. "
    "They unknowingly expose themselves to acute bacterial contamination because municipal data is either delayed by days or buried in complex chemical reports.\n\n"
    "This brings us to our formal challenge definition: How can digital twinning be applied to autonomous systems to detect and localize transient Combined Sewer Overflows for environmental authorities?"
)


# ==========================================================
# SLIDE 5: The PlumeTrace Architecture (Section 3 - 1/3)
# FULL SOLUTION (NOT LAB PROXY!)
# ==========================================================
s5 = prs.slides.add_slide(blank_layout)
set_background(s5)
add_slide_header(s5, "The PlumeTrace Architecture", category_pill="Technical Solution 1/3")

col3_w = Inches(3.644)
col3_gap = Inches(0.4)
s5_card_h = Inches(3.25)
s5_top = Inches(1.55)

# Card 1: Autonomous River Robot (ASV)
c1_left = Inches(0.8)
add_card(s5, c1_left, s5_top, col3_w, s5_card_h, "Autonomous River Robot", [
    "Autonomous Surface Vessel (ASV) on Pegnitz",
    "Continuous chemical payload (Ammonium, DO, pH)",
    "360° LiDAR maps riverbank morphology & culverts",
    "Edge autonomy with fail-safe return-to-dock"
], icon_name="river_asv", tag="Aquatic Physical Layer", chip_text="Active In-River Sensing  |  3D LiDAR  |  Auto-Dock", title_size=19, bullet_size=14)

# Connector Arrow 1 -> 2
arr1 = s5.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, c1_left + col3_w + Inches(0.08), s5_top + Inches(1.4), Inches(0.24), Inches(0.35))
arr1.fill.solid()
arr1.fill.fore_color.rgb = CYAN
arr1.line.fill.background()

# Card 2: Predictive Digital Twin
c2_left = c1_left + col3_w + col3_gap
add_card(s5, c2_left, s5_top, col3_w, s5_card_h, "Predictive Digital Twin", [
    "Hydrodynamic river advection-dispersion engine",
    "Ingests live DWD storm radar & river discharge",
    "Multi-objective solver computes optimal sampling",
    "Continuously directs robot where to navigate next"
], icon_name="cloud_twin", tag="Cloud Simulation & AI Core", chip_text="Hydrodynamic Dispersion  |  Radar  |  Retasking", title_size=19, bullet_size=14)

# Connector Arrow 2 -> 3
arr2 = s5.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, c2_left + col3_w + Inches(0.08), s5_top + Inches(1.4), Inches(0.24), Inches(0.35))
arr2.fill.solid()
arr2.fill.fore_color.rgb = CYAN
arr2.line.fill.background()

# Card 3: Municipal Command Center
c3_left = c2_left + col3_w + col3_gap
add_card(s5, c3_left, s5_top, col3_w, s5_card_h, "Municipal Command Center", [
    "Geospatial 3D twin with Bavarian LOD2 data",
    "Real-time pollution heatmaps & outfall health",
    "Pinpoints exact sewer outfalls causing violations",
    "Automated statutory alerts (<60s) to WWA & SUN"
], icon_name="digital_twin_3d", tag="Decision & Compliance Layer", chip_text="CesiumJS 3D  |  Bavarian LOD2  |  < 60s Alerts", title_size=19, bullet_size=14)

# Bottom Infographic Banner: End-to-End System Integration
arch_box = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(5.0), Inches(11.733), Inches(1.85))
arch_box.adjustments[0] = 0.035
arch_box.fill.solid()
arch_box.fill.fore_color.rgb = CARD_BG
arch_box.line.color.rgb = BORDER_CLR
arch_box.line.width = Pt(1.5)

tf_arch = arch_box.text_frame
tf_arch.word_wrap = True
tf_arch.vertical_anchor = MSO_ANCHOR.TOP
tf_arch.margin_left = Inches(0.35)
tf_arch.margin_right = Inches(0.35)
tf_arch.margin_top = Inches(0.18)

p_at = tf_arch.paragraphs[0]
p_at.text = "END-TO-END AUTONOMOUS ARCHITECTURE PIPELINE"
p_at.font.name = FONT_NAME
p_at.font.size = Pt(11)
p_at.font.bold = True
p_at.font.color.rgb = CYAN
p_at.space_after = Pt(8)

pipe_w = Inches(3.45)
pipe_gap = Inches(0.5)

# Step 1 Box
s1_p = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.1), Inches(5.42), pipe_w, Inches(1.22))
s1_p.adjustments[0] = 0.05
s1_p.fill.solid()
s1_p.fill.fore_color.rgb = WHITE
s1_p.line.color.rgb = SKY
s1_p.line.width = Pt(1)
tf_p1 = s1_p.text_frame
tf_p1.word_wrap = True
tf_p1.vertical_anchor = MSO_ANCHOR.TOP
tf_p1.margin_left = tf_p1.margin_right = tf_p1.margin_top = Inches(0.12)
p1_h = tf_p1.paragraphs[0]
p1_h.text = "1. Aquatic In-River Sensing"
p1_h.font.name = FONT_NAME
p1_h.font.size = Pt(12)
p1_h.font.bold = True
p1_h.font.color.rgb = NAVY
p1_b = tf_p1.add_paragraph()
p1_b.text = "Autonomous surface vessel streams chemical telemetry, obstacle LiDAR scans, and GPS coordinates at 5 Hz."
p1_b.font.name = FONT_NAME
p1_b.font.size = Pt(10.5)
p1_b.font.color.rgb = NAVY
p1_b.space_before = Pt(3)

ar_p1 = s5.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(1.1) + pipe_w + Inches(0.12), Inches(5.9), Inches(0.25), Inches(0.28))
ar_p1.fill.solid()
ar_p1.fill.fore_color.rgb = CYAN
ar_p1.line.fill.background()

# Step 2 Box
s2_p = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.1) + pipe_w + pipe_gap, Inches(5.42), pipe_w, Inches(1.22))
s2_p.adjustments[0] = 0.05
s2_p.fill.solid()
s2_p.fill.fore_color.rgb = WHITE
s2_p.line.color.rgb = SKY
s2_p.line.width = Pt(1)
tf_p2 = s2_p.text_frame
tf_p2.word_wrap = True
tf_p2.vertical_anchor = MSO_ANCHOR.TOP
tf_p2.margin_left = tf_p2.margin_right = tf_p2.margin_top = Inches(0.12)
p2_h = tf_p2.paragraphs[0]
p2_h.text = "2. Predictive Digital Twin"
p2_h.font.name = FONT_NAME
p2_h.font.size = Pt(12)
p2_h.font.bold = True
p2_h.font.color.rgb = NAVY
p2_b = tf_p2.add_paragraph()
p2_b.text = "Cloud twin simulates hydrodynamics, assimilates storm radar, and computes optimal upstream waypoints."
p2_b.font.name = FONT_NAME
p2_b.font.size = Pt(10.5)
p2_b.font.color.rgb = NAVY
p2_b.space_before = Pt(3)

ar_p2 = s5.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(1.1) + (pipe_w + pipe_gap) + pipe_w + Inches(0.12), Inches(5.9), Inches(0.25), Inches(0.28))
ar_p2.fill.solid()
ar_p2.fill.fore_color.rgb = CYAN
ar_p2.line.fill.background()

# Step 3 Box
s3_p = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.1) + (pipe_w + pipe_gap) * 2, Inches(5.42), pipe_w, Inches(1.22))
s3_p.adjustments[0] = 0.05
s3_p.fill.solid()
s3_p.fill.fore_color.rgb = WHITE
s3_p.line.color.rgb = SKY
s3_p.line.width = Pt(1)
tf_p3 = s3_p.text_frame
tf_p3.word_wrap = True
tf_p3.vertical_anchor = MSO_ANCHOR.TOP
tf_p3.margin_left = tf_p3.margin_right = tf_p3.margin_top = Inches(0.12)
p3_h = tf_p3.paragraphs[0]
p3_h.text = "3. City & Authority Actions"
p3_h.font.name = FONT_NAME
p3_h.font.size = Pt(12)
p3_h.font.bold = True
p3_h.font.color.rgb = NAVY
p3_b = tf_p3.add_paragraph()
p3_b.text = "CesiumJS renders live 3D risk heatmaps, updates outfall asset health, and dispatches statutory alerts."
p3_b.font.name = FONT_NAME
p3_b.font.size = Pt(10.5)
p3_b.font.color.rgb = NAVY
p3_b.space_before = Pt(3)

add_notes(s5,
    "Here is our overarching technical solution: PlumeTrace connects physical robotics, cloud digital twinning, and municipal decision-making into one unified ecosystem.\n\n"
    "First, on the water: An Autonomous Surface Vessel continuously patrols the Pegnitz corridor, equipped with chemical sensors for ammonium and dissolved oxygen, and 360-degree LiDAR mapping riverbank morphology.\n\n"
    "Second, in the cloud: A predictive Digital Twin runs hydrodynamic advection-dispersion modeling. By assimilating real-time weather radar from the German Weather Service (DWD) and river discharge, the twin anticipates where storm runoff will arrive and tells the robot where to navigate next.\n\n"
    "Third, in the city hall: A 3D geospatial dashboard built on CesiumJS and Bavarian LOD2 OpenData translates raw data into outfall asset health scores, enabling targeted infrastructure investment and immediate public warnings."
)


# ==========================================================
# SLIDE 6: Autonomous Closed-Loop Guidance (Section 3 - 2/3)
# ==========================================================
s6 = prs.slides.add_slide(blank_layout)
set_background(s6)
add_slide_header(s6, "Autonomous Closed-Loop Guidance", category_pill="Technical Solution 2/3")

s6_card_h = Inches(3.2)
add_card(s6, Inches(0.8), Inches(1.55), col_w, s6_card_h, "4D Adaptive Retasking", [
    "Chemical Gradient: homes upstream to leaking pipe",
    "Storm Rain Radar: pre-positions vessel before runoff",
    "Data Freshness: prioritizes unvisited river reaches",
    "Dynamic goal updates dispatched in under 35 seconds"
], icon_name="adaptive_retask", tag="Autonomy Core", chip_text="Multi-Objective Optimizer  |  Upstream Gradient Homing  |  < 35s Loop", title_size=21, bullet_size=15)

add_card(s6, Inches(6.866), Inches(1.55), col_w, s6_card_h, "Why Digital Twinning?", [
    "Active Gradient Tracing overcomes point dilution",
    "Predictive storm anticipation replaces reactive lab lag",
    "One mobile vessel replaces 50+ biofouled static probes",
    "Continuous feedback synchronizes twin with physical state"
], icon_name="safety_resilience", tag="Digital Twin Rationale", chip_text="Solves Point Dilution  |  Predictive Protection  |  CapEx Optimization", title_size=21, bullet_size=15)

# Bottom Infographic Banner: The 4D Continuous Decision Loop
loop_box = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.95), Inches(11.733), Inches(1.95))
loop_box.adjustments[0] = 0.035
loop_box.fill.solid()
loop_box.fill.fore_color.rgb = CARD_BG
loop_box.line.color.rgb = BORDER_CLR
loop_box.line.width = Pt(1.5)

tf_lp = loop_box.text_frame
tf_lp.word_wrap = True
tf_lp.vertical_anchor = MSO_ANCHOR.TOP
tf_lp.margin_left = Inches(0.35)
tf_lp.margin_right = Inches(0.35)
tf_lp.margin_top = Inches(0.18)

p_lt = tf_lp.paragraphs[0]
p_lt.text = "THE 4D AUTONOMOUS DECISION CYCLE (CONTINUOUS CLOSED LOOP)"
p_lt.font.name = FONT_NAME
p_lt.font.size = Pt(11)
p_lt.font.bold = True
p_lt.font.color.rgb = CYAN
p_lt.space_after = Pt(8)

step_w = Inches(2.45)
step_gap = Inches(0.48)

steps_data = [
    ("1. SENSE", "Gradient Spike", "Mobile payload detects ammonium spike above baseline."),
    ("2. ASSIMILATE", "Radar & Flow", "Digital twin integrates DWD rain radar & Pegnitz flow rate."),
    ("3. RETASK", "Optimal Waypoint", "Optimizer computes upstream navigation goal in < 35s."),
    ("4. LOCALIZED", "Source Confirmed", "Leaking outfall pinpointed and logged with geo-proof.")
]

for idx, (st_num, st_name, st_desc) in enumerate(steps_data):
    sx = Inches(1.05) + Inches(idx) * (step_w + step_gap)
    s_box = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, sx, Inches(5.38), step_w, Inches(1.3))
    s_box.adjustments[0] = 0.06
    s_box.fill.solid()
    s_box.fill.fore_color.rgb = WHITE
    s_box.line.color.rgb = SKY
    s_box.line.width = Pt(1)
    
    tf_s = s_box.text_frame
    tf_s.word_wrap = True
    tf_s.vertical_anchor = MSO_ANCHOR.TOP
    tf_s.margin_left = tf_s.margin_right = tf_s.margin_top = Inches(0.12)
    
    ps1 = tf_s.paragraphs[0]
    ps1.text = st_num
    ps1.font.name = FONT_NAME
    ps1.font.size = Pt(10.5)
    ps1.font.bold = True
    ps1.font.color.rgb = CYAN
    
    ps2 = tf_s.add_paragraph()
    ps2.text = st_name
    ps2.font.name = FONT_NAME
    ps2.font.size = Pt(12)
    ps2.font.bold = True
    ps2.font.color.rgb = NAVY
    ps2.space_before = Pt(1)
    
    ps3 = tf_s.add_paragraph()
    ps3.text = st_desc
    ps3.font.name = FONT_NAME
    ps3.font.size = Pt(10)
    ps3.font.color.rgb = NAVY
    ps3.space_before = Pt(3)
    
    if idx < 3:
        arr_s = s6.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, sx + step_w + Inches(0.12), Inches(5.88), Inches(0.24), Inches(0.28))
        arr_s.fill.solid()
        arr_s.fill.fore_color.rgb = CYAN
        arr_s.line.fill.background()

add_notes(s6,
    "The core innovation of PlumeTrace is its Autonomous Closed Loop.\n\n"
    "Instead of driving a static patrol line, our system continuously recomputes waypoints based on a 4D objective function: "
    "tracking chemical gradients upstream, anticipating rain runoff via live weather radar, and ensuring older areas are revisited.\n\n"
    "Why does digital twinning beat traditional static sensors? Static probes suffer from point dilution: they tell you pollution passed, but cannot identify where it originated. "
    "By coupling physical sensing with predictive twin simulation, we pinpoint the exact leaking outfall in minutes."
)


# ==========================================================
# SLIDE 7: Stakeholder Action & AI Public Access (Section 3 - 3/3)
# ==========================================================
s7 = prs.slides.add_slide(blank_layout)
set_background(s7)
add_slide_header(s7, "Stakeholder Action & AI Public Access", category_pill="Technical Solution 3/3")

s7_card_h = Inches(3.2)
add_card(s7, Inches(0.8), Inches(1.55), col_w, s7_card_h, "City & Authority Command", [
    "Outfall Asset Health: links chemical spikes to specific pipe IDs",
    "Targeted CapEx: empirical proof for 1.5M - 5M+ EUR basin upgrades",
    "Chronic Seepage: uncovers leaking pipes before structural collapse",
    "Automated audit logs for EU Water Framework Directive & OGewV"
], icon_name="authority", tag="Governance & CapEx Prioritization", chip_text="Asset Health Scoring  |  Targeted €1.5M-€5M+ CapEx  |  EU WFD Compliance", title_size=20, bullet_size=15)

add_card(s7, Inches(6.866), Inches(1.55), col_w, s7_card_h, "AI Public Access via MCP", [
    "Model Context Protocol (MCP) connects AI models to live twin data",
    "Conversational Queries: 'Can I surf at Fuchslochwelle today?'",
    "Live Citizen Traffic Light: instant Green / Yellow / Red alerts",
    "Eliminates 48h lab delay with direct public health warnings"
], icon_name="ai_mcp", tag="Citizen Interaction & Open Data", chip_text="MCP Integration  |  Conversational AI Assistant  |  Citizen Traffic Light", title_size=20, bullet_size=15)

# Bottom Infographic Banner: MCP & Open Data Integration Architecture
mcp_box = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(4.95), Inches(11.733), Inches(1.95))
mcp_box.adjustments[0] = 0.035
mcp_box.fill.solid()
mcp_box.fill.fore_color.rgb = CARD_BG
mcp_box.line.color.rgb = BORDER_CLR
mcp_box.line.width = Pt(1.5)

tf_mcp = mcp_box.text_frame
tf_mcp.word_wrap = True
tf_mcp.vertical_anchor = MSO_ANCHOR.TOP
tf_mcp.margin_left = Inches(0.35)
tf_mcp.margin_right = Inches(0.35)
tf_mcp.margin_top = Inches(0.18)

p_mcpt = tf_mcp.paragraphs[0]
p_mcpt.text = "OPEN DATA & MCP INTEGRATION ARCHITECTURE (PUBLIC & CITY ACCESS)"
p_mcpt.font.name = FONT_NAME
p_mcpt.font.size = Pt(11)
p_mcpt.font.bold = True
p_mcpt.font.color.rgb = CYAN
p_mcpt.space_after = Pt(8)

# 3 Pipeline Steps for MCP
pipe_w7 = Inches(3.45)
pipe_gap7 = Inches(0.5)

# Box 1
b1_mcp = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.1), Inches(5.38), pipe_w7, Inches(1.28))
b1_mcp.adjustments[0] = 0.05
b1_mcp.fill.solid()
b1_mcp.fill.fore_color.rgb = WHITE
b1_mcp.line.color.rgb = SKY
b1_mcp.line.width = Pt(1)
tf_mb1 = b1_mcp.text_frame
tf_mb1.word_wrap = True
tf_mb1.vertical_anchor = MSO_ANCHOR.TOP
tf_mb1.margin_left = tf_mb1.margin_right = tf_mb1.margin_top = Inches(0.12)
pm1_h = tf_mb1.paragraphs[0]
pm1_h.text = "1. Public Open Data Sources"
pm1_h.font.name = FONT_NAME
pm1_h.font.size = Pt(12)
pm1_h.font.bold = True
pm1_h.font.color.rgb = NAVY
pm1_b = tf_mb1.add_paragraph()
pm1_b.text = "Bavarian LOD2 3D mesh, DWD precipitation radar, and GKD Bayern real-time gauge telemetry."
pm1_b.font.name = FONT_NAME
pm1_b.font.size = Pt(10.5)
pm1_b.font.color.rgb = NAVY
pm1_b.space_before = Pt(3)

ar_m1 = s7.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(1.1) + pipe_w7 + Inches(0.12), Inches(5.9), Inches(0.25), Inches(0.28))
ar_m1.fill.solid()
ar_m1.fill.fore_color.rgb = CYAN
ar_m1.line.fill.background()

# Box 2
b2_mcp = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.1) + pipe_w7 + pipe_gap7, Inches(5.38), pipe_w7, Inches(1.28))
b2_mcp.adjustments[0] = 0.05
b2_mcp.fill.solid()
b2_mcp.fill.fore_color.rgb = WHITE
b2_mcp.line.color.rgb = SKY
b2_mcp.line.width = Pt(1)
tf_mb2 = b2_mcp.text_frame
tf_mb2.word_wrap = True
tf_mb2.vertical_anchor = MSO_ANCHOR.TOP
tf_mb2.margin_left = tf_mb2.margin_right = tf_mb2.margin_top = Inches(0.12)
pm2_h = tf_mb2.paragraphs[0]
pm2_h.text = "2. PlumeTrace MCP Server"
pm2_h.font.name = FONT_NAME
pm2_h.font.size = Pt(12)
pm2_h.font.bold = True
pm2_h.font.color.rgb = NAVY
pm2_b = tf_mb2.add_paragraph()
pm2_b.text = "Standardized Model Context Protocol exposes river safety status, outfall scores, and alerts to AI agents."
pm2_b.font.name = FONT_NAME
pm2_b.font.size = Pt(10.5)
pm2_b.font.color.rgb = NAVY
pm2_b.space_before = Pt(3)

ar_m2 = s7.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(1.1) + (pipe_w7 + pipe_gap7) + pipe_w7 + Inches(0.12), Inches(5.9), Inches(0.25), Inches(0.28))
ar_m2.fill.solid()
ar_m2.fill.fore_color.rgb = CYAN
ar_m2.line.fill.background()

# Box 3
b3_mcp = s7.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.1) + (pipe_w7 + pipe_gap7) * 2, Inches(5.38), pipe_w7, Inches(1.28))
b3_mcp.adjustments[0] = 0.05
b3_mcp.fill.solid()
b3_mcp.fill.fore_color.rgb = WHITE
b3_mcp.line.color.rgb = SKY
b3_mcp.line.width = Pt(1)
tf_mb3 = b3_mcp.text_frame
tf_mb3.word_wrap = True
tf_mb3.vertical_anchor = MSO_ANCHOR.TOP
tf_mb3.margin_left = tf_mb3.margin_right = tf_mb3.margin_top = Inches(0.12)
pm3_h = tf_mb3.paragraphs[0]
pm3_h.text = "3. Public & City Interfaces"
pm3_h.font.name = FONT_NAME
pm3_h.font.size = Pt(12)
pm3_h.font.bold = True
pm3_h.font.color.rgb = NAVY
pm3_b = tf_mb3.add_paragraph()
pm3_b.text = "Natural language AI answers citizen queries instantly; city dashboard automates regulatory compliance."
pm3_b.font.name = FONT_NAME
pm3_b.font.size = Pt(10.5)
pm3_b.font.color.rgb = NAVY
pm3_b.space_before = Pt(3)

add_notes(s7,
    "Finally, how do stakeholders interact with PlumeTrace?\n\n"
    "For Water Authorities (SUN & WWA): We provide concrete asset intelligence. By assigning health scores to specific outfall IDs, "
    "we provide the empirical justification needed to prioritize multi-million euro retention basin expansions.\n\n"
    "For Citizens and Surfers: We expose the Digital Twin via the Model Context Protocol (MCP). Anyone can ask an AI assistant: "
    "'Can I surf at the Fuchslochwelle wave today?' or 'Is the river safe for my dog right now?'. "
    "The AI queries live telemetry and forecasts, returning a clear traffic light advisory (Green, Yellow, or Red). "
    "This transforms complex environmental chemistry into immediate, transparent public safety."
)

prs.save(OUTPUT_PATH)
print(f"Successfully generated PowerPoint presentation at: {OUTPUT_PATH}")
