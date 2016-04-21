import libtcodpy as libtcod;

SCREEN_WIDTH = 80;
SCREEN_HEIGHT = 30
LIMIT_FPS = 20

playerx = SCREEN_WIDTH / 2
playery = SCREEN_HEIGHT / 2

def handle_keys():
    global playerx, playery

    #movement keys
    if libtcod.console_is_key_pressed(libtcod.KEY_UP):
        player.move(0, -1)

    elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
        player.move(0, 1)

    elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
        player.move(-1, 0)

    elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
        player.move(1, 0)

    key = libtcod.console_check_for_keypress ()
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return True


# init
font = 'libtcod-1.5.1/data/fonts/arial12x12.png'
libtcod.console_set_custom_font (font, libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
libtcod.sys_set_fps(LIMIT_FPS)

# Initialize minor consoles
con = libtcod.console_new(SCREEN_WIDTH, SCREEN_HEIGHT)

# Object Class!
class Object:
    #this is a generic object: the player, a monster, an item, the stairs...
    #it's always represented by a character on screen.
    def __init__(self, x, y, char, color):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
 
    def move(self, dx, dy):
        print not map[self.x + dx][self.y + dy].blocked

        if not map[self.x + dx][self.y + dy].blocked:
            #move by the given amount
            self.x += dx
            self.y += dy
 
    def draw(self):
        #set the color and then draw the character that represents this object at its position
        libtcod.console_set_default_foreground(con, self.color)
        libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)
 
    def clear(self):
        #erase the character that represents this object
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)


################################################################################
# Map
################################################################################
MAP_WIDTH = 80
MAP_HEIGHT = 45

color_dark_wall = libtcod.Color(0, 0, 100)
color_dark_ground = libtcod.Color(50, 50, 150)

class Tile:
    #a tile of the map and its properties
    def __init__(self, blocked, block_sight = None):
        self.blocked = blocked
 
        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight

def make_map():
    global map
 
    # Fill map with "unblocked" tiles
    map = [[ Tile(False)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]

    map[30][22].blocked = True
    map[30][22].block_sight = True
    map[50][22].blocked = True
    map[50][22].block_sight = True

def render_all():
    #draw all objects in the list
    for object in objects:
        object.draw()

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            wall = map[x][y].block_sight
            if wall:
                libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET )
            else:
                libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET )

    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

################################################################################
# Initialize the map
################################################################################
make_map()

################################################################################
# Initialize actors and items
################################################################################
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', libtcod.white)
npc = Object(SCREEN_WIDTH/2 - 5, SCREEN_HEIGHT/2, '@', libtcod.yellow)
objects = [npc, player]

################################################################################
# Event Loop
################################################################################
while not libtcod.console_is_window_closed():

    # Render
    libtcod.console_set_default_foreground(0, libtcod.white)
    render_all()
    libtcod.console_flush()

    # Clear objects from screen on next tick to prevent ghosting
    for object in objects:
        object.clear()

    # Handle user input
    exit = handle_keys()
    if exit:
        break


