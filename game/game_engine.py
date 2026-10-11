
import math
import array
import pygame

from .player import Player
from .platform import Platform
from .hazard import Hazard


WHITE = (255, 255, 255)
BROWN = (150, 100, 60)
RED = (220, 60, 60)
GREEN = (0, 200, 0)
YELLOW = (255, 220, 80)


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.start_x = 40
        self.start_y = height - 120

        self.difficulties = {
            "Easy": {"gravity": 0.45, "jump": -12.5, "speed": 4},
            "Medium": {"gravity": 0.60, "jump": -12, "speed": 4},
            "Hard": {"gravity": 0.75, "jump": -13, "speed": 4.5},
        }

        self.difficulty = "Medium"
        self.font = pygame.font.SysFont("Arial", 30)
        self.small_font = pygame.font.SysFont("Arial", 20)

        self.sounds = {}
        self._init_sounds()
        self._build_level()

    def _init_sounds(self):
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(
                    frequency=22050,
                    size=-16,
                    channels=1,
                    buffer=512
                )

            sample_rate = 22050

            def make_tone(frequency, duration, volume=0.25):
                count = int(sample_rate * duration)
                samples = array.array("h")

                for i in range(count):
                    envelope = 1.0 - i / count
                    value = int(
                        32767 * volume * envelope
                        * math.sin(
                            2 * math.pi * frequency
                            * i / sample_rate
                        )
                    )
                    samples.append(value)

                return pygame.mixer.Sound(buffer=samples.tobytes())

            self.sounds = {
                "jump": make_tone(650, 0.10),
                "goal": make_tone(900, 0.18),
                "death": make_tone(180, 0.30),
            }

        except (pygame.error, OSError):
            self.sounds = {}

    def _play_sound(self, name):
        sound = self.sounds.get(name)
        if sound:
            try:
                sound.play()
            except pygame.error:
                pass

    def _build_level(self):
        ground_y = self.height - 40

        self.platforms = [
            Platform(0, ground_y, 200),
            Platform(220, ground_y, 140),
            Platform(420, ground_y - 60, 120),
            Platform(600, ground_y, 180),
        ]

        # Reduced hazard width: 40 pixels instead of 100.
        self.hazards = [
            Hazard(270, ground_y - 14, 40)
        ]

        self.goal_x = 740

        settings = self.difficulties[self.difficulty]
        self.gravity = settings["gravity"]

        self.player = Player(self.start_x, self.start_y)
        self.player.speed = settings["speed"]
        self.player.jump_strength = settings["jump"]

        self.score = 0
        self.game_over = False

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.game_over:
            if event.key == pygame.K_r:
                self._build_level()

            elif event.key in (pygame.K_1, pygame.K_KP1):
                self.difficulty = "Easy"
                self._build_level()

            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.difficulty = "Medium"
                self._build_level()

            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.difficulty = "Hard"
                self._build_level()

            return

        if event.key in (
            pygame.K_SPACE, pygame.K_UP, pygame.K_w
        ):
            if self.player.on_ground:
                self.player.jump()
                self._play_sound("jump")

    def handle_input(self):
        if self.game_over:
            self.player.vx = 0
            return

        keys = pygame.key.get_pressed()
        self.player.vx = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.player.vx -= self.player.speed

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.player.vx += self.player.speed

    def _end_game(self):
        if not self.game_over:
            self.game_over = True
            self.player.vx = 0
            self._play_sound("death")

    def update(self):
        if self.game_over:
            return

        # Gravity and maximum falling speed
        self.player.vy = min(
            self.player.vy + self.gravity, 12
        )

        # Horizontal movement
        self.player.x = max(
            0,
            min(
                self.width - self.player.width,
                self.player.x + self.player.vx
            )
        )

        previous_bottom = self.player.y + self.player.height
        next_y = self.player.y + self.player.vy
        next_bottom = next_y + self.player.height

        self.player.on_ground = False

        # Detect landing on platforms while falling
        if self.player.vy >= 0:
            for platform in self.platforms:
                horizontal_overlap = (
                    self.player.x + self.player.width > platform.x
                    and self.player.x < platform.x + platform.width
                )

                crossed_platform = (
                    previous_bottom <= platform.y
                    and next_bottom >= platform.y
                )

                if horizontal_overlap and crossed_platform:
                    next_y = platform.y - self.player.height
                    self.player.vy = 0
                    self.player.on_ground = True
                    break

        self.player.y = next_y

        # Hazard collision
        for hazard in self.hazards:
            if self.player.rect().colliderect(hazard.rect()):
                self._end_game()
                return

        # Falling off the screen
        if self.player.y > self.height:
            self._end_game()
            return

        # Goal reached
        if self.player.x >= self.goal_x:
            self.score += 1
            self._play_sound("goal")

            self.player.x = self.start_x
            self.player.y = self.start_y
            self.player.vx = 0
            self.player.vy = 0
            self.player.on_ground = False

    def render(self, screen):
        for platform in self.platforms:
            pygame.draw.rect(screen, BROWN, platform.rect())

        for hazard in self.hazards:
            pygame.draw.rect(screen, RED, hazard.rect())

        goal_rect = pygame.Rect(
            self.goal_x, 0, 6, self.height
        )
        pygame.draw.rect(screen, GREEN, goal_rect)

        pygame.draw.rect(screen, WHITE, self.player.rect())

        score_text = self.font.render(
            f"Score: {self.score}", True, WHITE
        )
        screen.blit(score_text, (10, 10))

        difficulty_text = self.small_font.render(
            f"Difficulty: {self.difficulty}", True, WHITE
        )
        screen.blit(difficulty_text, (10, 48))

        if self.game_over:
            overlay = pygame.Surface(
                (self.width, self.height), pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            lines = [
                ("GAME OVER", WHITE),
                (f"Final Score: {self.score}", WHITE),
                ("R - Replay", YELLOW),
                ("1 - Easy   2 - Medium   3 - Hard", YELLOW),
            ]

            start_y = self.height // 2 - 75

            for i, (message, color) in enumerate(lines):
                font = self.font if i < 2 else self.small_font
                text = font.render(message, True, color)
                rect = text.get_rect(
                    center=(
                        self.width // 2,
                        start_y + i * 42
                    )
                )
                screen.blit(text, rect)
