from libqtile import bar
from libqtile.log_utils import logger
from libqtile.popup import Popup
from libqtile.widget import base
from stravalib import unit_helper

from qtile_extras.resources.stravadata import get_strava_data
from qtile_extras.resources.stravadata.sync import CYCLING_TYPES, RUNNING_TYPES, WALKING_TYPES


class StravaWidget(base._Widget, base.MarginMixin):
    orientations = base.ORIENTATION_HORIZONTAL
    _experimental = True
    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size"),
        ("foreground", "ffffff", "Text colour"),
        ("text", "{CA:%b}: Run {CD_Running:.1f}km Bike: {CD_Bike:.1f}km", "Widget text"),
        ("refresh_interval", 1800, "Time to update data"),
        ("startup_delay", 10, "Time before sending first web request"),
        ("popup_display_timeout", 15, "Time to display extended info"),
        ("warning_colour", "aaaa00", "Highlight when there is an error."),
        (
            "activity_types",
            None,
            "List of allowed activity/sport types (e.g. ['Run', 'Ride', 'VirtualRide']). Set None for all.",
        ),
        (
            "formatters",
            {},
            "Dict of custom formatters: {'key': func(activities, unit_helper)}",
        ),
    ]

    _dependencies = ["stravalib", "pint"]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(StravaWidget.defaults)
        self.add_defaults(base.MarginMixin.defaults)

        if "font_colour" in config:
            self.foreground = config["font_colour"]
            logger.warning(
                "The use of `font_colour` is deprecated. "
                "Please update your config to use `foreground` instead."
            )

        self.data = None
        self.raw_activities = []
        self.display_text = ""

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.timeout_add(self.startup_delay, self.refresh)

    def _get_data(self):
        return get_strava_data(
            interval=self.refresh_interval,
            activity_types=self.activity_types,
        )

    def _populate_format_keys(self):
        self.formatted_data = {}
        periods = {
            "C": self.data.current,
            "Y": self.data.year,
            "A": self.data.alltime,
        }

        specific_types = ["Run", "Ride", "VirtualRide", "Walk", "Hike", "Swim"]

        families = {
            "Bike": CYCLING_TYPES,
            "Running": RUNNING_TYPES,
            "Walking": WALKING_TYPES,
        }

        for prefix, period in periods.items():
            if not period:
                continue

            self.formatted_data[f"{prefix}D"] = period.get_distance()
            self.formatted_data[f"{prefix}C"] = period.get_count()
            self.formatted_data[f"{prefix}T"] = period.get_format_time()
            self.formatted_data[f"{prefix}P"] = period.get_pace()
            self.formatted_data[f"{prefix}S"] = period.get_speed()
            self.formatted_data[f"{prefix}A"] = period.date
            self.formatted_data[f"{prefix}N"] = period.name

            for t in specific_types:
                self.formatted_data[f"{prefix}D_{t}"] = period.get_distance(t)
                self.formatted_data[f"{prefix}C_{t}"] = period.get_count(t)
                self.formatted_data[f"{prefix}T_{t}"] = period.get_format_time(t)
                self.formatted_data[f"{prefix}P_{t}"] = period.get_pace(t)
                self.formatted_data[f"{prefix}S_{t}"] = period.get_speed(t)

            for fam_name, fam_types in families.items():
                self.formatted_data[f"{prefix}D_{fam_name}"] = period.get_distance(fam_types)
                self.formatted_data[f"{prefix}C_{fam_name}"] = period.get_count(fam_types)
                self.formatted_data[f"{prefix}T_{fam_name}"] = period.get_format_time(fam_types)
                self.formatted_data[f"{prefix}P_{fam_name}"] = period.get_pace(fam_types)
                self.formatted_data[f"{prefix}S_{fam_name}"] = period.get_speed(fam_types)

        if isinstance(self.formatters, dict):
            for key, fn in self.formatters.items():
                try:
                    self.formatted_data[key] = fn(self.raw_activities, unit_helper)
                except Exception:
                    logger.exception("Error running custom Strava formatter '%s'", key)
                    self.formatted_data[key] = "Error"

    def _read_data(self, future):
        results = future.result()

        if results:
            success, payload = results

            if not success:
                logger.warning("Error retrieving data: %s.", payload)
            else:
                if isinstance(payload, dict) and "raw" in payload:
                    self.data = payload["history"]
                    self.raw_activities = payload["raw"]
                else:
                    self.data = payload
                    self.raw_activities = []

                self._populate_format_keys()
                self.timeout_add(1, self.bar.draw)

        self.timeout_add(self.refresh_interval, self.refresh)

    def refresh(self):
        future = self.qtile.run_in_executor(self._get_data)
        future.add_done_callback(self._read_data)

    def calculate_length(self):
        total = 0
        if self.data is not None and self.text:
            text = self.format_text(self.text)
            width, _ = self.drawer.max_layout_size([text], self.font, self.fontsize)
            total += width + 2 * self.margin
        total += self.height
        return total

    def draw_icon(self):
        scale = self.height / 24.0
        self.drawer.set_source_rgb("ffffff")
        self.drawer.ctx.set_line_width(2)
        self.drawer.ctx.move_to(8 * scale, 14 * scale)
        self.drawer.ctx.line_to(12 * scale, 6 * scale)
        self.drawer.ctx.line_to(16 * scale, 14 * scale)
        self.drawer.ctx.stroke()

        self.drawer.ctx.set_line_width(1)
        self.drawer.ctx.move_to(13 * scale, 14 * scale)
        self.drawer.ctx.line_to(16 * scale, 20 * scale)
        self.drawer.ctx.line_to(19 * scale, 14 * scale)
        self.drawer.ctx.stroke()

    def draw_highlight(self, top=False, colour="000000"):
        self.drawer.set_source_rgb(colour)
        y = 0 if top else self.bar.height - 2
        self.drawer.fillrect(0, y, self.width, 2, 2)

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        x_offset = 0

        self.draw_icon()
        x_offset += self.height

        if self.data is None:
            self.draw_highlight(top=True, colour=self.warning_colour)
        else:
            self.display_text = self.format_text(self.text)
            layout = self.drawer.textlayout(
                self.display_text, self.foreground, self.font, self.fontsize, None, wrap=False
            )
            y_offset = (self.bar.height - layout.height) / 2
            layout.draw(x_offset + self.margin_x, y_offset)

        self.draw_at_default_position()

    def button_press(self, x, y, button):
        self.show_popup_summary()

    def mouse_enter(self, x, y):
        pass

    def format_text(self, text):
        try:
            return text.format(**self.formatted_data)
        except Exception:
            logger.exception("Exception when trying to format text.")
            return "Error"

    def show_popup_summary(self):
        if not self.data:
            return False

        lines = []
        heading = "{:^6} {:^20} {:^8} {:^10} {:^6}".format("Date", "Title", "km", "time", "pace")
        lines.append(heading)

        for act in self.data.current.children:
            line = (
                f"{act.date:%d %b}: {act.name:<20.20} {act.distance:7,.1f} "
                f"{act.format_time:>10} {act.format_pace:>6}"
            )
            lines.append(line)

        sub = (
            f"\n{self.data.current.date:%b %y}: {self.data.current.name:<20.20} {self.data.current.distance:7,.1f} "
            f"{self.data.current.format_time:>10} "
            f"{self.data.current.format_pace:>6}"
        )
        lines.append(sub)

        for month in self.data.previous:
            line = (
                f"{month.groupdate:%b %y}: {month.name:<20.20} {month.distance:7,.1f} "
                f"{month.format_time:>10} {month.format_pace:>6}"
            )
            lines.append(line)

        year = (
            f"\n{self.data.year.groupdate:%Y}  : {self.data.year.name:<20.20} {self.data.year.distance:7,.1f} "
            f"{self.data.year.format_time:>10} "
            f"{self.data.year.format_pace:>6}"
        )
        lines.append(year)

        alltime = (
            f"\nTOTAL : {self.data.alltime.name:<20.20} {self.data.alltime.distance:7,.1f} "
            f"{self.data.alltime.format_time:>10} "
            f"{self.data.alltime.format_pace:>6}"
        )
        lines.append(alltime)

        self.popup = Popup(
            self.qtile,
            y=self.bar.height,
            width=900,
            height=900,
            font="monospace",
            horizontal_padding=10,
            vertical_padding=10,
            opacity=0.8,
        )
        self.popup.text = "\n".join(lines)
        self.popup.height = self.popup.layout.height + (2 * self.popup.vertical_padding)
        self.popup.width = self.popup.layout.width + (2 * self.popup.horizontal_padding)
        self.popup.x = min(self.offsetx, self.bar.width - self.popup.width)
        self.popup.place()
        self.popup.draw_text()
        self.popup.unhide()
        self.popup.draw()
        self.timeout_add(self.popup_display_timeout, self.popup.kill)

    def info(self):
        info = base._Widget.info(self)
        info["display_text"] = self.display_text
        return info
