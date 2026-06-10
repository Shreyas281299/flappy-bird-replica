import random
from dataclasses import dataclass
from pathlib import Path

import pygame


SCREEN_WIDTH = 432
SCREEN_HEIGHT = 768
FPS = 60

SKY = (112, 197, 206)
GROUND = (222, 216, 149)
GROUND_DARK = (199, 190, 117)
WHITE = (255, 255, 255)
BLACK = (31, 31, 31)

GROUND_HEIGHT = 110
BIRD_WIDTH = 51
BIRD_HEIGHT = 36
BIRD_X = 105
GRAVITY = 0.42
FLAP_STRENGTH = -7.5
MAX_FALL_SPEED = 9
PIPE_WIDTH = 74
PIPE_GAP = 172
PIPE_SPEED = 3
PIPE_INTERVAL_MS = 1450


@dataclass
class PipePair:
    x: float
    gap_y: int
    scored: bool = False

    def top_rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), 0, PIPE_WIDTH, self.gap_y - PIPE_GAP // 2)

    def bottom_rect(self) -> pygame.Rect:
        bottom_y = self.gap_y + PIPE_GAP // 2
        return pygame.Rect(
            int(self.x),
            bottom_y,
            PIPE_WIDTH,
            SCREEN_HEIGHT - GROUND_HEIGHT - bottom_y,
        )

    def is_off_screen(self) -> bool:
        return self.x + PIPE_WIDTH < 0


class FlappyBirdGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Flappy Bird Replica")

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 56)
        self.small_font = pygame.font.Font(None, 32)
        self.load_assets()
        self.reset()

    def load_assets(self) -> None:
        asset_dir = Path(__file__).resolve().parent / "assets"
        bird_files = (
            "yellowbird-upflap.png",
            "yellowbird-midflap.png",
            "yellowbird-downflap.png",
        )
        self.bird_frames = [
            pygame.transform.scale(
                pygame.image.load(asset_dir / filename).convert_alpha(),
                (BIRD_WIDTH, BIRD_HEIGHT),
            )
            for filename in bird_files
        ]
        self.pipe_image = pygame.image.load(asset_dir / "pipe-green.png").convert_alpha()

    def reset(self) -> None:
        self.bird_y = SCREEN_HEIGHT // 2
        self.bird_velocity = 0.0
        self.pipes: list[PipePair] = []
        self.score = 0
        self.best_score = getattr(self, "best_score", 0)
        self.game_over = False
        self.started = False
        self.ground_scroll = 0
        self.last_pipe_time = pygame.time.get_ticks()

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS)
            running = self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_SPACE, pygame.K_UP):
                    self.flap()
                if event.key == pygame.K_r and self.game_over:
                    self.reset()
                if event.key == pygame.K_ESCAPE:
                    return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.flap()
        return True

    def flap(self) -> None:
        if self.game_over:
            self.reset()
            return
        self.started = True
        self.bird_velocity = FLAP_STRENGTH

    def update(self, dt: int) -> None:
        if self.game_over:
            ground_top = SCREEN_HEIGHT - GROUND_HEIGHT
            if self.bird_rect().bottom < ground_top:
                self.bird_velocity = min(self.bird_velocity + GRAVITY, MAX_FALL_SPEED)
                self.bird_y += self.bird_velocity
            return

        if not self.started:
            return

        self.bird_velocity = min(self.bird_velocity + GRAVITY, MAX_FALL_SPEED)
        self.bird_y += self.bird_velocity
        self.ground_scroll = (self.ground_scroll - PIPE_SPEED) % 24

        now = pygame.time.get_ticks()
        if now - self.last_pipe_time >= PIPE_INTERVAL_MS:
            self.spawn_pipe()
            self.last_pipe_time = now

        for pipe in self.pipes:
            pipe.x -= PIPE_SPEED

            if not pipe.scored and pipe.x + PIPE_WIDTH < BIRD_X:
                pipe.scored = True
                self.score += 1
                self.best_score = max(self.best_score, self.score)

        self.pipes = [pipe for pipe in self.pipes if not pipe.is_off_screen()]

        if self.check_collision():
            self.game_over = True

    def spawn_pipe(self) -> None:
        min_gap_center = 145
        max_gap_center = SCREEN_HEIGHT - GROUND_HEIGHT - 145
        self.pipes.append(
            PipePair(SCREEN_WIDTH + 18, random.randint(min_gap_center, max_gap_center))
        )

    def bird_rect(self) -> pygame.Rect:
        return pygame.Rect(
            BIRD_X - BIRD_WIDTH // 2,
            int(self.bird_y) - BIRD_HEIGHT // 2,
            BIRD_WIDTH,
            BIRD_HEIGHT,
        )

    def check_collision(self) -> bool:
        bird = self.bird_rect()
        if bird.top <= 0 or bird.bottom >= SCREEN_HEIGHT - GROUND_HEIGHT:
            return True

        return any(
            bird.colliderect(pipe.top_rect()) or bird.colliderect(pipe.bottom_rect())
            for pipe in self.pipes
        )

    def draw(self) -> None:
        self.screen.fill(SKY)
        self.draw_background()
        self.draw_pipes()
        self.draw_ground()
        self.draw_bird()
        self.draw_score()

        if not self.started and not self.game_over:
            self.draw_center_message("SPACE or CLICK", "to flap")
        elif self.game_over:
            self.draw_center_message("Game Over", "Press R, SPACE, or click")

        pygame.display.flip()

    def draw_background(self) -> None:
        for cloud_x, cloud_y, scale in (
            (58, 120, 1.0),
            (265, 92, 0.82),
            (338, 205, 1.1),
        ):
            self.draw_cloud(cloud_x, cloud_y, scale)

    def draw_cloud(self, x: int, y: int, scale: float) -> None:
        radius = int(20 * scale)
        pygame.draw.circle(self.screen, WHITE, (x, y), radius)
        pygame.draw.circle(self.screen, WHITE, (x + radius, y - 8), radius + 5)
        pygame.draw.circle(self.screen, WHITE, (x + radius * 2, y), radius)
        pygame.draw.rect(
            self.screen,
            WHITE,
            (x, y, radius * 2, radius),
            border_radius=radius // 2,
        )

    def draw_pipes(self) -> None:
        for pipe in self.pipes:
            self.draw_pipe(pipe.top_rect(), points_down=True)
            self.draw_pipe(pipe.bottom_rect(), points_down=False)

    def draw_pipe(self, rect: pygame.Rect, points_down: bool) -> None:
        if rect.height <= 0:
            return

        image = pygame.transform.scale(self.pipe_image, (rect.width, rect.height))
        if points_down:
            image = pygame.transform.flip(image, False, True)
        self.screen.blit(image, rect)

    def draw_ground(self) -> None:
        ground_y = SCREEN_HEIGHT - GROUND_HEIGHT
        pygame.draw.rect(self.screen, GROUND, (0, ground_y, SCREEN_WIDTH, GROUND_HEIGHT))
        pygame.draw.rect(self.screen, GROUND_DARK, (0, ground_y, SCREEN_WIDTH, 7))

        for x in range(-24 + self.ground_scroll, SCREEN_WIDTH, 24):
            pygame.draw.polygon(
                self.screen,
                GROUND_DARK,
                [(x, ground_y + 24), (x + 12, ground_y + 10), (x + 24, ground_y + 24)],
            )

    def draw_bird(self) -> None:
        bird = self.bird_rect()
        if self.started and not self.game_over:
            frame_index = (pygame.time.get_ticks() // 110) % len(self.bird_frames)
        else:
            frame_index = 1

        angle = max(-85, min(30, -self.bird_velocity * 5))
        rotated_bird = pygame.transform.rotozoom(self.bird_frames[frame_index], angle, 1.0)
        rotated_rect = rotated_bird.get_rect(center=bird.center)
        self.screen.blit(rotated_bird, rotated_rect)

    def draw_score(self) -> None:
        score_surface = self.font.render(str(self.score), True, WHITE)
        shadow_surface = self.font.render(str(self.score), True, BLACK)
        score_rect = score_surface.get_rect(center=(SCREEN_WIDTH // 2, 70))
        self.screen.blit(shadow_surface, score_rect.move(3, 3))
        self.screen.blit(score_surface, score_rect)

        best_surface = self.small_font.render(f"Best: {self.best_score}", True, WHITE)
        best_shadow = self.small_font.render(f"Best: {self.best_score}", True, BLACK)
        self.screen.blit(best_shadow, (16, 18))
        self.screen.blit(best_surface, (14, 16))

    def draw_center_message(self, title: str, subtitle: str) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 70))
        self.screen.blit(overlay, (0, 0))

        title_surface = self.font.render(title, True, WHITE)
        subtitle_surface = self.small_font.render(subtitle, True, WHITE)
        title_rect = title_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 35))
        subtitle_rect = subtitle_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 12))
        self.screen.blit(title_surface, title_rect)
        self.screen.blit(subtitle_surface, subtitle_rect)


if __name__ == "__main__":
    FlappyBirdGame().run()
