import tornado.ioloop
import tornado.web
import tornado.websocket
import json
import psycopg2

from tornado.options import define, options, parse_command_line

define("port", default=8888, help="run on the given port", type=int)

# we gonna store clients in dictionary..
clients = dict()

# Gon keep the db connection global as heck.
conn = psycopg2.connect(database = "commons", 
                            user = "postgres", 
                        password = "pass123", 
                            host = "127.0.0.1", 
                            port = "5432")
cursor = conn.cursor()

def broadcast(obj):
    connect_message = json.dumps(obj)
    for c in clients:
        clients[c]["object"].write_message(connect_message)

class CssHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render("web/index.css")

class JsHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render("web/commonsGame.js")

class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.render("web/index.html")


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self, *args):
        # self.id = self.get_argument("Id")
        self.stream.set_nodelay(True)
        self.id = -1
        # clients[self.id] = {"id": self.id, "object": self}

    def on_message(self, message):        
        msg = json.loads(message);
        if msg['type'] == 'connect':
            self.handleConnection(msg)
        elif msg['type'] == 'chat':
            self.handleChat(msg)
        elif msg['type'] == 'delete':
            cursor.execute("DELETE FROM player WHERE id = %s", (self.id,))
            self.write_message(json.dumps({"name":"Commons", "text":"You have died of dysentery.", "type":"chat"}))
            self.close()
        elif msg['type'] == 'move':
            self.handleMove()
        
    def on_close(self):
        cursor.execute("SELECT player_id FROM login WHERE player_id = %s;", (self.id,))
        if cursor.rowcount > 1:
            cursor.execute("UPDATE login SET logout_time = current_timestamp WHERE player_id = %s", (self.id,))

        if self.id in clients:
            del clients[self.id]
        conn.commit()

    def handleConnection(self, msg):
        cursor.execute("SELECT id, name, password FROM player WHERE name LIKE %s;", (msg['name'],))
        if cursor.rowcount < 1:
            msg['name'] = msg['name'].replace("<", "")
            if 255 > len(msg['name']) > 0 and 255 > len(str(msg['pass'])) > 0:
                cursor.execute("INSERT INTO player (name, password) VALUES (%s, %s);",
                    (msg['name'], msg['pass']))            
                conn.commit()
                cursor.execute("SELECT id, name, password FROM player WHERE name = %s;", 
                    (msg['name'],))
                details = cursor.fetchone()
        elif msg['pass'] != details[2]:
            clients[-1] = {"object":self}
            return 
        details = cursor.fetchone()
        self.id = details[0]
        clients[self.id] = {"object": self, "name":details[1], "id":details[0]}
        broadcast({"type":"connect", "name":details[1]})
        cursor.execute("INSERT INTO login (player_id) VALUES (%s)", (self.id,))

        if len(clients) == 1:
            cursor.execute("INSERT INTO game (player_one_id) VALUES (%s)", (self.id,))
            conn.commit()
        elif len(clients) == 2:
            cursor.execute("SELECT id FROM game WHERE player_two_id IS NULL;")
            if cursor.rowcount > 0:
                clients[self.id]["game_id"] = cursor.fetchone()[0]
                broadcast({"name":"", "text":"<h3>GAME BEGUN.<h3>", "type":"chat"})
                cursor.execute("UPDATE game SET player_two_id = %s WHERE id = %s", 
                    (self.id, clients[self.id]["game_id"]))

        cursor.execute("""SELECT player.name, text, time 
                            FROM chat 
                            INNER JOIN player ON player.id = chat.player_id 
                            ORDER BY time ASC LIMIT 1000;""")
        chat_log = cursor.fetchall()
        for log in chat_log:
            self.write_message(json.dumps({"name":log[0], "text":log[1], "type":"chat"}))

    def handleChat(self, obj):
        if len(obj["text"]) > 0:
            obj["text"] = obj["text"].replace("<","")
            cursor.execute(
                """INSERT INTO chat (player_id, text)
                    VALUES(%s, %s)""",
                    (str(self.id), obj["text"]))
            obj["name"] = clients[self.id]["name"]
            broadcast(obj)

    def handleMove(self):
        if self.game_id != 0:
            cursor.execute("INSERT INTO move (player_id, game_id) VALUES (%s,%s)", (self.id, self.game_id))

app = tornado.web.Application([
    (r'/*', IndexHandler),
    (r'/js', JsHandler),
    (r'/css', CssHandler),
    (r'/ws', WebSocketHandler),
])

if __name__ == '__main__':
    parse_command_line()
    app.listen(options.port)
    print "Running server at http://localhost:%i" % (options.port)
    tornado.ioloop.IOLoop.instance().start()