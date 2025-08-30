import pygame
import sys
import random
import socket
import threading
import json
from enum import Enum
import pickle
from cryptography.fernet import Fernet


def load_encrypted(filename, key):
    f = Fernet(key)
    with open(filename, "rb") as f_in:
        encrypted = f_in.read()
    data = f.decrypt(encrypted)
    return pickle.loads(data)  # 反序列化回 Python 对象


with open("data/KEY", "rb") as file:
    word_pairs = load_encrypted("data/WORDS", file.read())


# 颜色定义
class Colors:
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (200, 200, 200)
    LIGHT_GRAY = (230, 230, 230)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 120, 255)
    YELLOW = (255, 255, 0)
    BACKGROUND = (240, 240, 245)


# 游戏状态枚举
class GameState(Enum):
    LOBBY = 1
    PLAYING = 2
    VOTING = 3
    RESULT = 4


# 输入框类
class TextInputBox:
    def __init__(
        self,
        x,
        y,
        w,
        h,
        font,
        placeholder="请输入内容",
        text_color=Colors.BLACK,
        box_color=Colors.BLACK,
        on_enter=None,
        text="",
    ):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = box_color
        self.text_color = text_color
        self.text = text
        self.font = font
        self.placeholder = placeholder
        self.active = False
        self.done = False
        self.on_enter = on_enter

        self.cursor_visible = True
        self.cursor_switch_ms = 250
        self.cursor_ms_counter = 0
        self.cursor_position = 0  # 光标位置

    def handle_event(self, event):
        if event.type == pygame.TEXTINPUT and self.active:
            self.text = (
                self.text[: self.cursor_position]
                + event.text
                + self.text[self.cursor_position :]
            )
            self.cursor_position += len(event.text)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
            else:
                self.active = False

        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.done = True
                if self.on_enter:
                    self.on_enter(self.text)
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_position > 0:
                    self.text = (
                        self.text[: self.cursor_position - 1]
                        + self.text[self.cursor_position :]
                    )
                    self.cursor_position -= 1
            elif event.key == pygame.K_DELETE:
                if self.cursor_position < len(self.text):
                    self.text = (
                        self.text[: self.cursor_position]
                        + self.text[self.cursor_position + 1 :]
                    )
            elif event.key == pygame.K_LEFT:
                if self.cursor_position > 0:
                    self.cursor_position -= 1
            elif event.key == pygame.K_RIGHT:
                if self.cursor_position < len(self.text):
                    self.cursor_position += 1
            elif (
                event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL)
            ) or (
                event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_META)
            ):
                try:
                    import pyperclip

                    paste_text = pyperclip.paste()
                    if isinstance(paste_text, str):
                        self.text = (
                            self.text[: self.cursor_position]
                            + paste_text
                            + self.text[self.cursor_position :]
                        )
                        self.cursor_position += len(paste_text)
                except Exception as e:
                    print(f"粘贴失败: {e}")

    def update(self, dt):
        if self.active:
            self.cursor_ms_counter += dt
            if self.cursor_ms_counter >= self.cursor_switch_ms:
                self.cursor_ms_counter %= self.cursor_switch_ms
                self.cursor_visible = not self.cursor_visible
        else:
            self.cursor_visible = False
            self.cursor_ms_counter = 0

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, 2)
        pygame.draw.rect(surface, Colors.LIGHT_GRAY, self.rect.inflate(-4, -4))

        if self.text or self.active:
            display_text = self.text
            color = self.text_color
        else:
            display_text = self.placeholder
            color = (150, 150, 150)

        # 渲染文本
        text_surface = self.font.render(display_text, True, color)
        text_pos = (
            self.rect.x + 5,
            self.rect.y + (self.rect.height - text_surface.get_height()) // 2,
        )
        surface.blit(text_surface, text_pos)

        # 绘制光标
        if self.active and self.cursor_visible:
            cursor_x = (
                self.rect.x + 5 + self.font.size(self.text[: self.cursor_position])[0]
            )
            cursor_y = text_pos[1]
            cursor_height = text_surface.get_height()
            pygame.draw.line(
                surface,
                self.text_color,
                (cursor_x, cursor_y),
                (cursor_x, cursor_y + cursor_height),
                2,
            )

    def get_value(self):
        return self.text.strip()

    def reset(self):
        self.text = ""
        self.cursor_position = 0
        self.active = False
        self.done = False
        self.cursor_visible = True
        self.cursor_ms_counter = 0


# 按钮类
class Button:
    def __init__(
        self,
        x,
        y,
        w,
        h,
        text,
        font,
        color=Colors.BLUE,
        text_color=Colors.WHITE,
        on_click=None,
    ):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.color = color
        self.text_color = text_color
        self.on_click = on_click
        self.hover = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.hover and self.on_click:
                self.on_click()

    def draw(self, surface):
        color = self.color
        if self.hover:
            color = (
                min(color[0] + 20, 255),
                min(color[1] + 20, 255),
                min(color[2] + 20, 255),
            )

        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, Colors.BLACK, self.rect, 2, border_radius=5)

        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)


# 玩家类
class Player:
    def __init__(self, _id, name, is_host=False):
        self.id = _id
        self.name = name
        self.is_host = is_host
        self.word = ""
        self.is_undercover = False
        self.votes = 0
        self.eliminated = False
        self.message = ""

    def draw(self, surface, x, y, width, height, is_me=False, game_state=None):
        # 绘制玩家框
        color = Colors.LIGHT_GRAY
        if is_me:
            color = (200, 230, 255)
        elif self.eliminated:
            color = (230, 200, 200)

        pygame.draw.rect(surface, color, (x, y, width, height), border_radius=5)
        pygame.draw.rect(
            surface, Colors.BLACK, (x, y, width, height), 2, border_radius=5
        )

        # 绘制玩家名称
        font = pygame.font.Font("default.ttf", 24)
        name_surface = font.render(self.name, True, Colors.BLACK)
        surface.blit(name_surface, (x + 10, y + 10))

        # 显示最新消息在名字后面
        if self.message and not self.eliminated:
            msg_font = pygame.font.Font("default.ttf", 18)  # 小一点字体
            display_msg = self.message
            if len(display_msg) > 15:
                display_msg = display_msg[:12] + "..."
            msg_surface = msg_font.render(display_msg, True, (0, 100, 0))  # 深绿色
            surface.blit(
                msg_surface, (x + 15 + name_surface.get_width(), y + 12)
            )  # 挨在名字后面

        # 显示主机标识
        if self.is_host:
            host_surface = font.render("主机", True, Colors.BLUE)
            surface.blit(host_surface, (x + width - 60, y + 10))

        # 显示淘汰状态
        if self.eliminated:
            eliminated_surface = font.render("已淘汰", True, Colors.RED)
            surface.blit(eliminated_surface, (x + 10, y + 40))

        # 显示投票数
        if game_state == GameState.VOTING or game_state == GameState.RESULT:
            votes_surface = font.render(f"票数: {self.votes}", True, Colors.BLACK)
            surface.blit(votes_surface, (x + width - 80, y + 40))


# 游戏类
class Game:
    def __init__(self):
        self.state = GameState.LOBBY
        self.players = []
        self.my_id = None
        self.current_turn = 0
        self.turn_count = 0
        self.votes = {}
        self.undercover_id = None
        self.winner = None
        self.chat_history = []

    def next_turn(self):
        # 找到下一个未淘汰的玩家
        next_turn = (self.current_turn + 1) % len(self.players)
        while self.players[next_turn].eliminated:
            next_turn = (next_turn + 1) % len(self.players)

        self.current_turn = next_turn
        self.turn_count += 1

        # 如果已经进行了两轮，进入投票阶段
        if self.turn_count >= len(self.players) * 2:
            self.state = GameState.VOTING
            # 重置投票
            for player in self.players:
                player.votes = 0
            self.votes = {}

    def vote(self, voter_id, target_id):
        if voter_id in self.votes:
            # 撤销之前的投票
            prev_target = self.votes[voter_id]
            for player in self.players:
                if player.id == prev_target:
                    player.votes -= 1
                    break

        # 记录新投票
        self.votes[voter_id] = target_id
        for player in self.players:
            if player.id == target_id:
                player.votes += 1
                break


# 游戏服务器类
class GameServer:
    def __init__(self, host="::", port=12345):
        self.undercover_id = None
        self.votes = {}
        self.player_info = {}  # {player_id: {"name": name, "is_host": bool}}
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}
        self.next_id = 1
        self.running = False
        self.game_state = GameState.LOBBY
        self.current_turn = 0
        self.turn_count = 0

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        try:
            self.server_socket.bind((self.host, self.port))
        except OSError as e:
            if e.errno == 48:
                print("端口已被占用")
                return
        self.server_socket.listen(5)
        self.running = True
        print(f"服务器启动: {self.host}:{self.port}")

        thread = threading.Thread(target=self.accept_clients)
        thread.daemon = True
        thread.start()

    def accept_clients(self):
        while self.running:
            conn, ip = self.server_socket.accept()
            player_id = self.next_id
            self.next_id += 1
            self.clients[player_id] = (conn, ip)

            print(f"玩家 {player_id} 已连接: {ip}")
            thread = threading.Thread(target=self.handle_client, args=(player_id, conn))
            thread.daemon = True
            thread.start()

    def check_voting_result(self):
        # 计算每个玩家的得票数
        vote_counts = {}
        for target_id in self.votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

        # 找到得票最多的玩家
        max_votes = max(vote_counts.values()) if vote_counts else 0
        candidates = [pid for pid, votes in vote_counts.items() if votes == max_votes]

        # 如果只有一个得票最多的玩家，淘汰该玩家
        if len(candidates) == 1:
            eliminated_id = candidates[0]

            # 标记被淘汰的玩家
            for player_id in self.player_info:
                if player_id == eliminated_id:
                    self.player_info[player_id]["eliminated"] = True
                    break

            # 检查游戏是否结束
            if eliminated_id == self.undercover_id:
                # 卧底被淘汰，平民胜利
                # 广播游戏结果和所有玩家的词语
                self.broadcast(
                    {
                        "type": "game_over",
                        "winner": "平民",
                        "undercover_id": self.undercover_id,
                        "player_words": {
                            pid: info.get("word", "")
                            for pid, info in self.player_info.items()
                        },
                    }
                )
                self.game_state = GameState.RESULT
            else:
                # 检查是否卧底胜利（存活玩家≤2且卧底仍在游戏中）
                alive_players = [
                    pid
                    for pid, info in self.player_info.items()
                    if not info.get("eliminated", False)
                ]

                if len(alive_players) <= 2 and self.undercover_id in alive_players:
                    # 卧底胜利
                    self.broadcast(
                        {
                            "type": "game_over",
                            "winner": "卧底",
                            "undercover_id": self.undercover_id,
                            "player_words": {
                                pid: info.get("word", "")
                                for pid, info in self.player_info.items()
                            },
                        }
                    )
                    self.game_state = GameState.RESULT
                else:
                    # 游戏继续，进入下一轮
                    self.next_turn()
        else:
            # 平票，继续游戏
            self.next_turn()

        # 清空投票记录
        self.votes = {}

    def handle_client(self, player_id, conn):
        buffer = ""  # 用于累积接收的数据
        while self.running:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break

                buffer += data
                # 按换行符分割消息
                while "\n" in buffer:
                    message_str, buffer = buffer.split("\n", 1)
                    try:
                        message = json.loads(message_str)
                        self.handle_message(player_id, message)
                    except json.JSONDecodeError as e:
                        print(f"JSON 解析错误: {e}")
            except Exception as e:
                print(f"客户端错误: {e}")
                break

        # 客户端断开连接的处理
        print(f"玩家 {player_id} 断开连接")
        conn.close()

        # 如果玩家在玩家列表中，移除并广播
        if player_id in self.player_info:
            player_name = self.player_info[player_id]["name"]
            del self.player_info[player_id]

            # 广播玩家离开消息
            self.broadcast(
                {
                    "type": "player_left",
                    "player_id": player_id,
                    "player_name": player_name,
                }
            )

        # 从客户端列表中移除
        if player_id in self.clients:
            del self.clients[player_id]

        # 如果游戏正在进行中，检查游戏状态
        if self.game_state == GameState.PLAYING or self.game_state == GameState.VOTING:
            # 检查是否还有足够的玩家继续游戏
            active_players = [
                pid
                for pid, info in self.player_info.items()
                if not info.get("eliminated", False)
            ]

            if len(active_players) < 2:
                # 玩家不足，结束游戏
                self.broadcast(
                    {
                        "type": "game_over",
                        "winner": "游戏因玩家退出而结束",
                        "player_words": {
                            pid: info.get("word", "")
                            for pid, info in self.player_info.items()
                        },
                    }
                )
                self.game_state = GameState.RESULT
            else:
                # 如果退出的是当前回合的玩家，切换到下一个玩家
                player_ids = list(self.player_info.keys())
                if (
                    self.current_turn < len(player_ids)
                    and player_ids[self.current_turn] == player_id
                ):
                    self.next_turn()

    def handle_message(self, player_id, message):
        msg_type = message.get("type")

        if msg_type == "join":
            name = message["name"]
            is_host = message.get("is_host", False)

            # 检查是否已经有主机
            existing_host = any(
                info.get("is_host", False) for info in self.player_info.values()
            )
            if is_host and existing_host:
                # 已经有主机了，不允许再设置为主机
                is_host = False
                # 通知客户端
                self.send_to(
                    player_id,
                    {
                        "type": "error",
                        "message": "已经有主机存在，您已作为普通玩家加入",
                    },
                )

            # 保存玩家信息
            self.player_info[player_id] = {"name": name, "is_host": is_host}

            # 给新玩家发送已有玩家列表
            existing_players = []
            for pid, info in self.player_info.items():
                if pid != player_id:
                    existing_players.append(
                        {"id": pid, "name": info["name"], "is_host": info["is_host"]}
                    )

            self.send_to(
                player_id,
                {
                    "type": "player_list",
                    "players": existing_players,
                    "your_id": player_id,
                    "is_host": is_host,  # 告诉客户端它的主机状态
                },
            )

            # 广播新玩家加入
            self.broadcast(
                {
                    "type": "player_joined",
                    "id": player_id,
                    "name": name,
                    "is_host": is_host,
                }
            )

        elif msg_type == "start_game":
            # 只有主机可以开始游戏
            if not self.player_info[player_id]["is_host"]:
                return

            self.game_state = GameState.PLAYING

            # 获取所有玩家ID
            player_ids = list(self.player_info.keys())
            if not player_ids:
                return

            # 随机选择卧底
            self.undercover_id = random.choice(player_ids)  # 保存卧底ID
            word_pair = random.choice(word_pairs)

            # 分配词语并通知所有玩家
            for pid in player_ids:
                is_undercover = pid == self.undercover_id  # 使用保存的卧底ID
                word = word_pair[1] if is_undercover else word_pair[0]

                # 保存玩家的词语信息
                self.player_info[pid]["word"] = word
                self.player_info[pid]["is_undercover"] = is_undercover

                msg = {
                    "type": "game_start",
                    "your_id": pid,
                    "word": word,
                    "is_undercover": is_undercover,
                    "players": [
                        {
                            "id": p_id,
                            "name": p_info["name"],
                            "is_host": p_info["is_host"],
                        }
                        for p_id, p_info in self.player_info.items()
                    ],
                }
                self.send_to(pid, msg)

            # 设置第一个回合
            self.current_turn = 0
            self.turn_count = 0
            self.broadcast({"type": "next_turn", "current_turn": self.current_turn})

        elif msg_type == "vote":
            target_id = message["target_id"]
            # 记录投票
            self.votes[player_id] = target_id

            # 广播投票
            self.broadcast(
                {"type": "vote", "voter_id": player_id, "target_id": target_id}
            )

            # 检查是否所有玩家都已投票
            active_players = [pid for pid in self.player_info.keys()]
            if len(self.votes) >= len(active_players):
                self.check_voting_result()

        elif msg_type == "send_message":
            # 检查是否是当前回合的玩家
            player_ids = list(self.player_info.keys())
            if player_ids[self.current_turn] != player_id:
                return

            text = message["message"]
            self.broadcast(
                {"type": "new_message", "player_id": player_id, "message": text}
            )

            # 切换到下一个回合
            self.next_turn()

        elif msg_type == "chat_message":
            text = message["message"]
            # 广播聊天消息给所有玩家
            self.broadcast(
                {"type": "new_message", "player_id": player_id, "message": text}
            )

        elif msg_type == "quit":
            # 正常退出，不需要额外处理，连接会在handle_client中关闭
            pass

        elif msg_type == "restart_game":
            # 只有主机可以重新开始游戏
            if not self.player_info[player_id]["is_host"]:
                return

            # 重置游戏
            self.reset_game()

    def next_turn(self):
        player_ids = list(self.player_info.keys())
        self.current_turn = (self.current_turn + 1) % len(player_ids)
        self.turn_count += 1

        # 如果已经进行了两轮，进入投票阶段
        if self.turn_count >= len(player_ids) * 2:
            self.game_state = GameState.VOTING
            self.broadcast({"type": "voting_start"})
        else:
            self.broadcast({"type": "next_turn", "current_turn": self.current_turn})

    def send_to(self, player_id, data):
        try:
            conn, _ = self.clients[player_id]
            # 在 JSON 消息末尾添加换行符作为分隔符
            message = json.dumps(data) + "\n"
            conn.send(message.encode())
        except Exception as e:
            print(f"发送失败: {e}")

    def broadcast(self, data):
        for pid in list(self.clients.keys()):
            self.send_to(pid, data)

    def reset_game(self):
        """重置游戏状态，但不关闭服务器"""
        self.game_state = GameState.LOBBY
        self.current_turn = 0
        self.turn_count = 0
        self.votes = {}
        self.undercover_id = None

        # 重置所有玩家状态
        for player_id in self.player_info:
            self.player_info[player_id] = {
                "name": self.player_info[player_id]["name"],
                "is_host": self.player_info[player_id]["is_host"],
                "eliminated": False,
            }

        # 广播游戏重置消息
        self.broadcast(
            {
                "type": "game_reset",
                "players": [
                    {"id": p_id, "name": p_info["name"], "is_host": p_info["is_host"]}
                    for p_id, p_info in self.player_info.items()
                ],
            }
        )


# 网络客户端类
class NetworkClient:
    def __init__(self, _game):
        self.selected_vote_target = None
        self.has_voted = None
        self.game = _game
        self.socket = None
        self.connected = False
        self.host = False
        self.server_address = None

    def connect(self, address, port, is_host=False):
        try:
            self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.socket.connect((address, port))
            self.connected = True
            self.host = is_host
            self.server_address = (address, port)

            # 启动接收线程
            thread = threading.Thread(target=self.receive_data)
            thread.daemon = True
            thread.start()

            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False

    def send(self, data):
        if self.connected:
            try:
                # 在 JSON 消息末尾添加换行符作为分隔符
                message = json.dumps(data) + "\n"
                self.socket.send(message.encode())
            except Exception as e:
                print(f"发送失败: {e}")

    def receive_data(self):
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    # 连接断开
                    self.connected = False
                    self.handle_disconnect()
                    break

                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.strip() == "":
                        continue
                    try:
                        message = json.loads(line)
                        self.handle_message(message)
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误: {e}, line: {line}")

            except Exception as e:
                print(f"接收错误: {e}")
                self.connected = False
                self.handle_disconnect()
                break

    def handle_disconnect(self):
        # 处理连接断开
        if hasattr(self.game, "chat_history"):
            self.game.chat_history.append("系统: 与服务器断开连接")

        # 重置游戏状态
        self.game.state = GameState.LOBBY
        self.game.players = []

    def handle_message(self, message):
        # 处理服务器消息
        msg_type = message.get("type")

        if msg_type == "player_joined":
            player_id = message["id"]
            player_name = message["name"]
            is_host = message["is_host"]
            self.game.players.append(Player(player_id, player_name, is_host))

        elif msg_type == "game_start":
            self.game.state = GameState.PLAYING
            self.game.my_id = message["your_id"]

            # 创建玩家列表（清空原来的）
            self.game.players = []
            for player_data in message["players"]:
                player = Player(
                    player_data["id"], player_data["name"], player_data["is_host"]
                )
                self.game.players.append(player)

            # 设置自己的词语和身份
            my_player = next(p for p in self.game.players if p.id == self.game.my_id)
            my_player.word = message["word"]
            my_player.is_undercover = message["is_undercover"]

        elif msg_type == "player_eliminated":
            player_id = message["player_id"]
            for player in self.game.players:
                if player.id == player_id:
                    player.eliminated = True
                    break

        elif msg_type == "game_over":
            self.game.state = GameState.RESULT
            self.game.winner = message["winner"]

            # 保存卧底ID
            if "undercover_id" in message:
                self.game.undercover_id = message["undercover_id"]

            # 更新所有玩家的词语和身份
            if "player_words" in message:
                for player_id, word in message["player_words"].items():
                    # 将字符串类型的player_id转换为整数（如果需要）
                    player_id_int = (
                        int(player_id) if isinstance(player_id, str) else player_id
                    )

                    for player in self.game.players:
                        if player.id == player_id_int:
                            player.word = word
                            # 设置卧底身份
                            if (
                                hasattr(self.game, "undercover_id")
                                and player.id == self.game.undercover_id
                            ):
                                player.is_undercover = True
                            else:
                                player.is_undercover = False  # 明确设置为非卧底
                            break

        elif msg_type == "new_message":
            player_id = message["player_id"]
            msg = message["message"]
            for player in self.game.players:
                if player.id == player_id:
                    player.message = msg
                    self.game.chat_history.append(f"{player.name}: {msg}")
                    break

        elif msg_type == "player_left":
            player_id = message["player_id"]
            player_name = message["player_name"]

            # 从玩家列表中移除
            self.game.players = [p for p in self.game.players if p.id != player_id]

            # 添加到聊天历史
            self.game.chat_history.append(f"系统: {player_name} 离开了游戏")

            # 如果退出的是当前回合的玩家，切换到下一个玩家
            if (
                self.game.state == GameState.PLAYING
                and self.game.current_turn < len(self.game.players)
                and self.game.players[self.game.current_turn].id == player_id
            ):
                self.game.next_turn()

        elif msg_type == "next_turn":
            self.game.current_turn = message["current_turn"]
            self.game.turn_count += 1

        elif msg_type == "voting_start":
            self.game.state = GameState.VOTING

        elif msg_type == "player_list":
            # 保存自己的ID和主机状态
            if "your_id" in message:
                self.game.my_id = message["your_id"]
            if "is_host" in message:
                self.host = message["is_host"]

            for player_data in message["players"]:
                self.game.players.append(
                    Player(
                        player_data["id"], player_data["name"], player_data["is_host"]
                    )
                )

        elif msg_type == "vote":
            voter_id = message["voter_id"]
            target_id = message["target_id"]
            self.game.vote(voter_id, target_id)

            # 检查是否所有玩家都已投票
            active_players = [p for p in self.game.players if not p.eliminated]
            if len(self.game.votes) >= len(active_players):
                self.check_voting_result()

        elif msg_type == "error":
            # 显示错误消息
            print(f"服务器错误: {message['message']}")

        elif msg_type == "game_reset":
            # 重置游戏状态
            self.game.state = GameState.LOBBY
            self.game.players = []

            # 重新添加玩家
            for player_data in message["players"]:
                player = Player(
                    player_data["id"], player_data["name"], player_data["is_host"]
                )
                # 重置玩家状态
                player.eliminated = False
                player.word = ""
                player.is_undercover = False
                player.votes = 0
                player.message = ""
                self.game.players.append(player)

            # 清空聊天记录和其他游戏状态
            self.game.chat_history = []
            self.game.votes = {}
            self.game.current_turn = 0
            self.game.turn_count = 0
            self.game.winner = None
            self.game.undercover_id = None

            # 重置客户端特定的投票状态
            self.selected_vote_target = None
            self.has_voted = False

    def check_voting_result(self):
        # 计算每个玩家的得票数
        vote_counts = {}
        for target_id in self.game.votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

        # 找到得票最多的玩家
        max_votes = max(vote_counts.values()) if vote_counts else 0
        candidates = [pid for pid, votes in vote_counts.items() if votes == max_votes]

        # 如果只有一个得票最多的玩家，淘汰该玩家
        if len(candidates) == 1:
            eliminated_id = candidates[0]

            # 标记被淘汰的玩家
            for player in self.game.players:
                if player.id == eliminated_id:
                    player.eliminated = True
                    break

            # 检查游戏是否结束
            if eliminated_id == self.game.undercover_id:
                # 卧底被淘汰，平民胜利
                self.game.state = GameState.RESULT
                self.game.winner = "平民"
            else:
                # 游戏继续，进入下一轮
                self.game.state = GameState.PLAYING
                self.game.next_turn()
        else:
            # 平票，继续游戏
            self.game.state = GameState.PLAYING
            self.game.next_turn()

        # 重置投票状态
        self.game.votes = {}
        self.selected_vote_target = None
        self.has_voted = False


# 主游戏类
class UndercoverGame:
    def __init__(self):
        self.server = None
        pygame.init()
        self.has_voted = False
        self.width, self.height = 1000, 700
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("谁是卧底")

        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font("default.ttf", 28)
        self.small_font = pygame.font.Font("default.ttf", 24)

        self.game = Game()
        self.network = NetworkClient(self.game)

        # 创建UI元素
        self.name_input = TextInputBox(400, 250, 200, 40, self.font, "游戏名字")
        self.host_input = TextInputBox(
            400, 320, 200, 40, self.font, "服务器IP", text="::"
        )
        self.port_input = TextInputBox(
            400, 390, 200, 40, self.font, "端口", text="12345"
        )
        self.message_input = TextInputBox(
            50, 650, 700, 40, self.font, "输入你的描述..."
        )

        self.join_button = Button(
            400, 460, 200, 40, "加入游戏", self.font, on_click=self.join_game
        )
        self.host_button = Button(
            400, 510, 200, 40, "创建游戏", self.font, on_click=self.host_game
        )
        self.start_button = Button(
            400, 560, 200, 40, "开始游戏", self.font, on_click=self.start_game
        )
        self.vote_buttons = []

        # 当前选中的投票目标
        self.selected_vote_target = None

    def join_game(self):
        name = self.name_input.get_value()
        host = self.host_input.get_value()
        port = int(self.port_input.get_value())

        if name and host and port:
            if self.network.connect(host, port, is_host=False):
                self.network.send({"type": "join", "name": name})

    def host_game(self):
        name = self.name_input.get_value()
        port = int(self.port_input.get_value())

        if name and port:
            # 检查是否已经存在服务器
            if (self.server is not None) and self.server.running:
                # 已经有一个服务器在运行，直接连接
                if self.network.connect("127.0.0.1", port, is_host=True):
                    self.network.send({"type": "join", "name": name, "is_host": True})
                return

            # 启动服务器
            self.server = GameServer(self.host_input.get_value(), port)
            self.server.start()

            # 作为主机客户端连接自己
            if self.network.connect("127.0.0.1", port, is_host=True):
                # 发送 join 消息
                self.network.send({"type": "join", "name": name, "is_host": True})

    def start_game(self):
        if self.network.host and self.network.connected:
            self.network.send({"type": "start_game"})
            # 重置投票状态
            self.selected_vote_target = None
            self.has_voted = False

    def send_message(self, message):
        if self.network.connected and message:
            self.network.send({"type": "send_message", "message": message})
            self.message_input.reset()

    def vote(self, target_id):
        if self.network.connected and target_id and not self.has_voted:
            self.network.send({"type": "vote", "target_id": target_id})
            self.has_voted = True  # 设置已投票标志

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit_game()
                return False

            self.name_input.handle_event(event)
            self.host_input.handle_event(event)
            self.port_input.handle_event(event)
            self.message_input.handle_event(event)
            self.join_button.handle_event(event)
            self.host_button.handle_event(event)
            self.start_button.handle_event(event)

            for vote_button in self.vote_buttons:
                vote_button.handle_event(event)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and self.message_input.active:
                    message_text = self.message_input.get_value()
                    if message_text:
                        if self.game.state == GameState.PLAYING:
                            # 检查是否是当前回合
                            if (
                                self.game.players[self.game.current_turn].id
                                == self.game.my_id
                            ):
                                self.send_message(message_text)
                        elif self.game.state == GameState.VOTING:
                            # 投票阶段发送普通聊天消息
                            self.send_chat_message(message_text)

            # 处理投票按钮点击
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and self.game.state == GameState.VOTING
            ):
                for i, player in enumerate(self.game.players):
                    if player.id != self.game.my_id and not player.eliminated:
                        button_rect = pygame.Rect(800, 150 + i * 60, 150, 40)
                        if button_rect.collidepoint(event.pos):
                            self.selected_vote_target = player.id
                            # 直接发送投票，不需要再按回车
                            self.vote(player.id)

        return True

    def send_chat_message(self, message):
        if self.network.connected and message:
            # 发送聊天消息而不是游戏描述
            self.network.send({"type": "chat_message", "message": message})
            self.message_input.reset()

    def restart_game(self):
        if self.network.connected:
            # 检查是否是主机
            my_player = next(
                (p for p in self.game.players if p.id == self.game.my_id), None
            )
            is_host = my_player and my_player.is_host if my_player else False

            if is_host:
                # 主机发送重新开始请求
                self.network.send({"type": "restart_game"})
            else:
                # 非主机玩家返回到主界面
                self.quit_game()
                # 重置游戏状态
                self.game = Game()
                self.network = NetworkClient(self.game)

    def draw(self):
        self.screen.fill(Colors.BACKGROUND)

        # 显示连接状态
        if not self.network.connected and self.game.state != GameState.LOBBY:
            status_text = self.font.render("与服务器断开连接", True, Colors.RED)
            self.screen.blit(status_text, (10, 10))

        if not self.network.connected:
            self.draw_lobby()
        else:
            if self.game.state == GameState.LOBBY:
                self.draw_waiting_room()
            elif self.game.state == GameState.PLAYING:
                self.draw_game()
            elif self.game.state == GameState.VOTING:
                self.draw_voting()
            elif self.game.state == GameState.RESULT:
                self.draw_result()

        pygame.display.flip()

    def draw_lobby(self):
        # 绘制标题
        title_font = pygame.font.Font("default.ttf", 48)
        title_surface = title_font.render("谁是卧底", True, Colors.BLUE)
        self.screen.blit(
            title_surface, (self.width // 2 - title_surface.get_width() // 2, 100)
        )

        # 绘制输入框和按钮
        self.screen.blit(self.font.render("名字:", True, Colors.BLACK), (300, 260))
        self.name_input.draw(self.screen)

        self.screen.blit(self.font.render("服务器IP:", True, Colors.BLACK), (245, 330))
        self.host_input.draw(self.screen)

        self.screen.blit(self.font.render("端口:", True, Colors.BLACK), (300, 400))
        self.port_input.draw(self.screen)

        self.join_button.draw(self.screen)
        self.host_button.draw(self.screen)

        # 绘制说明
        instructions = [
            "游戏说明:",
            "1. 所有玩家会收到一个相似但不完全相同的词语",
            "2. 卧底的词语与其他玩家不同",
            "3. 玩家轮流描述自己的词语",
            "4. 描述结束后进行投票，找出卧底",
            "5. 如果卧底被淘汰，平民胜利；否则卧底胜利",
        ]

        for i, line in enumerate(instructions):
            text_surface = self.small_font.render(line, True, Colors.BLACK)
            self.screen.blit(text_surface, (50, 450 + i * 30))

    def draw_waiting_room(self):
        # 绘制标题
        title_font = pygame.font.Font("default.ttf", 48)
        title_surface = title_font.render("等待房间", True, Colors.BLUE)
        self.screen.blit(
            title_surface, (self.width // 2 - title_surface.get_width() // 2, 50)
        )

        # 绘制玩家列表
        self.screen.blit(self.font.render("玩家列表:", True, Colors.BLACK), (50, 120))
        for i, player in enumerate(self.game.players):
            player_status = f"{player.name} {'(主机)' if player.is_host else ''}"
            text_surface = self.font.render(player_status, True, Colors.BLACK)
            self.screen.blit(text_surface, (50, 160 + i * 40))

        # 显示开始按钮（仅主机）
        # 使用服务器返回的主机状态，而不是本地的network.host
        my_player = next(
            (p for p in self.game.players if p.id == self.game.my_id), None
        )
        is_host = my_player and my_player.is_host if my_player else False

        if is_host:
            self.start_button.draw(self.screen)
        else:
            waiting_text = self.font.render("等待主机开始游戏...", True, Colors.BLACK)
            self.screen.blit(waiting_text, (400, 500))

    def draw_game(self):
        # 绘制标题
        title_font = pygame.font.Font("default.ttf", 36)
        title_text = "游戏进行中 - 描述你的词语"
        title_surface = title_font.render(title_text, True, Colors.BLUE)
        self.screen.blit(
            title_surface, (self.width // 2 - title_surface.get_width() // 2, 20)
        )

        # 显示自己的词语
        my_player = next(
            (p for p in self.game.players if p.id == self.game.my_id), None
        )
        if my_player:
            word_text = self.font.render(
                f"你的词语: {my_player.word}", True, Colors.BLACK
            )
            self.screen.blit(word_text, (50, 70))

        # 显示当前回合
        current_player = self.game.players[self.game.current_turn]
        turn_text = self.font.render(
            f"当前回合: {current_player.name}", True, Colors.BLACK
        )
        self.screen.blit(turn_text, (50, 100))

        # 绘制玩家列表
        for i, player in enumerate(self.game.players):
            is_me = player.id == self.game.my_id
            player.draw(self.screen, 50, 150 + i * 60, 700, 50, is_me, self.game.state)

        # 绘制聊天历史
        chat_title = self.font.render("聊天记录:", True, Colors.BLACK)
        self.screen.blit(chat_title, (50, 150 + len(self.game.players) * 60 + 20))

        for i, msg in enumerate(self.game.chat_history[-5:]):
            msg_surface = self.small_font.render(msg, True, Colors.BLACK)
            self.screen.blit(
                msg_surface, (50, 200 + len(self.game.players) * 60 + i * 25)
            )

        # 绘制输入框
        if self.game.players[self.game.current_turn].id == self.game.my_id:
            self.message_input.draw(self.screen)
            hint_text = self.small_font.render("按回车发送描述", True, Colors.BLACK)
            self.screen.blit(hint_text, (760, 660))
        else:
            waiting_text = self.font.render("请等待其他玩家描述...", True, Colors.BLACK)
            self.screen.blit(waiting_text, (300, 660))

    def draw_voting(self):
        # 绘制标题
        title_font = pygame.font.Font("default.ttf", 36)

        # 检查是否已经投票
        has_voted = self.has_voted or self.selected_vote_target is not None

        if has_voted:
            title_text = "投票阶段 - 已投票，等待其他玩家"
        else:
            title_text = "投票阶段 - 选出你认为的卧底"

        title_surface = title_font.render(title_text, True, Colors.RED)
        self.screen.blit(
            title_surface, (self.width // 2 - title_surface.get_width() // 2, 20)
        )

        # 绘制玩家列表
        for i, player in enumerate(self.game.players):
            is_me = player.id == self.game.my_id
            player.draw(self.screen, 50, 150 + i * 60, 700, 50, is_me, self.game.state)

            # 绘制投票按钮（不能投自己，且未投票时才显示）
            if player.id != self.game.my_id and not player.eliminated and not has_voted:
                button_color = (
                    Colors.RED
                    if self.selected_vote_target == player.id
                    else Colors.GRAY
                )
                button_rect = pygame.Rect(800, 150 + i * 60, 150, 40)
                pygame.draw.rect(
                    self.screen, button_color, button_rect, border_radius=5
                )
                pygame.draw.rect(
                    self.screen, Colors.BLACK, button_rect, 2, border_radius=5
                )

                vote_text = self.small_font.render("投票", True, Colors.BLACK)
                self.screen.blit(
                    vote_text,
                    (
                        button_rect.centerx - vote_text.get_width() // 2,
                        button_rect.centery - vote_text.get_height() // 2,
                    ),
                )

        # 显示提示
        if self.selected_vote_target:
            target_player = next(
                (p for p in self.game.players if p.id == self.selected_vote_target),
                None,
            )
            if target_player:
                hint_text = self.font.render(
                    f"已投票给: {target_player.name}", True, Colors.BLACK
                )
                self.screen.blit(hint_text, (50, 100))
        else:
            hint_text = self.font.render("请选择你要投票的玩家", True, Colors.BLACK)
            self.screen.blit(hint_text, (50, 100))

        # 显示投票进度
        active_players = [p for p in self.game.players if not p.eliminated]
        progress_text = self.font.render(
            f"投票进度: {len(self.game.votes)}/{len(active_players)}",
            True,
            Colors.BLACK,
        )
        self.screen.blit(progress_text, (700, 100))

        # 绘制聊天历史
        chat_title = self.font.render("聊天记录:", True, Colors.BLACK)
        self.screen.blit(chat_title, (50, 150 + len(self.game.players) * 60 + 20))

        for i, msg in enumerate(self.game.chat_history[-5:]):
            msg_surface = self.small_font.render(msg, True, Colors.BLACK)
            self.screen.blit(
                msg_surface, (50, 200 + len(self.game.players) * 60 + i * 25)
            )

        # 绘制输入框 - 在投票阶段也显示输入框，让玩家可以讨论
        self.message_input.draw(self.screen)
        hint_text = self.small_font.render("按回车发送消息讨论", True, Colors.BLACK)
        self.screen.blit(hint_text, (760, 660))

        # 显示等待提示
        if has_voted:
            waiting_text = self.font.render(
                "已投票，等待其他玩家...", True, Colors.BLACK
            )
            self.screen.blit(waiting_text, (400, 620))

    def draw_result(self):
        # 绘制标题
        title_font = pygame.font.Font("default.ttf", 48)
        title_text = f"游戏结束 - {self.game.winner}胜利"
        color = Colors.GREEN
        if self.game.winner == "卧底":
            color = Colors.RED
        title_surface = title_font.render(title_text, True, color)
        self.screen.blit(
            title_surface, (self.width // 2 - title_surface.get_width() // 2, 50)
        )

        # 显示卧底信息
        undercover = next((p for p in self.game.players if p.is_undercover), None)
        if undercover:
            undercover_text = self.font.render(
                f"卧底是: {undercover.name}", True, Colors.RED
            )
            self.screen.blit(
                undercover_text,
                (self.width // 2 - undercover_text.get_width() // 2, 120),
            )

        # 显示所有玩家的词语
        words_text = self.font.render("玩家词语:", True, Colors.BLACK)
        self.screen.blit(words_text, (50, 180))

        for i, player in enumerate(self.game.players):
            word_type = "卧底词" if player.is_undercover else "平民词"
            player_text = self.font.render(
                f"{player.name}: {player.word} ({word_type})", True, Colors.BLACK
            )
            self.screen.blit(player_text, (50, 220 + i * 40))

        # 显示重新开始按钮（仅主机）或返回按钮（非主机）
        my_player = next(
            (p for p in self.game.players if p.id == self.game.my_id), None
        )
        is_host = my_player and my_player.is_host if my_player else False

        if is_host:
            _restart_button = Button(
                self.width // 2 - 100,
                500,
                200,
                50,
                "重新开始",
                self.font,
                on_click=self.restart_game,
            )
            #  restart_button.draw(self.screen)
            ...
        else:
            _return_button = Button(
                self.width // 2 - 100,
                500,
                200,
                50,
                "返回主界面",
                self.font,
                on_click=self.return_to_lobby,
            )
            #  return_button.draw(self.screen)
            ...

    def return_to_lobby(self):
        """非主机玩家返回到主界面"""
        self.quit_game()
        # 重置游戏状态
        self.game = Game()
        self.network = NetworkClient(self.game)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60)

            # 更新输入框
            self.name_input.update(dt)
            self.message_input.update(dt)
            self.host_input.update(dt)
            self.port_input.update(dt)

            # 处理事件
            running = self.handle_events()

            # 绘制游戏
            self.draw()

            # 控制帧率
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def quit_game(self):
        if hasattr(self, "network") and self.network.connected:
            try:
                # 发送退出消息
                self.network.send({"type": "quit"})
                self.network.connected = False
                if hasattr(self.network, "socket"):
                    self.network.socket.close()
            except Exception as e:
                print(e)

        # 注意：不要关闭服务器，即使我们是主机
        # 这样主机可以继续使用同一个服务器端口

        # 重置客户端状态
        self.has_voted = False
        self.selected_vote_target = None


# 启动游戏
if __name__ == "__main__":
    game = UndercoverGame()
    game.run()
