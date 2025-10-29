# I am adding comments for me to easily understand the codes

import pygame
import math
import random
from settings import *

# Buttons and UI screens (menu, level select, HUD, death, victory)
class Button:
    def __init__(self, x, y, w, h, text, color=BLUE, hover_color=CYAN, asset_manager=None):
        # Base size and position of the button
        self.base_rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        self.rect = self.base_rect.copy()  # This changes as we animate
        self.text = text  # Text shown on the button
        self.color = color  # Normal color
        self.hover_color = hover_color  # Color when hovered
        self.is_hovered = False  # True when mouse is over it
        self.asset_manager = asset_manager  # For button images
        # Animation values for hover scaling
        self.hover_scale = 1.0
        self.target_scale = 1.0
        self.pulse_timer = random.uniform(0, math.pi * 2)

    def update(self, mouse_pos):
        """Check if mouse is over the button and animate size a bit."""
        self.is_hovered = self.base_rect.collidepoint(mouse_pos)
        # Smoothly move scale towards the target
        self.target_scale = BUTTON_HOVER_SCALE if self.is_hovered else 1.0
        self.hover_scale += (self.target_scale - self.hover_scale) * 0.15
        # Resize the rect based on the scale
        w = int(self.base_rect.width * self.hover_scale)
        h = int(self.base_rect.height * self.hover_scale)
        self.rect = pygame.Rect(
            self.base_rect.centerx - w // 2,
            self.base_rect.centery - h // 2,
            w, h
        )
        self.pulse_timer += 0.05

    def draw(self, screen, font):
        """Draw the button with a shadow and text."""
        color = self.hover_color if self.is_hovered else self.color
        # Drop shadow for depth
        shadow_rect = self.rect.copy()
        shadow_rect.x += BUTTON_SHADOW_OFFSET
        shadow_rect.y += BUTTON_SHADOW_OFFSET
        pygame.draw.rect(screen, (20, 20, 20), shadow_rect, border_radius=8)
        # Use images if available, otherwise draw a simple rectangle
        if self.asset_manager and ('button_hover' if self.is_hovered else 'button_normal') in self.asset_manager.ui_images:
            btn_img = self.asset_manager.ui_images['button_hover' if self.is_hovered else 'button_normal']
            scaled_img = pygame.transform.scale(btn_img, (self.rect.width, self.rect.height))
            screen.blit(scaled_img, self.rect)
        else:
            pygame.draw.rect(screen, color, self.rect, border_radius=8)
            if self.is_hovered:
                pulse = abs(math.sin(self.pulse_timer))
                glow_surf = pygame.Surface((self.rect.w + 10, self.rect.h + 10), pygame.SRCALPHA)
                glow_alpha = int(80 * pulse)
                pygame.draw.rect(glow_surf, (*CYAN, glow_alpha), (0, 0, self.rect.w + 10, self.rect.h + 10), border_radius=10)
                screen.blit(glow_surf, (self.rect.x - 5, self.rect.y - 5))
            pygame.draw.rect(screen, WHITE, self.rect, 3, border_radius=8)
        # Text centered on the button
        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, event):
        """Return True when the left mouse button clicks this button."""
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered

class UIManager:
    def __init__(self, save_manager, level_count, asset_manager=None):
        # References to other systems
        self.save_manager = save_manager
        self.level_count = level_count
        self.asset_manager = asset_manager
        # Fonts for drawing text
        self.font_huge = pygame.font.Font(None, 100)
        self.font_large = pygame.font.Font(None, 72)
        self.font_med = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)
        # Animation helpers
        self.menu_timer = 0
        self.death_timer = 0
        self.victory_timer = 0
        # Floating particles in the main menu
        self.menu_particles = []
        self._init_menu_particles()
        # Particle lists used in overlays
        self.death_particles = []
        self.victory_particles = []
        # Create all the buttons now
        self._create_buttons()
    
    def _init_menu_particles(self):
        """Make random dots that float in the menu background."""
        for _ in range(MENU_PARTICLE_COUNT):
            self.menu_particles.append({
                'x': random.randint(0, SCREEN_WIDTH),
                'y': random.randint(0, SCREEN_HEIGHT),
                'vx': random.uniform(-20, 20),
                'vy': random.uniform(-30, 30),
                'size': random.randint(2, 4),
                'alpha': random.randint(50, 150)
            })

    def _create_buttons(self):
        """Create buttons for the main menu and level select grid."""
        center_x = SCREEN_WIDTH // 2
        self.menu_buttons = [
            Button(center_x, SCREEN_HEIGHT // 2 - 100, 250, 70, "PLAY", asset_manager=self.asset_manager),
            Button(center_x, SCREEN_HEIGHT // 2, 250, 70, "SETTINGS", asset_manager=self.asset_manager),
            Button(center_x, SCREEN_HEIGHT // 2 + 100, 250, 70, "EXIT", asset_manager=self.asset_manager),
        ]

        self.level_buttons = []
        rows, cols = 2, 5  # 10 buttons grid (2 rows x 5 columns)
        btn_w, btn_h = 160, 110
        spacing_x, spacing_y = 190, 150
        grid_w = (cols - 1) * spacing_x
        start_x = center_x - grid_w // 2
        start_y = SCREEN_HEIGHT // 2 - 100

        for i in range(self.level_count):
            row = i // cols
            col = i % cols
            x = start_x + col * spacing_x
            y = start_y + row * spacing_y
            self.level_buttons.append(Button(x, y, btn_w, btn_h, f"Level {i + 1}", asset_manager=self.asset_manager))

    def draw_menu(self, screen):
        """Draw the main menu with a pulsing title and floating dots."""
        screen.fill(DARK_PURPLE)
        # Move and draw the dots
        for particle in self.menu_particles:
            particle['x'] += particle['vx'] * 0.016
            particle['y'] += particle['vy'] * 0.016
            # Wrap to the other side when leaving the screen
            if particle['x'] < 0: particle['x'] = SCREEN_WIDTH
            if particle['x'] > SCREEN_WIDTH: particle['x'] = 0
            if particle['y'] < 0: particle['y'] = SCREEN_HEIGHT
            if particle['y'] > SCREEN_HEIGHT: particle['y'] = 0
            color = (*WHITE, particle['alpha'])
            surf = pygame.Surface((particle['size']*2, particle['size']*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (particle['size'], particle['size']), particle['size'])
            screen.blit(surf, (int(particle['x']), int(particle['y'])))
        
        # Title scales up and down slowly
        self.menu_timer += 0.05
        pulse = abs(math.sin(self.menu_timer * TITLE_PULSE_SPEED))
        title_scale = 1.0 + 0.05 * pulse
        title_text = "DON'T EVEN BOTHER"
        title_surf = self.font_huge.render(title_text, True, RED)
        title_w, title_h = title_surf.get_size()
        scaled_w, scaled_h = int(title_w * title_scale), int(title_h * title_scale)
        title_scaled = pygame.transform.scale(title_surf, (scaled_w, scaled_h))
        # Shadow behind the title
        title_shadow = self.font_huge.render(title_text, True, DARK_RED)
        title_shadow_scaled = pygame.transform.scale(title_shadow, (scaled_w, scaled_h))
        shadow_rect = title_shadow_scaled.get_rect(centerx=screen.get_width() // 2 + 5, y=155)
        screen.blit(title_shadow_scaled, shadow_rect)
        # Main title
        title_rect = title_scaled.get_rect(centerx=screen.get_width() // 2, y=150)
        screen.blit(title_scaled, title_rect)
        # Subtitle text
        subtitle = self.font_small.render("Pure Evil Edition - NO WARNINGS!", True, ORANGE)
        screen.blit(subtitle, subtitle.get_rect(centerx=screen.get_width() // 2, y=260))
        
        # Death counter
        deaths_y = screen.get_height() - 120
        if self.asset_manager and 'skull_icon' in self.asset_manager.ui_images:
            skull = self.asset_manager.ui_images['skull_icon']
            skull_rect = skull.get_rect(centerx=screen.get_width() // 2 - 120, centery=deaths_y + 15)
            screen.blit(skull, skull_rect)
        deaths = self.font_small.render(f"Total Deaths: {self.save_manager.data['total_deaths']}", True, RED)
        screen.blit(deaths, deaths.get_rect(centerx=screen.get_width() // 2, centery=deaths_y))
        # Small hint text
        hint = self.font_small.render("ESC = Menu | F11 = Fullscreen", True, GRAY)
        screen.blit(hint, hint.get_rect(centerx=screen.get_width() // 2, bottom=screen.get_height() - 60))
        # Draw the menu buttons
        for btn in self.menu_buttons:
            btn.draw(screen, self.font_med)

    def draw_level_select(self, screen):
        """Draw grid of level buttons and lock the ones not unlocked."""
        screen.fill(DARK_PURPLE)
        title = self.font_large.render("SELECT LEVEL", True, YELLOW)
        hint = self.font_small.render("ESC to go back", True, WHITE)
        screen.blit(title, title.get_rect(centerx=screen.get_width() // 2, y=100))
        screen.blit(hint, hint.get_rect(centerx=screen.get_width() // 2, bottom=screen.get_height() - 60))
        unlocked = min(self.save_manager.data["unlocked_level"], self.level_count)
        for i, btn in enumerate(self.level_buttons):
            if i + 1 <= unlocked:
                btn.draw(screen, self.font_med)
            else:
                pygame.draw.rect(screen, GRAY, btn.rect)
                pygame.draw.rect(screen, DARK_PURPLE, btn.rect, 3)
                lock_surf = self.font_med.render("LOCKED", True, DARK_PURPLE)
                screen.blit(lock_surf, lock_surf.get_rect(center=btn.rect.center))

    def draw_hud(self, screen, level):
        """Draw small info: deaths and level number while playing."""
        if self.asset_manager and 'skull_icon' in self.asset_manager.ui_images:
            skull = self.asset_manager.ui_images['skull_icon']
            skull_scaled = pygame.transform.scale(skull, (28, 28))
            screen.blit(skull_scaled, (15, 15))
            deaths_txt = self.font_small.render(f"{level.death_count}", True, RED)
            screen.blit(deaths_txt, (50, 20))
        else:
            deaths_txt = self.font_small.render(f"Deaths: {level.death_count}", True, RED)
            screen.blit(deaths_txt, (20, 20))
        level_txt = self.font_small.render(f"Level {level.num}", True, YELLOW)
        level_rect = level_txt.get_rect(right=GAME_WIDTH - 20, top=20)
        border_rect = level_rect.inflate(10, 10)
        pygame.draw.rect(screen, DARK_PURPLE, border_rect, border_radius=5)
        pygame.draw.rect(screen, YELLOW, border_rect, 2, border_radius=5)
        screen.blit(level_txt, level_rect)

    def draw_death_screen(self, screen, message):
        """Dark overlay, falling embers, big YOU DIED text, and a taunt."""
        vignette = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        center_x, center_y = screen.get_width() // 2, screen.get_height() // 2
        for r in range(max(screen.get_width(), screen.get_height()) // 2, 0, -20):
            alpha = int(150 * (1 - r / (max(screen.get_width(), screen.get_height()) // 2)))
            pygame.draw.circle(vignette, (*DARK_RED, alpha), (center_x, center_y), r)
        screen.blit(vignette, (0, 0))
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((80, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        if len(self.death_particles) < 30:
            for _ in range(30):
                self.death_particles.append({
                    'x': random.randint(0, screen.get_width()),
                    'y': -20,
                    'vy': random.uniform(50, 150),
                    'size': random.randint(3, 8),
                    'color': random.choice([RED, DARK_RED, ORANGE]),
                    'life': random.uniform(2, 4)
                })
        for particle in self.death_particles[:]:
            particle['y'] += particle['vy'] * 0.016
            particle['life'] -= 0.016
            if particle['y'] > screen.get_height() or particle['life'] <= 0:
                self.death_particles.remove(particle)
            else:
                alpha = int(255 * (particle['life'] / 4))
                surf = pygame.Surface((particle['size']*2, particle['size']*2), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*particle['color'], alpha), (particle['size'], particle['size']), particle['size'])
                screen.blit(surf, (int(particle['x']), int(particle['y'])))
        self.death_timer += 0.1
        shake_x = int(random.uniform(-3, 3) * abs(math.sin(self.death_timer * 5)))
        shake_y = int(random.uniform(-3, 3) * abs(math.sin(self.death_timer * 5)))
        pulse = 1.0 + 0.1 * abs(math.sin(self.death_timer * 2))
        msg_text = "YOU DIED"
        msg = self.font_huge.render(msg_text, True, RED)
        msg_w, msg_h = msg.get_size()
        msg_scaled = pygame.transform.scale(msg, (int(msg_w * pulse), int(msg_h * pulse)))
        msg_rect = msg_scaled.get_rect(centerx=screen.get_width() // 2 + shake_x, centery=screen.get_height() // 3 + shake_y)
        screen.blit(msg_scaled, msg_rect)
        taunt = self.font_large.render(message, True, ORANGE)
        screen.blit(taunt, taunt.get_rect(centerx=screen.get_width() // 2, centery=screen.get_height() // 2))
        hint = self.font_med.render("Press R to restart | ESC for menu", True, WHITE)
        screen.blit(hint, hint.get_rect(centerx=screen.get_width() // 2, centery=screen.get_height() // 2 + 120))

    def draw_victory_screen(self, screen, death_count):
        """Green overlay, confetti, big win text, stars, and continue hint."""
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 100, 0, 150))
        screen.blit(overlay, (0, 0))
        if len(self.victory_particles) < 100:
            for _ in range(100):
                self.victory_particles.append({
                    'x': random.randint(0, screen.get_width()),
                    'y': random.randint(-100, -20),
                    'vx': random.uniform(-50, 50),
                    'vy': random.uniform(100, 200),
                    'size': random.randint(4, 10),
                    'color': random.choice([GREEN, YELLOW, CYAN, WHITE]),
                    'rotation': random.uniform(0, 360),
                    'rot_speed': random.uniform(-5, 5)
                })
        for particle in self.victory_particles[:]:
            particle['x'] += particle['vx'] * 0.016
            particle['y'] += particle['vy'] * 0.016
            particle['rotation'] += particle['rot_speed']
            if particle['y'] > screen.get_height() + 20:
                self.victory_particles.remove(particle)
            else:
                surf = pygame.Surface((particle['size']*2, particle['size']*2), pygame.SRCALPHA)
                pygame.draw.rect(surf, particle['color'], (0, 0, particle['size'], particle['size']))
                rotated = pygame.transform.rotate(surf, particle['rotation'])
                rect = rotated.get_rect(center=(int(particle['x']), int(particle['y'])))
                screen.blit(rotated, rect)
        self.victory_timer += 0.08
        pulse = 1.0 + 0.08 * abs(math.sin(self.victory_timer * 2))
        win_text = "LEVEL COMPLETE!"
        win = self.font_huge.render(win_text, True, GREEN)
        win_w, win_h = win.get_size()
        win_scaled = pygame.transform.scale(win, (int(win_w * pulse), int(win_h * pulse)))
        win_rect = win_scaled.get_rect(centerx=screen.get_width() // 2, centery=screen.get_height() // 3)
        glow_alpha = int(100 * abs(math.sin(self.victory_timer * 3)))
        glow_surf = pygame.Surface((win_rect.w + 20, win_rect.h + 20), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*GREEN, glow_alpha), (0, 0, win_rect.w + 20, win_rect.h + 20))
        screen.blit(glow_surf, (win_rect.x - 10, win_rect.y - 10))
        screen.blit(win_scaled, win_rect)
        # Stars based on how many times you died
        stars = 3 if death_count == 0 else (2 if death_count < 5 else 1)
        star_y = screen.get_height() // 2 - 40
        star_spacing = 50
        star_start_x = screen.get_width() // 2 - (stars - 1) * star_spacing // 2
        for i in range(3):
            x = star_start_x + i * star_spacing
            color = YELLOW if i < stars else GRAY
            points = []
            for j in range(5):
                angle = math.radians(j * 72 - 90)
                radius = 15 if j % 2 == 0 else 7
                points.append((x + radius * math.cos(angle), star_y + radius * math.sin(angle)))
            pygame.draw.polygon(screen, color, points)
        deaths = self.font_large.render(f"Deaths: {death_count}", True, YELLOW)
        screen.blit(deaths, deaths.get_rect(centerx=screen.get_width() // 2, centery=screen.get_height() // 2 + 20))
        cont = self.font_med.render("Press SPACE to continue | ESC for menu", True, WHITE)
        screen.blit(cont, cont.get_rect(centerx=screen.get_width() // 2, centery=screen.get_height() // 2 + 120))
