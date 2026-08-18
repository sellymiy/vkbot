"""Минимальный асинхронный клиент SA-MP Query Protocol."""
import asyncio, struct, time
from dataclasses import dataclass

@dataclass
class Player:
    player_id: int
    name: str
    score: int

@dataclass
class SampInfo:
    hostname: str
    online: int
    max_players: int
    players: list[Player]
    ping: int

class SampQuery:
    def __init__(self, host: str, port: int, timeout: float = 5):
        self.host, self.port, self.timeout = host, port, timeout

    async def info(self) -> SampInfo:
        # Реализация через обычный UDP-сокет корректно работает с большинством SA-MP серверов.
        import socket
        loop = asyncio.get_running_loop(); sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        packet = b"SAMP" + bytes(map(int, self.host.split("."))) + struct.pack("<H", self.port) + b"i"
        started = time.monotonic(); await loop.sock_sendto(sock, packet, (self.host, self.port))
        try:
            data, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), self.timeout)
        finally: sock.close()
        if len(data) < 11 or data[:4] != b"SAMP": raise ValueError("Некорректный ответ SA-MP")
        payload = data[11:]
        if len(payload) < 9: raise ValueError("Короткий ответ SA-MP")
        _, online, maximum, name_len = struct.unpack_from("<BHHI", payload, 0)
        if 9 + name_len > len(payload): raise ValueError("Поврежденный ответ SA-MP")
        hostname = payload[9:9 + name_len]
        try: players = await self.players()
        except (TimeoutError, asyncio.TimeoutError): players = []
        return SampInfo(hostname.decode("cp1251", "replace"), online, maximum, players, round((time.monotonic()-started)*1000))

    async def players(self) -> list[Player]:
        import socket
        loop = asyncio.get_running_loop(); sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); sock.setblocking(False)
        packet = b"SAMP" + bytes(map(int, self.host.split("."))) + struct.pack("<H", self.port) + b"d"
        await loop.sock_sendto(sock, packet, (self.host, self.port))
        try: data, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), self.timeout)
        finally: sock.close()
        payload = data[11:]
        if len(payload) < 2: return []
        count = struct.unpack_from("<H", payload, 0)[0]; offset = 2; result = []
        for _ in range(count):
            if offset + 1 > len(payload): break
            player_id = payload[offset]; offset += 1
            name_len = payload[offset]; offset += 1
            name = payload[offset:offset + name_len].decode("cp1251", "replace"); offset += name_len
            if offset + 8 > len(payload): break
            score = struct.unpack_from("<i", payload, offset)[0]; offset += 4
            offset += 4  # ping игрока
            result.append(Player(player_id, name, score))
        return result
