# I am adding comments for me to easily understand the codes

import pygame
from settings import *

# This class controls the player: movement, jumping, and drawing
class Player:
    def __init__(self, x, y, asset_manager):
        self.width = PLAYER_WIDTH  # Player width in pixels
        self.height = PLAYER_HEIGHT  # Player height in pixels
        self.x = float(x)  # Current X position
        self.y = float(y)  # Current Y position
        self.vel_x = 0.0  # Horizontal speed
        self.vel_y = 0.0  # Vertical speed
        self.on_ground = False  # True if standing on a platform
        self.alive = True  # False when we die
        self.facing_right = True  # Which way the player faces
        self.asset_manager = asset_manager  # To get sprites

        # Animation state (idle, run, jump)
        self.state = 'idle'
        self.previous_state = 'idle'
        self.frame = 0  # Which frame we are on
        self.frame_timer = 0  # Timer to change animation frames
        self.state_change_cooldown = 0  # Small delay to avoid flicker
        self.animations = {}  # Stores frames for each state
        self._load_animations()  # Fill the animations dict
        
        # Death effect data
        self.death_timer = 0
        self.death_particles = []

    def _load_animations(self):
        """Load frames for idle, run, and jump if we have images."""
        if 'idle' in self.asset_manager.images and self.asset_manager.images['idle']:
            frames = self.asset_manager.extract_frames(self.asset_manager.images['idle'], 32, 32)
            if frames:
                self.animations['idle'] = frames
        
        if 'run' in self.asset_manager.images and self.asset_manager.images['run']:
            frames = self.asset_manager.extract_frames(self.asset_manager.images['run'], 32, 32)
            if frames:
                self.animations['run'] = frames
        
        if 'jump' in self.asset_manager.images and self.asset_manager.images['jump']:
            frames = self.asset_manager.extract_frames(self.asset_manager.images['jump'], 32, 32)
            if frames:
                self.animations['jump'] = frames

    def update(self, dt, keys, platforms):
        """Update player physics and animation each frame."""
        # If dead, only update the death particles
        if not self.alive:
            self.death_timer += dt
            self._update_death_particles(dt)
            return

        # Cooldown to prevent animation flickering
        if self.state_change_cooldown > 0:
            self.state_change_cooldown -= dt

        self._handle_movement(dt, keys)  # Read keyboard and set velocity
        self._apply_physics(dt)          # Apply gravity and move
        self._handle_collisions(platforms)  # Land on platforms or hit ceilings/walls
        self._update_animation(dt)       # Choose animation and advance frames

    def _handle_movement(self, dt, keys):
        """Change horizontal speed based on left/right keys."""
        move_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        move_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]

        if move_left:
            self.vel_x -= ACCELERATION * dt
            self.facing_right = False
        elif move_right:
            self.vel_x += ACCELERATION * dt
            self.facing_right = True
        else:
            # No input: slow down until we stop
            if self.vel_x > 0:
                self.vel_x = max(0, self.vel_x - DECELERATION * dt)
            elif self.vel_x < 0:
                self.vel_x = min(0, self.vel_x + DECELERATION * dt)

        # Clamp speed so we don't go too fast
        self.vel_x = max(-PLAYER_SPEED, min(PLAYER_SPEED, self.vel_x))

    def _apply_physics(self, dt):
        """Apply gravity and update position."""
        self.vel_y += GRAVITY * dt  # Fall speed increases over time
        self.vel_y = min(self.vel_y, 1000)  # Limit fall speed
        self.x += self.vel_x * dt  # Move horizontally
        self.y += self.vel_y * dt  # Move vertically

    def _handle_collisions(self, platforms):
        """Stop the player when hitting platforms (ground or walls)."""
        self.on_ground = False
        player_rect = self.get_rect()

        for plat in platforms:
            if player_rect.colliderect(plat):
                # Landing on top of a platform
                if self.vel_y > 0 and player_rect.bottom > plat.top and player_rect.bottom < plat.top + 25:
                    self.y = float(plat.top - self.height)
                    self.vel_y = 0
                    self.on_ground = True
                # Hitting the bottom of a platform
                elif self.vel_y < 0 and player_rect.top < plat.bottom:
                    self.y = float(plat.bottom)
                    self.vel_y = 0

                # Update rect and resolve side collisions
                player_rect = self.get_rect()
                if player_rect.colliderect(plat):
                    if self.vel_x > 0:
                        self.x = float(plat.left - self.width)
                    elif self.vel_x < 0:
                        self.x = float(plat.right)
                    self.vel_x = 0

    def _update_animation(self, dt):
        """Pick the right animation and advance the frame timer."""
        old_state = self.state
        new_state = self.state

        # Jump has highest priority, then run, else idle
        if not self.on_ground:
            new_state = 'jump'
        elif abs(self.vel_x) > 15:
            new_state = 'run'
        else:
            new_state = 'idle'

        # Only switch if the cooldown is over
        if new_state != old_state and self.state_change_cooldown <= 0:
            self.state = new_state
            self.previous_state = old_state
            self.frame = 0
            self.frame_timer = 0
            self.state_change_cooldown = 0.05  # Wait a tiny bit before switching again

        # Advance frames over time
        self.frame_timer += dt
        frame_duration = 0.08 if self.state == 'run' else 0.1
        if self.frame_timer >= frame_duration:
            self.frame_timer -= frame_duration
            if self.state in self.animations and self.animations[self.state]:
                self.frame = (self.frame + 1) % len(self.animations[self.state])
    
    def _update_death_particles(self, dt):
        """Move death particles down and remove them when they fade."""
        for particle in self.death_particles[:]:
            particle['x'] += particle['vx'] * dt
            particle['y'] += particle['vy'] * dt
            particle['vy'] += 500 * dt  # Gravity pulls them down
            particle['life'] -= dt
            if particle['life'] <= 0:
                self.death_particles.remove(particle)

    def jump(self):
        """Jump only if we are standing on the ground."""
        if self.on_ground and self.alive:
            self.vel_y = JUMP_FORCE

    def die(self):
        """Set dead state and create some particles for feedback."""
        self.alive = False
        self.death_timer = 0
        
        import random
        for _ in range(20):
            angle = random.uniform(0, 6.28)
            speed = random.uniform(100, 300)
            self.death_particles.append({
                'x': self.x + self.width / 2,
                'y': self.y + self.height / 2,
                'vx': speed * pygame.math.Vector2(1, 0).rotate_rad(angle).x,
                'vy': speed * pygame.math.Vector2(1, 0).rotate_rad(angle).y - 200,
                'life': random.uniform(0.5, 1.0),
                'color': random.choice([RED, ORANGE, YELLOW])
            })

    def reset(self, x, y):
        """Bring the player back to the spawn point and clear effects."""
        self.x = float(x)
        self.y = float(y)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.alive = True
        self.frame = 0
        self.frame_timer = 0
        self.state = 'idle'
        self.previous_state = 'idle'
        self.state_change_cooldown = 0
        self.death_timer = 0
        self.death_particles = []

    def get_rect(self):
        """Get the rectangle for collisions and drawing."""
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def draw(self, screen, camera_x):
        """Draw the player or the death particles if dead."""
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y)

        # When dead, draw the particles and stop
        if not self.alive:
            for particle in self.death_particles:
                px = int(particle['x'] - camera_x)
                py = int(particle['y'])
                size = max(2, int(4 * (particle['life'] / 1.0)))
                pygame.draw.circle(screen, particle['color'], (px, py), size)
            return

        # Try to draw from animation frames if available
        if self.state in self.animations and self.animations[self.state] and len(self.animations[self.state]) > 0:
            frame_idx = min(self.frame, len(self.animations[self.state]) - 1)
            current_frame = self.animations[self.state][frame_idx]
            if not self.facing_right:
                current_frame = pygame.transform.flip(current_frame, True, False)
            screen.blit(current_frame, (screen_x, screen_y))
        else:
            # Draw a simple green box if no sprites are loaded
            pygame.draw.rect(screen, GREEN, (screen_x, screen_y, self.width, self.height))
            pygame.draw.rect(screen, DARK_GREEN, (screen_x, screen_y, self.width, self.height), 2)
            eye_color = WHITE
            pygame.draw.circle(screen, eye_color, (screen_x + 10, screen_y + 10), 3)
            pygame.draw.circle(screen, eye_color, (screen_x + 22, screen_y + 10), 3)
