import os
from PIL import Image, ImageDraw

ICONS_DIR = os.path.join(os.path.dirname(__file__), "assets", "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

# Brand colors in RGBA
NAVY = (2, 48, 71, 255)       # #023047
CYAN = (33, 158, 188, 255)    # #219ebc
SKY = (142, 202, 230, 255)    # #8ecae6
GOLD = (255, 183, 3, 255)     # #ffb703
ORANGE = (251, 133, 0, 255)   # #fb8500
WHITE = (255, 255, 255, 255)
TRANSPARENT = (0, 0, 0, 0)

SIZE = 512
FINAL_SIZE = 128

def create_base(bg_color):
    img = Image.new("RGBA", (SIZE, SIZE), TRANSPARENT)
    draw = ImageDraw.Draw(img)
    # Circle background
    draw.ellipse((24, 24, SIZE - 24, SIZE - 24), fill=bg_color)
    return img, draw

def save_icon(img, name):
    res = img.resize((FINAL_SIZE, FINAL_SIZE), Image.Resampling.LANCZOS)
    path = os.path.join(ICONS_DIR, f"{name}.png")
    res.save(path, "PNG")
    print(f"Saved: {path}")

# 1. Health (Medical Cross)
img, d = create_base(CYAN)
w = 64
cx, cy = SIZE // 2, SIZE // 2
arm = 140
d.rectangle((cx - w, cy - arm, cx + w, cy + arm), fill=WHITE)
d.rectangle((cx - arm, cy - w, cx + arm, cy + w), fill=WHITE)
save_icon(img, "health")

# 2. Storm Pipe (Outfall Pipe with Water Flow)
img, d = create_base(ORANGE)
cx, cy = SIZE // 2, SIZE // 2
# Pipe cylinder
d.ellipse((cx - 140, cy - 110, cx + 140, cy - 30), outline=WHITE, width=28)
d.arc((cx - 140, cy - 60, cx + 140, cy + 20), 0, 180, fill=WHITE, width=28)
# Water drop streams
for dx in [-70, 0, 70]:
    d.line([(cx + dx, cy + 60), (cx + dx, cy + 140)], fill=WHITE, width=24)
save_icon(img, "storm_pipe")

# 3. Agriculture (Plant Sprout / Leaf)
img, d = create_base(CYAN)
cx, cy = SIZE // 2, SIZE // 2
# Central stem
d.line([(cx, cy + 140), (cx, cy - 30)], fill=WHITE, width=28)
# Left leaf curve
d.arc((cx - 150, cy - 80, cx, cy + 70), 200, 360, fill=WHITE, width=24)
d.arc((cx - 150, cy - 30, cx, cy + 120), 0, 160, fill=WHITE, width=24)
# Right leaf curve
d.arc((cx, cy - 110, cx + 150, cy + 40), 180, 340, fill=WHITE, width=24)
d.arc((cx, cy - 60, cx + 150, cy + 90), 20, 180, fill=WHITE, width=24)
save_icon(img, "agriculture")

# 4. Drought (Sun & Heat Waves)
img, d = create_base(GOLD)
cx, cy = SIZE // 2, SIZE // 2
# Sun core
d.ellipse((cx - 80, cy - 80, cx + 80, cy + 80), fill=WHITE)
# Rays
import math
for deg in range(0, 360, 45):
    rad = math.radians(deg)
    x1 = cx + math.cos(rad) * 110
    y1 = cy + math.sin(rad) * 110
    x2 = cx + math.cos(rad) * 160
    y2 = cy + math.sin(rad) * 160
    d.line([(x1, y1), (x2, y2)], fill=WHITE, width=24)
save_icon(img, "drought")

# 5. Municipal Sensor (Tower / Sensor Station)
img, d = create_base(NAVY)
cx, cy = SIZE // 2, SIZE // 2
# Central sensor mast
d.line([(cx, cy - 120), (cx, cy + 140)], fill=WHITE, width=26)
d.ellipse((cx - 30, cy - 140, cx + 30, cy - 80), fill=CYAN)
# Transmit waves
d.arc((cx - 100, cy - 150, cx + 100, cy + 50), 220, 320, fill=WHITE, width=22)
d.arc((cx - 150, cy - 200, cx + 150, cy + 100), 220, 320, fill=WHITE, width=22)
# Base triangle
d.polygon([(cx - 80, cy + 140), (cx + 80, cy + 140), (cx, cy + 50)], outline=WHITE)
save_icon(img, "municipal_sensor")

# 6. Sampling Gap (Clock with Alert Exclamation)
img, d = create_base(ORANGE)
cx, cy = SIZE // 2, SIZE // 2
d.ellipse((cx - 130, cy - 130, cx + 130, cy + 130), outline=WHITE, width=26)
# Clock hands
d.line([(cx, cy), (cx, cy - 70)], fill=WHITE, width=24)
d.line([(cx, cy), (cx + 60, cy)], fill=WHITE, width=24)
# Small alert badge
d.ellipse((cx + 70, cy + 70, cx + 150, cy + 150), fill=NAVY)
d.line([(cx + 110, cy + 85), (cx + 110, cy + 120)], fill=WHITE, width=12)
d.ellipse((cx + 105, cy + 128, cx + 115, cy + 138), fill=WHITE)
save_icon(img, "sampling_gap")

# 7. Authority (Government / Legal Columns)
img, d = create_base(NAVY)
cx, cy = SIZE // 2, SIZE // 2
# Roof pediment triangle
d.polygon([(cx - 140, cy - 60), (cx + 140, cy - 60), (cx, cy - 140)], fill=WHITE)
# Columns
for col_x in [cx - 100, cx - 35, cx + 35, cx + 100]:
    d.rectangle((col_x - 12, cy - 45, col_x + 12, cy + 100), fill=WHITE)
# Foundation base
d.rectangle((cx - 150, cy + 100, cx + 150, cy + 135), fill=WHITE)
save_icon(img, "authority")

# 8. Citizens / Surfers (Water Wave & Action)
img, d = create_base(CYAN)
cx, cy = SIZE // 2, SIZE // 2
# Wave curves
d.arc((cx - 140, cy - 80, cx + 20, cy + 80), 0, 180, fill=WHITE, width=26)
d.arc((cx - 20, cy - 40, cx + 140, cy + 120), 180, 360, fill=WHITE, width=26)
d.arc((cx - 120, cy + 20, cx + 120, cy + 150), 200, 340, fill=WHITE, width=22)
# Sun/figure head
d.ellipse((cx - 30, cy - 130, cx + 30, cy - 70), fill=WHITE)
save_icon(img, "citizens_surfer")

# 9. Physical Platform (Robotic Surface Vessel / ASV)
img, d = create_base(CYAN)
cx, cy = SIZE // 2, SIZE // 2
# Boat hull polygon
d.polygon([(cx - 140, cy + 30), (cx + 140, cy + 30), (cx + 100, cy + 110), (cx - 100, cy + 110)], fill=WHITE)
# Cabin / computing box
d.rectangle((cx - 65, cy - 40, cx + 65, cy + 30), fill=NAVY)
# LiDAR dome on top
d.arc((cx - 35, cy - 100, cx + 35, cy - 30), 180, 360, fill=WHITE, width=22)
d.line([(cx - 35, cy - 30), (cx + 35, cy - 30)], fill=WHITE, width=22)
d.ellipse((cx - 12, cy - 75, cx + 12, cy - 51), fill=ORANGE)
save_icon(img, "physical_robot")

# 10. Simulation Mirror (Twin Cloud Nodes / Orbit)
img, d = create_base(NAVY)
cx, cy = SIZE // 2, SIZE // 2
# Dual synchronized nodes
d.ellipse((cx - 120, cy - 50, cx - 20, cy + 50), fill=CYAN)
d.ellipse((cx + 20, cy - 50, cx + 120, cy + 50), outline=WHITE, width=20)
# Bi-directional arrows/arcs
d.arc((cx - 110, cy - 120, cx + 110, cy + 100), 200, 340, fill=WHITE, width=20)
d.arc((cx - 110, cy - 100, cx + 110, cy + 120), 20, 160, fill=WHITE, width=20)
save_icon(img, "simulation_mirror")

# 11. 3D Digital Twin (Isometric Geo-Cube)
img, d = create_base(ORANGE)
cx, cy = SIZE // 2, SIZE // 2
# Isometric cube
d.polygon([(cx, cy - 130), (cx + 110, cy - 65), (cx, cy), (cx - 110, cy - 65)], fill=WHITE)
d.polygon([(cx - 110, cy - 65), (cx, cy), (cx, cy + 125), (cx - 110, cy + 60)], fill=NAVY)
d.polygon([(cx, cy), (cx + 110, cy - 65), (cx + 110, cy + 60), (cx, cy + 125)], fill=CYAN)
save_icon(img, "digital_twin_3d")

# 12. 4D Adaptive Retasking (Dynamic Compass / Target)
img, d = create_base(CYAN)
cx, cy = SIZE // 2, SIZE // 2
d.ellipse((cx - 130, cy - 130, cx + 130, cy + 130), outline=WHITE, width=24)
# Compass needle pointing NE
d.polygon([(cx, cy - 110), (cx + 30, cy), (cx, cy + 30), (cx - 30, cy)], fill=ORANGE)
d.polygon([(cx, cy + 110), (cx + 30, cy), (cx, cy - 30), (cx - 30, cy)], fill=WHITE)
d.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill=NAVY)
save_icon(img, "adaptive_retask")

# 13. Safety & Resilience (Shield & Checkmark)
img, d = create_base(NAVY)
cx, cy = SIZE // 2, SIZE // 2
# Shield outline
d.polygon([(cx, cy - 130), (cx + 110, cy - 70), (cx + 90, cy + 60), (cx, cy + 135), (cx - 90, cy + 60), (cx - 110, cy - 70)], fill=WHITE)
# Inner shield
d.polygon([(cx, cy - 100), (cx + 80, cy - 50), (cx + 65, cy + 45), (cx, cy + 105), (cx - 65, cy + 45), (cx - 80, cy - 50)], fill=NAVY)
# Checkmark inside
d.line([(cx - 45, cy - 5), (cx - 10, cy + 35), (cx + 50, cy - 35)], fill=CYAN, width=22)
save_icon(img, "safety_resilience")

# 14. Gradient Tracing (Contour Radar & Upstream Vector)
img, d = create_base(CYAN)
cx, cy = SIZE // 2, SIZE // 2
d.ellipse((cx - 140, cy - 140, cx + 140, cy + 140), outline=WHITE, width=16)
d.ellipse((cx - 95, cy - 95, cx + 95, cy + 95), outline=WHITE, width=16)
d.ellipse((cx - 50, cy - 50, cx + 50, cy + 50), outline=WHITE, width=16)
# Upward tracking arrow
d.line([(cx, cy + 110), (cx, cy - 100)], fill=ORANGE, width=24)
d.polygon([(cx, cy - 130), (cx - 35, cy - 70), (cx + 35, cy - 70)], fill=ORANGE)
save_icon(img, "gradient_tracing")

# 15. Asset Intelligence (Infrastructure Database & Verified Check)
img, d = create_base(NAVY)
cx, cy = SIZE // 2, SIZE // 2
# Stacked database cylinders
for dy in [-60, 10, 80]:
    d.ellipse((cx - 100, cy + dy - 30, cx + 100, cy + dy + 30), outline=WHITE, width=20)
    d.line([(cx - 100, cy + dy), (cx - 100, cy + dy + 40)], fill=WHITE, width=20)
    d.line([(cx + 100, cy + dy), (cx + 100, cy + dy + 40)], fill=WHITE, width=20)
# Verified tick on side
d.ellipse((cx + 40, cy - 120, cx + 120, cy - 40), fill=CYAN)
d.line([(cx + 60, cy - 80), (cx + 75, cy - 65), (cx + 105, cy - 95)], fill=WHITE, width=12)
save_icon(img, "asset_intelligence")

# 16. River Corridor Mapping (3D LiDAR Fan Scan)
img, d = create_base(ORANGE)
cx, cy = SIZE // 2, SIZE // 2
# Scanner emitter
d.ellipse((cx - 30, cy - 120, cx + 30, cy - 60), fill=WHITE)
# Fan rays scanning downward
d.line([(cx, cy - 60), (cx - 120, cy + 100)], fill=WHITE, width=18)
d.line([(cx, cy - 60), (cx - 40, cy + 115)], fill=WHITE, width=18)
d.line([(cx, cy - 60), (cx + 40, cy + 115)], fill=WHITE, width=18)
d.line([(cx, cy - 60), (cx + 120, cy + 100)], fill=WHITE, width=18)
# Riverbank contour line
d.line([(cx - 140, cy + 110), (cx - 30, cy + 125), (cx + 40, cy + 125), (cx + 140, cy + 105)], fill=NAVY, width=22)
save_icon(img, "corridor_mapping")

# 17. Operational Economics (1 vs 50+ Efficiency Bar / Scale)
img, d = create_base(CYAN)
cx, cy = SIZE // 2, SIZE // 2
# 1 large circle (autonomous robot)
d.ellipse((cx - 130, cy - 50, cx - 30, cy + 50), fill=WHITE)
# Multiplier / Arrow
d.polygon([(cx - 15, cy), (cx + 15, cy - 25), (cx + 15, cy + 25)], fill=ORANGE)
# Cluster of small fixed dots (50+)
dots = [
    (cx + 60, cy - 60), (cx + 95, cy - 60), (cx + 130, cy - 60),
    (cx + 60, cy - 20), (cx + 95, cy - 20), (cx + 130, cy - 20),
    (cx + 60, cy + 20), (cx + 95, cy + 20), (cx + 130, cy + 20),
    (cx + 60, cy + 60), (cx + 95, cy + 60), (cx + 130, cy + 60),
]
for dx, dy in dots:
    d.ellipse((dx - 10, dy - 10, dx + 10, dy + 10), fill=WHITE)
save_icon(img, "economics")

print("All 17 icons generated successfully.")

# 18. AI & MCP (AI Sparkle & Interface Nodes)
img, d = create_base(CYAN)
cx, cy = SIZE // 2, SIZE // 2
# Central 4-pointed AI sparkle
d.polygon([(cx, cy - 130), (cx + 35, cy - 35), (cx + 130, cy), (cx + 35, cy + 35), (cx, cy + 130), (cx - 35, cy + 35), (cx - 130, cy), (cx - 35, cy - 35)], fill=WHITE)
# Smaller offset sparkle
d.polygon([(cx + 90, cy - 90), (cx + 105, cy - 60), (cx + 135, cy - 45), (cx + 105, cy - 30), (cx + 90, cy), (cx + 75, cy - 30), (cx + 45, cy - 45), (cx + 75, cy - 60)], fill=GOLD)
save_icon(img, "ai_mcp")

# 19. Traffic Light (Citizen Safety Signal)
img, d = create_base(NAVY)
cx, cy = SIZE // 2, SIZE // 2
# Traffic light housing
d.rounded_rectangle((cx - 60, cy - 135, cx + 60, cy + 135), radius=35, fill=(1, 22, 36, 255), outline=WHITE, width=14)
# Red light (top)
d.ellipse((cx - 35, cy - 110, cx + 35, cy - 40), fill=ORANGE)
# Yellow light (mid)
d.ellipse((cx - 35, cy - 35, cx + 35, cy + 35), fill=GOLD)
# Green light (bottom - glowing)
d.ellipse((cx - 35, cy + 40, cx + 35, cy + 110), fill=CYAN)
save_icon(img, "traffic_light")

# 20. River Robot ASV (Autonomous Surface Vessel on River Waves)
img, d = create_base(CYAN)
cx, cy = SIZE // 2, SIZE // 2
# Boat hull on water
d.polygon([(cx - 140, cy + 20), (cx + 140, cy + 20), (cx + 95, cy + 90), (cx - 95, cy + 90)], fill=WHITE)
# Sensor mast / LiDAR
d.line([(cx - 20, cy + 20), (cx - 20, cy - 70)], fill=WHITE, width=22)
d.ellipse((cx - 45, cy - 105, cx + 5, cy - 55), fill=NAVY)
# Antenna ray
d.line([(cx + 25, cy + 20), (cx + 55, cy - 40)], fill=WHITE, width=14)
# Water wave line below
d.arc((cx - 150, cy + 85, cx - 10, cy + 155), 200, 340, fill=WHITE, width=20)
d.arc((cx - 20, cy + 85, cx + 120, cy + 155), 200, 340, fill=WHITE, width=20)
save_icon(img, "river_asv")

# 21. Cloud Digital Twin (Predictive Cloud Engine)
img, d = create_base(NAVY)
cx, cy = SIZE // 2, SIZE // 2
# Cloud shape
d.ellipse((cx - 120, cy - 40, cx - 10, cy + 60), fill=WHITE)
d.ellipse((cx - 60, cy - 90, cx + 70, cy + 30), fill=WHITE)
d.ellipse((cx + 10, cy - 50, cx + 120, cy + 60), fill=WHITE)
d.rectangle((cx - 80, cy + 10, cx + 80, cy + 60), fill=WHITE)
# Inner twin sync icon in cyan
d.ellipse((cx - 45, cy - 15, cx - 5, cy + 25), fill=CYAN)
d.ellipse((cx + 5, cy - 15, cx + 45, cy + 25), fill=CYAN)
d.arc((cx - 40, cy - 35, cx + 40, cy + 45), 20, 160, fill=NAVY, width=12)
d.arc((cx - 40, cy - 35, cx + 40, cy + 45), 200, 340, fill=NAVY, width=12)
save_icon(img, "cloud_twin")

print("All extra icons generated successfully.")
