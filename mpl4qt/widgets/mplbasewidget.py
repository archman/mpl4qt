# -*- coding: utf-8 -*-
"""
mplbasewidget.py

Base class for matplotlib widget for PyQt.

Copyright (C) 2018 Tong Zhang <zhangt@frib.msu.edu>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""

from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtGui import QResizeEvent

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib as mpl
from matplotlib.ticker import AutoMinorLocator
from matplotlib.ticker import NullLocator

import numpy as np
import time
from collections import deque
from functools import partial

MPL_VERSION = mpl.__version__
DTMSEC = 500  # msec
DTSEC = DTMSEC / 1000.0  # sec


class BasePlotWidget(FigureCanvas):
    #
    keycombo_cached = pyqtSignal(str, float)

    def __init__(self, parent=None, width=5, height=4, dpi=100, **kws):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.figure.add_subplot(111)
        self.init_figure()
        super(BasePlotWidget, self).__init__(self.figure)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sys_bg_color = self.palette().color(QPalette.Background)
        self.sys_fg_color = self.palette().color(QPalette.Foreground)
        DEFAULT_FONTS = {
            'title': QFontDatabase.systemFont(QFontDatabase.TitleFont),
            'fixed': QFontDatabase.systemFont(QFontDatabase.FixedFont),
            'general': QFontDatabase.systemFont(QFontDatabase.GeneralFont),
        }
        self.sys_label_font = DEFAULT_FONTS['general']
        self.sys_title_font = DEFAULT_FONTS['title']
        self.post_style_figure()
        self.adjustSize()
        self.set_context_menu()

        # track (x,y)
        self.mpl_connect('motion_notify_event', self.on_motion)

        # key press
        self.mpl_connect('key_press_event', self.on_key_press)

        # key release
        self.mpl_connect('key_release_event', self.on_key_release)

        # pick
        self.mpl_connect('pick_event', self.on_pick)

        # button
        self.mpl_connect('button_release_event', self.on_release)

        self.mpl_connect('scroll_event', self.on_scroll)

        self.setFocusPolicy(Qt.ClickFocus)
        self.setFocus()

        # dnd
        self.setAcceptDrops(True)

        # window/widget/dialog handlers
        self._handlers = {}

        # hvlines
        self._hline = None        # h-ruler
        self._vline = None        # v-ruler
        self._cpoint = None       # cross-point of h,v rulers
        self._cpoint_text = None  # coord annote of cross-point

        # keypress cache
        self.dq_keycombo = deque([], 2)
        self.keycombo_cached.connect(self.on_update_keycombo_cache)

    def connect_button_press_event(self):
        """Connect 'button_press_event'
        """
        self.btn_cid = self.mpl_connect('button_press_event', self.on_press)

    def disconnect_button_press_event(self):
        """Disconnect 'button_press_event'
        """
        self.mpl_disconnect(self.btn_cid)

    def post_style_figure(self):
        self.set_figure_color()

    def on_scroll(self, e):
        if e.step > 0:
            f = 1.05 ** e.step
        else:
            f = 0.95 ** (-e.step)
        self.zoom(e, f)

    def zoom(self, e, factor):
        x0, y0 = e.xdata, e.ydata
        x_left, x_right = self.axes.get_xlim()
        y_bottom, y_up = self.axes.get_ylim()

        self.axes.set_xlim((x0 - (x0 - x_left) * factor,
                            x0 + (x_right - x0) * factor))
        self.axes.set_ylim((y0 - (y0 - y_bottom) * factor,
                            y0 + (y_up - y0) * factor))
        self.update_figure()

    def on_motion(self, e):
        pass

    def on_key_press(self, e):
        k, t = e.key, time.time()
        self.keycombo_cached.emit(k, t)
        QTimer.singleShot(DTMSEC, partial(self._on_delay_pop, k, t))

    def on_key_release(self, e):
        if len(self.dq_keycombo) != 2:
            return
        (k1, t1) = self.dq_keycombo.popleft()
        (k2, t2) = self.dq_keycombo.popleft()
        if t2 - t1 < DTSEC:
            self.process_keyshort_combo(k1, k2)

    def on_pick(self, e):
        pass

    def on_press(self, e):
        pass

    def on_release(self, e):
        pass

    def dragEnterEvent(self, e):
        pass

    def dropEvent(self, e):
        pass

    def init_figure(self):
        raise NotImplementedError

    def update_figure(self):
        self.draw_idle()

    def resize_figure(self):
        """Must be triggered for set fig size.
        """
        self.resizeEvent(QResizeEvent(self.size(), self.size()))

    def set_figure_color(self, color=None):
        if color is None:
            color = self.sys_bg_color.getRgbF()
        self.figure.set_facecolor(color)
        self.figure.set_edgecolor(color)
        if MPL_VERSION > "1.5.1":
            self.axes.set_facecolor(color)
        else:
            self.axes.set_axis_bgcolor(color)

    def set_ticks_color(self, color=None):
        if color is None:
            color = self.sys_bg_color.getRgbF()
        all_lbls = self.axes.get_xticklabels() + self.axes.get_yticklabels()
        [lbl.set_color(color) for lbl in all_lbls]

    def toggle_mticks(self, f):
        if f:
            self.axes.xaxis.set_minor_locator(AutoMinorLocator())
            self.axes.yaxis.set_minor_locator(AutoMinorLocator())
        else:
            self.axes.xaxis.set_minor_locator(NullLocator())
            self.axes.yaxis.set_minor_locator(NullLocator())

    def toggle_grid(self,
                    toggle_checked=False,
                    which='major',
                    b=None,
                    color=None,
                    **kws):
        if toggle_checked:
            which = 'both' if kws.get('mticks', True) else 'major'
            self.axes.grid(which=which, color=color, linestyle='--')
        else:
            self.axes.grid(b=False, which='minor')
            self.axes.grid(b=False)

    def set_xylabel_font(self, font=None):
        if font is None:
            font = self.sys_label_font
        _set_font(self.axes.xaxis.label, font)
        _set_font(self.axes.yaxis.label, font)

    def set_xyticks_font(self, font=None):
        if font is None:
            font = self.sys_label_font
        all_lbls = self.axes.get_xticklabels() + self.axes.get_yticklabels()
        [_set_font(lbl, font) for lbl in all_lbls]

    def set_title_font(self, font=None):
        if font is None:
            font = self.sys_title_font
        _set_font(self.axes.title, font)

    def set_context_menu(self, ):
        self.setContextMenuPolicy(Qt.DefaultContextMenu)

    def clear_figure(self):
        self.axes.clear()
        self.update_figure()

    @pyqtSlot('QString', float)
    def on_update_keycombo_cache(self, key, ts):
        self.dq_keycombo.append((key, ts))

    def _on_delay_pop(self, k, t):
        if (k, t) not in self.dq_keycombo:
            return
        self.process_keyshort(k)
        self.dq_keycombo.remove((k, t))

    def process_keyshort(self, k):
        """Override this method to define keyshorts.
        """
        print("Capture key: ", k)

    def process_keyshort_combo(self, k1, k2):
        """Override this method to define combo keyshorts.
        """
        print("Capture key combo: ", k1, k2)


class MatplotlibBaseWidget(BasePlotWidget):
    """MatplotlibBaseWidget(BasePlotWidget)
    """
    def __init__(self, parent=None):
         super(MatplotlibBaseWidget, self).__init__(parent)

    def init_figure(self):
        pass


class MatplotlibCMapWidget(BasePlotWidget):
    def __init__(self, parent=None):
        super(MatplotlibCMapWidget, self).__init__(parent, height=0.2)
        self.figure.set_tight_layout(True)
        self.figure.subplots_adjust(
                top=0.9999, bottom=0.0001, left=0.0001, right=0.9999)
        self.axes.set_axis_off()

        # reverse cmap flag, '' or '_r'
        self._rcmap = ''

    def init_figure(self):
        gradient = np.linspace(0, 1, 256)
        gradient = np.vstack((gradient, gradient))
        self.im = self.axes.imshow(gradient, aspect='auto')

    def set_cmap(self, c):
        self._cmap = c
        self.im.set_cmap(self._cmap + self._rcmap)
        self.update_figure()

    def set_reverse_cmap(self, f):
        self._rcmap = '_r' if f else ''
        self.set_cmap(self._cmap)


def _set_font(obj, font):
    obj.set_size(font.pointSizeF())
    obj.set_family(font.family())
    obj.set_weight(int(font.weight() / 87.0 * 1000))
    obj.set_stretch(font.stretch())
    if font.italic():
        obj.set_style('italic')
    else:
        obj.set_style('normal')


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication

    app = QApplication([])
    window = MatplotlibBaseWidget()
    window.show()

    app.exec_()
