import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

# Output file path
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "plumetrace_section_1_and_2.pptx")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo.jpeg")

# Initialize presentation
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_slide_layout = prs.slide_layouts[6] # Blank slide layout

# Color definitions
NAVY = RGBColor(2, 48, 71)       # #023047
CYAN = RGBColor(33, 158, 188)     # #219ebc
SKY = RGBColor(142, 202, 230)     # #8ecae6
GOLD = RGBColor(255, 183, 3)      # #ffb703
ORANGE = RGBColor(251, 133, 0)    # #fb8500
WHITE = RGBColor(255, 255, 255)   # #ffffff
CARD_BG = RGBColor(244, 249, 252) # Soft tint

FONT_NAME = "Calibri"

def set_slide_background(slide):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = WHITE

def add_header_title(slide, title_text):
    txBox = slide.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(0.9))
    tf = txBox.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = title_text
    p.font.name = FONT_NAME
    p.font.size = Pt(38)
    p.font.bold = True
    p.font.color.rgb = NAVY

def add_speaker_note(slide, note_text):
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = note_text

# ==========================================================
# SLIDE 1: Title Slide
# ==========================================================
s1 = prs.slides.add_slide(blank_slide_layout)
set_slide_background(s1)

# Add Logo if exists
if os.path.exists(LOGO_PATH):
    s1.shapes.add_picture(LOGO_PATH, Inches(1.2), Inches(2.2), width=Inches(3.2), height=Inches(3.2))

# Title & Subtitle text frame
s1_box = s1.shapes.add_textbox(Inches(4.9), Inches(2.3), Inches(7.5), Inches(3.0))
tf1 = s1_box.text_frame
tf1.word_wrap = True
tf1.margin_left = tf1.margin_top = tf1.margin_right = tf1.margin_bottom = 0

p1 = tf1.paragraphs[0]
p1.text = "PlumeTrace"
p1.font.name = FONT_NAME
p1.font.size = Pt(60)
p1.font.bold = True
p1.font.color.rgb = CYAN
p1.space_after = Pt(14)

p2 = tf1.add_paragraph()
p2.text = "Autonomous Water Protection for the Pegnitz River"
p2.font.name = FONT_NAME
p2.font.size = Pt(26)
p2.font.bold = True
p2.font.color.rgb = NAVY

add_speaker_note(s1, 
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
s2 = prs.slides.add_slide(blank_slide_layout)
set_slide_background(s2)
add_header_title(s2, "Why Pegnitz")

cards_data_s2 = [
    {
        "title": "Public Health",
        "bullets": [
            "Raw sewage spikes after rainfall",
            "Instant health risk for surfers, waders, and park visitors"
        ],
        "left": Inches(0.8), "top": Inches(1.8)
    },
    {
        "title": "Sewer Overflows (CSOs)",
        "bullets": [
            "1,500 km municipal network overloaded by storms",
            "1.5M - 5M+ EUR cost per retention basin"
        ],
        "left": Inches(6.8), "top": Inches(1.8)
    },
    {
        "title": "Knoblauchsland Agriculture",
        "bullets": [
            "Nitrate leaching into drinking water aquifers",
            "Strict EU limits and compliance pressure"
        ],
        "left": Inches(0.8), "top": Inches(4.4)
    },
    {
        "title": "Summer Heat and Drought",
        "bullets": [
            "Low flow concentrates pollutants",
            "Dissolved oxygen drops < 3 mg/L (fish kills)"
        ],
        "left": Inches(6.8), "top": Inches(4.4)
    }
]

card_w = Inches(5.7)
card_h = Inches(2.2)

for c in cards_data_s2:
    shape = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c["left"], c["top"], card_w, card_h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = CARD_BG
    shape.line.color.rgb = SKY
    shape.line.width = Pt(1.5)
    
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.3)
    tf.margin_right = Inches(0.3)
    tf.margin_top = Inches(0.22)
    tf.margin_bottom = Inches(0.2)
    
    p = tf.paragraphs[0]
    p.text = c["title"]
    p.font.name = FONT_NAME
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = NAVY
    p.space_after = Pt(10)
    
    for b in c["bullets"]:
        bp = tf.add_paragraph()
        bp.text = f"-  {b}"
        bp.font.name = FONT_NAME
        bp.font.size = Pt(16)
        bp.font.color.rgb = NAVY
        bp.space_after = Pt(4)

add_speaker_note(s2,
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
s3 = prs.slides.add_slide(blank_slide_layout)
set_slide_background(s3)
add_header_title(s3, "Current Monitoring")

col_w = Inches(5.7)
col_h = Inches(4.1)

# Left Column: Municipal Authorities
left_shape = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), col_w, col_h)
left_shape.fill.solid()
left_shape.fill.fore_color.rgb = CARD_BG
left_shape.line.color.rgb = SKY
left_shape.line.width = Pt(1.5)

tf_left = left_shape.text_frame
tf_left.word_wrap = True
tf_left.margin_left = tf_left.margin_right = Inches(0.35)
tf_left.margin_top = Inches(0.25)

p_lh = tf_left.paragraphs[0]
p_lh.text = "Municipal Authorities"
p_lh.font.name = FONT_NAME
p_lh.font.size = Pt(22)
p_lh.font.bold = True
p_lh.font.color.rgb = NAVY
p_lh.space_after = Pt(4)

p_sub = tf_left.add_paragraph()
p_sub.text = "Stadtentwässerung Nürnberg (SUN) & Wasserwirtschaftsamt (WWA)"
p_sub.font.name = FONT_NAME
p_sub.font.size = Pt(13)
p_sub.font.bold = True
p_sub.font.color.rgb = CYAN
p_sub.space_after = Pt(12)

left_bullets = [
    "Temperature, pH, conductivity, turbidity",
    "Dissolved oxygen and nutrients (Nitrate, Phosphate)",
    "Ammonium (NH4+): primary raw sewage tracer"
]
for b in left_bullets:
    bp = tf_left.add_paragraph()
    bp.text = f"-  {b}"
    bp.font.name = FONT_NAME
    bp.font.size = Pt(16)
    bp.font.color.rgb = NAVY
    bp.space_after = Pt(8)

# Right Column: The Sampling Gap
right_shape = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), col_w, col_h)
right_shape.fill.solid()
right_shape.fill.fore_color.rgb = CARD_BG
right_shape.line.color.rgb = SKY
right_shape.line.width = Pt(1.5)

tf_right = right_shape.text_frame
tf_right.word_wrap = True
tf_right.margin_left = tf_right.margin_right = Inches(0.35)
tf_right.margin_top = Inches(0.25)

p_rh = tf_right.paragraphs[0]
p_rh.text = "The Sampling Gap"
p_rh.font.name = FONT_NAME
p_rh.font.size = Pt(22)
p_rh.font.bold = True
p_rh.font.color.rgb = NAVY
p_rh.space_after = Pt(16)

right_bullets = [
    "Automatic sensors: continuous, but confined to few fixed locations",
    "Manual grab sampling: often only 1x per month (24-48h lab delay)",
    "Convective storm overflows: last only 2 to 4 hours"
]
for b in right_bullets:
    bp = tf_right.add_paragraph()
    bp.text = f"-  {b}"
    bp.font.name = FONT_NAME
    bp.font.size = Pt(16)
    bp.font.color.rgb = NAVY
    bp.space_after = Pt(12)

# Bottom Highlight: The Result
res_shape = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(6.15), Inches(11.7), Inches(0.8))
res_shape.fill.solid()
res_shape.fill.fore_color.rgb = CARD_BG
res_shape.line.color.rgb = CYAN
res_shape.line.width = Pt(1.5)

tf_res = res_shape.text_frame
tf_res.word_wrap = True
tf_res.margin_left = Inches(0.3)
tf_res.margin_top = Inches(0.18)

p_res = tf_res.paragraphs[0]
p_res.text = "The Result:  "
p_res.font.name = FONT_NAME
p_res.font.size = Pt(17)
p_res.font.bold = True
p_res.font.color.rgb = ORANGE

run_res = p_res.add_run()
run_res.text = "Plume arrives, causes harm, and clears undetected."
run_res.font.name = FONT_NAME
run_res.font.size = Pt(17)
run_res.font.bold = True
run_res.font.color.rgb = NAVY

add_speaker_note(s3,
    "To address this, we looked at what municipal authorities currently measure.\n\n"
    "In Nuremberg, the drainage service SUN tracks eight standard parameters: temperature, pH, conductivity, turbidity, "
    "dissolved oxygen, and nutrients like ammonium, nitrate, and phosphate. Ammonium is the critical chemical fingerprint of raw sewage.\n\n"
    "The sampling gap is two-fold: automated sensors are confined to a few fixed points, while manual sampling happens as rarely as once a month with days of lab delay. "
    "The result: acute plumes arrive, cause damage, and clear completely undetected."
)

# ==========================================================
# SLIDE 4: Key Stakeholders
# ==========================================================
s4 = prs.slides.add_slide(blank_slide_layout)
set_slide_background(s4)
add_header_title(s4, "Key Stakeholders")

# Left Column: Water Authorities
s4_left = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), col_w, Inches(4.9))
s4_left.fill.solid()
s4_left.fill.fore_color.rgb = CARD_BG
s4_left.line.color.rgb = SKY
s4_left.line.width = Pt(1.5)

tf4_l = s4_left.text_frame
tf4_l.word_wrap = True
tf4_l.margin_left = tf4_l.margin_right = Inches(0.35)
tf4_l.margin_top = Inches(0.3)

p4_lh = tf4_l.paragraphs[0]
p4_lh.text = "Water Authorities (WWA, SUN)"
p4_lh.font.name = FONT_NAME
p4_lh.font.size = Pt(22)
p4_lh.font.bold = True
p4_lh.font.color.rgb = NAVY
p4_lh.space_after = Pt(16)

s4_left_bullets = [
    "Cannot locate pollution origin (fixed stations lack spatial tracking)",
    "Blind infrastructure spending (1.5M - 5M+ EUR per basin without plume data)",
    "Chronic pipe seepage undetected until structural failure",
    "Lab results arrive 24-48 hours too late for emergency action"
]
for b in s4_left_bullets:
    bp = tf4_l.add_paragraph()
    bp.text = f"-  {b}"
    bp.font.name = FONT_NAME
    bp.font.size = Pt(16)
    bp.font.color.rgb = NAVY
    bp.space_after = Pt(12)

# Right Column: Citizens and Surfers
s4_right = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.8), col_w, Inches(4.9))
s4_right.fill.solid()
s4_right.fill.fore_color.rgb = CARD_BG
s4_right.line.color.rgb = SKY
s4_right.line.width = Pt(1.5)

tf4_r = s4_right.text_frame
tf4_r.word_wrap = True
tf4_r.margin_left = tf4_r.margin_right = Inches(0.35)
tf4_r.margin_top = Inches(0.3)

p4_rh = tf4_r.paragraphs[0]
p4_rh.text = "Citizens and Surfers"
p4_rh.font.name = FONT_NAME
p4_rh.font.size = Pt(22)
p4_rh.font.bold = True
p4_rh.font.color.rgb = NAVY
p4_rh.space_after = Pt(16)

s4_right_bullets = [
    "Zero real-time visibility into water safety",
    "Unknowingly enter water during toxic overflow events",
    "High risk of gastrointestinal and skin infections",
    "Delayed municipal reports provide no immediate guidance"
]
for b in s4_right_bullets:
    bp = tf4_r.add_paragraph()
    bp.text = f"-  {b}"
    bp.font.name = FONT_NAME
    bp.font.size = Pt(16)
    bp.font.color.rgb = NAVY
    bp.space_after = Pt(12)

add_speaker_note(s4,
    "This monitoring failure creates acute problems for our two key stakeholder groups today:\n\n"
    "First, Water Authorities like SUN and WWA: They must invest millions of euros into retention basins, "
    "but without spatial plume tracking, they are forced to invest blindly without knowing which overflow pipes cause the greatest damage. "
    "Furthermore, laboratory delays mean they only learn of acute spills days after they have already washed away.\n\n"
    "Second, Citizens and Surfers: People entering the Pegnitz at the Fuchslochwelle or in city parks have zero real-time warning. "
    "They unknowingly expose themselves to acute bacterial contamination because municipal data is either delayed by days or buried in complex chemical reports."
)

# Save presentation
prs.save(OUTPUT_PATH)
print(f"Successfully generated PowerPoint presentation at: {OUTPUT_PATH}")
