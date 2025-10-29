# I am adding comments for me to easily understand the codes

import pygame
import os

# Get the screen size from the user's display
try:
    pygame.init()
    display_info = pygame.display.Info()
    SCREEN_WIDTH = display_info.current_w  # Full screen width
    SCREEN_HEIGHT = display_info.current_h  # Full screen height
except pygame.error:
    # If pygame fails, use default HD resolution
    SCREEN_WIDTH = 1920
    SCREEN_HEIGHT = 1080

# Game window size (smaller than screen for scaling)
GAME_WIDTH = 800
GAME_HEIGHT = 600

# Basic game settings
FPS = 60  # Frames per second
TITLE = "Don't Even Bother - PURE EVIL"  # Game window title

# File paths for loading game assets
BASE_PATH = os.path.dirname(os.path.abspath(__file__))  # Current folder
ASSETS_PATH = os.path.join(BASE_PATH, "assets")  # Assets folder path

# Color definitions using RGB values (Red, Green, Blue)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (220, 20, 60)
DARK_RED = (80, 0, 0)
GREEN = (50, 205, 50)
DARK_GREEN = (0, 100, 0)
BLUE = (70, 130, 255)
DARK_BLUE = (10, 20, 40)
PURPLE = (138, 43, 226)
DARK_PURPLE = (25, 10, 35)
YELLOW = (255, 215, 0)
ORANGE = (255, 140, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (192, 192, 192)
CYAN = (0, 255, 255)
PINK = (255, 105, 180)

# Player movement and physics settings
GRAVITY = 2500  # How fast player falls down
PLAYER_SPEED = 300  # Maximum speed player can move
JUMP_FORCE = -650  # How strong the jump is (negative = upward)
ACCELERATION = 3000  # How fast player speeds up
DECELERATION = 2200  # How fast player slows down

# Player character size in pixels
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 32

# Trap difficulty settings
FAKE_PLATFORM_DELAY_MIN = 0.2  # Minimum time before fake platform breaks
FAKE_PLATFORM_DELAY_MAX = 0.6  # Maximum time before fake platform breaks
SAW_SPEED_MULTIPLIER = 1.0  # How fast saws move (1.0 = normal speed)
INVISIBLE_SPIKE_REVEAL_DISTANCE = 60  # How close player must be to see spikes
NARROW_GAP_MIN_HEIGHT = 30  # Smallest gap height player can fit through

# Particle effects settings (for visual flair)
PARTICLE_LIFETIME_MIN = 0.3  # How long particles last (minimum)
PARTICLE_LIFETIME_MAX = 1.2  # How long particles last (maximum)
PARTICLE_COUNT_DEATH = 25  # Number of particles when player dies
PARTICLE_COUNT_TRAP = 15  # Number of particles for trap effects
PARTICLE_COUNT_PLATFORM_CRUMBLE = 30  # Particles when platform breaks
PARTICLE_GRAVITY = 600  # How fast particles fall

# Visual effects for dramatic moments
SCREEN_SHAKE_INTENSITY = 15  # How violent the screen shake is
SCREEN_SHAKE_DURATION = 0.4  # How long screen shakes
DEATH_FLASH_DURATION = 0.15  # Red flash duration when dying
DEATH_FLASH_COLOR = (180, 0, 0, 100)  # Red color with transparency
CAMERA_SMOOTHNESS = 12  # How smoothly camera follows player

# Menu and UI animation settings
BUTTON_HOVER_SCALE = 1.08  # How much buttons grow when hovered
BUTTON_PRESS_SCALE = 0.95  # How much buttons shrink when clicked
BUTTON_SHADOW_OFFSET = 5  # Shadow distance for buttons
TITLE_PULSE_SPEED = 2.0  # How fast title pulses
MENU_PARTICLE_COUNT = 50  # Floating particles in menu

# Mean messages shown when player dies
DEATH_MESSAGES = [
    "Did you even try?", "My grandma is better", "Just quit already", "Pathetic",
    "Are you even trying?", "LOL", "Git gud scrub", "Skill issue detected",
    "Delete the game", "Imagine dying here", "You're embarrassing",
    "Try using your hands", "Is this your first game?", "Literally how", "Yikes...",
    "Maybe try an easier game", "This is sad to watch", "Your parents are disappointed",
    "Brain not found. Respawn instead.", "Even the tutorial NPCs do better.",
    "Pro tip: Try not dying next time.", "Was that your strategy, or a cry for help?",
    "You make losing look effortless!", "Achievement unlocked: Instant Regret.",
    "Respawning... because we both know you'll die again.",
    "A rock could do better", "Uninstall. Now.", "Your keyboard deserves better",
    "Frame-perfect fail", "Trash gameplay detected", "Stop embarrassing yourself",
    "This is why you have no friends", "My cat plays better blindfolded",
    "Actual skill: 0", "Are you trolling yourself?", "Peak incompetence achieved"
]
