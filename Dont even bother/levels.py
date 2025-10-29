import pygame
import random
import math
from traps import *
from settings import *

class Goal:
    def __init__(self, x, y, asset_manager=None):
        self.rect = pygame.Rect(x, y, 40, 50)
        self.pulse = 0
        self.asset_manager = asset_manager  # NEW: Asset manager for sprite loading
        self.sparkle_timer = 0  # NEW: Sparkle effect
        self.particles = []  # NEW: Victory particles

    def update(self, dt):
        self.pulse += dt * 3
        self.sparkle_timer += dt * 10
        
        # NEW: Update victory particles
        self.particles = [p for p in self.particles if p.update(dt)]
        
        # NEW: Spawn victory sparkles
        if random.random() < 0.1:
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(30, 80)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 60
            life = random.uniform(0.5, 1.0)
            self.particles.append(Particle(self.rect.centerx, self.rect.centery, vx, vy, GREEN, life, size=2))

    def check_collision(self, player):
        return self.rect.colliderect(player.get_rect())

    def draw(self, screen, camera_x):
        # Draw particles first
        for particle in self.particles:
            particle.draw(screen, camera_x)
        
        x = self.rect.x - camera_x
        p = abs(math.sin(self.pulse))
        
        # True goal is greener, less yellow than fake
        color = (int(50 + 155 * p), int(205 + 50 * p), int(50 + 155 * p))
        
        # NEW: Use sprite if available
        if self.asset_manager and 'goal' in self.asset_manager.images:
            goal_img = self.asset_manager.images['goal']
            screen.blit(goal_img, (x, self.rect.y))
        else:
            pygame.draw.rect(screen, color, (x, self.rect.y, self.rect.width, self.rect.height))
            pygame.draw.line(screen, BLACK, (x + 10, self.rect.y + 25), (x + 18, self.rect.y + 35), 3)
            pygame.draw.line(screen, BLACK, (x + 18, self.rect.y + 35), (x + 32, self.rect.y + 15), 3)
        
        # NEW: Victory glow effect (green, not yellow)
        glow_alpha = int(60 + 50 * abs(math.sin(self.sparkle_timer)))
        glow_surf = pygame.Surface((self.rect.w + 20, self.rect.h + 20), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*GREEN, glow_alpha), (0, 0, self.rect.w + 20, self.rect.h + 20))
        screen.blit(glow_surf, (x - 10, self.rect.y - 10))

class Level:
    
    def __init__(self, num, platforms, traps, spawn, goal_pos, width, asset_manager=None):
        self.num = num
        self.platforms = platforms
        self.fake_platforms = [t for t in traps if isinstance(t, FakePlatform)]
        self.traps = traps
        self.spawn = spawn
        self.goal = Goal(goal_pos[0], goal_pos[1], asset_manager)  # NEW: Pass asset_manager
        self.width = width
        self.death_count = 0
        self.asset_manager = asset_manager  # NEW: Store asset manager
    
    def get_all_platforms(self):
        solid = self.platforms.copy()
        for fake in self.fake_platforms:
            if fake.active:
                solid.append(fake.get_platform_rect())
        return solid
    
    def reset(self):
        for trap in self.traps:
            trap.reset()
        self.goal.pulse = 0

    def update(self, dt, player):
        for trap in self.traps:
            trap.update(dt, player)
        self.goal.update(dt)
    
    def draw(self, screen, camera_x):
        # NEW: Enhanced platform rendering with gradient effect
        for plat in self.platforms:
            x = plat.x - camera_x
            # Draw shadow
            shadow_rect = pygame.Rect(x + 2, plat.y + 2, plat.width, plat.height)
            pygame.draw.rect(screen, (40, 40, 40), shadow_rect)
            # Draw platform
            pygame.draw.rect(screen, WHITE, (x, plat.y, plat.width, plat.height))
            # Top highlight
            pygame.draw.line(screen, (255, 255, 255), (x, plat.y), (x + plat.width, plat.y), 2)
            # Border
            pygame.draw.rect(screen, GRAY, (x, plat.y, plat.width, plat.height), 2)
        
        for trap in self.traps:
            trap.draw(screen, camera_x)
        
        self.goal.draw(screen, camera_x)

class LevelFactory:
    
    @staticmethod
    def create_all_levels(asset_manager=None):
        """NEW: Now accepts asset_manager for passing to traps"""
        levels = []
        ground_y = 550
        
        # LEVEL 1 - ORIGINAL DIFFICULTY (Visual enhancements kept)
        plat1 = [
            pygame.Rect(0, ground_y, 200, 50), pygame.Rect(250, 500, 120, 20),
            pygame.Rect(420, 450, 100, 20), pygame.Rect(570, 400, 100, 20),
            pygame.Rect(720, 350, 120, 20), pygame.Rect(890, 300, 100, 20),
            pygame.Rect(1040, 350, 100, 20), pygame.Rect(1190, 400, 100, 20),
            pygame.Rect(1340, 350, 120, 20), pygame.Rect(1510, 300, 100, 20),
            pygame.Rect(1660, 350, 200, 20),
        ]
        trap1 = [
            InvisibleSpike(280, 484, 80, asset_manager), 
            TrollSaw(570, 400, 670, 100, asset_manager), 
            FakePlatform(720, 350, 120, 0.6),
            InvisibleSpike(920, 284, 80, asset_manager), 
            TrollSaw(1040, 350, 1140, 110, asset_manager),
            FakePlatform(1340, 350, 120, 0.5),
            InvisibleSpike(1540, 284, 80, asset_manager), 
            FakeGoal(1710, 300),
        ]
        levels.append(Level(1, plat1, trap1, (50, 500), (1810, 300), 2000, asset_manager))
        
        # LEVEL 2 - ORIGINAL DIFFICULTY
        plat2 = [
            pygame.Rect(0, ground_y, 150, 50), pygame.Rect(240, 500, 80, 20),
            pygame.Rect(410, 480, 70, 20), pygame.Rect(570, 460, 80, 20), 
            pygame.Rect(740, 440, 70, 20), pygame.Rect(900, 420, 80, 20),
            pygame.Rect(1070, 400, 70, 20), pygame.Rect(1220, 380, 80, 20),
            pygame.Rect(1390, 360, 90, 20), pygame.Rect(1570, 340, 100, 20),
            pygame.Rect(1760, 380, 150, 20), pygame.Rect(2000, 450, 200, 20),
        ]
        trap2 = [
            TrollSaw(200, 460, 350, 180, asset_manager), 
            TrollSaw(470, 420, 660, 200, asset_manager), 
            TrollSaw(800, 380, 1050, 220, asset_manager),
            TrollSaw(1200, 340, 1430, 240, asset_manager),
            FakePlatform(1880, 360, 90, 0.35),
            TrollSaw(1900, 300, 2100, 250, asset_manager),
            FakeGoal(1800, 330), 
            TrollSaw(2050, 410, 2200, 230, asset_manager),
        ]
        levels.append(Level(2, plat2, trap2, (50, 500), (2800, 400), 3000, asset_manager))
        
        # LEVEL 3 - ORIGINAL DIFFICULTY
        plat3 = [
            pygame.Rect(0, ground_y, 150, 50), pygame.Rect(200, 500, 100, 20),
            pygame.Rect(120, 450, 90, 20), pygame.Rect(250, 400, 90, 20),
            pygame.Rect(150, 350, 85, 20), pygame.Rect(300, 300, 85, 20),
            pygame.Rect(200, 250, 80, 20), pygame.Rect(350, 200, 80, 20),
            pygame.Rect(250, 150, 75, 20), pygame.Rect(420, 150, 100, 20),
            pygame.Rect(570, 150, 80, 20), pygame.Rect(700, 200, 80, 20),
            pygame.Rect(830, 250, 80, 20), pygame.Rect(960, 300, 90, 20),
            pygame.Rect(1100, 350, 100, 20), pygame.Rect(1250, 400, 150, 20),
        ]
        trap3 = [
            InvisibleSpike(250, 484, 70, asset_manager), 
            InvisibleSpike(165, 434, 70, asset_manager), 
            InvisibleSpike(295, 384, 70, asset_manager), 
            InvisibleSpike(195, 334, 70, asset_manager), 
            InvisibleSpike(345, 284, 70, asset_manager), 
            FakePlatform(200, 250, 80, 0.35),
            InvisibleSpike(240, 234, 70, asset_manager), 
            InvisibleSpike(480, 134, 70, asset_manager),
            InvisibleSpike(640, 134, 70, asset_manager), 
            FakePlatform(730, 200, 80, 0.3),
            InvisibleSpike(900, 234, 70, asset_manager), 
            InvisibleSpike(1030, 284, 70, asset_manager),
            InvisibleSpike(1170, 334, 70, asset_manager), 
            FakeGoal(1350, 350),
        ]
        levels.append(Level(3, plat3, trap3, (50, 500), (1400, 350), 1600, asset_manager))

        # LEVEL 4 - ORIGINAL DIFFICULTY
        plat4 = [
            pygame.Rect(0, ground_y, 150, 50), pygame.Rect(200, 500, 60, 20),
            pygame.Rect(290, 480, 55, 20), pygame.Rect(390, 460, 60, 20),
            pygame.Rect(495, 440, 55, 20), pygame.Rect(590, 420, 60, 20),
            pygame.Rect(690, 400, 55, 20), pygame.Rect(785, 380, 60, 20),
            pygame.Rect(885, 360, 55, 20), pygame.Rect(980, 340, 60, 20),
            pygame.Rect(1080, 360, 55, 20), pygame.Rect(1175, 380, 60, 20),
            pygame.Rect(1275, 400, 55, 20), pygame.Rect(1370, 420, 60, 20),
            pygame.Rect(1470, 440, 70, 20), pygame.Rect(1580, 460, 150, 20),
        ]
        trap4 = [
            NarrowGap(265, 450, 34),
            NarrowGap(360, 430, 32),
            NarrowGap(470, 410, 30),
            NarrowGap(585, 390, 30),
            FakePlatform(630, 420, 60, 0.3), 
            NarrowGap(690, 370, 26),
            NarrowGap(795, 350, 28),
            NarrowGap(905, 330, 30),
            NarrowGap(1010, 310, 28), 
            FakePlatform(1170, 360, 55, 0.25),
            NarrowGap(1230, 330, 26), 
            NarrowGap(1340, 350, 28),
            NarrowGap(1440, 370, 30), 
            NarrowGap(1550, 390, 32),
            FakeGoal(1650, 410),
        ]
        levels.append(Level(4, plat4, trap4, (50, 500), (1820, 410), 2000, asset_manager))
        
        # LEVEL 5 - ORIGINAL DIFFICULTY
        plat5 = [
            pygame.Rect(0, ground_y, 150, 50), pygame.Rect(200, 480, 90, 20),
            pygame.Rect(340, 420, 85, 20), pygame.Rect(480, 360, 90, 20),
            pygame.Rect(620, 300, 85, 20), pygame.Rect(760, 360, 90, 20),
            pygame.Rect(900, 420, 85, 20), pygame.Rect(1040, 480, 90, 20),
            pygame.Rect(1180, 420, 85, 20), pygame.Rect(1320, 360, 90, 20),
            pygame.Rect(1460, 300, 85, 20), pygame.Rect(1600, 360, 90, 20),
            pygame.Rect(1740, 420, 100, 20), pygame.Rect(1890, 480, 200, 20),
        ]
        trap5 = [
            TrollSaw(150, 460, 250, 280, asset_manager), 
            TrollSaw(270, 400, 370, 290, asset_manager), 
            TrollSaw(420, 340, 520, 300, asset_manager),
            TrollSaw(550, 280, 650, 310, asset_manager), 
            TrollSaw(700, 340, 800, 290, asset_manager), 
            TrollSaw(830, 400, 930, 300, asset_manager),
            TrollSaw(980, 460, 1080, 310, asset_manager),
            FakePlatform(1180, 420, 85, 0.3), 
            TrollSaw(1250, 340, 1350, 290, asset_manager), 
            TrollSaw(1390, 280, 1490, 320, asset_manager), 
            TrollSaw(1530, 340, 1630, 300, asset_manager), 
            TrollSaw(1670, 400, 1770, 310, asset_manager),
            FakeGoal(1840, 430), 
            TrollSaw(1920, 460, 2020, 250, asset_manager),
        ]
        levels.append(Level(5, plat5, trap5, (50, 500), (2050, 430), 2200, asset_manager))
        
        # LEVEL 6 - ORIGINAL DIFFICULTY
        plat6 = [
            pygame.Rect(0, ground_y, 150, 50), pygame.Rect(200, 480, 100, 20),
            pygame.Rect(400, 420, 90, 20), pygame.Rect(600, 360, 95, 20),
            pygame.Rect(800, 300, 90, 20), pygame.Rect(1000, 360, 95, 20),
            pygame.Rect(1200, 420, 90, 20), pygame.Rect(1400, 360, 95, 20),
            pygame.Rect(1600, 300, 90, 20), pygame.Rect(1800, 360, 95, 20),
            pygame.Rect(2000, 420, 100, 20), pygame.Rect(2200, 480, 200, 20),
        ]
        trap6 = [
            FakePlatform(200, 480, 100, 0.4), 
            FakeGoal(300, 430),
            FakePlatform(400, 420, 90, 0.35), 
            FakeGoal(500, 370),
            FakePlatform(600, 360, 95, 0.3), 
            FakeGoal(700, 310),
            FakePlatform(800, 300, 90, 0.25), 
            FakeGoal(900, 250),
            FakePlatform(1000, 360, 95, 0.3), 
            FakeGoal(1100, 310),
            FakePlatform(1200, 420, 90, 0.35), 
            FakeGoal(1300, 370),
            FakePlatform(1600, 300, 90, 0.25), 
            FakeGoal(1700, 250),
            FakePlatform(2000, 420, 100, 0.4), 
            FakeGoal(2100, 370),
        ]
        levels.append(Level(6, plat6, trap6, (50, 500), (2350, 430), 2500, asset_manager))
        
        # LEVEL 7 - ORIGINAL DIFFICULTY
        plat7 = [
            pygame.Rect(0, 200, 150, 20), pygame.Rect(200, 250, 80, 20),
            pygame.Rect(100, 300, 75, 20), pygame.Rect(230, 350, 80, 20),
            pygame.Rect(130, 400, 75, 20), pygame.Rect(260, 450, 80, 20),
            pygame.Rect(160, 500, 75, 20), pygame.Rect(290, ground_y, 100, 50),
            pygame.Rect(450, 500, 80, 20), pygame.Rect(590, 450, 75, 20),
            pygame.Rect(720, 400, 80, 20), pygame.Rect(860, 350, 75, 20),
            pygame.Rect(990, 300, 80, 20), pygame.Rect(1130, 350, 85, 20),
            pygame.Rect(1270, 400, 80, 20), pygame.Rect(1410, 450, 90, 20),
            pygame.Rect(1560, 500, 200, 20),
        ]
        trap7 = [
            InvisibleSpike(240, 234, 60, asset_manager), 
            TrollSaw(75, 280, 175, 190, asset_manager),
            InvisibleSpike(135, 284, 60, asset_manager), 
            FakePlatform(130, 400, 75, 0.3),
            TrollSaw(185, 430, 285, 200, asset_manager), 
            InvisibleSpike(200, 484, 60, asset_manager),
            TrollSaw(135, 480, 235, 210, asset_manager), 
            InvisibleSpike(340, 534, 60, asset_manager),
            TrollSaw(520, 480, 620, 200, asset_manager), 
            InvisibleSpike(625, 434, 60, asset_manager),
            TrollSaw(790, 380, 890, 210, asset_manager), 
            FakePlatform(860, 350, 75, 0.28),
            InvisibleSpike(1030, 284, 60, asset_manager), 
            TrollSaw(1060, 330, 1160, 220, asset_manager),
            FakeGoal(1480, 400), 
            InvisibleSpike(1445, 434, 60, asset_manager),
            TrollSaw(1480, 480, 1580, 230, asset_manager), 
            InvisibleSpike(1640, 484, 55, asset_manager),
        ]
        levels.append(Level(7, plat7, trap7, (50, 150), (1710, 450), 1900, asset_manager))
        
        # LEVEL 8 - ORIGINAL DIFFICULTY
        plat8 = [
            pygame.Rect(0, ground_y, 140, 50), pygame.Rect(180, 490, 65, 20),
            pygame.Rect(290, 430, 60, 20), pygame.Rect(395, 370, 65, 20),
            pygame.Rect(505, 310, 60, 20), pygame.Rect(610, 370, 55, 20),
            pygame.Rect(710, 430, 60, 20), pygame.Rect(815, 370, 55, 20),
            pygame.Rect(915, 310, 60, 20), pygame.Rect(1020, 250, 65, 20),
            pygame.Rect(1130, 310, 55, 20), pygame.Rect(1230, 370, 60, 20),
            pygame.Rect(1335, 310, 55, 20), pygame.Rect(1435, 370, 65, 20),
            pygame.Rect(1545, 430, 60, 20), pygame.Rect(1650, 370, 55, 20),
            pygame.Rect(1750, 310, 65, 20), pygame.Rect(1860, 370, 60, 20),
            pygame.Rect(1965, 430, 70, 20), pygame.Rect(2080, 490, 180, 20),
        ]
        trap8 = [
            TrollSaw(245, 410, 345, 260, asset_manager), 
            NarrowGap(350, 320, 28), 
            FakePlatform(505, 310, 60, 0.25), 
            TrollSaw(565, 350, 665, 270, asset_manager),
            InvisibleSpike(740, 414, 60, asset_manager), 
            NarrowGap(870, 330, 26),
            TrollSaw(970, 290, 1070, 280, asset_manager), 
            InvisibleSpike(1050, 234, 60, asset_manager),
            FakePlatform(1230, 370, 60, 0.22), 
            TrollSaw(1285, 290, 1385, 290, asset_manager),
            NarrowGap(1390, 320, 28), 
            InvisibleSpike(1465, 354, 60, asset_manager),
            TrollSaw(1600, 410, 1700, 270, asset_manager), 
            FakeGoal(1710, 260), 
            InvisibleSpike(1780, 294, 60, asset_manager),
            FakePlatform(1965, 430, 70, 0.25),
            TrollSaw(2020, 470, 2120, 280, asset_manager), 
            InvisibleSpike(2140, 474, 60, asset_manager),
        ]
        levels.append(Level(8, plat8, trap8, (50, 500), (2220, 440), 2400, asset_manager))
        
        # LEVEL 9 - ORIGINAL DIFFICULTY
        plat9 = [
            pygame.Rect(0, ground_y, 120, 50), pygame.Rect(160, 490, 45, 20),
            pygame.Rect(240, 450, 40, 20), pygame.Rect(315, 410, 45, 20),
            pygame.Rect(395, 370, 40, 20), pygame.Rect(470, 330, 45, 20),
            pygame.Rect(550, 290, 40, 20), pygame.Rect(625, 250, 45, 20),
            pygame.Rect(705, 290, 40, 20), pygame.Rect(780, 330, 45, 20),
            pygame.Rect(860, 370, 40, 20), pygame.Rect(945, 330, 45, 20),
            pygame.Rect(1035, 290, 40, 20), pygame.Rect(1120, 250, 45, 20),
            pygame.Rect(1210, 210, 40, 20), pygame.Rect(1295, 250, 45, 20),
            pygame.Rect(1475, 290, 40, 20), pygame.Rect(1560, 330, 45, 20),
            pygame.Rect(1650, 370, 40, 20), pygame.Rect(1735, 410, 50, 20),
            pygame.Rect(1830, 450, 60, 20), pygame.Rect(1935, 490, 150, 20),
        ]
        trap9 = [
            InvisibleSpike(180, 474, 50, asset_manager), 
            NarrowGap(205, 400, 26),
            TrollSaw(380, 390, 480, 290, asset_manager), 
            InvisibleSpike(300, 434, 50, asset_manager),
            NarrowGap(470, 350, 24), 
            InvisibleSpike(555, 314, 50, asset_manager),
            FakePlatform(600, 290, 40, 0.2), 
            NarrowGap(640, 280, 26),
            TrollSaw(820, 310, 920, 300, asset_manager), 
            NarrowGap(905, 350, 24), 
            FakePlatform(1125, 290, 40, 0.18), 
            TrollSaw(1255, 230, 1355, 310, asset_manager),
            NarrowGap(1345, 240, 22), 
            InvisibleSpike(1430, 234, 50, asset_manager),
            TrollSaw(1520, 310, 1620, 300, asset_manager), 
            FakePlatform(1650, 370, 40, 0.2),
            FakeGoal(1880, 400),
            TrollSaw(1980, 470, 2080, 290, asset_manager), 
            InvisibleSpike(2050, 474, 60, asset_manager),
        ]
        levels.append(Level(9, plat9, trap9, (50, 500), (2070, 440), 2200, asset_manager))
        
        # LEVEL 10 - ORIGINAL DIFFICULTY
        plat10 = [
            pygame.Rect(0, ground_y, 130, 50), pygame.Rect(170, 490, 70, 20),
            pygame.Rect(100, 440, 65, 20), pygame.Rect(220, 390, 70, 20),
            pygame.Rect(140, 340, 65, 20), pygame.Rect(260, 290, 70, 20),
            pygame.Rect(180, 240, 65, 20), pygame.Rect(300, 190, 75, 20),
            pygame.Rect(420, 190, 50, 20), pygame.Rect(515, 190, 45, 20),
            pygame.Rect(605, 190, 50, 20), pygame.Rect(700, 190, 45, 20),
            pygame.Rect(790, 190, 50, 20), pygame.Rect(880, 240, 50, 20),
            pygame.Rect(975, 290, 45, 20), pygame.Rect(1065, 340, 50, 20),
            pygame.Rect(1160, 290, 45, 20), pygame.Rect(1250, 240, 50, 20),
            pygame.Rect(1345, 290, 45, 20), pygame.Rect(1435, 340, 55, 20),
            pygame.Rect(1535, 390, 50, 20), pygame.Rect(1630, 340, 55, 20),
            pygame.Rect(1730, 390, 50, 20), pygame.Rect(1825, 440, 60, 20),
            pygame.Rect(1930, 490, 70, 20), pygame.Rect(2045, 440, 80, 20),
            pygame.Rect(2170, 490, 200, 20),
        ]
        trap10 = [
            InvisibleSpike(150, 474, 60, asset_manager), 
            TrollSaw(75, 420, 175, 280, asset_manager), 
            FakePlatform(140, 340, 65, 0.25),
            TrollSaw(135, 270, 235, 290, asset_manager), 
            NarrowGap(255, 220, 24), 
            TrollSaw(375, 170, 475, 310, asset_manager), 
            InvisibleSpike(565, 174, 60, asset_manager), 
            NarrowGap(655, 180, 22),
            FakePlatform(700, 190, 45, 0.18), 
            TrollSaw(745, 170, 845, 320, asset_manager),
            TrollSaw(925, 270, 1025, 300, asset_manager), 
            NarrowGap(1020, 300, 24), 
            FakePlatform(1160, 290, 45, 0.2), 
            TrollSaw(1205, 220, 1305, 310, asset_manager), 
            NarrowGap(1300, 260, 22),
            TrollSaw(1390, 320, 1490, 300, asset_manager), 
            FakeGoal(1580, 340), 
            TrollSaw(1585, 370, 1685, 290, asset_manager), 
            FakePlatform(1825, 440, 60, 0.22),
            TrollSaw(1875, 470, 1975, 310, asset_manager), 
            NarrowGap(1980, 410, 24), 
            FakeGoal(2220, 440),
            TrollSaw(2115, 470, 2215, 300, asset_manager), 
            InvisibleSpike(2280, 474, 60, asset_manager),
        ]
        levels.append(Level(10, plat10, trap10, (50, 500), (2340, 440), 2500, asset_manager))
        
        return levels
