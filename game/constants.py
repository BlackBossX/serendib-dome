# ─────────────────────────────────────────────
#  Serendib Dome – Game Constants
#  All distances in kilometres, time in seconds
# ─────────────────────────────────────────────

# ── World ────────────────────────────────────
WORLD_RADIUS_KM   = 50.0   # radar max range / spawn boundary
MAX_ALTITUDE_KM   = 20.0   # ceiling for the simulation volume
GRAVITY_KM_S2     = 0.0098 # g in km/s²  (9.8 m/s²)

# ── Time ─────────────────────────────────────
SIM_TIME_SCALE    = 1.5    # sim seconds per real second (1 = real-time, 8 = fast)
TARGET_FPS        = 60

# ── Radar ─────────────────────────────────────
RADAR_RANGE_KM        = 50.0   # detection radius
RADAR_SWEEP_DEG_S     = 60.0   # degrees per sim-second  (6s per full rotation)
RADAR_BEAM_WIDTH_DEG  = 12.0   # azimuth beam width
RADAR_MIN_DETECTIONS  = 4      # minimum hits before prediction is attempted

# ── Missiles ─────────────────────────────────
MISSILE_SPEED_MIN_KM_S  = 1.0
MISSILE_SPEED_MAX_KM_S  = 2.5
MISSILE_SPAWN_INTERVAL  = 20.0  # real-seconds between new threat spawns
MAX_ACTIVE_MISSILES     = 3

# ── Interceptors ─────────────────────────────
INTERCEPTOR_SPEED_KM_S  = 4.0
INTERCEPTOR_KILL_DIST   = 1.2  # km – proximity kill radius
MAX_INTERCEPTORS        = 8    # total interceptors in the battery

# ── Colours (RGB) ────────────────────────────
C_BG            = (8,  14,  24)
C_GRID          = (20, 50,  40)
C_BASE          = (0,  220, 120)
C_RADAR_SWEEP   = (0,  255,  80)
C_RADAR_RING    = (0,  100,  50)
C_MISSILE       = (255, 60,  40)
C_MISSILE_TRAIL = (200, 80,  20)
C_INTERCEPTOR   = (60, 160, 255)
C_INTER_TRAIL   = (30, 80,  200)
C_PREDICTED     = (255, 220,  40)
C_IMPACT        = (255, 100,   0)
C_EXPLOSION     = (255, 160,  20)
C_TEXT          = (180, 220, 200)
C_TEXT_WARN     = (255, 120,  50)
C_PANEL_BG      = (10,  20,  16)

# ── Window ───────────────────────────────────
WIN_WIDTH   = 1440
WIN_HEIGHT  = 840
VIEW3D_W    = 840   # left 3-D viewport width
VIEW3D_H    = 840
RADAR_W     = 600   # right panel width
RADAR_H     = 600   # radar circle panel height
HUD_H       = WIN_HEIGHT - RADAR_H  # stats bar at bottom-right
