# -*- coding: utf-8 -*-

import numpy as np
from functools import partial
from collections import deque

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QAbstractItemView
from PyQt5.QtWidgets import QToolButton
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QTableWidgetItem

from mpl4qt.ui.ui_markers_view import Ui_Form

MAX_N_SELECT = 2


class MarkersView(QWidget, Ui_Form):

    # named marker is to remove.
    marker_removed = pyqtSignal('QString')

    def __init__(self, markers, parent=None):
        super(MarkersView, self).__init__()
        self.parent = parent

        self.sel_dq = deque([], MAX_N_SELECT)

        self.setupUi(self)
        self.setWindowTitle("Markers")
        self.tw = self.tableWidget
        self.set_data(markers)

    def set_data(self, markers):
        self.data = markers
        self.show_data()

    def set_row(self, irow, x, y, name):
        item0 = QTableWidgetItem(name)
        self.tw.setItem(irow, 0, item0)
        item1 = QTableWidgetItem("{0:g}".format(x))
        self.tw.setItem(irow, 1, item1)
        item2 = QTableWidgetItem("{0:g}".format(y))
        self.tw.setItem(irow, 2, item2)
        del_btn = QToolButton(self)
        del_btn.setIcon(QIcon(QPixmap(":/icons/delete.png")))
        del_btn.setToolTip("Delete current marker")
        del_btn.clicked.connect(partial(self.on_delete, name))
        self.tw.setCellWidget(irow, 3, del_btn)

    def show_data(self):
        if self.data == []:
            self._reset_table()
            return
        self._preset_table()
        for i, (name, (_, _, _, _, (x, y))) in enumerate(self.data.items()):
            self.set_row(i, x, y, name)
        self._postset_table()

    @pyqtSlot()
    def on_delete(self, mk_name):
        # delete marker.
        for i in self.tw.findItems(mk_name, Qt.MatchExactly):
            self.marker_removed.emit(i.text())
            self.tw.removeRow(i.row())

    @pyqtSlot(bool, float, float, 'QString')
    def on_add_marker(self, is_new_marker, x, y, mk_name):
        # added a new marker, update (x,y)
        if is_new_marker:
            irow = self.tw.rowCount()
            self.tw.insertRow(irow)
            self.set_row(irow, x, y, mk_name)
        else:
            item0 = self.tw.findItems(mk_name, Qt.MatchExactly)[0]
            self.tw.item(item0.row(), 1).setText("{0:g}".format(x))
            self.tw.item(item0.row(), 2).setText("{0:g}".format(y))
        self._postset_table()

    def _postset_table(self):
        self.tw.horizontalHeader().setStretchLastSection(False)
        self.tw.resizeColumnsToContents()
        self.tw.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def _preset_table(self):
        """Set horizontal header labels, row/column size.
        """
        header = ['Name', 'X', 'Y', '']
        self.tw.setColumnCount(len(header))
        self.tw.setRowCount(len(self.data))
        self.tw.setHorizontalHeaderLabels(header)
        self.tw.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def _reset_table(self):
        """Reset table without data.
        """
        self._preset_table()
        self._postset_table()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()

    def on_press(self, i, j):
        if QGuiApplication.mouseButtons() == Qt.MiddleButton:
            cb = QGuiApplication.clipboard()
            if cb.supportsSelection():
                cb.setText(self.tw.item(i, j).text(), cb.Selection)

    @pyqtSlot()
    def on_selection_changed(self):
        # selection changed.
        cit = self.tw.currentItem()
        if cit is None:
            return
        self.sel_dq.append(cit.row())
        self.update_row_selection()
        self.update_stats()

    def update_row_selection(self):
        self.tw.itemSelectionChanged.disconnect()
        for i in range(self.tw.rowCount()):
            if i in self.sel_dq:
                selected = True
            else:
                selected = False
            for j in range(3):
                self.tw.item(i, j).setSelected(selected)
        self.tw.itemSelectionChanged.connect(self.on_selection_changed)

    def update_stats(self):
        # update stats.
        if len(self.sel_dq) < MAX_N_SELECT:
            return
        pt_array = np.zeros((2, 2))
        sel_namelist = ['', '']
        for i, irow in enumerate(self.sel_dq):
            sel_namelist[i] = self.tw.item(irow, 0).text()
            pt_array[i][0] = float(self.tw.item(irow, 1).text())
            pt_array[i][1] = float(self.tw.item(irow, 2).text())
        pt_mean = pt_array.mean(axis=0)
        pt_dis = np.sqrt((pt_array[0, 0] - pt_array[1, 0]) ** 2.0 +
                         (pt_array[0, 1] - pt_array[1, 1]) ** 2.0)
        self.selected_pts_lbl_1.setText(', '.join(sel_namelist) + ' is')
        self.selected_pts_lbl_2.setText(', '.join(sel_namelist) + ' is')
        self.mid_point_lbl.setText('x = {a[0]:g}, y = {a[1]:g}'.format(a=pt_mean))
        self.distance_lbl.setText('{0:g}'.format(pt_dis))

    def sizeHint(self):
        return QSize(300, 400)
