# Copyright (c) 2024 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import asyncio
import json
from collections import defaultdict
from enum import Enum, auto
from socket import gaierror

from libqtile.log_utils import logger
from libqtile.utils import create_task

# Snapcast JSONRPC: https://github.com/badaix/snapcast/blob/develop/doc/json_rpc_api/control.md
# Requests
CLIENT_GETSTATUS = "Client.GetStatus"
CLIENT_SETVOLUME = "Client.SetVolume"
CLIENT_SETLATENCY = "Client.SetLatency"
CLIENT_SETNAME = "Client.SetName"
GROUP_GETSTATUS = "Group.GetStatus"
GROUP_SETMUTE = "Group.SetMute"
GROUP_SETSTREAM = "Group.SetStream"
GROUP_SETCLIENTS = "Group.SetClients"
GROUP_SETNAME = "Group.SetName"
SERVER_GETRPCVERSION = "Server.GetRPCVersion"
SERVER_GETSTATUS = "Server.GetStatus"
SERVER_DELETECLIENT = "Server.DeleteClient"
STREAM_ADDSTREAM = "Stream.AddStream"
STREAM_REMOVESTREAM = "Stream.RemoveStream"
STREAM_CONTROL = "Stream.Control"
STREAM_SETPROPERTY = "Stream.SetProperty"

# Notifications
CLIENT_ONCONNECT = "Client.OnConnect"
CLIENT_ONDISCONNECT = "Client.OnDisconnect"
CLIENT_ONVOLUMECHANGED = "Client.OnVolumeChanged"
CLIENT_ONLATENCYCHANGED = "Client.OnLatencyChanged"
CLIENT_ONNAMECHANGED = "Client.OnNameChanged"
GROUP_ONMUTE = "Group.OnMute"
GROUP_ONSTREAMCHANGED = "Group.OnStreamChanged"
GROUP_ONNAMECHANGED = "Group.OnNameChanged"
STREAM_ONPROPERTIES = "Stream.OnProperties"
STREAM_ONUPDATE = "Stream.OnUpdate"
SERVER_ONUPDATE = "Server.OnUpdate"

# Custom
SERVER_ONDISCONNECT = "Server.OnDisconnect"


class MessageType(Enum):
    Notification = auto()
    Response = auto()


class SnapMessage(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def __getattr__(self, attr):
        return SnapMessage()

    def get_message_type(self):
        if self.id:
            return MessageType.Response
        else:
            return MessageType.Notification

    @classmethod
    def from_json(cls, message, parse=True):
        if parse:
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                return message

        if not isinstance(message, dict):
            return message
        else:
            return cls(
                {key: cls.from_json(message[key], parse=False) for key in message},
                parse=False,
            )


SERVER_DISCONNECT_MESSAGE = SnapMessage({"method": SERVER_ONDISCONNECT, "params": {}})


class SnapControl:
    msg_id = 0

    def __init__(self, uri, port=1705):
        self.uri = uri
        self.port = port
        self.connected = False
        self.reader = None
        self.writer = None
        self.subscriptions = defaultdict(list)
        self.request_queue = {}
        self.connect_error = False

    def subscribe(self, method, callback):
        self.subscriptions[method].append(callback)

    def unsubscribe(self, method, callback):
        while callback in self.subscriptions[method]:
            self.subscriptions[method].remove(callback)

    def _connect_error(self, message):
        if not self.connect_error:
            logger.error(message)
            self.connect_error = True

        return False

    async def start(self):
        if self.connected:
            return True

        try:
            self.reader, self.writer = await asyncio.open_connection(
                host=self.uri, port=self.port
            )
        except ConnectionRefusedError:
            return self._connect_error("Connection refused — port is closed.")
        except asyncio.TimeoutError:
            return self._connect_error("Connection attempt timed out.")
        except gaierror:
            return self._connect_error("Hostname could not be resolved.")
        except OSError:
            return self._connect_error("Connection error.")

        self.connected = True
        self.connect_error = False
        self.start_listener()
        await asyncio.sleep(0)
        return True

    def start_listener(self):
        if self.reader is None:
            return

        task = create_task(self.listen())
        task.add_done_callback(self._connection_ended)

    def _connection_ended(self, task):
        self.connected = False
        self.process_notification(SERVER_DISCONNECT_MESSAGE)

    async def listen(self):
        while self.connected:
            message = await self.reader.readline()
            message = message.decode()

            if not message.endswith("\r\n"):
                break

            snmsg = SnapMessage.from_json(message)

            match snmsg.get_message_type():
                case MessageType.Response:
                    self.process_response(snmsg)
                case MessageType.Notification:
                    self.process_notification(snmsg)

    def process_notification(self, message):
        for callback in self.subscriptions[message.method]:
            callback(message.params)

    def process_response(self, message):
        if message.id not in self.request_queue:
            return

        self.request_queue[message.id]["result"] = message.result or None
        self.request_queue[message.id]["error"] = message.error or None
        self.request_queue[message.id]["event"].set()

    async def finalize(self):
        self.writer.close()
        await self.writer.wait_closed()
        self.writer = None
        self.reader = None

    async def _send(self, method, params, callback=None):
        SnapControl.msg_id += 1
        msgid = SnapControl.msg_id
        data = {"id": msgid, "jsonrpc": "2.0", "method": method}
        if params:
            data["params"] = params

        datastr = f"{json.dumps(data)}\r\n".encode()
        self.request_queue[msgid] = {"event": asyncio.Event()}

        if self.writer.is_closing():
            return

        self.writer.write(datastr)
        await self.writer.drain()
        await self.request_queue[msgid]["event"].wait()
        result = self.request_queue[msgid].get("result")
        error = self.request_queue[msgid].get("error")
        del self.request_queue[msgid]

        if callback:
            callback(result, error)

    def send(self, method, params=dict(), callback=None):
        create_task(self._send(method, params, callback))
