from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import random
import math
import time

# Constants
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
LANE_WIDTH = 200
fovY = 120

# Game state
camera_pos = [0, 500, 500]
camera_mode = "third"
player_pos = [0, 30, 0]  # Y position adjusted for sphere radius
player_lane = 1
player_angle = 0
game_over = False
platform_offset = 0
platform_speed = 5

# Jump and slide states
is_jumping = False
jump_velocity = 0
gravity = -0.5
is_sliding = False
slide_duration = 0

def draw_player():
    player_pos[0] = (player_lane - 1) * LANE_WIDTH
    glPushMatrix()
    glTranslatef(player_pos[0], player_pos[1], player_pos[2])
    glRotatef(player_angle, 0, 0, 1)

    if game_over:
        glRotatef(90, 1, 0, 0)

    # Handle sliding transformation
    if is_sliding:
        glTranslatef(0, -15, 0)  # Adjust position to stay grounded
        glScalef(1, 0.5, 1)

    glColor3f(0.3, 0.9, 0.6)
    glutSolidSphere(30, 30, 30)

    glPopMatrix()



def keyboardListener(key, x, y):
    global player_angle, game_over, player_lane, is_jumping, is_sliding, slide_duration
    if game_over and key == b'r':
        restart_game()
        return
    if key == b'a' or key == b'd':
        if key == b'd' and player_lane > 0:
            player_lane -= 1
        elif key == b'a' and player_lane < 2:
            player_lane += 1
    elif key == b'v':
        global camera_mode
        camera_mode = "first" if camera_mode == "third" else "third"
    elif key == b' ':  # Jump
        global jump_velocity
        if not is_jumping and not is_sliding:
            is_jumping = True
            jump_velocity = 10
    elif key == b's':  # Slide
        if not is_sliding and not is_jumping:
            is_sliding = True
            slide_duration = 30


def specialKeyListener(key, x, y):
    global camera_pos, player_lane
    if key == GLUT_KEY_UP:
        camera_pos[1] += 10
    elif key == GLUT_KEY_DOWN:
        camera_pos[1] -= 10
    elif key == GLUT_KEY_LEFT:
        if player_lane > 0:
            player_lane -= 1
    elif key == GLUT_KEY_RIGHT:
        if player_lane < 2:
            player_lane += 1

def mouseListener(button, state, x, y):
    global camera_mode
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        camera_mode = "first" if camera_mode == "third" else "third"
def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(fovY, WINDOW_WIDTH/WINDOW_HEIGHT, 0.1, 3000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if camera_mode == "third":
        gluLookAt(
            camera_pos[0], camera_pos[1], camera_pos[2],
            player_pos[0], player_pos[1], player_pos[2],
            0, 1, 0
        )
    else:
        cx = player_pos[0] + 100 * math.cos(math.radians(player_angle))
        cz = player_pos[2] + 100 * math.sin(math.radians(player_angle))
        gluLookAt(
            player_pos[0], player_pos[1] + 50, player_pos[2],
            cx, player_pos[1] + 50, cz,
            0, 1, 0
        )



def draw_grid():
    global platform_offset
    step = 100
    num_segments = 400
    lane_width = LANE_WIDTH

    for lane in range(3):
        lane_x = (lane - 1) * LANE_WIDTH
        for i in range(num_segments):
            z_start = i * step - platform_offset
            z_end = (i + 1) * step - platform_offset

            glColor3f(0.7, 0.5, 0.95) if (i + lane) % 2 == 0 else glColor3f(1, 1, 1)
            
            glBegin(GL_QUADS)
            glVertex3f(lane_x - lane_width/2, 0, -z_start)
            glVertex3f(lane_x + lane_width/2, 0, -z_start)
            glVertex3f(lane_x + lane_width/2, 0, -z_end)
            glVertex3f(lane_x - lane_width/2, 0, -z_end)
            glEnd()


def update():
    global platform_offset, is_jumping, jump_velocity, is_sliding, slide_duration, player_pos
    if not game_over:
        platform_offset += platform_speed
        platform_offset %= math.inf

        # Jump mechanics
        if is_jumping:
            player_pos[1] += jump_velocity
            jump_velocity += gravity
            if player_pos[1] <= 30:
                player_pos[1] = 30
                is_jumping = False
                jump_velocity = 0

        # Slide mechanics
        if is_sliding:
            slide_duration -= 1
            if slide_duration <= 0:
                is_sliding = False # Reset offset to create infinite effect

def draw_simple_text(x, y, text, color=(1, 1, 1)):
    glColor3f(*color)
    glWindowPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_8_BY_13, ord(ch))

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    setupCamera()

    draw_grid()
    draw_player()
    
    glutSwapBuffers()

def idle():
    update()
    glutPostRedisplay()

def restart_game():
    global game_over, player_pos, player_lane, player_angle, platform_offset
    game_over = False
    player_lane = 1  # Middle lane
    player_pos = [0, 0, 40]
    player_angle = 0
    platform_offset = 0

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutCreateWindow(b"Infinite Runner")
    glEnable(GL_DEPTH_TEST)
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutIdleFunc(idle)
    glutMainLoop()

if __name__ == "__main__":
    main()
