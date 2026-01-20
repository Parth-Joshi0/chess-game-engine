import pygame
from dataclasses import dataclass

BOARD_SIZE = 8
SQ_SIZE = 80
WIDTH = HEIGHT = BOARD_SIZE * SQ_SIZE
FPS = 60

@dataclass
class GameConfig:
    white_player: str = "engine" # "human" or "engine"
    black_player: str = "engine"

    engine_mode: str = "depth" # "depth" or "time"
    depth: int = 4
    time_limit: float = 3 # seconds per move

class Button:
    def __init__(self, rect, text, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font

    def draw(self, screen):
        pygame.draw.rect(screen, (245,245,245), self.rect, border_radius=12)
        pygame.draw.rect(screen, (40,40,40), self.rect, 2, border_radius=12)
        img = self.font.render(self.text, True, (20,20,20))
        screen.blit(img, img.get_rect(center=self.rect.center))

    def clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )

class Toggle:
    # Clickable option select that cycles through options
    def __init__(self, rect, label, options, font, value=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.options = options
        self.font = font
        self.value = value if value is not None else options[0]

    def draw(self, screen):
        label_img = self.font.render(self.label, True, (240,240,240))
        screen.blit(label_img, (self.rect.x, self.rect.y - 28))

        pygame.draw.rect(screen, (245,245,245), self.rect, border_radius=12)
        pygame.draw.rect(screen, (40,40,40), self.rect, 2, border_radius=12)

        val_img = self.font.render(self.value.upper(), True, (20,20,20))
        screen.blit(val_img, val_img.get_rect(center=self.rect.center))

    def handle(self, event):
        # Cycle to next option on click
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        ):
            i = self.options.index(self.value)
            self.value = self.options[(i + 1) % len(self.options)]
            return True
        return False

class Slider:
    # Slider for numeric values (Time)
    def __init__(self, x, y, w, min_v, max_v, value, font, label, is_int=True):
        self.track = pygame.Rect(x, y, w, 10)
        self.min_v = min_v
        self.max_v = max_v
        self.value = value
        self.font = font
        self.label = label
        self.is_int = is_int
        self.dragging = False
        self.knob_r = 12

    def _t(self):
        # Get normalized position (0 to 1) of current value
        return (self.value - self.min_v) / (self.max_v - self.min_v)

    def _knob_pos(self):
        # Calculate Pixel Position of slider knob
        x = int(self.track.x + self._t() * self.track.w)
        y = self.track.centery
        return x, y

    def _set_from_mouse(self, mx):
        # Updates values based on mouse x position
        t = (mx - self.track.x) / self.track.w
        t = max(0.0, min(1.0, t))
        v = self.min_v + t * (self.max_v - self.min_v)
        self.value = int(round(v)) if self.is_int else round(v, 2)

    def draw(self, screen):
        txt = f"{self.label}: {self.value}"
        img = self.font.render(txt, True, (240,240,240))
        screen.blit(img, (self.track.x, self.track.y - 28))

        pygame.draw.rect(screen, (220,220,220), self.track, border_radius=8)
        kx, ky = self._knob_pos()
        pygame.draw.circle(screen, (245,245,245), (kx, ky), self.knob_r)
        pygame.draw.circle(screen, (40,40,40), (kx, ky), self.knob_r, 2)

    def handle(self, event):
        # Handle mouse drag events
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            kx, ky = self._knob_pos()
            if self.track.collidepoint(event.pos) or (
                pygame.Vector2(event.pos) - pygame.Vector2((kx, ky))
            ).length() <= self.knob_r + 6:
                self.dragging = True
                self._set_from_mouse(event.pos[0])
                return True

        if event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_mouse(event.pos[0])
            return True

        if event.type == pygame.MOUSEBUTTONUP and self.dragging:
            self.dragging = False
            return True

        return False

def run_home_screen(screen, clock) -> GameConfig:
    # Display Configuration Menu and Return game Settings
    title_font = pygame.font.SysFont("arialunicode", 56)
    font = pygame.font.SysFont("arialunicode", 26)
    small = pygame.font.SysFont("arialunicode", 20)

    cfg = GameConfig()
    cx = WIDTH // 2
    y0 = 150
    gap = 92

    white_t = Toggle((cx - 160, y0, 320, 52), "White", ["human", "engine"], font)
    black_t = Toggle((cx - 160, y0 + gap, 320, 52), "Black", ["human", "engine"], font)
    mode_t  = Toggle((cx - 160, y0 + 2*gap, 320, 52), "Engine control", ["depth", "time"], font)

    depth_s = Slider(cx - 200, y0 + 3*gap, 400, 1, 8, cfg.depth, font, "Depth", True)
    time_s  = Slider(cx - 200, y0 + 3*gap, 400, 0.1, 5.0, cfg.time_limit, font, "Time (sec)", False)

    start_btn = Button((cx - 160, HEIGHT - 140, 320, 70), "START GAME", font)

    while True:
        clock.tick(FPS)
        screen.fill((22,22,22))

        title = title_font.render("CHESS ENGINE", True, (245,245,245))
        screen.blit(title, title.get_rect(center=(cx, 70)))

        hint = small.render("Click to change • Drag slider • ESC to quit", True, (170,170,170))
        screen.blit(hint, hint.get_rect(center=(cx, 110)))

        white_t.draw(screen)
        black_t.draw(screen)
        mode_t.draw(screen)

        if mode_t.value == "depth":
            depth_s.draw(screen)
        else:
            time_s.draw(screen)

        start_btn.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                raise SystemExit

            white_t.handle(event)
            black_t.handle(event)
            mode_t.handle(event)

            (depth_s if mode_t.value == "depth" else time_s).handle(event)

            if start_btn.clicked(event):
                cfg.white_player = white_t.value
                cfg.black_player = black_t.value
                cfg.engine_mode = mode_t.value
                cfg.depth = depth_s.value
                cfg.time_limit = time_s.value
                return cfg

        pygame.display.flip()