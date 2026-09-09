from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time


WINDOW_W = 1000
WINDOW_H = 800
CELL = 120
WALL_H = 110
PLAYER_R = 24
PLAYER_SPEED = 215.0
STRAFE_SPEED = 190.0
TURN_SPEED = 3.0
ENEMY_BULLET_SPEED = 260.0
PLAYER_BULLET_SPEED = 720.0
MAX_PLAYER_HEALTH = 1000000
START_AMMO = 45
PICKUP_R = 30
PORTAL_R = 48
KEY_R = 22

fovY = 85
camera_pos = (0, 500, 500)

keys_down = {}
last_time = 0
anim_time = 0.0
level_number = 1
score = 0
game_over = False
victory = False
message = ""
message_timer = 0.0
inspection_camera = False
shake_timer = 0.0
boss_phase_tick = 0.0

player = {
    "x": 0.0,
    "y": 0.0,
    "z": 42.0,
    "yaw": 0.0,
    "pitch": 0.0,
    "health": MAX_PLAYER_HEALTH,
    "ammo": START_AMMO,
    "has_key": False,
    "fire_cd": 0.0,
    "hurt_cd": 0.0,
}

current_maze = []
maze_w = 0
maze_h = 0
world_origin_x = 0
world_origin_y = 0
open_cells = []
portal_cell = (1, 1)
keycard_cell = (1, 1)

turrets = []
chasers = []
boss = None
player_bullets = []
enemy_bullets = []
health_packs = []
ammo_packs = []
sparks = []
lava_cells = []


LEVELS = {
    1: {
        "name": "Level 1: Sentry Maze",
        "turrets": 7,
        "chasers": 0,
        "health": 4,
        "ammo": 4,
        "portal": (13, 9),
        "maze": [
            "###############",
            "#S....#.......#",
            "#.###.#.#####.#",
            "#...#.#.....#.#",
            "###.#.#####.#.#",
            "#...#.....#...#",
            "#.#######.###.#",
            "#.....#...#...#",
            "#.###.#.###.#.#",
            "#...#.......#P#",
            "###############",
        ],
    },
    2: {
        "name": "Level 2: Hunter Corridors",
        "turrets": 0,
        "chasers": 8,
        "health": 5,
        "ammo": 5,
        "portal": (15, 11),
        "maze": [
            "#################",
            "#S......#.......#",
            "#.#####.#.#####.#",
            "#.....#.#.....#.#",
            "#####.#.#####.#.#",
            "#.....#.....#...#",
            "#.#########.###.#",
            "#...#.......#...#",
            "###.#.#######.#.#",
            "#...#.....#...#.#",
            "#.#######.#.###.#",
            "#.............#P#",
            "#################",
        ],
    },
    3: {
        "name": "Level 3: Crossfire Labyrinth",
        "turrets": 8,
        "chasers": 9,
        "health": 6,
        "ammo": 7,
        "portal": (19, 13),
        "maze": [
            "#####################",
            "#S......#.....#.....#",
            "#.#######.###.#.###.#",
            "#.....#...#...#...#.#",
            "#####.#.###.#####.#.#",
            "#...#.#.....#.....#.#",
            "#.#.#.#######.#####.#",
            "#.#...#.....#.....#.#",
            "#.#####.###.#####.#.#",
            "#.....#...#...#...#.#",
            "#####.###.###.#.###.#",
            "#...#.....#...#.....#",
            "#.#.#######.#.....#.#",
            "#.#...............#P#",
            "#####################",
        ],
    },
    4: {
        "name": "Level 4: Lava Core Boss",
        "turrets": 0,
        "chasers": 0,
        "health": 7,
        "ammo": 8,
        "portal": None,
        "maze": [
            "###################",
            "#S................#",
            "#.................#",
            "#....LL.....LL....#",
            "#....LL.....LL....#",
            "#.................#",
            "#..LL.........LL..#",
            "#..LL.........LL..#",
            "#.................#",
            "#....LL.....LL....#",
            "#....LL.....LL....#",
            "#.................#",
            "#.................#",
            "###################",
        ],
    },
}


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)

    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def clamp(v, low, high):
    return max(low, min(high, v))


def dist2(ax, ay, bx, by):
    dx = ax - bx
    dy = ay - by
    return dx * dx + dy * dy


def angle_to(ax, ay, bx, by):
    return math.atan2(by - ay, bx - ax)


def cell_to_world(col, row):
    return (
        world_origin_x + col * CELL + CELL * 0.5,
        world_origin_y + row * CELL + CELL * 0.5,
    )


def world_to_cell(x, y):
    col = int((x - world_origin_x) // CELL)
    row = int((y - world_origin_y) // CELL)
    return col, row


def is_wall_cell(col, row):
    if col < 0 or row < 0 or row >= maze_h or col >= maze_w:
        return True
    return current_maze[row][col] == "#"


def is_lava_cell(col, row):
    if col < 0 or row < 0 or row >= maze_h or col >= maze_w:
        return False
    return current_maze[row][col] == "L"


def position_is_free(x, y, radius=PLAYER_R):
    checks = [
        (x, y),
        (x + radius, y),
        (x - radius, y),
        (x, y + radius),
        (x, y - radius),
        (x + radius * 0.7, y + radius * 0.7),
        (x - radius * 0.7, y - radius * 0.7),
        (x + radius * 0.7, y - radius * 0.7),
        (x - radius * 0.7, y + radius * 0.7),
    ]
    for px, py in checks:
        c, r = world_to_cell(px, py)
        if is_wall_cell(c, r):
            return False
    return True


def line_of_sight(ax, ay, bx, by):
    steps = int(max(6, math.sqrt(dist2(ax, ay, bx, by)) / 35))
    for i in range(1, steps):
        t = i / float(steps)
        x = ax + (bx - ax) * t
        y = ay + (by - ay) * t
        c, r = world_to_cell(x, y)
        if is_wall_cell(c, r):
            return False
    return True


def random_open_cell(avoid=None):
    avoid = [cell for cell in (avoid or []) if cell is not None]
    candidates = []
    for cell in open_cells:
        good = True
        for other in avoid:
            if abs(cell[0] - other[0]) + abs(cell[1] - other[1]) < 4:
                good = False
                break
        if good:
            candidates.append(cell)
    if not candidates:
        candidates = open_cells[:]
    return random.choice(candidates)


def show_message(text, seconds=2.4):
    global message, message_timer
    message = text
    message_timer = seconds


def reset_player_for_new_game():
    player["health"] = MAX_PLAYER_HEALTH
    player["ammo"] = START_AMMO
    player["has_key"] = False
    player["fire_cd"] = 0.0
    player["hurt_cd"] = 0.0
    player["yaw"] = 0.0
    player["pitch"] = 0.0


def load_level(num, keep_resources=True):
    global level_number, current_maze, maze_w, maze_h, world_origin_x, world_origin_y
    global open_cells, portal_cell, keycard_cell, turrets, chasers, boss, player_bullets
    global enemy_bullets, health_packs, ammo_packs, sparks, lava_cells, boss_phase_tick
    level_number = num
    cfg = LEVELS[level_number]
    current_maze = cfg["maze"]
    maze_h = len(current_maze)
    maze_w = len(current_maze[0])
    world_origin_x = -maze_w * CELL * 0.5
    world_origin_y = -maze_h * CELL * 0.5
    open_cells = []
    lava_cells = []
    start_cell = (1, 1)

    for row in range(maze_h):
        for col in range(maze_w):
            ch = current_maze[row][col]
            if ch != "#":
                open_cells.append((col, row))
            if ch == "S":
                start_cell = (col, row)
            if ch == "L":
                lava_cells.append((col, row))

    sx, sy = cell_to_world(*start_cell)
    player["x"] = sx
    player["y"] = sy
    player["z"] = 42.0
    player["yaw"] = 0.0
    player["pitch"] = 0.0
    player["has_key"] = False
    player["fire_cd"] = 0.0
    player["hurt_cd"] = 0.0

    if not keep_resources:
        reset_player_for_new_game()

    portal_cell = cfg["portal"] if cfg["portal"] else None
    keycard_cell = random_open_cell([start_cell, portal_cell] if portal_cell else [start_cell])
    while keycard_cell == start_cell or keycard_cell == portal_cell or is_lava_cell(*keycard_cell):
        keycard_cell = random_open_cell([start_cell, portal_cell] if portal_cell else [start_cell])

    turrets = []
    chasers = []
    boss = None
    player_bullets = []
    enemy_bullets = []
    health_packs = []
    ammo_packs = []
    sparks = []
    boss_phase_tick = 0.0

    avoid = [cell for cell in [start_cell, portal_cell, keycard_cell] if cell is not None]
    spawn_pickups(cfg["health"], cfg["ammo"], avoid)
    spawn_enemies(cfg["turrets"], cfg["chasers"], avoid)
    if level_number == 4:
        bx, by = cell_to_world(maze_w // 2, maze_h // 2)
        boss = {
            "x": bx,
            "y": by,
            "health": 420,
            "max_health": 420,
            "phase": 1,
            "fire_cd": 1.0,
            "slam_cd": 3.0,
            "alive": True,
        }
    show_message(cfg["name"], 2.8)


def spawn_pickups(health_count, ammo_count, avoid):
    used = avoid[:]
    for _ in range(health_count):
        cell = random_open_cell(used)
        while is_lava_cell(*cell):
            cell = random_open_cell(used)
        used.append(cell)
        x, y = cell_to_world(*cell)
        health_packs.append({"x": x, "y": y, "value": 28, "spin": random.random() * 360})
    for _ in range(ammo_count):
        cell = random_open_cell(used)
        while is_lava_cell(*cell):
            cell = random_open_cell(used)
        used.append(cell)
        x, y = cell_to_world(*cell)
        ammo_packs.append({"x": x, "y": y, "value": 18, "spin": random.random() * 360})


def spawn_enemies(turret_count, chaser_count, avoid):
    used = avoid[:]
    for i in range(turret_count):
        cell = random_open_cell(used)
        while is_lava_cell(*cell):
            cell = random_open_cell(used)
        used.append(cell)
        x, y = cell_to_world(*cell)
        turrets.append({
            "x": x,
            "y": y,
            "health": 70,
            "max_health": 70,
            "yaw": random.random() * math.tau,
            "fire_cd": random.uniform(0.3, 1.6),
            "scan": random.choice([-1, 1]),
            "alive": True,
        })
    for i in range(chaser_count):
        cell = random_open_cell(used)
        while is_lava_cell(*cell):
            cell = random_open_cell(used)
        used.append(cell)
        x, y = cell_to_world(*cell)
        chasers.append({
            "x": x,
            "y": y,
            "health": 55,
            "max_health": 55,
            "speed": random.uniform(95, 125),
            "hurt_cd": 0.0,
            "alive": True,
            "wander": random.random() * math.tau,
            "respawnable": level_number >= 2,
        })


def restart_game():
    global score, game_over, victory
    score = 0
    game_over = False
    victory = False
    load_level(1, keep_resources=False)


def add_spark(x, y, z, color):
    for _ in range(8):
        sparks.append({
            "x": x,
            "y": y,
            "z": z,
            "vx": random.uniform(-80, 80),
            "vy": random.uniform(-80, 80),
            "vz": random.uniform(20, 140),
            "life": random.uniform(0.25, 0.55),
            "color": color,
        })


def fire_player_bullet():
    if game_over or victory:
        return
    if player["fire_cd"] > 0:
        return
    if player["ammo"] <= 0:
        show_message("Out of ammo. Find an ammo pack.", 1.5)
        player["fire_cd"] = 0.2
        return
    player["ammo"] -= 1
    player["fire_cd"] = 0.22
    yaw = player["yaw"]
    pitch = player["pitch"]
    fx = math.cos(yaw) * math.cos(pitch)
    fy = math.sin(yaw) * math.cos(pitch)
    fz = math.sin(pitch)
    bx = player["x"] + fx * 42
    by = player["y"] + fy * 42
    bz = player["z"] + 22 + fz * 10
    player_bullets.append({
        "x": bx,
        "y": by,
        "z": bz,
        "vx": fx * PLAYER_BULLET_SPEED,
        "vy": fy * PLAYER_BULLET_SPEED,
        "vz": fz * PLAYER_BULLET_SPEED,
        "life": 1.4,
        "damage": 35,
    })
    add_spark(bx, by, bz, (1.0, 0.88, 0.28))


def enemy_fire(ex, ey, ez, speed=ENEMY_BULLET_SPEED, damage=11):
    ang = angle_to(ex, ey, player["x"], player["y"])
    enemy_bullets.append({
        "x": ex,
        "y": ey,
        "z": ez,
        "vx": math.cos(ang) * speed,
        "vy": math.sin(ang) * speed,
        "vz": random.uniform(-10, 22),
        "life": 3.2,
        "damage": damage,
    })


def damage_player(amount, source=""):
    global game_over, shake_timer
    if game_over or victory:
        return
    player["health"] = max(0, player["health"] - amount)
    player["hurt_cd"] = 0.35
    shake_timer = 0.22
    if source:
        show_message(source, 1.1)
    if player["health"] <= 0:
        game_over = True
        show_message("Game Over - press R to restart", 999)


def kill_enemy(enemy, kind):
    global score
    enemy["alive"] = False
    if kind == "turret":
        score += 70
        add_spark(enemy["x"], enemy["y"], 80, (0.8, 0.9, 1.0))
    elif kind == "chaser":
        score += 55
        add_spark(enemy["x"], enemy["y"], 50, (1.0, 0.35, 0.25))
        if enemy.get("respawnable") and random.random() < 0.35 and level_number in (2, 3):
            cell = random_open_cell([world_to_cell(player["x"], player["y"])])
            x, y = cell_to_world(*cell)
            chasers.append({
                "x": x,
                "y": y,
                "health": 55,
                "max_health": 55,
                "speed": random.uniform(95, 130),
                "hurt_cd": 0.0,
                "alive": True,
                "wander": random.random() * math.tau,
                "respawnable": True,
            })


def next_level():
    global victory
    if level_number < 4:
        load_level(level_number + 1, keep_resources=True)
    else:
        victory = True
        show_message("Victory - boss defeated. Press R to play again.", 999)


def move_player(dt):
    if game_over or victory:
        return
    forward = 0.0
    strafe = 0.0
    if keys_down.get(b"w", 0) > 0:
        forward += 1.0
    if keys_down.get(b"s", 0) > 0:
        forward -= 1.0
    if keys_down.get(b"a", 0) > 0:
        strafe -= 1.0
    if keys_down.get(b"d", 0) > 0:
        strafe += 1.0
    if keys_down.get(b"q", 0) > 0:
        player["yaw"] += TURN_SPEED * dt
    if keys_down.get(b"e", 0) > 0:
        player["yaw"] -= TURN_SPEED * dt

    yaw = player["yaw"]
    dx = math.cos(yaw) * forward * PLAYER_SPEED * dt
    dy = math.sin(yaw) * forward * PLAYER_SPEED * dt
    dx += math.cos(yaw - math.pi / 2) * strafe * STRAFE_SPEED * dt
    dy += math.sin(yaw - math.pi / 2) * strafe * STRAFE_SPEED * dt

    if dx != 0 or dy != 0:
        nx = player["x"] + dx
        ny = player["y"] + dy
        if position_is_free(nx, player["y"]):
            player["x"] = nx
        if position_is_free(player["x"], ny):
            player["y"] = ny

    c, r = world_to_cell(player["x"], player["y"])
    if is_lava_cell(c, r):
        damage_player(int(38 * dt) + 1, "Lava damage")


def update_pickups(dt):
    for pack in health_packs:
        pack["spin"] += 90 * dt
    for pack in ammo_packs:
        pack["spin"] += 120 * dt

    for pack in health_packs[:]:
        if dist2(player["x"], player["y"], pack["x"], pack["y"]) < (PICKUP_R + PLAYER_R) ** 2:
            player["health"] = min(MAX_PLAYER_HEALTH, player["health"] + pack["value"])
            health_packs.remove(pack)
            show_message("Health restored", 1.2)
            add_spark(pack["x"], pack["y"], 45, (0.2, 1.0, 0.35))

    for pack in ammo_packs[:]:
        if dist2(player["x"], player["y"], pack["x"], pack["y"]) < (PICKUP_R + PLAYER_R) ** 2:
            player["ammo"] += pack["value"]
            ammo_packs.remove(pack)
            show_message("Ammo collected", 1.2)
            add_spark(pack["x"], pack["y"], 45, (0.35, 0.65, 1.0))

    if level_number <= 3 and not player["has_key"]:
        kx, ky = cell_to_world(*keycard_cell)
        if dist2(player["x"], player["y"], kx, ky) < (KEY_R + PLAYER_R) ** 2:
            player["has_key"] = True
            show_message("Keycard acquired - portal unlocked", 2.1)
            add_spark(kx, ky, 70, (1.0, 0.9, 0.2))

    if portal_cell:
        px, py = cell_to_world(*portal_cell)
        if dist2(player["x"], player["y"], px, py) < (PORTAL_R + PLAYER_R) ** 2:
            if player["has_key"]:
                next_level()
            else:
                show_message("Portal locked. Find the keycard.", 1.6)


def update_turrets(dt):
    for turret in turrets:
        if not turret["alive"]:
            continue
        turret["yaw"] += turret["scan"] * 0.65 * dt
        turret["fire_cd"] -= dt
        d = math.sqrt(dist2(turret["x"], turret["y"], player["x"], player["y"]))
        if d < 620 and line_of_sight(turret["x"], turret["y"], player["x"], player["y"]):
            turret["yaw"] = angle_to(turret["x"], turret["y"], player["x"], player["y"])
            if turret["fire_cd"] <= 0:
                enemy_fire(turret["x"], turret["y"], 82, ENEMY_BULLET_SPEED, 10)
                turret["fire_cd"] = random.uniform(0.85, 1.35)


def update_chasers(dt):
    for chaser in chasers:
        if not chaser["alive"]:
            continue
        chaser["hurt_cd"] = max(0, chaser["hurt_cd"] - dt)
        d = math.sqrt(dist2(chaser["x"], chaser["y"], player["x"], player["y"]))
        chase = d < 620 and line_of_sight(chaser["x"], chaser["y"], player["x"], player["y"])
        if chase:
            ang = angle_to(chaser["x"], chaser["y"], player["x"], player["y"])
        else:
            chaser["wander"] += random.uniform(-1.4, 1.4) * dt
            ang = chaser["wander"]
        speed = chaser["speed"] * (1.2 if chase else 0.45)
        nx = chaser["x"] + math.cos(ang) * speed * dt
        ny = chaser["y"] + math.sin(ang) * speed * dt
        if position_is_free(nx, chaser["y"], 22):
            chaser["x"] = nx
        else:
            chaser["wander"] += 1.7
        if position_is_free(chaser["x"], ny, 22):
            chaser["y"] = ny
        else:
            chaser["wander"] -= 1.1
        if d < PLAYER_R + 28 and player["hurt_cd"] <= 0:
            damage_player(10 + level_number * 2, "Enemy collision")


def update_boss(dt):
    global boss_phase_tick
    if not boss or not boss["alive"]:
        return
    boss_phase_tick += dt
    d = math.sqrt(dist2(boss["x"], boss["y"], player["x"], player["y"]))
    boss["phase"] = 2 if boss["health"] < boss["max_health"] * 0.55 else 1
    boss["fire_cd"] -= dt
    boss["slam_cd"] -= dt

    if boss["fire_cd"] <= 0:
        count = 8 if boss["phase"] == 1 else 12
        base = angle_to(boss["x"], boss["y"], player["x"], player["y"])
        for i in range(count):
            offset = (i - count // 2) * 0.12
            ang = base + offset
            enemy_bullets.append({
                "x": boss["x"],
                "y": boss["y"],
                "z": 120,
                "vx": math.cos(ang) * (240 + boss["phase"] * 35),
                "vy": math.sin(ang) * (240 + boss["phase"] * 35),
                "vz": 0,
                "life": 4.0,
                "damage": 13,
            })
        boss["fire_cd"] = 1.2 if boss["phase"] == 1 else 0.85

    if boss["slam_cd"] <= 0:
        add_spark(boss["x"], boss["y"], 30, (1.0, 0.25, 0.1))
        if d < 260 and line_of_sight(boss["x"], boss["y"], player["x"], player["y"]):
            damage_player(18, "Boss shockwave")
        boss["slam_cd"] = 3.1 if boss["phase"] == 1 else 2.2

    if d < 95 and player["hurt_cd"] <= 0:
        damage_player(22, "Boss body hit")


def update_bullets(dt):
    global score
    for bullet in player_bullets[:]:
        bullet["x"] += bullet["vx"] * dt
        bullet["y"] += bullet["vy"] * dt
        bullet["z"] += bullet["vz"] * dt
        bullet["life"] -= dt
        c, r = world_to_cell(bullet["x"], bullet["y"])
        hit_wall = is_wall_cell(c, r) or bullet["z"] < 5 or bullet["z"] > 210
        if hit_wall or bullet["life"] <= 0:
            add_spark(bullet["x"], bullet["y"], max(10, bullet["z"]), (0.9, 0.8, 0.2))
            player_bullets.remove(bullet)
            continue
        hit = False
        for turret in turrets:
            if turret["alive"] and dist2(bullet["x"], bullet["y"], turret["x"], turret["y"]) < 42 ** 2 and bullet["z"] < 135:
                turret["health"] -= bullet["damage"]
                hit = True
                add_spark(bullet["x"], bullet["y"], bullet["z"], (0.5, 0.9, 1.0))
                if turret["health"] <= 0:
                    kill_enemy(turret, "turret")
                break
        if not hit:
            for chaser in chasers:
                if chaser["alive"] and dist2(bullet["x"], bullet["y"], chaser["x"], chaser["y"]) < 36 ** 2 and bullet["z"] < 105:
                    chaser["health"] -= bullet["damage"]
                    chaser["hurt_cd"] = 0.25
                    hit = True
                    add_spark(bullet["x"], bullet["y"], bullet["z"], (1.0, 0.35, 0.22))
                    if chaser["health"] <= 0:
                        kill_enemy(chaser, "chaser")
                    break
        if not hit and boss and boss["alive"]:
            if dist2(bullet["x"], bullet["y"], boss["x"], boss["y"]) < 95 ** 2 and 20 < bullet["z"] < 190:
                boss["health"] -= bullet["damage"]
                hit = True
                score += 8
                add_spark(bullet["x"], bullet["y"], bullet["z"], (1.0, 0.15, 0.1))
                if boss["health"] <= 0:
                    boss["alive"] = False
                    score += 500
                    next_level()
        if hit and bullet in player_bullets:
            player_bullets.remove(bullet)

    for bullet in enemy_bullets[:]:
        bullet["x"] += bullet["vx"] * dt
        bullet["y"] += bullet["vy"] * dt
        bullet["z"] += bullet["vz"] * dt
        bullet["life"] -= dt
        c, r = world_to_cell(bullet["x"], bullet["y"])
        if is_wall_cell(c, r) or bullet["life"] <= 0:
            enemy_bullets.remove(bullet)
            continue
        if dist2(bullet["x"], bullet["y"], player["x"], player["y"]) < (PLAYER_R + 12) ** 2 and 0 < bullet["z"] < 105:
            damage_player(bullet["damage"], "Hit by enemy fire")
            if bullet in enemy_bullets:
                enemy_bullets.remove(bullet)


def update_sparks(dt):
    for sp in sparks[:]:
        sp["x"] += sp["vx"] * dt
        sp["y"] += sp["vy"] * dt
        sp["z"] += sp["vz"] * dt
        sp["vz"] -= 260 * dt
        sp["life"] -= dt
        if sp["life"] <= 0:
            sparks.remove(sp)


def update_game(dt):
    global message_timer, shake_timer
    if message_timer > 0:
        message_timer -= dt
    shake_timer = max(0, shake_timer - dt)
    for k in list(keys_down.keys()):
        keys_down[k] = max(0, keys_down[k] - dt)
    player["fire_cd"] = max(0, player["fire_cd"] - dt)
    player["hurt_cd"] = max(0, player["hurt_cd"] - dt)
    move_player(dt)
    update_pickups(dt)
    update_turrets(dt)
    update_chasers(dt)
    update_boss(dt)
    update_bullets(dt)
    update_sparks(dt)


def draw_cube_at(x, y, z, sx, sy, sz, color):
    glPushMatrix()
    glColor3f(*color)
    glTranslatef(x, y, z)
    glScalef(sx, sy, sz)
    glutSolidCube(1)
    glPopMatrix()


def draw_cylinder_between_z(x, y, z, radius, height, color, slices=14):
    glPushMatrix()
    glColor3f(*color)
    glTranslatef(x, y, z)
    gluCylinder(gluNewQuadric(), radius, radius, height, slices, 2)
    glPopMatrix()


def draw_floor():
    glBegin(GL_QUADS)
    for row in range(maze_h):
        for col in range(maze_w):
            x0 = world_origin_x + col * CELL
            y0 = world_origin_y + row * CELL
            x1 = x0 + CELL
            y1 = y0 + CELL
            if is_lava_cell(col, row):
                pulse = 0.2 + 0.12 * math.sin(anim_time * 6.0 + col)
                glColor3f(0.9, 0.18 + pulse, 0.02)
            else:
                shade = 0.18 if (row + col) % 2 == 0 else 0.23
                if level_number == 1:
                    glColor3f(shade, shade + 0.05, shade + 0.08)
                elif level_number == 2:
                    glColor3f(shade + 0.03, shade + 0.02, shade + 0.03)
                elif level_number == 3:
                    glColor3f(shade + 0.02, shade, shade + 0.07)
                else:
                    glColor3f(shade + 0.08, shade + 0.01, shade)
            glVertex3f(x0, y0, 0)
            glVertex3f(x1, y0, 0)
            glVertex3f(x1, y1, 0)
            glVertex3f(x0, y1, 0)
    glEnd()


def draw_walls():
    for row in range(maze_h):
        for col in range(maze_w):
            if current_maze[row][col] != "#":
                continue
            x, y = cell_to_world(col, row)
            base = 0.31 + 0.04 * ((row + col) % 2)
            draw_cube_at(x, y, WALL_H * 0.5, CELL, CELL, WALL_H, (base, base + 0.05, base + 0.08))
            draw_cube_at(x, y, WALL_H + 4, CELL * 0.96, CELL * 0.96, 8, (0.07, 0.09, 0.12))


def draw_pickups():
    for pack in health_packs:
        glPushMatrix()
        glTranslatef(pack["x"], pack["y"], 34)
        glRotatef(pack["spin"], 0, 0, 1)
        draw_cube_at(0, 0, 0, 38, 12, 12, (0.1, 0.9, 0.18))
        draw_cube_at(0, 0, 0, 12, 38, 12, (0.1, 0.9, 0.18))
        glPopMatrix()
    for pack in ammo_packs:
        glPushMatrix()
        glTranslatef(pack["x"], pack["y"], 28)
        glRotatef(pack["spin"], 0, 0, 1)
        draw_cube_at(0, 0, 0, 34, 22, 22, (0.12, 0.42, 1.0))
        draw_cube_at(0, 0, 18, 20, 12, 14, (0.92, 0.9, 0.2))
        glPopMatrix()


def draw_key_and_portal():
    if level_number <= 3 and not player["has_key"]:
        x, y = cell_to_world(*keycard_cell)
        spin = anim_time * 70.0
        glPushMatrix()
        glTranslatef(x, y, 48 + 8 * math.sin(spin * 0.05))
        glRotatef(spin, 0, 0, 1)
        draw_cube_at(0, 0, 0, 46, 30, 6, (1.0, 0.84, 0.08))
        draw_cube_at(13, 0, 7, 12, 10, 7, (0.06, 0.08, 0.1))
        glPopMatrix()

    if portal_cell:
        x, y = cell_to_world(*portal_cell)
        t = anim_time * 4.0
        unlocked = player["has_key"]
        glPushMatrix()
        glTranslatef(x, y, 60)
        glRotatef(t * 50, 0, 0, 1)
        color = (0.15, 0.95, 1.0) if unlocked else (0.8, 0.15, 0.25)
        draw_cube_at(0, 0, 0, 16, 110, 16, color)
        draw_cube_at(0, 0, 0, 110, 16, 16, color)
        glRotatef(45, 0, 0, 1)
        draw_cube_at(0, 0, 0, 12, 88, 12, color)
        draw_cube_at(0, 0, 0, 88, 12, 12, color)
        glPopMatrix()


def draw_turret(turret):
    if not turret["alive"]:
        return
    glPushMatrix()
    glTranslatef(turret["x"], turret["y"], 0)
    draw_cube_at(0, 0, 14, 56, 56, 28, (0.22, 0.26, 0.29))
    glTranslatef(0, 0, 44)
    glRotatef(math.degrees(turret["yaw"]), 0, 0, 1)
    draw_cube_at(0, 0, 0, 46, 38, 30, (0.38, 0.44, 0.5))
    glPushMatrix()
    glTranslatef(34, 0, 5)
    glRotatef(90, 0, 1, 0)
    glColor3f(0.08, 0.1, 0.12)
    gluCylinder(gluNewQuadric(), 8, 8, 58, 12, 2)
    glPopMatrix()
    draw_health_bar(0, 0, 52, turret["health"], turret["max_health"], 48)
    glPopMatrix()


def draw_chaser(chaser):
    if not chaser["alive"]:
        return
    flash = 0.25 if chaser["hurt_cd"] > 0 else 0.0
    glPushMatrix()
    glTranslatef(chaser["x"], chaser["y"], 0)
    ang = angle_to(chaser["x"], chaser["y"], player["x"], player["y"])
    glRotatef(math.degrees(ang), 0, 0, 1)
    draw_cube_at(0, 0, 28, 42, 34, 56, (0.72 + flash, 0.12, 0.1))
    draw_cube_at(18, 14, 68, 10, 10, 10, (1.0, 0.85, 0.2))
    draw_cube_at(18, -14, 68, 10, 10, 10, (1.0, 0.85, 0.2))
    draw_cube_at(-10, 0, 10, 52, 20, 18, (0.28, 0.07, 0.06))
    draw_health_bar(0, 0, 86, chaser["health"], chaser["max_health"], 45)
    glPopMatrix()


def draw_boss():
    if not boss or not boss["alive"]:
        return
    pulse = 0.08 * math.sin(anim_time * 6.0)
    glPushMatrix()
    glTranslatef(boss["x"], boss["y"], 0)
    glRotatef(anim_time * 15.0, 0, 0, 1)
    draw_cube_at(0, 0, 72, 132, 132, 144, (0.45 + pulse, 0.08, 0.05))
    draw_cube_at(0, 0, 168, 82, 82, 52, (0.28, 0.03, 0.02))
    for ang in (0, 90, 180, 270):
        glPushMatrix()
        glRotatef(ang, 0, 0, 1)
        draw_cube_at(98, 0, 84, 86, 28, 34, (0.22, 0.02, 0.02))
        glPopMatrix()
    draw_health_bar(0, 0, 218, boss["health"], boss["max_health"], 150)
    glPopMatrix()


def draw_health_bar(x, y, z, hp, max_hp, width):
    pct = clamp(hp / float(max_hp), 0, 1)
    glPushMatrix()
    glTranslatef(x, y, z)
    draw_cube_at(0, 0, 0, width, 5, 5, (0.18, 0.02, 0.02))
    draw_cube_at(-(width * (1 - pct)) * 0.5, 0, 3, width * pct, 7, 7, (0.1, 0.85, 0.18))
    glPopMatrix()


def draw_bullets():
    for bullet in player_bullets:
        draw_cube_at(bullet["x"], bullet["y"], bullet["z"], 12, 12, 12, (1.0, 0.9, 0.15))
    for bullet in enemy_bullets:
        draw_cube_at(bullet["x"], bullet["y"], bullet["z"], 16, 16, 16, (1.0, 0.18, 0.08))


def draw_sparks():
    glPointSize(4)
    glBegin(GL_POINTS)
    for sp in sparks:
        glColor3f(*sp["color"])
        glVertex3f(sp["x"], sp["y"], sp["z"])
    glEnd()


def draw_limb(length, radius, color):
    glColor3f(*color)
    gluCylinder(gluNewQuadric(), radius, radius * 0.82, length, 10, 2)


def draw_player_model():
    walk_active = (
        keys_down.get(b"w", 0) > 0 or keys_down.get(b"a", 0) > 0 or
        keys_down.get(b"s", 0) > 0 or keys_down.get(b"d", 0) > 0
    )
    walk = math.sin(anim_time * 12.0) * (18 if walk_active else 4)
    hurt_flash = 0.25 if player["hurt_cd"] > 0 else 0.0

    glPushMatrix()
    glTranslatef(player["x"], player["y"], 0)
    glRotatef(math.degrees(player["yaw"]), 0, 0, 1)

    draw_cube_at(0, 0, 1, 66, 46, 3, (0.015, 0.018, 0.022))

    draw_cube_at(0, 11, 8, 18, 12, 16, (0.04, 0.05, 0.06))
    draw_cube_at(0, -11, 8, 18, 12, 16, (0.04, 0.05, 0.06))
    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(0, side * 12, 18)
        glRotatef(side * walk, 0, 1, 0)
        draw_limb(32, 7, (0.12, 0.18, 0.24))
        glPopMatrix()

    draw_cube_at(0, 0, 54, 34, 42, 50, (0.1 + hurt_flash, 0.22, 0.28))
    draw_cube_at(-16, 0, 58, 16, 34, 42, (0.05, 0.08, 0.1))
    draw_cube_at(5, 0, 73, 24, 34, 13, (0.17 + hurt_flash, 0.45, 0.52))
    draw_cube_at(9, 0, 45, 20, 30, 10, (0.07, 0.13, 0.16))

    glPushMatrix()
    glTranslatef(0, 0, 93)
    draw_cube_at(0, 0, 0, 32, 32, 32, (0.16 + hurt_flash, 0.18, 0.2))
    draw_cube_at(14, 0, 2, 7, 28, 8, (0.05, 0.9, 1.0))
    glPushMatrix()
    glTranslatef(-8, 0, 16)
    draw_limb(18, 2, (0.03, 0.04, 0.05))
    glPopMatrix()
    glPopMatrix()

    for side in (-1, 1):
        glPushMatrix()
        glTranslatef(8, side * 25, 70)
        glRotatef(82 + side * walk * 0.4, 0, 1, 0)
        draw_limb(36, 6, (0.11, 0.17, 0.2))
        glPopMatrix()
    draw_cube_at(33, 0, 67, 48, 9, 9, (0.04, 0.045, 0.05))
    draw_cube_at(56, 0, 67, 18, 5, 5, (0.0, 0.0, 0.0))
    draw_cube_at(22, -8, 58, 12, 6, 16, (0.16, 0.13, 0.09))

    draw_cube_at(-2, 24, 63, 20, 4, 24, (0.1, 0.8, 0.25))
    draw_cube_at(-2, -24, 63, 20, 4, 24, (0.12, 0.38, 1.0))
    glPopMatrix()


def draw_player_weapon():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 1500)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()

    glTranslatef(0.18, -0.34, -0.72)

    draw_cube_at(-0.13, -0.08, 0.02, 0.16, 0.07, 0.12, (0.70, 0.46, 0.30))
    draw_cube_at(0.10, -0.08, 0.02, 0.16, 0.07, 0.12, (0.70, 0.46, 0.30))
    draw_cube_at(-0.18, -0.18, 0.06, 0.20, 0.08, 0.18, (0.08, 0.17, 0.22))
    draw_cube_at(0.04, -0.18, 0.06, 0.20, 0.08, 0.18, (0.08, 0.17, 0.22))

    draw_cube_at(0.02, 0, -0.08, 0.16, 0.10, 0.38, (0.12, 0.13, 0.15))
    draw_cube_at(0.02, -0.06, 0.08, 0.08, 0.06, 0.16, (0.18, 0.16, 0.12))

    glPushMatrix()
    glTranslatef(0.02, 0, -0.28)
    glRotatef(180, 1, 0, 0)
    glColor3f(0.04, 0.04, 0.05)
    gluCylinder(gluNewQuadric(), 0.025, 0.025, 0.25, 10, 2)
    glPopMatrix()

    if player["fire_cd"] > 0.12:
        glPushMatrix()
        glTranslatef(0.02, 0, -0.56)
        glColor3f(1, 0.75, 0.1)
        draw_cube_at(0, 0, 0, 0.08, 0.08, 0.08, (1, 0.75, 0.1))
        glPopMatrix()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_hud():
    draw_text(12, 772, "Score: " + str(score))
    draw_text(12, 744, "Health: " + str(player["health"]) + "/" + str(MAX_PLAYER_HEALTH))
    draw_text(12, 716, "Ammo: " + str(player["ammo"]))
    draw_text(12, 688, "Level: " + str(level_number) + "  Keycard: " + ("YES" if player["has_key"] or level_number == 4 else "NO"))
    if boss and boss["alive"]:
        draw_text(12, 660, "Boss HP: " + str(max(0, int(boss["health"]))))
    if message_timer > 0 and message:
        draw_text(330, 744, message, GLUT_BITMAP_HELVETICA_18)
    if game_over:
        draw_text(350, 410, "GAME OVER", GLUT_BITMAP_HELVETICA_18)
        draw_text(300, 374, "Press R to restart from Level 1")
    if victory:
        draw_text(360, 410, "MISSION COMPLETE", GLUT_BITMAP_HELVETICA_18)
        draw_text(300, 374, "Final Score: " + str(score) + "   Press R to restart")
    draw_crosshair()


def draw_crosshair():
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(0.9, 0.95, 1.0)
    cx = WINDOW_W // 2
    cy = WINDOW_H // 2
    glBegin(GL_QUADS)
    glVertex3f(cx - 14, cy - 1, 0)
    glVertex3f(cx - 5, cy - 1, 0)
    glVertex3f(cx - 5, cy + 1, 0)
    glVertex3f(cx - 14, cy + 1, 0)
    glVertex3f(cx + 5, cy - 1, 0)
    glVertex3f(cx + 14, cy - 1, 0)
    glVertex3f(cx + 14, cy + 1, 0)
    glVertex3f(cx + 5, cy + 1, 0)
    glVertex3f(cx - 1, cy - 14, 0)
    glVertex3f(cx + 1, cy - 14, 0)
    glVertex3f(cx + 1, cy - 5, 0)
    glVertex3f(cx - 1, cy - 5, 0)
    glVertex3f(cx - 1, cy + 5, 0)
    glVertex3f(cx + 1, cy + 5, 0)
    glVertex3f(cx + 1, cy + 14, 0)
    glVertex3f(cx - 1, cy + 14, 0)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_minimap():
    size = 150
    ox = WINDOW_W - size - 18
    oy = WINDOW_H - size - 18
    cw = size / float(maze_w)
    ch = size / float(maze_h)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glBegin(GL_QUADS)
    for row in range(maze_h):
        for col in range(maze_w):
            x0 = ox + col * cw
            y0 = oy + (maze_h - row - 1) * ch
            if current_maze[row][col] == "#":
                glColor3f(0.55, 0.6, 0.66)
            elif current_maze[row][col] == "L":
                glColor3f(1.0, 0.22, 0.04)
            else:
                glColor3f(0.05, 0.07, 0.09)
            glVertex3f(x0, y0, 0)
            glVertex3f(x0 + cw - 1, y0, 0)
            glVertex3f(x0 + cw - 1, y0 + ch - 1, 0)
            glVertex3f(x0, y0 + ch - 1, 0)
    glEnd()
    pc, pr = world_to_cell(player["x"], player["y"])
    draw_map_dot(ox + pc * cw + cw * 0.5, oy + (maze_h - pr - 1) * ch + ch * 0.5, 5, (0.1, 1.0, 0.25))
    if portal_cell:
        draw_map_dot(ox + portal_cell[0] * cw + cw * 0.5, oy + (maze_h - portal_cell[1] - 1) * ch + ch * 0.5, 4, (0.1, 0.8, 1.0))
    if level_number <= 3 and not player["has_key"]:
        draw_map_dot(ox + keycard_cell[0] * cw + cw * 0.5, oy + (maze_h - keycard_cell[1] - 1) * ch + ch * 0.5, 4, (1.0, 0.9, 0.1))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_map_dot(x, y, radius, color):
    glColor3f(*color)
    glBegin(GL_QUADS)
    glVertex3f(x - radius, y - radius, 0)
    glVertex3f(x + radius, y - radius, 0)
    glVertex3f(x + radius, y + radius, 0)
    glVertex3f(x - radius, y + radius, 0)
    glEnd()


def keyboardListener(key, x, y):
    global inspection_camera
    k = key.lower()
    if k in (b"w", b"a", b"s", b"d", b"q", b"e"):
        keys_down[k] = 0.16
    if k == b"r":
        restart_game()
    elif k == b" ":
        fire_player_bullet()
    elif k == b"c":
        inspection_camera = not inspection_camera


def specialKeyListener(key, x, y):
    if key == GLUT_KEY_LEFT:
        player["yaw"] += 0.08
    elif key == GLUT_KEY_RIGHT:
        player["yaw"] -= 0.08
    elif key == GLUT_KEY_UP:
        player["pitch"] = clamp(player["pitch"] + 0.04, -0.55, 0.45)
    elif key == GLUT_KEY_DOWN:
        player["pitch"] = clamp(player["pitch"] - 0.04, -0.55, 0.45)


def mouseListener(button, state, x, y):
    global inspection_camera
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        fire_player_bullet()
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        inspection_camera = not inspection_camera


def setupCamera():
    global camera_pos
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, 1.25, 0.1, 3000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if inspection_camera:
        radius = max(maze_w, maze_h) * CELL * 0.62
        cx = player["x"] - math.cos(player["yaw"]) * 320
        cy = player["y"] - math.sin(player["yaw"]) * 320
        cz = 260
        if not position_is_free(cx, cy, 20):
            cx = player["x"] - radius * 0.18
            cy = player["y"] - radius * 0.18
            cz = 420
        camera_pos = (cx, cy, cz)
        gluLookAt(cx, cy, cz, player["x"], player["y"], 65, 0, 0, 1)
        return

    yaw = player["yaw"]
    pitch = player["pitch"]
    eye_x = player["x"]
    eye_y = player["y"]
    eye_z = player["z"] + 28
    if shake_timer > 0:
        eye_x += random.uniform(-3, 3)
        eye_y += random.uniform(-3, 3)
        eye_z += random.uniform(-2, 2)
    look_x = eye_x + math.cos(yaw) * math.cos(pitch) * 180
    look_y = eye_y + math.sin(yaw) * math.cos(pitch) * 180
    look_z = eye_z + math.sin(pitch) * 180
    camera_pos = (eye_x, eye_y, eye_z)
    gluLookAt(eye_x, eye_y, eye_z, look_x, look_y, look_z, 0, 0, 1)


def idle():
    global last_time, anim_time
    now = time.time()
    if last_time == 0:
        last_time = now
    dt = now - last_time
    last_time = now
    anim_time += dt
    dt = min(dt, 0.05)
    update_game(dt)
    glutPostRedisplay()


def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WINDOW_W, WINDOW_H)
    setupCamera()

    draw_floor()
    draw_walls()
    draw_key_and_portal()
    draw_pickups()
    for turret in turrets:
        draw_turret(turret)
    for chaser in chasers:
        draw_chaser(chaser)
    draw_boss()
    if inspection_camera:
        draw_player_model()
    draw_bullets()
    draw_sparks()
    if not inspection_camera:
        draw_player_weapon()
    draw_hud()
    draw_minimap()
    glutSwapBuffers()


def init_gl():
    glEnable(GL_DEPTH_TEST)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(0, 0)
    glutCreateWindow(b"3D FPS Maze - Keycard Portal Boss")
    init_gl()
    restart_game()
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    glutMainLoop()


if __name__ == "__main__":
    main()
