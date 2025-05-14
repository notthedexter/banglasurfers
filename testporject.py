import random
import time
import math
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# Window and game constants
WINDOW_WIDTH, WINDOW_HEIGHT = 1000, 800
LANE_WIDTH = 200
FOV_Y = 120
float_offset = math.sin(time.time() * 100) * 10

# Game state
camera_mode = "third"
player_pos = [0, 30, 0]
player_lane = 1  # 0=left,1=mid,2=right
camera_radius = 300  # Distance from the player
camera_angle = 0     # Horizontal angle in degrees

game_over = False
game_paused = False

# Platform movement
offset = 0
speed = 5  # constant movement speed

# Obstacles list
# Each obstacle: {lane, z_start, length, height, type: 'small'|'big', has_ramp: bool}
obstacles = []

# Timing
game_start = time.time()
last_color_change = game_start
path_color = [0.7, 0.5, 0.95]

# Player physics
is_jumping = False
jump_vel = 0
gravity = -0.9

# Player state on big blocks
on_block = False
block_end_z = 0

# Score & lives
score = 0
lives = 5
chance_big = 0.06
chance_coin = 0.2

# Spawn control
t_last_small = {0:-1,1:-1,2:-1}
min_small_dist = 200  # min gap between small blocks per lane


gun_start_time = 0
bullet_pos = None
bullet_speed = 50

# Timers and effect flags
shield_active = False
shield_start_time = 0

gun_active = False
gun_start_time = 0

speed_slowed = False
speed_start_time = 0
original_speed = speed  # Save original speed

cheat_sequence = []  # stores recent key entries
CHEAT_LIMIT = 10     # how many keys to track
cheat_message = ""
cheat_message_time = 0
CHEAT_MESSAGE_DURATION = 2  # seconds

skins = [
    {"body": (0.3, 0.9, 0.6), "pants": (0, 0, 1)},
    {"body": (1.0, 0.5, 0.5), "pants": (0.2, 0.2, 0.8)},
    {"body": (0.8, 0.8, 0.2), "pants": (0.1, 0.6, 0.1)},
    {"body": (0.5, 0.2, 0.7), "pants": (0.9, 0.3, 0.2)},
]
current_skin = 0


# Arrow keys: GLUT_KEY_UP = 101, GLUT_KEY_DOWN = 103
CHEATS = {
    (101, 101): "shield",  # up, up
    (103, 103): "gun",     # down, down
    (103, 101): "slow",    # down, up
    (101, 103): "score",   # up, down
}


player_angle = 1 # angle for dead state
leg_anim_angle = 0
leg_anim_direction = 1

def draw_player():
    global player_angle, leg_anim_angle, leg_anim_direction, current_skin

    player_pos[0] = (player_lane - 1) * LANE_WIDTH

    body_color = skins[current_skin]["body"]
    pant_color = skins[current_skin]["pants"]

    glPushMatrix()
    glTranslatef(*player_pos)

    glRotatef(-90, 1, 0, 0)
    glRotatef(90, 0, 0, 1)

    if game_over:
        glRotatef(90, 1, 0, 0)

    if not game_over and not is_jumping:
        leg_anim_angle += leg_anim_direction * 2
        if leg_anim_angle > 30 or leg_anim_angle < -30:
            leg_anim_direction *= -1
    else:
        leg_anim_angle = 0

    # Body
    glColor3f(*body_color)
    glutSolidCube(35)

    # Legs
    glPushMatrix()
    glTranslatef(0, -15, 0)
    glRotatef(180 + leg_anim_angle, 0, 1, 0)
    glColor3f(*pant_color)
    gluCylinder(gluNewQuadric(), 10, 4, 40, 10, 10)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0, 15, 0)
    glRotatef(180 - leg_anim_angle, 1, 1, 0)
    glColor3f(*pant_color)
    gluCylinder(gluNewQuadric(), 10, 4, 40, 10, 10)
    glPopMatrix()

    # Arms
    glPushMatrix()
    glTranslatef(0, 20, 20)
    glRotatef(90, 0, 1, 0)
    glColor3f(0.8, 0.6, 0.6)
    gluCylinder(gluNewQuadric(), 10, 4, 40, 10, 10)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(0, -20, 20)
    glRotatef(90, 0, 1, 0)
    glColor3f(0.8, 0.6, 0.6)
    gluCylinder(gluNewQuadric(), 10, 4, 40, 10, 10)
    glPopMatrix()

    # Head
    glPushMatrix()
    glTranslatef(0, 0, 40)
    glColor3f(0, 0, 0)
    glutSolidSphere(15, 20, 20)
    glPopMatrix()

    # Gun
    if gun_active:
        glPushMatrix()
        glTranslatef(0, 0, 30)
        glRotatef(90, 0, 1, 0)
        glColor3f(1.0, 0.7, 0.2)
        gluCylinder(gluNewQuadric(), 10, 3, 60, 10, 10)
        glPopMatrix()

    glPopMatrix()



def draw_grid():
    global offset, path_color
    step = 100
    segs = 1000  # Increased number of segments for a longer path
    

    for lane in range(3):
        x = (lane - 1) * LANE_WIDTH
        for i in range(segs):
            z0 = i * step - offset
            z1 = (i + 1) * step - offset

            color = path_color if (i + lane) % 2 == 0 else [1, 1, 1]
            glColor3f(*color)

            # Draw the ground grid
            glBegin(GL_QUADS)
            glVertex3f(x - LANE_WIDTH/2, 0, -z0)
            glVertex3f(x + LANE_WIDTH/2, 0, -z0)
            glVertex3f(x + LANE_WIDTH/2, 0, -z1)
            glVertex3f(x - LANE_WIDTH/2, 0, -z1)
            glEnd()

        

def generate_obstacles():
    global t_last_small, chance_big, chance_coin
    lanes = [0, 1, 2]
    min_z_gap = 250  # increased gap

    def is_zone_free(z, lane):
        return all(
            abs(obs['z_start'] - z) > min_z_gap or obs['lane'] != lane
            for obs in obstacles
        )

    active_lanes = {obs['lane'] for obs in obstacles if offset < obs['z_start'] < offset + 500}
    if len(active_lanes) >= 2:
        return

    has_big = any(obs['type'] == 'big' and offset < obs['z_start'] < offset + 500 for obs in obstacles)
    has_small = any(obs['type'] == 'small' and offset < obs['z_start'] < offset + 500 for obs in obstacles)
    has_bomb = any(obs['type'] == 'bomb' and offset < obs['z_start'] < offset + 500 for obs in obstacles)
    has_shield = any(obs['type'] == 'shield' and offset < obs['z_start'] < offset + 500 for obs in obstacles)
    has_speed = any(obs['type'] == 'speed' and offset < obs['z_start'] < offset + 500 for obs in obstacles)
    has_gun = any(obs['type'] == 'gun' and offset < obs['z_start'] < offset + 500 for obs in obstacles)
    has_wall = any(obs['type'] == 'wall' and offset < obs['z_start'] < offset + 500 for obs in obstacles)

    if not has_small and random.random() < chance_big:
        lane = random.choice([l for l in lanes if l not in active_lanes])
        count = random.choice([3, 4])
        base_z = offset + 800
        for i in range(count):
            z_start = base_z + i * 200
            if is_zone_free(z_start, lane):
                obstacles.append({
                    'lane': lane,
                    'z_start': z_start,
                    'length': 200,
                    'height': 100,
                    'type': 'big',
                    'has_ramp': (i == 0)
                })

    elif not has_big and random.random() < chance_coin:
        lane = random.choice([l for l in lanes if l not in active_lanes])
        z_start = offset + 600 + random.randint(0, 100)
        if is_zone_free(z_start, lane) and offset - t_last_small[lane] > min_small_dist:
            obstacles.append({
                'lane': lane,
                'z_start': z_start,
                'length': 30,
                'height': 40,
                'type': 'small',
                'has_ramp': False
            })
            t_last_small[lane] = offset

    elif not has_wall and random.random() < chance_coin:
        lane = random.choice([l for l in lanes if l not in active_lanes])
        z_start = offset + 600 + random.randint(0, 100)
        if is_zone_free(z_start, lane) and offset - t_last_small[lane] > min_small_dist:
            obstacles.append({
                'lane': lane,
                'z_start': z_start,
                'length': 40,
                'height': 30,
                'type': 'wall',
                'has_ramp': False
            })
            

    elif not has_bomb and random.random() < 0.1:
        lane = random.choice([l for l in lanes if l not in active_lanes])
        z_start = offset + 600 + random.randint(0, 100)
        if is_zone_free(z_start, lane) and offset - t_last_small[lane] > min_small_dist:
            obstacles.append({
                'lane': lane,
                'z_start': z_start,
                'length': 30,
                'height': 30,
                'type': 'bomb',
                'has_ramp': False
            })
            t_last_small[lane] = offset

    elif not has_shield and random.random() < 0.1:
        lane = random.choice([l for l in lanes if l not in active_lanes])
        z_start = offset + 600 + random.randint(0, 100)
        if is_zone_free(z_start, lane) and offset - t_last_small[lane] > min_small_dist:
            obstacles.append({
                'lane': lane,
                'z_start': z_start,
                'length': 30,
                'height': 40,
                'type': 'shield',
                'has_ramp': False
            })
            t_last_small[lane] = offset

    elif not has_speed and random.random() < 0.1:
        lane = random.choice([l for l in lanes if l not in active_lanes])
        z_start = offset + 600 + random.randint(0, 100)
        if is_zone_free(z_start, lane) and offset - t_last_small[lane] > min_small_dist:
            obstacles.append({
                'lane': lane,
                'z_start': z_start,
                'length': 30,
                'height': 40,
                'type': 'speed',
                'has_ramp': False
            })
            t_last_small[lane] = offset

    elif not has_gun and random.random() < 0.1:
        lane = random.choice([l for l in lanes if l not in active_lanes])
        z_start = offset + 600 + random.randint(0, 100)
        if is_zone_free(z_start, lane) and offset - t_last_small[lane] > min_small_dist:
            obstacles.append({
                'lane': lane,
                'z_start': z_start,
                'length': 30,
                'height': 40,
                'type': 'gun',
                'has_ramp': False
            })
            t_last_small[lane] = offset
    

def draw_obstacles():
    global on_block, block_end_z, player_pos, offset, lives
    global is_jumping, score
    global float_offset

    for obs in obstacles[:]:
        x = (obs['lane'] - 1) * LANE_WIDTH
        z0 = obs['z_start'] - offset

        # Obstacle color
        if obs['type'] == 'small':
            glColor3f(1, .98, 0)
            glPushMatrix()
            glTranslatef(x, obs['height'] / 2, -z0 - obs['length'] / 2)
            scale_z = obs['length'] / 30
            scale_y = obs['height'] / 30
            glScalef(1, scale_y, scale_z)
            glutSolidSphere(30, 30, 30)
            glPopMatrix()

        elif obs['type'] == 'big':
            glColor3f(0.2, 0.4, 0.8) if obs['has_ramp'] else glColor3f(0.8, 0.4, 0.1)
            glPushMatrix()
            glTranslatef(x, obs['height'] / 2, -z0 - obs['length'] / 2)
            scale_z = obs['length'] / 30
            scale_y = obs['height'] / 30
            glScalef(1, scale_y, scale_z)
            glutSolidCube(30)
            glPopMatrix()

        elif obs['type'] == 'wall':
            glColor3f(0, 0, 0)
            glPushMatrix()
            glTranslatef(x, obs['height'] / 2, -z0 - obs['length']/2)
            scale_z = obs['length'] /30
            scale_y = obs['height'] / 30
            glScalef(4, scale_y, scale_z)
            glutSolidCube(30)
            glPopMatrix()

        elif obs['type'] == 'bomb':
            glColor3f(1, 0, 1)
            scale_factor = 0.8 + 0.4 * math.sin(time.time() * 3)
            float_offset = math.sin(time.time() * 2) * 10  # oscillation
            glPushMatrix()
            glTranslatef(x, obs['height'] / 2 + float_offset, -z0 - obs['length'] / 2)
            glScalef(scale_factor, scale_factor, scale_factor)
            glutSolidSphere(30, 30, 30)
            glPopMatrix()


        elif obs['type'] == 'shield':
            float_offset = math.sin(time.time() * 2) * 10
            scale_factor = 1 + 0.2 * math.sin(time.time() * 3)
            glPushMatrix()

            # Move to shield position
            glTranslatef(x, obs['height'] / 2 + float_offset, -z0 - obs['length'] / 2)
            glScalef(scale_factor, scale_factor, scale_factor)

            # Draw back disc of shield
            glColor3f(0, 1, 0)
            glRotatef(90, 0, 1, 0)
            glRotatef(90, 1, 0, 0)  # Rotate to face forward
            gluDisk(gluNewQuadric(), 5, 30, 30, 1)

            # Draw a front emblem/bump (small sphere)
            glTranslatef(0, 0, 1)  # Slightly forward
            glColor3f(1, 1, 1)
            gluSphere(gluNewQuadric(), 8, 10, 10)

            glPopMatrix()


        elif obs['type'] == 'speed':
            glColor3f(0, 0, 1)
            glPushMatrix()
            scale_factor = 1 + 0.2 * math.sin(time.time() * 3)
            glTranslatef(x, obs['height'] / 2 + float_offset, -z0 - obs['length'] / 2)
            scale_z = obs['length'] / 30
            scale_y = obs['height'] / 30
            glScalef(scale_factor, scale_factor, scale_factor)
            glutSolidCube(30)
            glPopMatrix()


        elif obs['type'] == 'gun':
            glColor3f(1, 0, 0)
            glPushMatrix()
            scale_factor = 0.8 + 0.4 * math.sin(time.time() * 3)
            glTranslatef(x, obs['height'] / 2 + float_offset, -z0 - obs['length'] / 2)
            scale_z = obs['length'] / 30
            scale_y = obs['height'] / 30
            glScalef(scale_factor, scale_factor, scale_factor)
            glutSolidCylinder(30, 30, 30, 30)
            glPopMatrix()

        # Draw ramp if needed
        if obs['type'] == 'big' and obs['has_ramp']:
            glColor3f(0.9, 0.9, 0.2)
            glBegin(GL_TRIANGLES)
            glVertex3f(x - LANE_WIDTH / 2, 0, -z0-5)
            glVertex3f(x + LANE_WIDTH / 2, 0, -z0-5)
            glVertex3f(x, obs['height'], -z0-5)
            glEnd()

       
        # Ramp carry logic
        if obs['type'] == 'big' and obs['has_ramp']:
            ramp_start_z = obs['z_start']  # where ramp starts
            ramp_zone = 20  # how close the player must be to trigger climb
            if (
                abs(player_pos[0] - x) < LANE_WIDTH / 2
                and ramp_start_z - offset < player_pos[2] + ramp_zone < ramp_start_z - offset + ramp_zone
                and not is_jumping
            ):
                on_block = True
                block_end_z = obs['z_start'] + obs['length'] * 2  # give margin to drop after final big block
                player_pos[1] = obs['height'] + 30

        # Remove obstacles far behind
        if obs['z_start'] < offset - 200:
            obstacles.remove(obs)

    # Drop down after block ends
    if on_block and player_pos[2] < -(block_end_z - offset):
        on_block = False
        player_pos[1] = 30

def activate_cheat(action):
    global lives, score, shield_active, shield_start_time
    global gun_active, gun_start_time, speed_slowed, speed_start_time, speed, original_speed
    global cheat_message, cheat_message_time

    if action == "shield":
        shield_active = True
        shield_start_time = time.time()
        cheat_message = "CHEAT: Shield Activated"

    elif action == "gun":
        gun_active = True
        gun_start_time = time.time()
        cheat_message = "CHEAT: Gun Activated"

    elif action == "slow":
        if not speed_slowed:
            speed_slowed = True
            speed_start_time = time.time()
            speed = max(1, speed - 2)
            cheat_message = "CHEAT: Slow Motion"

    elif action == "score":
        score += 100
        lives += 1
        cheat_message = "CHEAT: +100 Score, +1 Life"

    cheat_message_time = time.time()



def change_path_color():
    global path_color, last_color_change
    if time.time() - last_color_change >= 30:
        path_color = [random.random(), random.random(), random.random()]
        last_color_change = time.time()

def reset_game():
    global game_over, offset, obstacles, score, lives, is_jumping, player_pos
    game_over = False
    offset = 0
    obstacles.clear()
    score = 0
    lives = 5
    is_jumping = False
    player_pos[1] = 30

def update():
    global offset, score, lives, game_over, is_jumping, jump_vel, bullet_pos, bullet_speed, speed
    global game_paused, shield_active, gun_active, gun_start_time, speed_slowed, speed_start_time, original_speed
    global speed_slowed, speed_start_time, original_speed, shield_active, shield_start_time

    if game_over or game_paused:
        return
    offset += speed
    change_path_color()
    generate_obstacles()
    # Jump physics
    if is_jumping:
        player_pos[1] += jump_vel
        jump_vel += gravity
        if player_pos[1] <= 30:
            player_pos[1] = 30
            is_jumping = False
    # Collision detection
    for obs in obstacles[:]:
        z0 = obs['z_start'] - offset
        x = (obs['lane'] - 1) * LANE_WIDTH
        player_x = player_pos[0]
        player_z = player_pos[2]

        dx = abs(player_x - x)
        dz = abs(player_z + z0)
        collision_range = dx < 40 and dz < obs['length'] / 2 and player_pos[1] <= obs['height'] + 10

        # Handle powerups
        if obs['type'] == 'bomb' and collision_range:
            score += random.randint(10, 100)
            obstacles.remove(obs)

        elif obs['type'] == 'shield' and collision_range:
            shield_active = True
            shield_start_time = time.time()
            obstacles.remove(obs)

        elif obs['type'] == 'speed' and collision_range:
            if not speed_slowed:
                speed_slowed = True
                speed_start_time = time.time()
                speed = max(1, speed - 2)  # Slow down
            obstacles.remove(obs)

        elif obs['type'] == 'gun' and collision_range:
            gun_active = True
            gun_start_time = time.time()
            obstacles.remove(obs)


        elif obs['type'] == 'small' and collision_range:
            score += 5
            obstacles.remove(obs)
        # Handle dangerous blocks (skip life loss if shield)
        elif obs['type'] in ['big', 'wall'] and not obs.get('has_ramp') and collision_range:
            if not shield_active:
                lives -= 1
            obstacles.remove(obs)

        if lives <= 0:
               game_over = True

        if gun_active and bullet_pos:
            bullet_pos[2] -= bullet_speed
            for obs in obstacles[:]:
                if obs['type'] in ['wall', 'big']:
                    ox = (obs['lane'] - 1) * LANE_WIDTH
                    oz = obs['z_start'] - offset
                    if abs(bullet_pos[0] - ox) < 40 and abs(-bullet_pos[2] - oz) < obs['length'] / 2:
                        obstacles.remove(obs)
                        bullet_pos = None
                        break
            if bullet_pos and bullet_pos[2] < -2000:
                bullet_pos = None
            if gun_active and time.time() - gun_start_time > 5:
                gun_active = False

            # ─── Timer Expiration for Shield ───
        if shield_active and time.time() - shield_start_time > 5:
            shield_active = False
            shield_start_time = 0

        # ─── Timer Expiration for Speed ───
        if speed_slowed and time.time() - speed_start_time > 5:
            speed_slowed = False
            speed_start_time = 0
            speed = original_speed

        # ─── Timer Expiration for Gun ───
        if gun_active and time.time() - gun_start_time > 10:
            gun_active = False
            gun_start_time = 0
            bullet_pos = None  # Clear any pending bullets


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
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


def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    setupCamera()
    draw_grid()
    draw_player()
    draw_obstacles()
    draw_text(10, WINDOW_HEIGHT - 20, f"Score: {score}")
    draw_text(10, WINDOW_HEIGHT - 50, f"Lives: {lives}")
    if game_over:
        draw_text(WINDOW_WIDTH/2 - 50, WINDOW_HEIGHT/2, "Game Over!")
        draw_text(WINDOW_WIDTH/2 - 100, WINDOW_HEIGHT/2 - 30, "Press 'R' to Restart")
    elif game_paused:
        draw_text(WINDOW_WIDTH/2 - 50, WINDOW_HEIGHT/2, "Game Paused")
    if bullet_pos:
        glPushMatrix()
        glColor3f(1, 1, 0)
        glTranslatef(bullet_pos[0], bullet_pos[1], bullet_pos[2])
        glutSolidSphere(10, 10, 10)
        glPopMatrix()
    
    if shield_active:
        remaining = max(0, 5 - int(time.time() - shield_start_time))
        draw_text(10, WINDOW_HEIGHT - 110, f"Shield: {remaining}s")

    if speed_slowed:
        remaining = max(0, 5 - int(time.time() - speed_start_time))
        draw_text(10, WINDOW_HEIGHT - 140, f"Slow: {remaining}s")

    if gun_active:
        remaining = max(0, 5 - int(time.time() - gun_start_time))
        draw_text(10, WINDOW_HEIGHT - 170, f"Gun: {remaining}s")

        # Show cheat activation message briefly
    if cheat_message and time.time() - cheat_message_time < CHEAT_MESSAGE_DURATION:
        draw_text(WINDOW_WIDTH/2 - 100, WINDOW_HEIGHT/2 + 100, cheat_message)
    glutSwapBuffers()


def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOV_Y, WINDOW_WIDTH / WINDOW_HEIGHT, 0.1, 3000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    # Camera follows the player
    if camera_mode == "third":
        # Third-person camera, follows the player from above
        if camera_mode == "third":
            # Convert angle to radians
            angle_rad = math.radians(camera_angle)

            # Camera rotates around player in horizontal circle (XZ plane)
            cam_x = player_pos[0] + camera_radius * math.sin(angle_rad)
            cam_y = player_pos[1] + 100  # height
            cam_z = player_pos[2] + camera_radius * math.cos(angle_rad)

            gluLookAt(cam_x, cam_y, cam_z,  # Camera position
                    player_pos[0], player_pos[1], player_pos[2],  # Look at player
                    0, 1, 0)  # Up vector

    else:
        # First-person camera, directly in front of the player
        head_height = 40
        eye_offset_z = 50

        eye_x = player_pos[0]
        eye_y = player_pos[1] + head_height + 30
        eye_z = player_pos[2] - 5

        look_x = eye_x
        look_y = eye_y
        look_z = eye_z - eye_offset_z

        gluLookAt(eye_x, eye_y, eye_z,
                  look_x, look_y, look_z,
                  0, 1, 0)


def keyboardListener(key, x, y):
    global player_lane, is_jumping, jump_vel, game_paused, game_over, camera_mode, gun_active, bullet_pos, camera_angle, current_skin
    if key == b'r' and game_over:
        restart_game()
        return
    if key == b'a' and player_lane > 0:
        player_lane -= 1
    elif key == b'd' and player_lane < 2:
        player_lane += 1
    elif key == b' ' and not is_jumping:
        is_jumping = True
        jump_vel = 10
    elif key == b'p':
        game_paused = not game_paused
    elif key == b'q':
        camera_angle += 5
    elif key == b'e':
        camera_angle -= 5
    elif key == b'v':
        # Change skin
        current_skin = (current_skin + 1) % len(skins)


def specialKeyListener(key, x, y):
    global player_lane, cheat_sequence
    if key == GLUT_KEY_LEFT and player_lane > 0:
        player_lane -= 1
    elif key == GLUT_KEY_RIGHT and player_lane < 2:
        player_lane += 1

    cheat_sequence.append(key)
    if len(cheat_sequence) > CHEAT_LIMIT:
        cheat_sequence.pop(0)

    # Check if any cheat is matched
    for code, action in CHEATS.items():
        if tuple(cheat_sequence[-len(code):]) == code:
            activate_cheat(action)
            cheat_sequence.clear()


def mouseListener(button, state, x, y):
    global bullet_pos, camera_mode

    # Left Mouse Button fires a bullet
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if gun_active and not bullet_pos:
            bullet_pos = [player_pos[0], player_pos[1], player_pos[2]]
    
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        # Right Mouse Button toggles camera tracking mode
        if camera_mode == "third":
            camera_mode = "first"
        else:
            camera_mode = "third"

    
def reset_game_state():
    global game_over, offset, obstacles, score, lives, is_jumping, player_pos, on_block, block_end_z
    global shield_active, gun_active, bullet_pos, gun_start_time
    global speed_slowed, speed_start_time, speed, original_speed
    global shield_active, shield_start_time

    game_over = False
    offset = 0
    obstacles.clear()
    score = 0
    lives = 5
    is_jumping = False
    player_pos = [0, 30, 0]
    on_block = False
    block_end_z = 0


    shield_active = False
    shield_start_time = 0

    speed_slowed = False
    speed_start_time = 0
    speed = original_speed

    gun_active = False
    gun_start_time = 0
    bullet_pos = None


def restart_game():
    reset_game_state()

def idle():
    update()
    glutPostRedisplay()


def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutCreateWindow(b"BanglaSurfers")
    glEnable(GL_DEPTH_TEST)
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(idle)
    glutMainLoop()

if __name__ == "__main__":
    main()
