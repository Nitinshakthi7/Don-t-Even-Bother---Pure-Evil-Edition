import pygame
import os
import math
from settings import ASSETS_PATH, RED, DARK_RED, GRAY, GREEN, DARK_GREEN, WHITE, BLACK, CYAN, DARK_BLUE, DARK_PURPLE, YELLOW, ORANGE

class AssetManager:
    def __init__(self):
        self.images = {}
        self.ui_images = {}
        self._load_assets()
        self._generate_fallback_assets()  # NEW: Generate programmatic assets if files missing

    def _load_assets(self):
        """Load all game assets from files"""
        try:
            # Player sprites - try new folder structure first
            idle_paths = [
                os.path.join(ASSETS_PATH, 'player', 'Idle.png'),
                os.path.join(ASSETS_PATH, 'Idle.png')
            ]
            for idle_path in idle_paths:
                if os.path.exists(idle_path):
                    self.images['idle'] = pygame.image.load(idle_path).convert_alpha()
                    break

            run_paths = [
                os.path.join(ASSETS_PATH, 'player', 'Run.png'),
                os.path.join(ASSETS_PATH, 'Run.png')
            ]
            for run_path in run_paths:
                if os.path.exists(run_path):
                    self.images['run'] = pygame.image.load(run_path).convert_alpha()
                    break

            jump_paths = [
                os.path.join(ASSETS_PATH, 'player', 'Jump.png'),
                os.path.join(ASSETS_PATH, 'Jump.png')
            ]
            for jump_path in jump_paths:
                if os.path.exists(jump_path):
                    self.images['jump'] = pygame.image.load(jump_path).convert_alpha()
                    break

            # NEW: Load trap sprites
            spike_path = os.path.join(ASSETS_PATH, 'traps', 'spike.png')
            if os.path.exists(spike_path):
                self.images['spike'] = pygame.image.load(spike_path).convert_alpha()

            saw_path = os.path.join(ASSETS_PATH, 'traps', 'saw.png')
            if os.path.exists(saw_path):
                self.images['saw'] = pygame.image.load(saw_path).convert_alpha()

            # NEW: Load goal sprite
            goal_path = os.path.join(ASSETS_PATH, 'goal', 'goal_flag.png')
            if os.path.exists(goal_path):
                self.images['goal'] = pygame.image.load(goal_path).convert_alpha()

            # Background
            bg_path = os.path.join(ASSETS_PATH, 'background', 'background.png')
            if os.path.exists(bg_path):
                self.images['background'] = pygame.image.load(bg_path).convert()
            
            # NEW: Parallax layers
            bg_layer1_path = os.path.join(ASSETS_PATH, 'background', 'bg_layer1.png')
            if os.path.exists(bg_layer1_path):
                self.images['bg_layer1'] = pygame.image.load(bg_layer1_path).convert_alpha()
            
            bg_layer2_path = os.path.join(ASSETS_PATH, 'background', 'bg_layer2.png')
            if os.path.exists(bg_layer2_path):
                self.images['bg_layer2'] = pygame.image.load(bg_layer2_path).convert_alpha()

            # NEW: UI elements
            button_normal_path = os.path.join(ASSETS_PATH, 'ui', 'button_normal.png')
            if os.path.exists(button_normal_path):
                self.ui_images['button_normal'] = pygame.image.load(button_normal_path).convert_alpha()
            
            button_hover_path = os.path.join(ASSETS_PATH, 'ui', 'button_hover.png')
            if os.path.exists(button_hover_path):
                self.ui_images['button_hover'] = pygame.image.load(button_hover_path).convert_alpha()
            
            skull_icon_path = os.path.join(ASSETS_PATH, 'ui', 'skull_icon.png')
            if os.path.exists(skull_icon_path):
                self.ui_images['skull_icon'] = pygame.image.load(skull_icon_path).convert_alpha()

        except pygame.error as e:
            print(f"Error loading assets: {e}")


    def _generate_fallback_assets(self):
        """NEW: Generate programmatic assets when files are missing"""
        
        # Generate spike sprite if missing
        if 'spike' not in self.images:
            spike_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
            points = [(8, 0), (0, 16), (16, 16)]  # Triangle
            pygame.draw.polygon(spike_surf, RED, points)
            pygame.draw.polygon(spike_surf, DARK_RED, points, 2)
            self.images['spike'] = spike_surf
        
        # Generate saw sprite if missing
        if 'saw' not in self.images:
            saw_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            center = (20, 20)
            # Draw saw blade with teeth
            pygame.draw.circle(saw_surf, GRAY, center, 19)
            pygame.draw.circle(saw_surf, (80, 80, 80), center, 8)
            # Draw teeth
            for i in range(8):
                angle = math.radians(i * 45)
                outer_x = center[0] + math.cos(angle) * 19
                outer_y = center[1] + math.sin(angle) * 19
                tooth_x = center[0] + math.cos(angle) * 21
                tooth_y = center[1] + math.sin(angle) * 21
                pygame.draw.circle(saw_surf, RED, (int(tooth_x), int(tooth_y)), 4)
            self.images['saw'] = saw_surf
        
        # Generate goal flag sprite if missing
        if 'goal' not in self.images:
            goal_surf = pygame.Surface((40, 50), pygame.SRCALPHA)
            # Pole
            pygame.draw.rect(goal_surf, GRAY, (10, 0, 3, 50))
            # Flag
            flag_points = [(13, 5), (35, 12), (13, 20)]
            pygame.draw.polygon(goal_surf, GREEN, flag_points)
            pygame.draw.polygon(goal_surf, DARK_GREEN, flag_points, 2)
            self.images['goal'] = goal_surf
        
        # Generate enhanced background if missing
        if 'background' not in self.images:
            bg_surf = pygame.Surface((800, 600))
            # Gradient from dark purple to dark blue
            for y in range(600):
                ratio = y / 600
                r = int(DARK_PURPLE[0] + (DARK_BLUE[0] - DARK_PURPLE[0]) * ratio)
                g = int(DARK_PURPLE[1] + (DARK_BLUE[1] - DARK_PURPLE[1]) * ratio)
                b = int(DARK_PURPLE[2] + (DARK_BLUE[2] - DARK_PURPLE[2]) * ratio)
                pygame.draw.line(bg_surf, (r, g, b), (0, y), (800, y))
            
            # Add some stars/dots for atmosphere
            import random
            random.seed(42)  # Consistent pattern
            for _ in range(100):
                x = random.randint(0, 800)
                y = random.randint(0, 400)
                size = random.randint(1, 2)
                brightness = random.randint(100, 255)
                pygame.draw.circle(bg_surf, (brightness, brightness, brightness), (x, y), size)
            
            self.images['background'] = bg_surf
        
        # Generate UI button sprites if missing
        if 'button_normal' not in self.ui_images:
            btn_surf = pygame.Surface((250, 70), pygame.SRCALPHA)
            pygame.draw.rect(btn_surf, (*DARK_BLUE, 200), (0, 0, 250, 70), border_radius=8)
            pygame.draw.rect(btn_surf, CYAN, (0, 0, 250, 70), 3, border_radius=8)
            self.ui_images['button_normal'] = btn_surf
        
        if 'button_hover' not in self.ui_images:
            btn_hover_surf = pygame.Surface((250, 70), pygame.SRCALPHA)
            pygame.draw.rect(btn_hover_surf, (*CYAN, 50), (-2, -2, 254, 74), border_radius=8)  # Glow
            pygame.draw.rect(btn_hover_surf, (*DARK_BLUE, 220), (0, 0, 250, 70), border_radius=8)
            pygame.draw.rect(btn_hover_surf, CYAN, (0, 0, 250, 70), 4, border_radius=8)
            self.ui_images['button_hover'] = btn_hover_surf
        
        # Generate skull icon for death counter
        if 'skull_icon' not in self.ui_images:
            skull_surf = pygame.Surface((32, 32), pygame.SRCALPHA)
            # Simple skull shape
            pygame.draw.circle(skull_surf, WHITE, (16, 14), 10)  # Head
            pygame.draw.rect(skull_surf, WHITE, (10, 20, 12, 8))  # Jaw
            pygame.draw.circle(skull_surf, BLACK, (12, 12), 3)  # Left eye
            pygame.draw.circle(skull_surf, BLACK, (20, 12), 3)  # Right eye
            pygame.draw.circle(skull_surf, BLACK, (16, 18), 2)  # Nose
            self.ui_images['skull_icon'] = skull_surf

    def extract_frames(self, image, frame_w, frame_h):
        """Extract animation frames from spritesheet"""
        frames = []
        if not image:
            return frames
        sheet_w, sheet_h = image.get_size()
        for y in range(0, sheet_h, frame_h):
            for x in range(0, sheet_w, frame_w):
                if x + frame_w <= sheet_w and y + frame_h <= sheet_h:
                    frame = image.subsurface(pygame.Rect(x, y, frame_w, frame_h))
                    frames.append(frame)
        return frames
