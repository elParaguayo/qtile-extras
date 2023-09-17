# This file is copied from https://github.com/qtile/qtile

"""
This file contains various helpers and basic variables for the test suite.

Defining them here rather than in conftest.py avoids issues with circular imports
between test/conftest.py and test/backend/<backend>/conftest.py files.
"""

import functools
import logging
import multiprocessing
import os
import subprocess
import sys
import tempfile
import time
import traceback
from abc import ABCMeta, abstractmethod
from pathlib import Path

from dbus_next import Message, Variant
from dbus_next.aio import MessageBus
from dbus_next.constants import MessageType, PropertyAccess
from dbus_next.service import ServiceInterface, dbus_property, method
from dbus_next.service import signal as dbus_signal
from libqtile import command, config, ipc, layout
from libqtile.confreader import Config
from libqtile.core.manager import Qtile
from libqtile.lazy import lazy
from libqtile.log_utils import init_log, logger
from libqtile.resources import default_config
from libqtile.utils import create_task

from qtile_extras.popup.toolkit import PopupRelativeLayout, PopupText

# the sizes for outputs
WIDTH = 800
HEIGHT = 600
SECOND_WIDTH = 640
SECOND_HEIGHT = 480

max_sleep = 5.0
sleep_time = 0.1


class Retry:
    def __init__(
        self,
        fail_msg="retry failed!",
        ignore_exceptions=(),
        dt=sleep_time,
        tmax=max_sleep,
        return_on_fail=False,
    ):
        self.fail_msg = fail_msg
        self.ignore_exceptions = ignore_exceptions
        self.dt = dt
        self.tmax = tmax
        self.return_on_fail = return_on_fail

    def __call__(self, fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            tmax = time.time() + self.tmax
            dt = self.dt
            ignore_exceptions = self.ignore_exceptions

            while time.time() <= tmax:
                try:
                    return fn(*args, **kwargs)
                except ignore_exceptions:
                    pass
                except AssertionError:
                    break
                time.sleep(dt)
                dt *= 1.5
            if self.return_on_fail:
                return False
            else:
                raise AssertionError(self.fail_msg)

        return wrapper


class BareConfig(Config):
    auto_fullscreen = True
    groups = [config.Group("a"), config.Group("b"), config.Group("c"), config.Group("d")]
    layouts = [layout.stack.Stack(num_stacks=1), layout.stack.Stack(num_stacks=2)]
    floating_layout = default_config.floating_layout
    keys = [
        config.Key(
            ["control"],
            "k",
            lazy.layout.up(),
        ),
        config.Key(
            ["control"],
            "j",
            lazy.layout.down(),
        ),
    ]
    mouse = []
    screens = [config.Screen()]
    follow_mouse_focus = False
    reconfigure_screens = False


class Backend(metaclass=ABCMeta):
    """A base class to help set up backends passed to TestManager"""

    def __init__(self, env, args=()):
        self.env = env
        self.args = args

    def create(self):
        """This is used to instantiate the Core"""
        return self.core(*self.args)

    def configure(self, manager):
        """This is used to do any post-startup configuration with the manager"""
        pass

    @abstractmethod
    def fake_click(self, x, y):
        """Click at the specified coordinates"""
        pass

    @abstractmethod
    def get_all_windows(self):
        """Get a list of all windows in ascending order of Z position"""
        pass


@Retry(ignore_exceptions=(ipc.IPCError,), return_on_fail=True)
def can_connect_qtile(socket_path, *, ok=None):
    if ok is not None and not ok():
        raise AssertionError()

    ipc_client = ipc.Client(socket_path)
    ipc_command = command.interface.IPCCommandInterface(ipc_client)
    client = command.client.InteractiveCommandClient(ipc_command)
    val = client.status()
    if val == "OK":
        return True
    return False


class TestManager:
    """Spawn a Qtile instance

    Setup a Qtile server instance on the given display, with the given socket
    and log files.  The Qtile server must be started, and then stopped when it
    is done.  Windows can be spawned for the Qtile instance to interact with
    with various `.test_*` methods.
    """

    def __init__(self, backend, debug_log):
        self.backend = backend
        self.log_level = logging.DEBUG if debug_log else logging.INFO
        self.backend.manager = self

        self.proc = None
        self.c = None
        self.testwindows = []

    def __enter__(self):
        """Set up resources"""
        self._sockfile = tempfile.NamedTemporaryFile()
        self.sockfile = self._sockfile.name
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Clean up resources"""
        self.terminate()
        self._sockfile.close()

    def start(self, config_class, no_spawn=False):
        rpipe, wpipe = multiprocessing.Pipe()

        def run_qtile():
            try:
                os.environ.pop("DISPLAY", None)
                os.environ.pop("WAYLAND_DISPLAY", None)
                kore = self.backend.create()
                os.environ.update(self.backend.env)
                init_log(self.log_level)
                if hasattr(self, "log_queue"):
                    logger.addHandler(logging.handlers.QueueHandler(self.log_queue))
                Qtile(
                    kore,
                    config_class(),
                    socket_path=self.sockfile,
                    no_spawn=no_spawn,
                ).loop()
            except Exception:
                wpipe.send(traceback.format_exc())

        self.proc = multiprocessing.Process(target=run_qtile)
        self.proc.start()

        # First, wait for socket to appear
        if can_connect_qtile(self.sockfile, ok=lambda: not rpipe.poll()):
            ipc_client = ipc.Client(self.sockfile)
            ipc_command = command.interface.IPCCommandInterface(ipc_client)
            self.c = command.client.InteractiveCommandClient(ipc_command)
            self.backend.configure(self)
            return
        if rpipe.poll(0.1):
            error = rpipe.recv()
            raise AssertionError("Error launching qtile, traceback:\n%s" % error)
        raise AssertionError("Error launching qtile")

    def create_manager(self, config_class):
        """Create a Qtile manager instance in this thread

        This should only be used when it is known that the manager will throw
        an error and the returned manager should not be started, otherwise this
        will likely block the thread.
        """
        init_log(self.log_level)
        kore = self.backend.create()
        config = config_class()
        for attr in dir(default_config):
            if not hasattr(config, attr):
                setattr(config, attr, getattr(default_config, attr))

        return Qtile(kore, config, socket_path=self.sockfile)

    def terminate(self):
        if self.proc is None:
            print("qtile is not alive", file=sys.stderr)  # type: ignore
        else:
            # try to send SIGTERM and wait up to 10 sec to quit
            self.proc.terminate()
            self.proc.join(10)

            if self.proc.is_alive():
                print("Killing qtile forcefully", file=sys.stderr)  # type: ignore
                # desperate times... this probably messes with multiprocessing...
                try:
                    os.kill(self.proc.pid, 9)
                    self.proc.join()
                except OSError:
                    # The process may have died due to some other error
                    pass

            if self.proc.exitcode:
                print("qtile exited with exitcode: %d" % self.proc.exitcode, file=sys.stderr)  # type: ignore

            self.proc = None

        for proc in self.testwindows[:]:
            proc.terminate()
            proc.wait()

            self.testwindows.remove(proc)

    def create_window(self, create, failed=None):
        """
        Uses the function `create` to create a window.

        Waits until qtile actually maps the window and then returns.
        """
        client = self.c
        start = len(client.windows())
        create()

        @Retry(ignore_exceptions=(RuntimeError,), fail_msg="Window never appeared...")
        def success():
            while failed is None or not failed():
                if len(client.windows()) > start:
                    return True
            raise RuntimeError("not here yet")

        return success()

    def _spawn_window(self, *args):
        """Starts a program which opens a window

        Spawns a new subprocess for a command that opens a window, given by the
        arguments to this method.  Spawns the new process and checks that qtile
        maps the new window.
        """
        if not args:
            raise AssertionError("Trying to run nothing! (missing arguments)")

        proc = None

        def spawn():
            nonlocal proc
            # Ensure the client only uses the test display
            env = os.environ.copy()
            env.pop("DISPLAY", None)
            env.pop("WAYLAND_DISPLAY", None)
            env.update(self.backend.env)
            proc = subprocess.Popen(args, env=env)

        def failed():
            if proc.poll() is not None:
                return True
            return False

        self.create_window(spawn, failed=failed)
        self.testwindows.append(proc)
        return proc

    def kill_window(self, proc):
        """Kill a window and check that qtile unmaps it

        Kills a window created by calling one of the `self.test*` methods,
        ensuring that qtile removes it from the `windows` attribute.
        """
        assert proc in self.testwindows, "Given process is not a spawned window"
        start = len(self.c.windows())
        proc.terminate()
        proc.wait()
        self.testwindows.remove(proc)

        @Retry(ignore_exceptions=(ValueError,))
        def success():
            if len(self.c.windows()) < start:
                return True
            raise ValueError("window is still in client list!")

        if not success():
            raise AssertionError("Window could not be killed...")

    def test_window(
        self, name, floating=False, wm_type="normal", export_sni=False, export_global_menu=False
    ):
        """
        Create a simple window in X or Wayland. If `floating` is True then the wmclass
        is set to "dialog", which triggers auto-floating based on `default_float_rules`.
        `wm_type` can be changed from "normal" to "notification", which creates a window
        that not only floats but does not grab focus.

        Setting `export_sni` to True will publish a simplified StatusNotifierItem interface
        on DBus.

        Windows created with this method must have their process killed explicitly, no
        matter what type they are.
        """
        python = sys.executable
        path = Path(__file__).parent / "scripts" / "window.py"
        wmclass = "dialog" if floating else "TestWindow"
        args = [python, path, "--name", wmclass, name, wm_type]
        if export_sni:
            args.append("export_sni_interface")
        if export_global_menu:
            args.append("export_global_menu")
        return self._spawn_window(*args)

    def test_notification(self, name="notification"):
        return self.test_window(name, wm_type="notification")

    def groupconsistency(self):
        groups = self.c.groups()
        screens = self.c.screens()
        seen = set()
        for g in groups.values():
            scrn = g["screen"]
            if scrn is not None:
                if scrn in seen:
                    raise AssertionError("Screen referenced from more than one group.")
                seen.add(scrn)
                assert screens[scrn]["group"] == g["name"]
        assert len(seen) == len(screens), "Not all screens had an attached group."


@Retry(ignore_exceptions=(AssertionError,), fail_msg="Window did not die!")
def assert_window_died(client, window_info):
    client.sync()
    wid = window_info["id"]
    assert wid not in set([x["id"] for x in client.windows()])


icon_path = Path(__file__).parent / "resources" / "icons" / "menuitem.png"


class GlobalMenu(ServiceInterface):
    """
    Simplified GlobalMenu interface.
    """

    def __init__(self, popup, *args):
        ServiceInterface.__init__(self, *args)
        self.popup = popup

    @dbus_signal()
    def LayoutUpdated(self) -> "ui":  # noqa: F821, N802
        return [1, 0]

    @method()
    def AboutToShow(self, id: "i") -> "b":  # noqa: F821, N802
        return True

    @method()
    def GetLayout(  # noqa: F722, N802
        self, parent_id: "i", recursion_depth: "i", properties: "as"  # noqa: F821
    ) -> "u(ia{sv}av)":  # noqa: F722, F821, N802
        if parent_id == 0:
            return [
                1,
                [
                    1,
                    {},
                    [
                        Variant(
                            "(ia{sv}av)",
                            [
                                1,
                                {
                                    "enabled": Variant("b", True),
                                    "visible": Variant("b", True),
                                    "label": Variant("s", "Qtile"),
                                    "children-display": Variant("s", "submenu"),
                                },
                                [],
                            ],
                        ),
                        Variant(
                            "(ia{sv}av)",
                            [
                                2,
                                {
                                    "enabled": Variant("b", True),
                                    "visible": Variant("b", True),
                                    "label": Variant("s", "Test"),
                                },
                                [],
                            ],
                        ),
                    ],
                ],
            ]

        elif parent_id == 1:
            return [
                1,
                [
                    1,
                    {},
                    [
                        Variant(
                            "(ia{sv}av)",
                            [
                                10,
                                {
                                    "enabled": Variant("b", True),
                                    "visible": Variant("b", True),
                                    "label": Variant("s", "Item 1"),
                                },
                                [],
                            ],
                        ),
                        Variant(
                            "(ia{sv}av)",
                            [
                                11,
                                {
                                    "enabled": Variant("b", True),
                                    "visible": Variant("b", True),
                                    "label": Variant("s", "Quit"),
                                },
                                [],
                            ],
                        ),
                    ],
                ],
            ]

    @method()
    def Event(self, id: "i", event_id: "s", data: "v", timestamp: "u"):  # noqa: F821, N802
        if id == 11:
            self.popup.bus.disconnect()
            task = create_task(self.popup.bus.wait_for_disconnect())
            task.add_done_callback(self.check_disconnect)

    def check_disconnect(self, task):
        if task.result() is None:
            self.popup.kill()


class SNIMenu(ServiceInterface):
    """
    Simplified DBusMenu interface.

    Only exports methods, properties and signals required by
    StatusNotifier widget.
    """

    def __init__(self, popup, name, *args):
        ServiceInterface.__init__(self, *args)
        self.popup = popup
        self.servicename = name

    @dbus_signal()
    def LayoutUpdated(self) -> "ui":  # noqa: F821, N802
        return [1, 0]

    @method()
    def AboutToShow(self, id: "i") -> "b":  # noqa: F821, N802
        return True

    @method()
    def GetLayout(  # noqa: F722, N802
        self, parent_id: "i", recursion_depth: "i", properties: "as"  # noqa: F722, F821
    ) -> "u(ia{sv}av)":  # noqa: F722, F821, N802
        with open(icon_path.as_posix(), "rb") as icon:
            raw = icon.read()

        return [
            1,
            [
                1,
                {},
                [
                    Variant(
                        "(ia{sv}av)",
                        [
                            0,
                            {
                                "enabled": Variant("b", True),
                                "visible": Variant("b", True),
                                "label": Variant("s", "Test Menu"),
                                "children-display": Variant("s", "submenu"),
                                "icon-data": Variant("ay", bytes(raw)),
                            },
                            [],
                        ],
                    ),
                    Variant(
                        "(ia{sv}av)",
                        [
                            1,
                            {
                                "enabled": Variant("b", True),
                                "visible": Variant("b", True),
                                "label": Variant("s", "Quit"),
                                "icon-data": Variant("s", icon_path.as_posix()),
                            },
                            [],
                        ],
                    ),
                ],
            ],
        ]

    @method()
    def Event(self, id: "i", event_id: "s", data: "v", timestamp: "u"):  # noqa: F821, N802
        if id == 1:
            self.popup.bus.disconnect()
            task = create_task(self.popup.bus.wait_for_disconnect())
            task.add_done_callback(self.check_disconnect)

    def check_disconnect(self, task):
        if task.result() is None:
            self.popup.kill()


class SNItem(ServiceInterface):
    """
    Simplified StatusNotifierItem interface.

    Only exports methods, properties and signals required by
    StatusNotifier widget.
    """

    def __init__(self, popup, name, *args):
        ServiceInterface.__init__(self, *args)
        self.popup = popup
        self.servicename = name

    @method()
    def Activate(self, x: "i", y: "i"):  # noqa: F821, N802
        self.popup.update_controls(textbox="Activated")

    @dbus_property(PropertyAccess.READ)
    def IconName(self) -> "s":  # noqa: F821, N802
        return ""

    @dbus_property(PropertyAccess.READ)
    def IconPixmap(self) -> "a(iiay)":  # noqa: F821, N802
        return [[32, 32, bytes([100] * (32 * 32 * 4))]]

    @dbus_property(PropertyAccess.READ)
    def AttentionIconPixmap(self) -> "a(iiay)":  # noqa: F821, N802
        return []

    @dbus_property(PropertyAccess.READ)
    def OverlayIconPixmap(self) -> "a(iiay)":  # noqa: F821, N802
        return []

    @dbus_property(PropertyAccess.READ)
    def IsMenu(self) -> "b":  # noqa: F821, N802
        return False

    @dbus_property(PropertyAccess.READ)
    def Menu(self) -> "s":  # noqa: F821, N802
        return "/DBusMenu"

    @dbus_signal()
    def NewIcon(self):  # noqa: N802
        pass

    @dbus_signal()
    def NewAttentionIcon(self):  # noqa: N802
        pass

    @dbus_signal()
    def NewOverlayIcon(self):  # noqa: N802
        pass


class DBusPopup(PopupRelativeLayout):
    def _configure(self, qtile=None):
        self.killed = False
        PopupRelativeLayout._configure(self, qtile)
        create_task(self.start_dbus_interfaces())

    async def start_dbus_interfaces(self):
        sni = getattr(self.qtile.config, "enable_sni", False)
        gm = getattr(self.qtile.config, "enable_global_menu", False)

        if not (sni or gm):
            return

        self.bus = await MessageBus().connect()

        if sni:
            name = f"test.qtile.window-{self.popup.win.wid}"

            item = SNItem(self, name, "org.kde.StatusNotifierItem")
            menu = SNIMenu(self, name, "com.canonical.dbusmenu")

            # Export interfaces on the bus
            self.bus.export("/StatusNotifierItem", item)
            self.bus.export("/DBusMenu", menu)

            # Request the service name
            await self.bus.request_name(name)

            msg = await self.bus.call(
                Message(
                    message_type=MessageType.METHOD_CALL,
                    destination="org.freedesktop.StatusNotifierWatcher",
                    interface="org.freedesktop.StatusNotifierWatcher",
                    path="/StatusNotifierWatcher",
                    member="RegisterStatusNotifierItem",
                    signature="s",
                    body=[self.bus.unique_name],
                )
            )

            if msg.message_type != MessageType.METHOD_RETURN:
                raise RuntimeError("Couldn't register status notifier item.")

        if gm:
            globalmenu = GlobalMenu(self, "com.canonical.dbusmenu")

            # Export interfaces on the bus
            self.bus.export("/GlobalMenu", globalmenu)

            # Request the service name
            await self.bus.request_name(f"test.qtile.window-global-menu-{self.popup.win.wid}")

            msg = await self.bus.call(
                Message(
                    message_type=MessageType.METHOD_CALL,
                    destination="com.canonical.AppMenu.Registrar",
                    interface="com.canonical.AppMenu.Registrar",
                    path="/com/canonical/AppMenu/Registrar",
                    member="RegisterWindow",
                    signature="uo",
                    body=[self.popup.win.wid, "/GlobalMenu"],
                )
            )

            if msg.message_type != MessageType.METHOD_RETURN:
                raise RuntimeError("Couldn't register global menu for window.")

    def kill(self):
        self.killed = True
        PopupRelativeLayout.kill(self)


class DBusConfig(BareConfig):
    def show_dbus_popup(qtile):  # noqa: N805
        dbus_window = DBusPopup(
            qtile=qtile,
            width=200,
            height=200,
            controls=[PopupText(text="Started", x=0, y=0, width=1, height=0.2, name="textbox")],
        )

        dbus_window.show()

        qtile.popup = dbus_window

    keys = [config.Key(["mod4"], "m", lazy.function(show_dbus_popup))]

    enable_sni = False
    enable_global_menu = False
