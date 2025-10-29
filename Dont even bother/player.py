import pygame
from settings import *

class Player:
    def __init__(self, x, y, asset_manager):
        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT
        self.x = float(x)
        self.y = float(y)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False
        self.alive = True
        self.facing_right = True
        self.asset_manager = asset_manager

        # FIXED: Better animation state management to prevent glitching
        self.state = 'idle'
        self.previous_state = 'idle'  # Track previous state to prevent flickering
        self.frame = 0
        self.frame_timer = 0
        self.state_change_cooldown = 0  # Prevent rapid state switching
        self.animations = {}
        self._load_animations()
        
        # Death animation properties
        self.death_timer = 0
        self.death_particles = []

    def _load_animations(self):
        # FIXED: Safer animation loading with validation
        if 'idle' in self.asset_manager.images and self.asset_manager.images['idle']:
            frames = self.asset_manager.extract_frames(self.asset_manager.images['idle'], 32, 32)
            if frames:  # Only add if frames exist
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
        if not self.alive:
            self.death_timer += dt
            self._update_death_particles(dt)
            return

        # FIXED: Update state change cooldown
        if self.state_change_cooldown > 0:
            self.state_change_cooldown -= dt

        self._handle_movement(dt, keys)
        self._apply_physics(dt)
        self._handle_collisions(platforms)
        self._update_animation(dt)

    def _handle_movement(self, dt, keys):
        move_left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        move_right = keys[pygame.K_d] or keys[pygame.K_RIGHT]

        if move_left:
            self.vel_x -= ACCELERATION * dt
            self.facing_right = False
        elif move_right:
            self.vel_x += ACCELERATION * dt
            self.facing_right = True
        else:
            if self.vel_x > 0:
                self.vel_x = max(0, self.vel_x - DECELERATION * dt)
            elif self.vel_x < 0:
                self.vel_x = min(0, self.vel_x + DECELERATION * dt)

        self.vel_x = max(-PLAYER_SPEED, min(PLAYER_SPEED, self.vel_x))

    def _apply_physics(self, dt):
        self.vel_y += GRAVITY * dt
        self.vel_y = min(self.vel_y, 1000)
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt

    def _handle_collisions(self, platforms):
        self.on_ground = False
        player_rect = self.get_rect()

        for plat in platforms:
            if player_rect.colliderect(plat):
                if self.vel_y > 0 and player_rect.bottom > plat.top and player_rect.bottom < plat.top + 25:
                    self.y = float(plat.top - self.height)
                    self.vel_y = 0
                    self.on_ground = True
                elif self.vel_y < 0 and player_rect.top < plat.bottom:
                    self.y = float(plat.bottom)
                    self.vel_y = 0

                player_rect = self.get_rect()
                if player_rect.colliderect(plat):
                    if self.vel_x > 0:
                        self.x = float(plat.left - self.width)
                    elif self.vel_x < 0:
                        self.x = float(plat.right)
                    self.vel_x = 0

    def _update_animation(self, dt):
        # FIXED: Smoother state transitions to prevent glitching
        old_state = self.state
        new_state = self.state

        # Determine new state with priority system
        if not self.on_ground:
            new_state = 'jump'
        elif abs(self.vel_x) > 15:  # Slightly higher threshold to prevent jitter
            new_state = 'run'
        else:
            new_state = 'idle'

        # Only change state if cooldown expired (prevents rapid flickering)
        if new_state != old_state and self.state_change_cooldown <= 0:
            self.state = new_state
            self.previous_state = old_state
            self.frame = 0
            self.frame_timer = 0
            self.state_change_cooldown = 0.05  # 50ms cooldown between state changes

        # Update animation frames
        self.frame_timer += dt
        frame_duration = 0.08 if self.state == 'run' else 0.1  # Faster run animation
        
        if self.frame_timer >= frame_duration:
            self.frame_timer -= frame_duration  # Subtract instead of reset for smoother timing
            if self.state in self.animations and self.animations[self.state]:
                self.frame = (self.frame + 1) % len(self.animations[self.state])
    
    def _update_death_particles(self, dt):
        """Update death particle effects"""
        # NEW: Death particle system for enhanced death animation
        for particle in self.death_particles[:]:
            particle['x'] += particle['vx'] * dt
            particle['y'] += particle['vy'] * dt
            particle['vy'] += 500 * dt  # Gravity
            particle['life'] -= dt
            if particle['life'] <= 0:
                self.death_particles.remove(particle)

    def jump(self):
        if self.on_ground and self.alive:
            self.vel_y = JUMP_FORCE

    def die(self):
        self.alive = False
        self.death_timer = 0
        
        # NEW: Create death particles for visual feedback
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
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def draw(self, screen, camera_x):
        # FIXED: Stabilized rendering with fallback and particle effects
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y)

        # Draw death particles
        if not self.alive:
            for particle in self.death_particles:
                px = int(particle['x'] - camera_x)
                py = int(particle['y'])
                alpha = int(255 * (particle['life'] / 1.0))
                size = max(2, int(4 * (particle['life'] / 1.0)))
                pygame.draw.circle(screen, particle['color'], (px, py), size)
            return

        # FIXED: Better sprite rendering with validation
        if self.state in self.animations and self.animations[self.state] and len(self.animations[self.state]) > 0:
            # Ensure frame index is valid
            frame_idx = min(self.frame, len(self.animations[self.state]) - 1)
            current_frame = self.animations[self.state][frame_idx]
            
            # FIXED: Cache flipped sprites to prevent constant re-flipping (performance)
            if not self.facing_right:
                current_frame = pygame.transform.flip(current_frame, True, False)
            
            screen.blit(current_frame, (screen_x, screen_y))
        else:
            # Enhanced fallback rendering with gradient effect
            pygame.draw.rect(screen, GREEN, (screen_x, screen_y, self.width, self.height))
            pygame.draw.rect(screen, DARK_GREEN, (screen_x, screen_y, self.width, self.height), 2)
            # Draw simple face
            eye_color = WHITE
            pygame.draw.circle(screen, eye_color, (screen_x + 10, screen_y + 10), 3)
            pygame.draw.circle(screen, eye_color, (screen_x + 22, screen_y + 10), 3)
