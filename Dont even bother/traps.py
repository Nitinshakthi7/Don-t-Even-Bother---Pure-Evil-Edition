# I am adding comments for me to easily understand the codes

import pygame
import random
import math
from abc import ABC, abstractmethod
from settings import *

# Particles are tiny circles used for simple effects like sparks
class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=3):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life  # How long the particle stays alive
        self.max_life = life
        self.size = size
    
    def update(self, dt):
        # Move the particle and make it fall a bit
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += PARTICLE_GRAVITY * dt
        self.life -= dt
        return self.life > 0  # Return False when it should be removed
    
    def draw(self, screen, camera_x):
        if self.life > 0:
            alpha_ratio = self.life / self.max_life
            size = max(1, int(self.size * alpha_ratio))
            screen_x = int(self.x - camera_x)
            screen_y = int(self.y)
            pygame.draw.circle(screen, self.color, (screen_x, screen_y), size)

# A Trap is any object that can hurt or trick the player
class Trap(ABC):
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)  # Where the trap is
        self.active = True  # Some traps can turn off
        self.particles = []  # Each trap can spawn particles

    @abstractmethod
    def update(self, dt, player): pass
    @abstractmethod
    def draw(self, screen, camera_x): pass
    @abstractmethod
    def reset(self): pass
    
    def check_collision(self, player):
        """Check if the player touches this trap."""
        return self.active and self.rect.colliderect(player.get_rect())
    
    def update_particles(self, dt):
        """Update and remove finished particles."""
        self.particles = [p for p in self.particles if p.update(dt)]
    
    def draw_particles(self, screen, camera_x):
        """Draw any particles this trap created."""
        for particle in self.particles:
            particle.draw(screen, camera_x)
    
    def spawn_particles(self, x, y, count, color, speed_range=(50, 150)):
        """Create a bunch of particles at a position."""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(*speed_range)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 100  # Make them shoot up a bit
            life = random.uniform(PARTICLE_LIFETIME_MIN, PARTICLE_LIFETIME_MAX)
            self.particles.append(Particle(x, y, vx, vy, color, life))

# Invisible spikes only appear when you get close
class InvisibleSpike(Trap):
    def __init__(self, x, y, reveal_dist=INVISIBLE_SPIKE_REVEAL_DISTANCE, asset_manager=None):
        super().__init__(x, y, 16, 16)
        self.visible = False
        self.reveal_dist = reveal_dist  # How close to reveal
        self.asset_manager = asset_manager
        self.just_revealed = False
    
    def update(self, dt, player):
        self.update_particles(dt)
        if not self.visible and abs(player.x - self.rect.x) < self.reveal_dist:
            self.visible = True
            self.just_revealed = True
            # Small burst when they appear
            self.spawn_particles(
                self.rect.centerx,
                self.rect.centery,
                PARTICLE_COUNT_TRAP,
                RED,
                speed_range=(80, 200)
            )
    
    def draw(self, screen, camera_x):
        self.draw_particles(screen, camera_x)
        if self.visible:
            x = self.rect.x - camera_x
            # Draw sprite if we have one, else draw a red triangle
            if self.asset_manager and 'spike' in self.asset_manager.images:
                spike_img = self.asset_manager.images['spike']
                screen.blit(spike_img, (x, self.rect.y))
            else:
                p = [(x+self.rect.w//2, self.rect.y), (x, self.rect.bottom), (x+self.rect.w, self.rect.bottom)]
                pygame.draw.polygon(screen, RED, p)
                pygame.draw.polygon(screen, DARK_RED, p, 2)
                if self.just_revealed:
                    glow_alpha = int(100 * abs(math.sin(pygame.time.get_ticks() / 100)))
                    glow_surf = pygame.Surface((self.rect.w + 10, self.rect.h + 10), pygame.SRCALPHA)
                    pygame.draw.polygon(glow_surf, (*RED, glow_alpha), 
                                      [(self.rect.w//2 + 5, 0), (0, self.rect.h + 10), (self.rect.w + 10, self.rect.h + 10)])
                    screen.blit(glow_surf, (x - 5, self.rect.y - 5))
    
    def reset(self):
        self.visible = False
        self.just_revealed = False
        self.particles = []

# Fake platforms look solid but drop after a short delay
class FakePlatform(Trap):
    def __init__(self, x, y, width, delay=0.3):
        super().__init__(x, y, width, 20)
        self.delay = delay  # Time before it disappears
        self.timer = 0
        self.touched = False
        self.crumble_particles_spawned = False
    
    def update(self, dt, player):
        self.update_particles(dt)
        if self.active and self.rect.colliderect(player.get_rect()):
            if not self.touched:
                self.touched = True
            self.timer += dt
            # Spawn small dust after half the time to warn the player
            if self.timer / self.delay > 0.5 and not self.crumble_particles_spawned:
                self.crumble_particles_spawned = True
                for i in range(PARTICLE_COUNT_PLATFORM_CRUMBLE):
                    particle_x = self.rect.x + random.uniform(0, self.rect.w)
                    self.spawn_particles(
                        particle_x,
                        self.rect.y,
                        1,
                        LIGHT_GRAY,
                        speed_range=(30, 100)
                    )
            if self.timer >= self.delay:
                self.active = False
    
    def draw(self, screen, camera_x):
        self.draw_particles(screen, camera_x)
        if self.active:
            x = self.rect.x - camera_x
            alpha = max(0, 1.0 - (self.timer / self.delay)) if self.touched else 1.0
            color = tuple(int(c * alpha) for c in LIGHT_GRAY)
            # Shake a bit to show it's weak
            shake_intensity = int(5 * (self.timer / self.delay)) if self.touched else 0
            shake_x = random.randint(-shake_intensity, shake_intensity) if self.touched else 0
            shake_y = random.randint(-shake_intensity // 2, shake_intensity // 2) if self.touched else 0
            if self.touched and alpha < 0.7:
                crack_surf = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
                pygame.draw.rect(crack_surf, color, (0, 0, self.rect.w, self.rect.h))
                for _ in range(int(5 * (1 - alpha))):
                    crack_x = random.randint(0, self.rect.w)
                    crack_length = random.randint(5, self.rect.w // 3)
                    pygame.draw.line(crack_surf, DARK_PURPLE, (crack_x, 0), (crack_x + crack_length, self.rect.h), 2)
                screen.blit(crack_surf, (x + shake_x, self.rect.y + shake_y))
            else:
                pygame.draw.rect(screen, color, (x + shake_x, self.rect.y + shake_y, self.rect.w, self.rect.h))
            pygame.draw.rect(screen, GRAY, (x + shake_x, self.rect.y + shake_y, self.rect.w, self.rect.h), 2)
    
    def get_platform_rect(self):
        return self.rect if self.active else pygame.Rect(0, 0, 0, 0)
    
    def reset(self):
        self.active = True
        self.touched = False
        self.timer = 0
        self.crumble_particles_spawned = False
        self.particles = []

# Gray platform that drops after you stand on it for a while
class TimedPlatform(Trap):
    def __init__(self, x, y, width, on_time=2.0, off_time=None):
        super().__init__(x, y, width, 20)
        self.delay = max(2.0, float(on_time))  # Minimum 2 seconds to be fair
        self.timer = 0.0
        self.touched = False
        self.falling = False
        self.vy = 0.0
        self.float_y = float(y)
        self.start_y = y
    
    def _player_on_top(self, player):
        """Check if the player's feet are on this platform."""
        pr = player.get_rect()
        horizontal = (pr.right > self.rect.left) and (pr.left < self.rect.right)
        feet_close = abs(pr.bottom - self.rect.top) <= 3
        return horizontal and feet_close
    
    def update(self, dt, player):
        """Start falling after the delay once the player stands on it."""
        if self.falling:
            self.vy += GRAVITY * 0.6 * dt
            self.float_y += self.vy * dt
            self.rect.y = int(self.float_y)
            self.active = False
            return
        if self._player_on_top(player):
            self.touched = True
            self.timer += dt
        else:
            self.timer = max(0.0, self.timer - dt * 0.3)
        if self.touched and self.timer > self.delay * 0.5:
            self.rect.x += random.choice([-1, 0, 1])
            self.rect.x -= random.choice([-1, 0, 1])
        if self.touched and self.timer >= self.delay:
            self.falling = True
            self.active = False
    
    def draw(self, screen, camera_x):
        """Draw a gray rectangle that fades a bit while waiting to fall."""
        if self.falling:
            return
        x = self.rect.x - camera_x
        alpha_ratio = 0.0 if not self.touched else min(1.0, self.timer / self.delay)
        base = 180
        shade = max(80, int(base * (1.0 - 0.3 * alpha_ratio)))
        pygame.draw.rect(screen, (shade, shade, shade), (x, self.rect.y, self.rect.w, self.rect.h))
        pygame.draw.rect(screen, GRAY, (x, self.rect.y, self.rect.w, self.rect.h), 2)
    
    def get_platform_rect(self):
        return self.rect if (not self.falling) else pygame.Rect(0, 0, 0, 0)
    
    def reset(self):
        self.timer = 0.0
        self.touched = False
        self.falling = False
        self.vy = 0.0
        self.float_y = float(self.start_y)
        self.rect.y = self.start_y
        self.active = True

# A saw that moves back and forth and sometimes speeds up or slows down
class TrollSaw(Trap):
    def __init__(self, x, y, end_x, speed=150, asset_manager=None):
        super().__init__(x, y, 38, 38)
        # Make the given y be the center of the saw
        self.rect.y -= self.rect.h // 2
        self.start_x = x
        self.end_x = end_x
        self.speed = int(speed * SAW_SPEED_MULTIPLIER)
        self.direction = 1
        self.rotation = 0
        self.speed_mult = 1.0
        self.asset_manager = asset_manager
        self.trail_positions = []  # Remember past positions for a small trail
        self.trail_max_length = 5
    
    def update(self, dt, player):
        """Move the saw and randomly change speed sometimes."""
        self.update_particles(dt)
        if random.random() < 0.03:
            self.speed_mult = random.uniform(0.6, 2.2)
        self.rect.x += int(self.speed * self.direction * self.speed_mult * dt)
        if self.rect.x >= self.end_x or self.rect.x <= self.start_x:
            self.direction *= -1
            self.spawn_particles(
                self.rect.centerx,
                self.rect.centery,
                8,
                ORANGE,
                speed_range=(50, 120)
            )
        self.rotation += 400 * dt * self.speed_mult
        self.trail_positions.append((self.rect.centerx, self.rect.centery))
        if len(self.trail_positions) > self.trail_max_length:
            self.trail_positions.pop(0)
    
    def draw(self, screen, camera_x):
        x, y = self.rect.centerx - camera_x, self.rect.centery
        # Draw a faint trail
        for i, (trail_x, trail_y) in enumerate(self.trail_positions):
            alpha = int(100 * (i / len(self.trail_positions)))
            trail_screen_x = trail_x - camera_x
            trail_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(trail_surf, (*GRAY, alpha), (20, 20), 19)
            screen.blit(trail_surf, (trail_screen_x - 20, trail_y - 20))
        # Draw particles
        self.draw_particles(screen, camera_x)
        # Draw using sprite if available
        if self.asset_manager and 'saw' in self.asset_manager.images:
            saw_img = self.asset_manager.images['saw']
            rotated_saw = pygame.transform.rotate(saw_img, -self.rotation)
            saw_rect = rotated_saw.get_rect(center=(x, y))
            screen.blit(rotated_saw, saw_rect)
        else:
            # Simple fallback drawing
            glow_surf = pygame.Surface((50, 50), pygame.SRCALPHA)
            glow_alpha = int(80 + 50 * abs(math.sin(self.rotation / 50)))
            pygame.draw.circle(glow_surf, (*RED, glow_alpha), (25, 25), 25)
            screen.blit(glow_surf, (x - 25, y - 25))
            pygame.draw.circle(screen, GRAY, (x, y), 19)
            pygame.draw.circle(screen, (60, 60, 60), (x, y), 8)
            for i in range(8):
                angle = math.radians(self.rotation + i * 45)
                ex, ey = x + math.cos(angle) * 19, y + math.sin(angle) * 19
                tooth_x, tooth_y = x + math.cos(angle) * 22, y + math.sin(angle) * 22
                pygame.draw.line(screen, RED, (ex, ey), (tooth_x, tooth_y), 4)
                pygame.draw.circle(screen, DARK_RED, (int(tooth_x), int(tooth_y)), 2)
    
    def reset(self):
        self.rect.x = self.start_x
        self.direction = 1
        self.trail_positions = []
        self.particles = []

# Fake goal kills the player when touched, looks similar to the real goal
class FakeGoal(Trap):
    def __init__(self, x, y):
        super().__init__(x, y, 40, 50)
        self.pulse = 0
        self.shimmer = 0
    
    def update(self, dt, player):
        self.update_particles(dt)
        self.pulse += dt * 3
        self.shimmer += dt * 8
        if random.random() < 0.05:
            self.spawn_particles(
                self.rect.centerx,
                self.rect.y + 10,
                2,
                YELLOW,
                speed_range=(20, 60)
            )
    
    def draw(self, screen, camera_x):
        self.draw_particles(screen, camera_x)
        x = self.rect.x - camera_x
        p = abs(math.sin(self.pulse))
        color = (int(80 + 125 * p), int(220 + 35 * p), int(30 + 125 * p))
        shimmer_offset = int(3 * abs(math.sin(self.shimmer)))
        pygame.draw.rect(screen, color, (x, self.rect.y, self.rect.w, self.rect.h))
        glow_surf = pygame.Surface((self.rect.w + 10, self.rect.h + 10), pygame.SRCALPHA)
        glow_alpha = int(40 + 30 * abs(math.sin(self.shimmer)))
        pygame.draw.rect(glow_surf, (*YELLOW, glow_alpha), (0, 0, self.rect.w + 10, self.rect.h + 10))
        screen.blit(glow_surf, (x - 5, self.rect.y - 5))
        pygame.draw.line(screen, BLACK, (x + 10, self.rect.y + 25), (x + 18 + shimmer_offset, self.rect.y + 35), 3)
        pygame.draw.line(screen, BLACK, (x + 18 + shimmer_offset, self.rect.y + 35), (x + 32, self.rect.y + 15), 3)
    
    def reset(self):
        self.pulse = 0
        self.shimmer = 0
        self.particles = []

# A vertical wall with a small safe gap to jump through
class NarrowGap(Trap):
    def __init__(self, x, y, gap_h=NARROW_GAP_MIN_HEIGHT):
        super().__init__(x, 0, 20, GAME_HEIGHT)
        self.gap_y = y  # Top of the safe gap
        self.gap_h = gap_h  # Height of the safe gap
        self.pulse = 0
    
    def update(self, dt, player):
        self.update_particles(dt)
        self.pulse += dt * 4
        # Tiny red sparks to show danger at the edges sometimes
        if random.random() < 0.02:
            self.spawn_particles(self.rect.centerx, self.gap_y - 5, 1, RED, speed_range=(10, 30))
            self.spawn_particles(self.rect.centerx, self.gap_y + self.gap_h + 5, 1, RED, speed_range=(10, 30))
    
    def check_collision(self, player):
        pr = player.get_rect()
        top_rect = pygame.Rect(self.rect.x, 0, self.rect.w, self.gap_y)
        bottom_rect = pygame.Rect(self.rect.x, self.gap_y + self.gap_h, self.rect.w, self.rect.h)
        return top_rect.colliderect(pr) or bottom_rect.colliderect(pr)
    
    def draw(self, screen, camera_x):
        self.draw_particles(screen, camera_x)
        x = self.rect.x - camera_x
        pulse_val = int(30 * abs(math.sin(self.pulse)))
        spike_color = (GRAY[0] + pulse_val, GRAY[1], GRAY[2])
        # Top spikes
        for i in range(0, self.gap_y, 15):
            p = [(x + 10, i), (x, i + 10), (x + 20, i + 10)]
            pygame.draw.polygon(screen, spike_color, p)
            pygame.draw.polygon(screen, DARK_RED, p, 1)
        # Bottom spikes
        for i in range(self.gap_y + self.gap_h, GAME_HEIGHT, 15):
            p = [(x + 10, i + 10), (x, i), (x + 20, i)]
            pygame.draw.polygon(screen, spike_color, p)
            pygame.draw.polygon(screen, DARK_RED, p, 1)
        # Red bars to highlight the safe gap edges
        edge_alpha = int(100 + 100 * abs(math.sin(self.pulse * 2)))
        danger_surf = pygame.Surface((self.rect.w, 5), pygame.SRCALPHA)
        pygame.draw.rect(danger_surf, (*RED, edge_alpha), (0, 0, self.rect.w, 5))
        screen.blit(danger_surf, (x, self.gap_y - 2))
        screen.blit(danger_surf, (x, self.gap_y + self.gap_h - 3))
    
    def reset(self):
        self.pulse = 0
        self.particles = []
