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

from libqtile.log_utils import logger
from libqtile.utils import create_task
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake


class MessageType:
    Notification = 1
    Response = 2
    Error = 3


class SnapMessage(dict):
    def __init__(self, *args, message_type=None, **kwargs):
        super(SnapMessage, self).__init__(*args, **kwargs)
        self.__dict__ = self
        if message_type is not None:
            print("Setting message type")
            self.message_type = message_type

    @classmethod
    def from_json(cls, message, message_type=None, parse=True):
        if parse:
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                return message

        if not isinstance(message, dict):
            return message
        else:
            print(f"{message_type=}")
            return cls(
                {key: cls.from_json(message[key], parse=False) for key in message},
                message_type=message_type,
                parse=False,
            )


class SnapControl:
    msg_id = 1

    def __init__(self, server, port):
        self._uri = f"ws://{server}:{port}/jsonrpc"
        self.connected = False
        self.callbacks = set()
        self.request_callbacks = {}
        self.client = None
        self._connect_error = None

    def subscribe(self, callback):
        self.callbacks.add(callback)

    async def start(self):
        if self.connected:
            return True

        try:
            self.client = await connect(self._uri)
            self.connected = True
            create_task(self.listen())
            await asyncio.sleep(0)
            return True
        except (OSError, InvalidHandshake, TimeoutError) as e:
            self._connect_error = e
            return False

    async def listen(self):
        try:
            while self.connected:
                message = await self.client.recv()

                self.snmsg = SnapMessage.from_json(message, message_type=MessageType.Notification)

                try:
                    message = json.loads(message)
                except json.JSONDecodeError:
                    continue

                self._check_request_callback(message)

                for callback in self.callbacks:
                    callback(message)
        except ConnectionClosed:
            pass

    def _check_request_callback(self, message):
        if "id" not in message:
            return

        if (msgid := message["id"]) in self.request_callbacks:
            if "error" in message:
                logger.warning("Error received: %s", message)
                return

            callback = self.request_callbacks.pop(msgid)
            callback(message["result"])

    async def finalize(self):
        self.callbacks.clear()

        if self.client is not None:
            await self.client.close()

    async def _send(self, request, params, callback=None):
        data = {"id": SnapControl.msg_id, "jsonrpc": "2.0", "method": request}
        if params:
            data["params"] = params

        if callback is not None:
            self.request_callbacks[SnapControl.msg_id] = callback

        datastr = json.dumps(data)

        try:
            await self.client.send(datastr)
        except ConnectionClosed:
            return False, datastr

        SnapControl.msg_id += 1
        return True, datastr

    def send(self, request, params=dict(), callback=None):
        task = create_task(self._send(request, params, callback))
        task.add_done_callback(self._on_sent)

    def _on_sent(self, task):
        sent, data = task.result()
        if sent:
            logger.debug("Message sent successfully: %s", data)
        else:
            logger.warning("Unable to send message to snapserver. Connection closed.")
