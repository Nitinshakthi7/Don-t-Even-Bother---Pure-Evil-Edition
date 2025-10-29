# I am adding comments for me to easily understand the codes

import pygame
import random
import math
from traps import *
from settings import *

# The Goal is the real finish object the player must touch
class Goal:
    def __init__(self, x, y, asset_manager=None):
        self.rect = pygame.Rect(x, y, 40, 50)  # Area to collide with the player
        self.pulse = 0  # Timer for color pulsing
        self.asset_manager = asset_manager  # To load goal sprite if available
        self.sparkle_timer = 0  # Timer for glow effect
        self.particles = []  # Small sparkles around the goal

    def update(self, dt):
        # Keep timers moving
        self.pulse += dt * 3
        self.sparkle_timer += dt * 10
        # Remove old particles and keep the rest
        self.particles = [p for p in self.particles if p.update(dt)]
        # Sometimes add a new sparkle
        if random.random() < 0.1:
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(30, 80)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 60
            life = random.uniform(0.5, 1.0)
            self.particles.append(Particle(self.rect.centerx, self.rect.centery, vx, vy, GREEN, life, size=2))

    def check_collision(self, player):
        # True when player touches the goal
        return self.rect.colliderect(player.get_rect())

    def draw(self, screen, camera_x):
        # Draw sparkles first
        for particle in self.particles:
            particle.draw(screen, camera_x)
        x = self.rect.x - camera_x
        p = abs(math.sin(self.pulse))
        # Make real goal green-ish so it looks different from fake goals
        color = (int(50 + 155 * p), int(205 + 50 * p), int(50 + 155 * p))
        # Use image if we have one, else draw a rectangle flag
        if self.asset_manager and 'goal' in self.asset_manager.images:
            goal_img = self.asset_manager.images['goal']
            screen.blit(goal_img, (x, self.rect.y))
        else:
            pygame.draw.rect(screen, color, (x, self.rect.y, self.rect.width, self.rect.height))
            pygame.draw.line(screen, BLACK, (x + 10, self.rect.y + 25), (x + 18, self.rect.y + 35), 3)
            pygame.draw.line(screen, BLACK, (x + 18, self.rect.y + 35), (x + 32, self.rect.y + 15), 3)
        # Soft green glow behind the goal
        glow_alpha = int(60 + 50 * abs(math.sin(self.sparkle_timer)))
        glow_surf = pygame.Surface((self.rect.w + 20, self.rect.h + 20), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*GREEN, glow_alpha), (0, 0, self.rect.w + 20, self.rect.h + 20))
        screen.blit(glow_surf, (x - 10, self.rect.y - 10))

# A Level contains platforms, traps, and the goal
class Level:
    def __init__(self, num, platforms, traps, spawn, goal_pos, width, asset_manager=None):
        self.num = num  # Level number for UI
        self.platforms = platforms  # Solid ground rectangles
        # Keep a list of traps that act like platforms
        self.fake_platforms = [t for t in traps if isinstance(t, FakePlatform)]
        self.timed_platforms = [t for t in traps if isinstance(t, TimedPlatform)]
        self.traps = traps  # All traps in the level
        self.spawn = spawn  # Where the player starts
        self.goal = Goal(goal_pos[0], goal_pos[1], asset_manager)
        self.width = width  # Scrollable width of the level
        self.death_count = 0  # Deaths in this level
        self.asset_manager = asset_manager
    
    def get_all_platforms(self):
        """Return every rectangle the player can stand on right now."""
        solid = self.platforms.copy()
        for fake in self.fake_platforms:
            if fake.active:
                solid.append(fake.get_platform_rect())
        for tp in self.timed_platforms:
            if tp.active:
                solid.append(tp.get_platform_rect())
        return solid
    
    def reset(self):
        """Reset traps and simple visual timers."""
        for trap in self.traps:
            trap.reset()
        self.goal.pulse = 0

    def update(self, dt, player):
        """Update traps and goal each frame."""
        for trap in self.traps:
            trap.update(dt, player)
        self.goal.update(dt)
    
    def draw(self, screen, camera_x):
        """Draw platforms, traps, and the goal using the camera offset."""
        for plat in self.platforms:
            x = plat.x - camera_x
            # Small shadow for depth
            shadow_rect = pygame.Rect(x + 2, plat.y + 2, plat.width, plat.height)
            pygame.draw.rect(screen, (40, 40, 40), shadow_rect)
            # Main platform look
            pygame.draw.rect(screen, WHITE, (x, plat.y, plat.width, plat.height))
            pygame.draw.line(screen, (255, 255, 255), (x, plat.y), (x + plat.width, plat.y), 2)
            pygame.draw.rect(screen, GRAY, (x, plat.y, plat.width, plat.height), 2)
        for trap in self.traps:
            trap.draw(screen, camera_x)
        self.goal.draw(screen, camera_x)

# Builds every level used by the game
class LevelFactory:
    @staticmethod
    def create_all_levels(asset_manager=None):
        """Create and return a list of Level objects."""
        levels = []
        ground_y = 550
        
        # LEVEL 1 — First Doubt (Muted Stone Ruins)
        plat1 = [
            pygame.Rect(0, ground_y, 220, 50),
            pygame.Rect(300, 500, 120, 20),
            pygame.Rect(480, 470, 110, 20),
            pygame.Rect(650, 440, 110, 20),
            pygame.Rect(820, 410, 120, 20),
            pygame.Rect(1000, 380, 120, 20),
            pygame.Rect(1190, 360, 140, 20),
            pygame.Rect(1380, 340, 160, 20),
            pygame.Rect(1600, 340, 200, 20),
        ]
        trap1 = [
            InvisibleSpike(330, 484, 80, asset_manager),
            FakePlatform(480, 470, 110, 0.6),
            TrollSaw(620, 420, 740, 120, asset_manager),
            InvisibleSpike(855, 394, 80, asset_manager),
            FakePlatform(1000, 380, 120, 0.5),
            TimedPlatform(1380, 340, 160, on_time=2.0),
        ]
        levels.append(Level(1, plat1, trap1, (50, 500), (1760, 300), 1900, asset_manager))

        # LEVEL 2 — Trust Issues (Autumn Forest)
        plat2 = [
            pygame.Rect(0, ground_y, 180, 50),
            pygame.Rect(240, 510, 90, 20),
            pygame.Rect(380, 490, 90, 20),
            pygame.Rect(520, 470, 100, 20),
            pygame.Rect(690, 440, 110, 20),
            pygame.Rect(860, 420, 120, 20),
            pygame.Rect(1040, 390, 130, 20),
            pygame.Rect(1240, 360, 140, 20),
            pygame.Rect(1460, 360, 180, 20),
            pygame.Rect(1700, 420, 220, 20),
        ]
        trap2 = [
            FakePlatform(240, 510, 90, 0.35),
            FakePlatform(380, 490, 90, 0.35),
            InvisibleSpike(520, 454, 80, asset_manager),
            TrollSaw(650, 420, 770, 180, asset_manager),
            FakePlatform(860, 420, 120, 0.3),
            TrollSaw(1000, 360, 1160, 220, asset_manager),
            TimedPlatform(1240, 360, 140, on_time=2.0),
            InvisibleSpike(1280, 344, 80, asset_manager),
            FakeGoal(1470, 340),
            TrollSaw(1500, 330, 1660, 240, asset_manager),
        ]
        levels.append(Level(2, plat2, trap2, (50, 500), (1880, 380), 2100, asset_manager))

        # LEVEL 3 — Whiplash Gears (Factory Interior)
        plat3 = [
            pygame.Rect(0, ground_y, 180, 50),
            pygame.Rect(240, 520, 100, 20),
            pygame.Rect(420, 520, 160, 20),
            pygame.Rect(640, 500, 120, 20),
            pygame.Rect(820, 460, 110, 20),
            pygame.Rect(980, 420, 100, 20),
            pygame.Rect(1120, 380, 120, 20),
            pygame.Rect(1260, 340, 140, 20),
            pygame.Rect(1460, 340, 200, 20),
        ]
        trap3 = [
            InvisibleSpike(260, 504, 70, asset_manager),
            TrollSaw(420, 500, 580, 220, asset_manager),
            FakePlatform(640, 500, 120, 0.35),
            InvisibleSpike(850, 444, 70, asset_manager),
            TrollSaw(940, 400, 1080, 230, asset_manager),
            InvisibleSpike(1120, 364, 70, asset_manager),
            TimedPlatform(1260, 340, 140, on_time=2.0),
            FakeGoal(1440, 320),
        ]
        levels.append(Level(3, plat3, trap3, (50, 500), (1640, 300), 1800, asset_manager))

        # LEVEL 4 — Phantom Steps (Moonlit Cliffs)
        plat4 = [
            pygame.Rect(0, ground_y, 160, 50),
            pygame.Rect(220, 520, 50, 20), pygame.Rect(280, 510, 50, 20),
            pygame.Rect(340, 500, 50, 20), pygame.Rect(400, 490, 50, 20),
            pygame.Rect(460, 480, 50, 20), pygame.Rect(520, 470, 50, 20),
            pygame.Rect(580, 460, 50, 20), pygame.Rect(640, 450, 50, 20),
            pygame.Rect(700, 440, 60, 20), pygame.Rect(780, 420, 140, 20),
            pygame.Rect(960, 400, 200, 20),
        ]
        trap4 = [
            # Alternate real/fake steps
            FakePlatform(220, 520, 50, 0.25),
            InvisibleSpike(275, 494, 60, asset_manager),
            FakePlatform(340, 500, 50, 0.25),
            InvisibleSpike(395, 474, 60, asset_manager),
            FakePlatform(460, 480, 50, 0.22),
            InvisibleSpike(515, 454, 60, asset_manager),
            FakePlatform(580, 460, 50, 0.22),
            TrollSaw(720, 420, 780, 180, asset_manager),
            FakeGoal(770, 400),
        ]
        levels.append(Level(4, plat4, trap4, (50, 500), (1120, 360), 1300, asset_manager))

        # LEVEL 5 — The Long Way (Cavern Lake)
        plat5 = [
            pygame.Rect(0, ground_y, 170, 50),
            # Short route (top)
            pygame.Rect(220, 520, 120, 20), pygame.Rect(380, 490, 120, 20), pygame.Rect(540, 460, 120, 20),
            pygame.Rect(700, 430, 140, 20),
            # Long lake route (bottom)
            pygame.Rect(220, 560, 120, 20), pygame.Rect(380, 560, 120, 20), pygame.Rect(540, 560, 120, 20),
            pygame.Rect(700, 560, 140, 20), pygame.Rect(880, 520, 140, 20), pygame.Rect(1060, 480, 160, 20),
            pygame.Rect(1250, 440, 180, 20), pygame.Rect(1460, 420, 200, 20),
            pygame.Rect(1700, 420, 220, 20),
        ]
        trap5 = [
            # Short route is deadly
            InvisibleSpike(250, 504, 80, asset_manager), InvisibleSpike(410, 474, 80, asset_manager),
            InvisibleSpike(570, 444, 80, asset_manager), FakeGoal(840, 410),
            # Long route: every third plank fake
            FakePlatform(380, 560, 120, 0.35), FakePlatform(700, 560, 140, 0.35),
            TrollSaw(860, 500, 940, 200, asset_manager), TrollSaw(1040, 460, 1160, 220, asset_manager),
            TimedPlatform(1250, 440, 180, on_time=2.0),
            InvisibleSpike(1460, 404, 80, asset_manager),
        ]
        levels.append(Level(5, plat5, trap5, (50, 500), (1800, 380), 2000, asset_manager))

        # LEVEL 6 — Two Lies and a Truth (Temple of Choices)
        plat6 = [
            pygame.Rect(0, ground_y, 160, 50),
            # Lane A (top)
            pygame.Rect(220, 500, 140, 20), pygame.Rect(400, 500, 140, 20), pygame.Rect(580, 500, 140, 20),
            # Lane B (middle)
            pygame.Rect(220, 540, 140, 20), pygame.Rect(400, 540, 140, 20), pygame.Rect(580, 540, 140, 20),
            # Lane C (bottom)
            pygame.Rect(220, 580, 140, 20), pygame.Rect(400, 580, 140, 20), pygame.Rect(580, 580, 140, 20),
            # Tower
            pygame.Rect(760, 520, 100, 20), pygame.Rect(880, 480, 100, 20), pygame.Rect(1000, 440, 100, 20),
            pygame.Rect(1120, 400, 100, 20), pygame.Rect(1240, 360, 100, 20), pygame.Rect(1360, 320, 120, 20),
        ]
        trap6 = [
            # Lane A: many fake
            FakePlatform(220, 500, 140, 0.35), FakePlatform(400, 500, 140, 0.35),
            # Lane B: saw bursts
            TrollSaw(300, 520, 540, 260, asset_manager),
            # Lane C: spikes on markers
            InvisibleSpike(220, 564, 70, asset_manager), InvisibleSpike(400, 564, 70, asset_manager),
            # Ends: decoy goals
            FakeGoal(720, 490), FakeGoal(720, 530),
            # Tower mixes
            FakePlatform(880, 480, 100, 0.3), TimedPlatform(1000, 440, 100, on_time=2.0),
            TrollSaw(1080, 380, 1200, 230, asset_manager), InvisibleSpike(1240, 344, 70, asset_manager),
        ]
        levels.append(Level(6, plat6, trap6, (50, 500), (1380, 280), 1600, asset_manager))

        # LEVEL 7 — Momentum Tax (Stormworks)
        plat7 = [
            pygame.Rect(0, ground_y, 160, 50),
            pygame.Rect(220, 520, 120, 20), pygame.Rect(380, 500, 120, 20),
            pygame.Rect(540, 470, 120, 20), pygame.Rect(700, 440, 120, 20),
            pygame.Rect(860, 410, 120, 20), pygame.Rect(1020, 390, 140, 20),
            pygame.Rect(1200, 370, 160, 20), pygame.Rect(1390, 360, 200, 20),
        ]
        trap7 = [
            # Spikes on stop-go tiles
            InvisibleSpike(260, 504, 60, asset_manager), InvisibleSpike(420, 484, 60, asset_manager),
            FakePlatform(540, 470, 120, 0.28), TimedPlatform(700, 440, 120, on_time=2.0),
            TrollSaw(820, 390, 940, 240, asset_manager), TrollSaw(980, 370, 1100, 260, asset_manager),
            FakeGoal(1180, 360),
        ]
        levels.append(Level(7, plat7, trap7, (50, 500), (1520, 320), 1700, asset_manager))

        # LEVEL 8 — Vanishing Act (Crystal Catacombs)
        plat8 = [
            pygame.Rect(0, ground_y, 150, 50),
            pygame.Rect(220, 520, 100, 20), pygame.Rect(360, 520, 100, 20), pygame.Rect(500, 520, 100, 20),
            pygame.Rect(640, 500, 120, 20), pygame.Rect(800, 470, 130, 20), pygame.Rect(970, 440, 140, 20),
            pygame.Rect(1150, 410, 150, 20), pygame.Rect(1340, 390, 180, 20),
        ]
        trap8 = [
            # Two-of-five tile sequences with fakes
            FakePlatform(220, 520, 100, 0.22), FakePlatform(500, 520, 100, 0.22),
            TrollSaw(600, 480, 760, 280, asset_manager),
            InvisibleSpike(800, 454, 60, asset_manager),
            FakePlatform(970, 440, 140, 0.22),
            TrollSaw(1100, 390, 1260, 260, asset_manager),
            FakeGoal(1320, 370),
        ]
        levels.append(Level(8, plat8, trap8, (50, 500), (1480, 350), 1600, asset_manager))

        # LEVEL 9 — Pattern Debt (The Archive)
        plat9 = [
            pygame.Rect(0, ground_y, 140, 50),
            # Segment A
            pygame.Rect(220, 520, 60, 20), pygame.Rect(300, 500, 60, 20), pygame.Rect(380, 480, 60, 20),
            pygame.Rect(460, 460, 60, 20), pygame.Rect(540, 440, 80, 20),
            # Segment B
            pygame.Rect(680, 420, 120, 20), pygame.Rect(840, 390, 120, 20), pygame.Rect(1000, 360, 140, 20),
            # Segment C
            pygame.Rect(1180, 340, 100, 20), pygame.Rect(1300, 340, 100, 20), pygame.Rect(1420, 340, 100, 20),
            pygame.Rect(1540, 340, 160, 20),
        ]
        trap9 = [
            # A: wind+fake steps approximated by alternating spikes/fakes
            FakePlatform(220, 520, 60, 0.22), InvisibleSpike(300, 484, 60, asset_manager),
            FakePlatform(380, 480, 60, 0.22), InvisibleSpike(460, 444, 60, asset_manager),
            TrollSaw(520, 420, 600, 240, asset_manager),
            # B: moving platforms desync approximated by saw timing
            TrollSaw(680, 400, 800, 260, asset_manager),
            FakePlatform(840, 390, 120, 0.25),
            TrollSaw(960, 340, 1100, 260, asset_manager),
            # C: punish micro-stepping
            InvisibleSpike(1180, 324, 60, asset_manager), InvisibleSpike(1300, 324, 60, asset_manager),
            FakeGoal(1540, 320),
        ]
        levels.append(Level(9, plat9, trap9, (50, 500), (1680, 300), 1800, asset_manager))

        # LEVEL 10 — The Final Lie (Ascension Spire)
        plat10 = [
            pygame.Rect(0, ground_y, 160, 50),
            # Spiral ascent (outer corners fake, inner corners spiked)
            pygame.Rect(220, 520, 90, 20), pygame.Rect(350, 480, 90, 20),
            pygame.Rect(480, 440, 90, 20), pygame.Rect(610, 400, 90, 20),
            pygame.Rect(740, 360, 90, 20), pygame.Rect(870, 320, 90, 20),
            pygame.Rect(1000, 280, 90, 20), pygame.Rect(1130, 240, 90, 20),
            pygame.Rect(1260, 240, 140, 20),
        ]
        trap10 = [
            # Inner corners with invisible spikes
            InvisibleSpike(220, 504, 60, asset_manager), InvisibleSpike(350, 464, 60, asset_manager),
            InvisibleSpike(480, 424, 60, asset_manager), InvisibleSpike(610, 384, 60, asset_manager),
            InvisibleSpike(740, 344, 60, asset_manager), InvisibleSpike(870, 304, 60, asset_manager),
            # Outer corners fake
            FakePlatform(350, 480, 90, 0.2), FakePlatform(610, 400, 90, 0.2), FakePlatform(870, 320, 90, 0.2),
            # Saws with speed gates approximated by randomness
            TrollSaw(300, 460, 560, 300, asset_manager), TrollSaw(660, 380, 920, 300, asset_manager),
            # Mid-run fake goals
            FakeGoal(980, 260), FakeGoal(1260, 220),
        ]
        levels.append(Level(10, plat10, trap10, (50, 500), (1380, 200), 1500, asset_manager))

        return levels
