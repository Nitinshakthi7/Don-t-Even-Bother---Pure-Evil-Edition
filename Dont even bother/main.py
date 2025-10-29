# I am adding comments for me to easily understand the codes

import pygame
import random
from settings import *
from assets import AssetManager
from utils import SaveManager, Camera
from player import Player
from levels import LevelFactory
from ui import UIManager

# This file sets up the game loop and switches between menus and levels
class Game:
    def __init__(self):
        # Set up pygame and window
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        # Core game state flags
        self.is_running = True
        self.is_fullscreen = True
        self.state = 'menu'  # Can be: menu, level_select, playing, death, victory

        # Load helpers and content
        self.asset_manager = AssetManager()
        self.save_manager = SaveManager()
        self.levels = LevelFactory.create_all_levels(self.asset_manager)
        self.ui_manager = UIManager(self.save_manager, len(self.levels), self.asset_manager)

        # Off-screen surface that we scale to the window size
        self.game_surface = pygame.Surface((GAME_WIDTH, GAME_HEIGHT))
        # These get filled when a level starts
        self.player = None
        self.camera = None
        self.current_level = None
        # Death/victory UI helpers
        self.current_death_message = ""
        self.death_flash_timer = 0
        self.death_flash_active = False

    def run(self):
        """Main game loop: process input, update, then draw every frame."""
        while self.is_running:
            dt = self.clock.tick(FPS) / 1000.0  # Delta time in seconds
            self._handle_events()
            self._update(dt)
            self._draw()
        pygame.quit()

    def _handle_events(self):
        """Handle keyboard and mouse events based on current state."""
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11: self._toggle_fullscreen()
                if event.key == pygame.K_ESCAPE: self.state = 'menu'

            # Menu buttons (PLAY / SETTINGS / EXIT)
            if self.state == 'menu':
                for btn in self.ui_manager.menu_buttons:
                    btn.update(mouse_pos)
                    if btn.is_clicked(event):
                        if btn.text == "PLAY":
                            self.state = 'level_select'
                            # Clear click so it doesn't also trigger a level button
                            pygame.event.clear(pygame.MOUSEBUTTONDOWN)
                            return
                        elif btn.text == "EXIT":
                            self.is_running = False

            # Level select buttons (only up to unlocked)
            if self.state == 'level_select':
                unlocked = min(self.save_manager.data["unlocked_level"], len(self.levels))
                for i, btn in enumerate(self.ui_manager.level_buttons):
                    btn.update(mouse_pos)
                    if i + 1 <= unlocked and btn.is_clicked(event):
                        self._start_level(i + 1)

            # Restart after death
            if self.state == 'death' and event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                self._reset_level()
            
            # Continue after victory
            if self.state == 'victory' and (event.type == pygame.KEYDOWN and 
                 event.key in [pygame.K_RETURN, pygame.K_SPACE]):
                next_level_num = self.current_level.num + 1
                if next_level_num <= len(self.levels):
                    self.save_manager.unlock_level(next_level_num)
                    self._start_level(next_level_num)
                else:
                    self.state = 'menu'

    def _update(self, dt):
        """Update the current game state (player, traps, camera)."""
        # Fade out the death flash
        if self.death_flash_active:
            self.death_flash_timer -= dt
            if self.death_flash_timer <= 0:
                self.death_flash_active = False
        
        if self.state == 'playing':
            keys = pygame.key.get_pressed()

            # Jump with W / Up / Space
            if keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]:
                self.player.jump()

            # Update game objects
            self.player.update(dt, keys, self.current_level.get_all_platforms())
            self.current_level.update(dt, self.player)
            self.camera.update(self.player.x, dt)

            # Check traps and falling out of the world
            for trap in self.current_level.traps:
                if trap.check_collision(self.player):
                    self._player_die(); return
            
            if self.player.y > GAME_HEIGHT + 100:
                self._player_die(); return

            # Check if we reached the real goal
            if self.current_level.goal.check_collision(self.player):
                self.state = 'victory'

    def _draw(self):
        """Draw the current screen (menu, level select, or gameplay)."""
        if self.state == 'menu':
            self.ui_manager.draw_menu(self.screen)
        elif self.state == 'level_select':
            self.ui_manager.draw_level_select(self.screen)
        elif self.state in ['playing', 'death', 'victory']:
            self.game_surface.fill(DARK_BLUE)

            # Draw background (with optional parallax layers)
            bg_image = self.asset_manager.images.get('background')
            if bg_image:
                bg_width = bg_image.get_width()
                camera_x_offset = self.camera.get_x() % bg_width
                for i in range(-1, (GAME_WIDTH // bg_width) + 2):
                    self.game_surface.blit(bg_image, (i * bg_width - camera_x_offset, 0))
            
            bg_layer1 = self.asset_manager.images.get('bg_layer1')
            if bg_layer1:
                layer1_offset = (self.camera.get_x() * 0.5) % bg_layer1.get_width()
                for i in range(-1, (GAME_WIDTH // bg_layer1.get_width()) + 2):
                    self.game_surface.blit(bg_layer1, (i * bg_layer1.get_width() - layer1_offset, 0))
            
            bg_layer2 = self.asset_manager.images.get('bg_layer2')
            if bg_layer2:
                layer2_offset = (self.camera.get_x() * 0.2) % bg_layer2.get_width()
                for i in range(-1, (GAME_WIDTH // bg_layer2.get_width()) + 2):
                    self.game_surface.blit(bg_layer2, (i * bg_layer2.get_width() - layer2_offset, 0))

            # Draw level and player using camera offset
            camera_x = self.camera.get_x()
            self.current_level.draw(self.game_surface, camera_x)
            self.player.draw(self.game_surface, camera_x)
            self.ui_manager.draw_hud(self.game_surface, self.current_level)
            
            # Red flash on death
            if self.death_flash_active:
                flash_alpha = int(255 * (self.death_flash_timer / DEATH_FLASH_DURATION))
                flash_surf = pygame.Surface(self.game_surface.get_size(), pygame.SRCALPHA)
                flash_surf.fill((*DEATH_FLASH_COLOR[:3], min(flash_alpha, DEATH_FLASH_COLOR[3])))
                self.game_surface.blit(flash_surf, (0, 0))
            
            # Scale the game surface up to the window size
            scaled_surface = pygame.transform.scale(self.game_surface, self.screen.get_size())
            self.screen.blit(scaled_surface, (0, 0))
            
            # Draw overlays for death or victory
            if self.state == 'death':
                self.ui_manager.draw_death_screen(self.screen, self.current_death_message)
            elif self.state == 'victory':
                self.ui_manager.draw_victory_screen(self.screen, self.current_level.death_count)
        pygame.display.flip()

    def _start_level(self, level_num):
        """Load a level and spawn the player."""
        if 1 <= level_num <= len(self.levels):
            self.current_level = self.levels[level_num - 1]
            self.current_level.death_count = 0
            self.current_level.reset()
            spawn_x, spawn_y = self.current_level.spawn
            self.player = Player(spawn_x, spawn_y, self.asset_manager)
            self.camera = Camera(self.current_level.width)
            self.state = 'playing'

    def _reset_level(self):
        """Restart the current level from the spawn point."""
        if self.current_level:
            spawn_x, spawn_y = self.current_level.spawn
            self.player.reset(spawn_x, spawn_y)
            self.current_level.reset()
            self.state = 'playing'

    def _player_die(self):
        """Handle everything that happens when the player dies."""
        self.player.die()
        self.camera.shake(intensity=SCREEN_SHAKE_INTENSITY, duration=SCREEN_SHAKE_DURATION)
        self.current_death_message = random.choice(DEATH_MESSAGES)
        self.current_level.death_count += 1
        self.save_manager.add_death()
        self.death_flash_active = True
        self.death_flash_timer = DEATH_FLASH_DURATION
        self.state = 'death'

    def _toggle_fullscreen(self):
        """Switch between fullscreen and windowed mode."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)

if __name__ == "__main__":
    game = Game()
    game.run()
