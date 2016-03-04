#-----------------------------------------------------------
# Copyright (C) 2016 Nathan Woodrow
#-----------------------------------------------------------
# Licensed under the terms of GNU GPL 2
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#---------------------------------------------------------------------

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from qgis.core import QgsMapLayerRegistry

import images


def classFactory(iface):
    return SelectionSetsPlugin(iface)


class SelectionSetWidget(QWidget):
    saveSet = pyqtSignal()
    saveSetAll = pyqtSignal()
    setSelected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super(SelectionSetWidget, self).__init__(parent)

        self.saveAllAction = QAction(images.ADDALL, "Save selection set (All layers)", self)
        self.saveAction = QAction(images.ADD, "Save selection set (Active layer)", self)
        self.deleteAction = QAction(images.REMOVE, "Delete set", self)
        self.saveAllAction.triggered.connect(self.saveSetAll.emit)
        self.saveAction.triggered.connect(self.saveSet.emit)
        self.deleteAction.triggered.connect(self.deleteSet)

        self.menu = QMenu()
        self.menu.addAction(self.saveAction)
        self.menu.addAction(self.saveAllAction)
        self.toolbar = QToolBar()
        self.saveButton = QToolButton()
        self.toolbar.addWidget(self.saveButton)
        self.deleteAction = self.toolbar.addAction(self.deleteAction)

        self.saveButton.setMenu(self.menu)
        self.saveButton.setPopupMode(QToolButton.MenuButtonPopup)
        self.saveButton.setDefaultAction(self.saveAction)

        self.setList = QListView()
        self.setModel = QStandardItemModel()
        self.setList.setModel(self.setModel)
        self.setList.selectionModel().currentChanged.connect(self._itemSelected)

        layout = QVBoxLayout()
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.setList)

    def deleteSet(self):
        current = self.setList.selectionModel().currentIndex()
        self.setModel.removeRow(current.row())

    def _data_from_index(self, index):
        data = index.data(Qt.UserRole + 1)
        return data

    def addSelectionSet(self, selectionset):
        name = ",".join(layer.name() for layer in selectionset.keys())
        length = sum(len(items) for items in selectionset.values())
        item = QStandardItem("{} ({})".format(name, length))

        data = {}
        for layer, ids in selectionset.iteritems():
            data[layer.id()] = ids

        item.setData(data, Qt.UserRole + 1)
        self.setModel.appendRow(item)

    def _itemSelected(self, current, old):
        data = self._data_from_index(current)
        if data is None:
            return
        self.setSelected.emit(data)


class SelectionSetsPlugin:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        self.action = QAction("Selection Sets", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.dock = QDockWidget("Selection Sets", self.iface.mainWindow())
        self.setWidget = SelectionSetWidget()
        self.setWidget.saveSet.connect(self.saveSet)
        self.setWidget.saveSetAll.connect(self.saveSetAll)
        self.setWidget.setSelected.connect(self.updateSelection)
        self.dock.setWidget(self.setWidget)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.hide()
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removeDockWidget(self.dock)
        del self.action

    def run(self):
        self.dock.show()

    def saveSet(self):
        layer = self.iface.activeLayer()
        ids = layer.selectedFeaturesIds()
        data = {}
        data[layer] = ids
        self.setWidget.addSelectionSet(data)

    def saveSetAll(self):
        data = {}
        for layer in QgsMapLayerRegistry.instance().mapLayers().values():
            ids = layer.selectedFeaturesIds()
            if not ids:
                continue
            data[layer] = ids
        self.setWidget.addSelectionSet(data)

    def updateSelection(self, data):
        for layer in QgsMapLayerRegistry.instance().mapLayers().values():
            layer.removeSelection()
            try:
                ids = data[layer.id()]
                layer.select(ids)
            except KeyError:
                pass
