from qgis.PyQt.QtGui import  QIcon
import os


def image(name):
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    return QIcon(filename)

REMOVE = image("iconRemove.svg")
ADD = image("iconSelectAdd.svg")
ADDALL = image("iconSelected.svg")
