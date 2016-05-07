import math
import textwrap
import random
import libtcodpy as libtcod;

SCREEN_WIDTH = 80;
SCREEN_HEIGHT = 45
VIEWPORT_WIDTH = 80
VIEWPORT_HEIGHT = 35
MENU_WIDTH = SCREEN_WIDTH - (SCREEN_WIDTH / 4)
LIMIT_FPS = 20

color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

TILE_TYPE = {
    'GRASS_1': {
        'char': '',
        'foreground_color': libtcod.Color(0, 255, 0),
        'background_color': libtcod.Color(0, 255, 0)
    },
    'GRASS_2': {
        'char': '',
        'foreground_color': libtcod.Color(0, 210, 0),
        'background_color': libtcod.Color(0, 210, 0)
    },
    'GRASS_3': {
        'char': '',
        'foreground_color': libtcod.Color(0, 190, 0),
        'background_color': libtcod.Color(0, 190, 0)
    },
    'FLOOR_WOOD': {
        'char': '_',
        'foreground_color': libtcod.Color(50, 20, 20),
        'background_color': libtcod.Color(100, 50, 70)
    },
    'WALL_STONE': {
        'char': '',
        'foreground_color': libtcod.Color(230, 230, 230),
        'background_color': libtcod.Color(230, 230, 230)
    }
}

#sizes and coordinates relevant for the GUI
BAR_WIDTH = 20
PANEL_HEIGHT = 10
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

################################################################################
# User Input
################################################################################
def handle_keys():
    global need_fov_refresh

    # Movement keys
    key = libtcod.console_check_for_keypress (True)


    if key.vk == libtcod.KEY_ENTER and key.lalt:
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())

    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit'

    # Only allow movement if we're in the 'playing' state
    if game_state == 'playing':
        if key.c == ord('k'):
            player_move_or_attack(0, -1)
            need_fov_refresh = True

        elif key.c == ord('j'):
            player_move_or_attack(0, 1)
            need_fov_refresh = True

        elif key.c == ord('h'):
            player_move_or_attack(-1, 0)
            need_fov_refresh = True

        elif key.c == ord('l'):
            player_move_or_attack(1, 0)
            need_fov_refresh = True

        elif key.c == ord('y'):
            player_move_or_attack(-1, -1)
            need_fov_refresh = True

        elif key.c == ord('u'):
            player_move_or_attack(1, -1)
            need_fov_refresh = True

        elif key.c == ord('n'):
            player_move_or_attack(1, 1)
            need_fov_refresh = True

        elif key.c == ord('b'):
            player_move_or_attack(-1, 1)
            need_fov_refresh = True

        # Pick up an item on the ground
        elif key.c == ord('g'):
            for object in objects:
                if object.x == player.x and object.y == player.y and object.item:
                    object.item.pick_up(player)

        # View inventory
        elif key.c == ord('i'):
            item = show_inventory('Here\'s what you\'ve got...')

            if item != None: 
                item.use()

        # Close door
        elif key.c == ord('c'):
            door_object = get_first_adjacent(player, 'door')
            if door_object is not None:
                door_object.door.close()
                need_fov_refresh = True
            else:
                message('There isn\'t a door close enough to shut.')

        elif key.c == ord('s'):
            smashable_object = get_first_adjacent(player, 'smashable')
            if smashable_object is not None:
                smashable_object.smashable.smash(player)
                need_fov_refresh = True
            else:
                message('There isn\'t anything nearby to smash')

        # Wait a turn
        elif key.c == ord('.'):
            pass

        else:
            return 'didnt-take-turn'

class Camera:
    def __init__(self, viewport_w, viewport_h, map_w, map_h):
        self.viewport_w = viewport_w
        self.viewport_h = viewport_h
        self.map_w = map_w
        self.map_h = map_h

    def center(self, target):
        self.x = target.x - (self.viewport_w / 2)
        self.y = target.y - (self.viewport_h / 2)
        if self.x < 0: self.x = 0
        if self.y < 0: self.y = 0
        if self.x >= self.map_w - self.viewport_w: self.x = self.map_w - self.viewport_w - 1
        if self.y >= self.map_h - self.viewport_h: self.y = self.map_h - self.viewport_h - 1

################################################################################
# Objects, Monsters, and Items
################################################################################
class Object:
    #this is a generic object: the player, a monster, an item, the stairs...
    #it's always represented by a character on screen.
    def __init__(self, x, y, char, name, color, 
        blocks=False, fighter=None, ai=None, item=None, door=None, smashable=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks

        self.fighter = fighter
        if self.fighter:  #let the fighter component know who owns it
            self.fighter.owner = self
 
        self.ai = ai
        if self.ai:  #let the AI component know who owns it
            self.ai.owner = self
        
        self.item = item
        if self.item:  #let the Item component know who owns it
            self.item.owner = self

        self.door = door
        if self.door:  #let the Item component know who owns it
            self.door.owner = self

        self.smashable = smashable
        if self.smashable:  #let the Item component know who owns it
            self.smashable.owner = self

    def move_towards(self, target_x, target_y):
        #vector from this object to the target, and distance
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
 
        #normalize it to length 1 (preserving direction), then round it and
        #convert to integer so the movement is restricted to the map grid
        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        moved = self.move(dx, dy)

    def distance_to(self, other):
        #return the distance to another object
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)
 
    def move(self, dx, dy):
        if not is_blocked(self.x+dx, self.y+dy):
            #move by the given amount
            self.x += dx
            self.y += dy
            return True
        else:
            return False
 
    def draw(self):
        # Don't draw if outside of the player's field-of-view
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            # set the color and then draw the character that represents this object at its position
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x - cam.x, self.y - cam.y, self.char, libtcod.BKGND_NONE)
 
    def clear(self):
        #erase the character that represents this object
        libtcod.console_put_char(con, self.x - cam.x, self.y - cam.y, ' ', libtcod.BKGND_NONE)

class Fighter:
    #combat-related properties and methods (monster, player, NPC).
    def __init__(self, hp, defense, power, death_function=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.death_function = death_function

    def take_damage(self, damage):
        # Decrement health
        self.hp -= damage

        #check for death. if there's a death function, call it
        if self.hp <= 0:
            if self.death_function is not None:
                self.death_function(self.owner)

    def heal(self, amount):
        # Heal by the given amount without going over the maximim
        self.hp += amount
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def attack(self, target):
        #a simple formula for attack damage
        damage = self.power - target.fighter.defense
 
        if damage > 0:
            #make the target take some damage
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage) + ' hit points.)')
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it has no effect!')

class BasicMonster:
    #AI for a basic monster.
    def take_turn(self):
        #a basic monster takes its turn. If you can see it, it can see you
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
 
            #move towards player if far away
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)
 
            #close enough, attack! (if the player is still alive.)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)

class Item:
    def __init__(self, use_function=None, carrier=None):
        self.use_function = use_function
        self.carrier = carrier

    #an item that can be picked up and used.
    def pick_up(self, carrier):
        #add to the player's inventory and remove from the map
        if len(inventory) >= 26:
            message('Your inventory is full, cannot pick up ' + self.owner.name + '.', libtcod.red)
        else:
            # Now this item is being carried by someone... or SOMETHING!
            self.carrier = carrier

            # TODO: Add to carrier inventory instead of player inventory
            inventory.append(self.owner)
            objects.remove(self.owner)

            message(carrier.name + ' picked up a ' + self.owner.name + '!', libtcod.green)
    
    def use(self):
        # If we have a 'use' function, call it.
        if self.use_function is None:
            message('The ', self.owner.name + ' cannot be used.  Sorey bud.')
        else:
            if self.use_function(self.carrier) != 'cancelled':
                # If not cancelled, destroy the item after use
                inventory.remove(self.owner)

class Door:
    def close(self):
        x = self.owner.x
        y = self.owner.y
        self.owner.char = '+'
        self.owner.blocks = True
        map[x][y].block_sight = True
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

    def open(self):
        x = self.owner.x
        y = self.owner.y
        self.owner.char = '/'
        self.owner.blocks = False
        map[x][y].block_sight = False
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

class Smashable:
    def smash(self, smasher=None):
        x = self.owner.x
        y = self.owner.y
        self.owner.char = '"'
        self.owner.blocks = False
        map[x][y].block_sight = False
        libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)
        if smasher is not None:
            message(smasher.name + ' smashes the ' + self.owner.name + '.')
        else:
            message(self.owner.name + ' is smashed.')

def player_death(player):
    #the game ended!
    global game_state
    message('You died!')
    game_state = 'dead'
 
    #for added effect, transform the player into a corpse!
    player.char = '%'
    player.color = libtcod.dark_red
 
    # We're on the floor now
    send_to_back(monster)

def monster_death(monster):
    #transform it into a nasty corpse! it doesn't block, can't be
    #attacked and doesn't move
    message(monster.name.capitalize() + ' is dead!')
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'Remains of ' + monster.name

    # We're on the floor now
    send_to_back(monster)

# Common item uses:
def cast_heal(target, amount=10):
    # Heal the player
    if target.fighter and target.fighter.hp < target.fighter.max_hp:
        if target == player: message('You are healed!', libtcod.light_violet)
        else: message('The ' + target.name + ' is healed.', libtcod.light_violet)
        target.fighter.heal(amount)
    else:
        print target.fighter
        return 'cancelled'

################################################################################
# Initialize actors and items
################################################################################
player_fighter = Fighter(hp=30, defense=8, power=10, death_function=player_death)
player = Object(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, '@', 'Player', libtcod.white, blocks=True, fighter=player_fighter)
objects = [player]
inventory = []

def send_to_back(object):
    #make this object be drawn first, so all others appear above it if they're in the same tile.
    global objects
    objects.remove(object)
    objects.insert(0, object)

################################################################################
# Additional player set-up
################################################################################
def player_move_or_attack(dx, dy):
    global fov_recompute
 
    #the coordinates the player is moving to/attacking
    x = player.x + dx
    y = player.y + dy
 
    #try to find an attackable object there
    target = None
    for object in objects:
        if object.x == x and object.y == y:
            target = object

            #attack if target found, move otherwise
            if target is not None and target.blocks:
                if object.fighter:
                    player.fighter.attack(target)
                    return

                elif object.door:
                    target.door.open()
                    fov_recompute = True
                    return
                    
    player.move(dx, dy)
    fov_recompute = True

################################################################################
# Map
################################################################################
MAP_WIDTH = 500
MAP_HEIGHT = 500

ROOM_MAX_SIZE = 20
ROOM_MIN_SIZE = 10
MAX_ROOMS = 450

MAX_ROOM_MONSTERS = 3
MAX_ROOM_ITEMS = 3

# Noise for generating terrain
height_map = libtcod.noise_new(2)

color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 150)
color_light_ground = libtcod.Color(200, 180, 50)

class Tile:
    #a tile of the map and its properties
    def __init__(self, blocked, data, block_sight = None, tile_type=None):
        self.blocked = blocked
        self.tile_type = tile_type
        self.data = data
 
        #by default, if a tile is blocked, it also blocks sight
        if block_sight is None: block_sight = blocked
        self.block_sight = block_sight
        self.explored = False

class Rect:
    #a rectangle on the map. used to characterize a room.
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        center_x = (self.x1 + self.x2) / 2
        center_y = (self.y1 + self.y2) / 2
        return (center_x, center_y)
 
    def intersect(self, other):
        #returns true if this rectangle intersects with another one
        return (self.x1 <= other.x2 and self.x2 >= other.x1 and
                self.y1 <= other.y2 and self.y2 >= other.y1)

def create_room(room):
    global map
    #go through the tiles in the rectangle and make them passable
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            map[x][y].blocked = False
            map[x][y].block_sight = False

def create_h_tunnel(x1, x2, y):
    global map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

def create_v_tunnel(y1, y2, x):
    global map
    #vertical tunnel
    for y in range(min(y1, y2), max(y1, y2) + 1):
        map[x][y].blocked = False
        map[x][y].block_sight = False

def place_objects(room):
    #choose random number of monsters
    num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)
 
    for i in range(num_monsters):
        #choose random spot for this monster
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)

        if is_blocked(x, y):
            continue
 
        if libtcod.random_get_int(0, 0, 100) < 80:  #80% chance of getting an orc
            #create an orc
            monster_fighter = Fighter(hp=10, defense=5, power=10, death_function=monster_death)
            monster_ai = BasicMonster()
            monster = Object(x, y, 'o', 'Orc', libtcod.desaturated_green, 
                blocks=True, fighter=monster_fighter, ai=monster_ai)
        else:
            #create a troll
            monster_fighter = Fighter(hp=10, defense=5, power=10, death_function=monster_death)
            monster_ai = BasicMonster()
            monster = Object(x, y, 'T', 'Troll', libtcod.darker_green, 
                blocks=True, fighter=monster_fighter, ai=monster_ai)
 
        objects.append(monster)

    #choose random number of items
    num_items = libtcod.random_get_int(0, 0, MAX_ROOM_ITEMS)
 
    for i in range(num_items):
        #choose random spot for this item
        x = libtcod.random_get_int(0, room.x1+1, room.x2-1)
        y = libtcod.random_get_int(0, room.y1+1, room.y2-1)
 
        #only place it if the tile is not blocked
        if not is_blocked(x, y):
            #create a healing potion
            item_component = Item(use_function=cast_heal)
            item = Object(x, y, '!', 'healing potion', libtcod.violet, 
                blocks=False, item=item_component)
 
            objects.append(item)
            send_to_back(item)  #items appear below other objects

def make_debug_map():
    global map
 
    # Fill map with "unblocked" tiles
    map = [[ Tile(False)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if y == 0 or y == MAP_HEIGHT-1 or x == 0 or x == MAP_WIDTH-1:
                map[x][y].blocked = True

    player.x = 20
    player.y = 20

def make_map():
    global map
 
    # Fill map with "unblocked" tiles
    map = [[ Tile(True)
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]

    rooms = []
    num_rooms = 0

    for r in range(MAX_ROOMS):
        #random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)
 
        #run through the other rooms and see if they intersect with this one
        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            #this means there are no intersections, so this room is valid
 
            #"paint" it to the map's tiles
            create_room(new_room)
 
            #center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()
 
            if num_rooms == 0:
                #this is the first room, where the player starts at
                player.x = new_x
                player.y = new_y
                
            else:
                #all rooms after the first:
                #connect it to the previous room with a tunnel
 
                #center coordinates of previous room
                (prev_x, prev_y) = rooms[num_rooms-1].center()
 
                #draw a coin (random number that is either 0 or 1)
                if libtcod.random_get_int(0, 0, 1) == 1:
                    #first move horizontally, then vertically
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    #first move vertically, then horizontally
                    create_v_tunnel(prev_y, new_y, prev_x)
                    create_h_tunnel(prev_x, new_x, new_y)

            # Add some objects to the room
            place_objects(new_room)
 
            #finally, append the new room to the list
            rooms.append(new_room)
            num_rooms += 1

            # optional: print "room number" to see how the map drawing worked
            # we may have more than ten rooms, so print 'A' for the first room, 'B' for the next...
            # room_no = Object(new_x, new_y, chr(65+num_rooms), libtcod.white)
            # objects.insert(0, room_no) #draw early, so monsters are drawn on top

def create_building(room):
    global map
    walls = []
    #go through the tiles in the rectangle and make them impassable
    for x in range(room.x1, room.x2):
        for y in range(room.y1, room.y2):
            map[x][y].data = TILE_TYPE['FLOOR_WOOD']
            
            if x == room.x1 or y == room.y1 or x == room.x2-1 or y == room.y2-1:
                map[x][y].blocked = True
                map[x][y].block_sight = True
                map[x][y].data = TILE_TYPE['WALL_STONE']

                if (x == room.x1 and y == room.y1) or (x == room.x2-1 and y == room.y1) or (x == room.x2-1 and y == room.y2-1) or (x == room.x1 and room.y2-1):
                    pass
                else:
                    walls.append((x, y))

    # Make doors
    num_doors = 2
    doors = []
    while len(doors) < num_doors:
        selected = walls[libtcod.random_get_int(0, 0, len(walls)-1)]
        if not selected in doors:
            x, y = selected
            map[x][y].block_sight = True
            map[x][y].blocked = False
            map[x][y].data = TILE_TYPE['FLOOR_WOOD']
            
            door_component = Door()
            new_door = Object(x, y, '+', 'door', libtcod.dark_sepia, 
                blocks=True, door=door_component)
            objects.append(new_door)
            doors.append(selected)

    # Make windows
    num_windows = 2
    windows = []
    while len(windows) < num_windows:
        selected = walls[libtcod.random_get_int(0, 0, len(walls)-1)]
        if not selected in doors and not selected in windows:
            x, y = selected
            map[x][y].block_sight = False
            map[x][y].blocked = False
            map[x][y].data = TILE_TYPE['FLOOR_WOOD']

            new_window = Object(x, y, '#', 'window', libtcod.light_blue, 
                blocks=True, smashable=Smashable())
            objects.append(new_window)
            windows.append(selected)

def make_outdoor_map():
    global map
 
    # Fill map with "unblocked" tiles
    data = libtcod.noise_get(height_map, [10, 10])
    map = [[ Tile(False, data=TILE_TYPE['GRASS_3'])
        for y in range(MAP_HEIGHT) ]
            for x in range(MAP_WIDTH) ]

    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            data = libtcod.noise_get(height_map, [x*0.1, y*0.1], libtcod.NOISE_PERLIN)
            # print data
            if data > 0.2:  data = TILE_TYPE['GRASS_1']
            elif data < -0.2: data = TILE_TYPE['GRASS_3']
            else: data = TILE_TYPE['GRASS_2']
            map[y][x].data = data

    buildings = []
    num_buildings = 0

    for r in range(MAX_ROOMS):
        #random width and height
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        #random position without going out of the boundaries of the map
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        #"Rect" class makes rectangles easier to work with
        new_room = Rect(x, y, w, h)
 
        #run through the other buildings and see if they intersect with this one
        failed = False
        for other_room in buildings:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            #this means there are no intersections, so this room is valid
 
            #"paint" it to the map's tiles
            create_building(new_room)
 
            #center coordinates of new room, will be useful later
            (new_x, new_y) = new_room.center()
 
            if num_buildings == 0:
                #this is the first room, where the player starts at
                player.x = new_x
                player.y = new_y

            # Add some objects to the room
            place_objects(new_room)
 
            #finally, append the new room to the list
            buildings.append(new_room)
            num_buildings += 1

            # optional: print "room number" to see how the map drawing worked
            # we may have more than ten rooms, so print 'A' for the first room, 'B' for the next...
            # room_no = Object(new_x, new_y, chr(65+num_rooms), libtcod.white)
            # objects.insert(0, room_no) #draw early, so monsters are drawn on top

def is_blocked(x, y):
    #first test the map tile
    if map[x][y].blocked:
        return True
 
    #now check for any blocking objects
    for object in objects:
        if object.blocks and object.x == x and object.y == y:
            return True
 
    return False      

def render_all():
    global fov_map, color_dark_wall, color_light_wall
    global color_dark_ground, color_light_ground
    global need_fov_refresh


    if need_fov_refresh:

        #recompute FOV if needed (the player moved or something)
        need_fov_refresh = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)
 
        #go through all tiles, and set their background color according to the FOV
        for y in range(VIEWPORT_HEIGHT):
            for x in range(VIEWPORT_WIDTH):

                map_x = cam.x + x
                map_y = cam.y + y

                visible = libtcod.map_is_in_fov(fov_map, map_x, map_y)
                wall = map[map_x][map_y].block_sight

                foreground_color = map[map_x][map_y].data['foreground_color']
                background_color = map[map_x][map_y].data['background_color']
                tile_char = map[map_x][map_y].data['char']
                
                if not visible:
                    #if it's not visible right now, the player can only see it if it's explored
                    if map[map_x][map_y].explored:
                        foreground_color = libtcod.color_lerp(foreground_color, libtcod.black, 0.5)
                        background_color = libtcod.color_lerp(background_color, libtcod.black, 0.5)
                    else:
                        foreground_color = libtcod.black;
                        background_color = libtcod.black;

                else:
                    #it's visible

                    #since it's visible, explore it
                    map[map_x][map_y].explored = True

                if len(tile_char) > 0: libtcod.console_put_char(con, x, y, tile_char)
                libtcod.console_set_char_foreground(con, x, y, foreground_color )
                libtcod.console_set_char_background(con, x, y, background_color )
 
    #draw all objects in the list
    for object in objects:
        if object != player:
            object.draw()
    player.draw()
     
    #blit the contents of "con" to the root console
    libtcod.console_blit(con, 0, 0, VIEWPORT_WIDTH, VIEWPORT_HEIGHT, 0, 0, 0)

    #prepare to render the GUI panel
    libtcod.console_set_default_background(panel, libtcod.black)
    libtcod.console_clear(panel)
 
    #show the player's stats
    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp,
        libtcod.light_red, libtcod.darker_red)

    #print the game messages, one line at a time
    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1
 
    #blit the contents of "panel" to the root console
    libtcod.console_blit(panel, 0, 0, VIEWPORT_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)

def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    #render a bar (HP, experience, etc). first calculate the width of the bar
    bar_width = int(float(value) / maximum * total_width)
 
    #render the background first
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)
 
    #now render the bar on top
    libtcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    #finally, some centered text with the values
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
        name + ': ' + str(value) + '/' + str(maximum))

def get_first_adjacent(target, component_name):
    x = target.x
    y = target.y

    adjacent_tiles = [
        # N
        (x, y-1),
        # NE
        (x+1,y-1),
        # E
        (x+1,y),
        # SE
        (x+1,y+1),
        # S
        (x,y+1),
        # SW
        (x-1,y+1),
        # W
        (x-1,y),
        # NW
        (x-1,y-1)
    ]
    for tile in adjacent_tiles:
        x, y = tile
        for object in objects:
            if object.x == x and object.y == y and hasattr(target, component_name) and getattr(object, component_name) != None:
                return object
    return None

################################################################################
# Game Messages
################################################################################
game_msgs = []

def message(new_msg, color = libtcod.white):
    #split the message if necessary, among multiple lines
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)
 
    for line in new_msg_lines:
        #if the buffer is full, remove the first line to make room for the new one
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]
 
        #add the new line as a tuple, with the text and the color
        game_msgs.append( (line, color) )

################################################################################
# Menus
################################################################################
def show_menu(header, options, width):
    if len(options) > 26: raise ValueError('Menu cannot not have more than 26 items.')
    
    #calculate total height for the header (after auto-wrap) and one line per option
    header_height = libtcod.console_get_height_rect(con, 0, 0, width, SCREEN_HEIGHT, header)
    height = len(options) + header_height

    #create an off-screen console that represents the menu's window
    window = libtcod.console_new(width, height)
 
    #print the header, with auto-wrap
    libtcod.console_set_default_foreground(window, libtcod.white)
    libtcod.console_print_rect_ex(window, 0, 0, width, height, libtcod.BKGND_NONE, libtcod.LEFT, header)

    #print all the options
    y = header_height
    letter_index = ord('a')
    for option_text in options:
        text = '(' + chr(letter_index) + ') ' + option_text
        libtcod.console_print_ex(window, 0, y, libtcod.BKGND_NONE, libtcod.LEFT, text)
        y += 1
        letter_index += 1
    
    #blit the contents of "window" to the root console
    x = SCREEN_WIDTH/2 - width/2
    y = SCREEN_HEIGHT/2 - height/2
    libtcod.console_blit(window, 0, 0, width, height, 0, x, y, 1.0, 0.7)

    #present the root console to the player and wait for a key-press
    libtcod.console_flush()
    key = libtcod.console_wait_for_keypress(True)

    index = key.c - ord('a')
    if index >=0 and index < len(options): return index;
    return None

def show_inventory(header):
    # Show the inventory if we have stuff to show
    if len(inventory) == 0:
        message('Your inventory is empty!')
    else:
        index = show_menu(header, [item.name for item in inventory], MENU_WIDTH)
        
        # If an item was chosen, return it.
        if index is None: return None
        else: return inventory[index].item

################################################################################
# Field of View
################################################################################
FOV_ALGO = 0  #default FOV algorithm
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 30

# Do we need to refresh FOV this turn?
need_fov_refresh = True

# Initialize FOV map
def make_fov_map():
    global fov_map
    fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            libtcod.map_set_properties(fov_map, x, y, not map[x][y].block_sight, not map[x][y].blocked)

################################################################################
# Initialization
################################################################################
font = 'arial20x20.png'
libtcod.console_set_custom_font (font, libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'python/libtcod tutorial', False)
libtcod.sys_set_fps(LIMIT_FPS)

# Track game state
game_state = 'playing'
player_action = 'None'

# Initialize minor consoles
con = libtcod.console_new(VIEWPORT_WIDTH, VIEWPORT_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

cam = Camera(VIEWPORT_WIDTH, VIEWPORT_HEIGHT, MAP_WIDTH, MAP_HEIGHT)

make_outdoor_map()
#make_debug_map()
make_fov_map()

#a warm welcoming message!
message('Welcome to the end of the world...', libtcod.red)

################################################################################
# Event Loop
################################################################################
while not libtcod.console_is_window_closed():

    # Render
    libtcod.console_set_default_foreground(0, libtcod.white)
    cam.center(player)
    render_all()
    libtcod.console_flush()

    # Clear objects from screen on next tick to prevent ghosting
    for object in objects:
        object.clear()

    # Handle user input
    player_action = handle_keys()

    #let monsters take their turn
    if game_state == 'playing' and player_action != 'didnt-take-turn':
        for object in objects:
            if object.ai:
                object.ai.take_turn()

    if player_action == 'exit':
        break


