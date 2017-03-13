from PyQt4.QtGui import *
from PyQt4.QtCore import *
from qgis.core import QgsMapLayerRegistry, QgsProject, QgsMessageLog, QgsVectorLayer

import images
import json


def classFactory(iface):
    return SelectionSetsPlugin(iface)


class SelectionSetWidget(QWidget):
    saveSet = pyqtSignal()
    saveSetAll = pyqtSignal()
    setSelected = pyqtSignal(dict)
    modified = pyqtSignal()

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
        self.modified.emit()

    def _data_from_index(self, index):
        data = index.data(Qt.UserRole + 1)
        return data

    def addSelectionSet(self, selectionset, notify=True):
        name = ",".join(layer.name() for layer in selectionset.keys())
        length = sum(len(items) for items in selectionset.values())
        name = "{} ({})".format(name, length)
        self.itemFromData(name, selectionset, notify)

    def itemFromData(self, name, selectionset, notify=True):
        item = QStandardItem(name)

        data = {}
        for layer, ids in selectionset.iteritems():
            # TODO This is just a hack because I'm lazy for now
            if isinstance(layer, QgsVectorLayer):
                data[layer.id()] = ids
            else:
                data[layer] = ids

        item.setData(data, Qt.UserRole + 1)
        self.setModel.appendRow(item)
        if notify:
            self.modified.emit()

    def _itemSelected(self, current, old):
        data = self._data_from_index(current)
        if data is None:
            return
        self.setSelected.emit(data)

    def dataForSaving(self):
        data = {}
        for row in range(self.setModel.rowCount()):
            item = self.setModel.item(row)
            name = item.text()
            itemdata = item.data()
            data[name] = itemdata
        return data

    def setFromLoaded(self, data):
        self.setModel.clear()
        for name, itemdata in data.iteritems():
            self.itemFromData(name, itemdata, notify=False)

    def clear(self):
        self.setModel.clear()


class SelectionSetsPlugin:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        self.action = QAction("Selection Sets", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.dock = QDockWidget("Selection Sets", self.iface.mainWindow())
        self.setWidget = SelectionSetWidget()
        self.setWidget.modified.connect(self.saveIntoProject)
        self.setWidget.saveSet.connect(self.saveSet)
        self.setWidget.saveSetAll.connect(self.saveSetAll)
        self.setWidget.setSelected.connect(self.updateSelection)
        self.dock.setWidget(self.setWidget)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.hide()
        self.iface.addToolBarIcon(self.action)
        QgsProject.instance().readProject.connect(self.loadFromProject)
        self.iface.newProjectCreated.connect(self.setWidget.clear)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removeDockWidget(self.dock)
        del self.action

    def run(self):
        self.dock.show()

    def saveIntoProject(self):
        data = self.setWidget.dataForSaving()
        datas = json.dumps(data)
        QgsProject.instance().writeEntry("SelectionSets", "/sets", datas)

    def loadFromProject(self):
        datas = QgsProject.instance().readEntry("SelectionSets", "/sets")[0]
        QgsMessageLog.logMessage(datas)
        try:
            data = json.loads(datas)
            self.setWidget.setFromLoaded(data)
        except ValueError:
            self.setWidget.clear()

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
            if isinstance(layer, QgsVectorLayer):
                layer.removeSelection()
            try:
                ids = data[layer.id()]
                layer.select(ids)
            except KeyError:
                pass
