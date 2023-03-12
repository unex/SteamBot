import os
import base64

from steam.client import SteamClient
from steam.enums import EResult
from steam.enums.emsg import EMsg
from steam.guard import generate_twofactor_code

import redis
from gevent import sleep

USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")
SHARED_SECRET = os.environ.get("SHARED_SECRET")
REDIS_URI = os.environ.get("REDIS_URI")

print(USERNAME)
print(PASSWORD)
print(SHARED_SECRET)

app_ids = [
        221410, # Steam for Linux
        753, # Steam
        7, # Steam Client
        250820, # SteamVR
        8, # winui2
        480, # Spacewar
    ]

redis = redis.Redis.from_url(REDIS_URI)

client = SteamClient()
client.set_credential_location(".")


class SharedLibrary:
    __slots__ = ('friend', 'game')

    allowed = [
        76561198236856148, # dewisblaze
        76561198105896825, # TheRadioactivePotato
    ]

    def __init__(self):
        self.get()

    def get(self):
        try:
            self.friend = int(redis.get("steambot_friend").decode('utf-8'))
        except AttributeError:
            self.friend = 0

        try:
            self.game = int(redis.get("steambot_game").decode('utf-8'))
        except AttributeError:
            self.game = 0

        print(f'SharedLibrary {self.friend=} {self.game=}')

    def clear(self):
        redis.set("steambot_friend", 0)
        redis.set("steambot_game", 0)
        self.get()

    def set(self, friend, game):
        redis.set("steambot_friend", friend)
        redis.set("steambot_game", game)
        self.get()

sl = SharedLibrary()


@client.on("error")
def handle_error(result):
    print(f'Logon result: {repr(result)}')

@client.on("channel_secured")
def send_login():
    if client.relogin_available:
        client.relogin()

@client.on("connected")
def handle_connected():
    print(f'Connected to {client.current_server_addr}')

@client.on("reconnect")
def handle_reconnect(delay):
    print(f'Reconnect in {delay}')

@client.on("disconnected")
def handle_disconnect():
    print("Disconnected.")

    if client.relogin_available:
        client.reconnect(maxdelay=30)

@client.on("logged_on")
def handle_after_logon():
    print(f'Logged on as: {client.user.name} - {client.steam_id.community_url}')

    if not sl.friend:
        client.games_played(app_ids)

@client.on("chat_message")
def handle_chat_message(user, message):
    if(message.startswith('/unlock') and user.steam_id in sl.allowed):
        print(f'{user.name} has requested an unlock')

        client.games_played([])

        user.send_message("You have 30 seconds")

        sleep(30)

        game = user.get_ps('game_played_app_id')

        if not game:
            print(f'{user.name} unlock request timed out')
            user.send_message("Timed out")
            client.games_played(app_ids)

        else:
            print(f'{user.name} is now playing {game}')
            sl.set(user.steam_id, game)

@client.on(EMsg.ServiceMethod)
def handle_games_played(msg):
    if hasattr(msg.body, 'games'):
        print(f'Now playing {msg.body.games[0].appid}')

@client.on(EMsg.ClientPersonaState)
def handle_persona_state(msg):
    for f in msg.body.friends:
        if f.friendid == sl.friend and not f.gameid:
            print(f'{f.player_name} no longer in game')
            sl.clear()
            client.games_played(app_ids)
            break

try:
    two_factor_code = generate_twofactor_code(base64.b64decode(SHARED_SECRET))
    result = client.login(USERNAME, PASSWORD, None, None, two_factor_code)

    if result != EResult.OK:
        print(f'Failed to login: {repr(result)}')
        raise SystemExit

    client.run_forever()

except KeyboardInterrupt:
    if client.connected:
        print("Logout")
        client.logout()
