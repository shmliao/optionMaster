# encoding: UTF-8

from vnpy.trader.uiQt import QtGui, QtWidgets, QtCore

COLOR_BID = QtGui.QColor(255,174,201)
COLOR_ASK = QtGui.QColor(160,255,160)
COLOR_STRIKE = QtGui.QColor(0,0,160)
COLOR_POS = QtGui.QColor(225,255,255)
COLOR_SYMBOL = QtGui.QColor('white')
COLOR_BLACK = QtGui.QColor('black')

#波动率的计算方式comprehensive:每个月的利率一样，采用平值期权上下两档，五档数据计算,Separate：每个合约都有独立的利率分开算
VOLATILITY_RULE_COMPREHENSIVE="comprehensive"
VOLATILITY_RULE_SEPARATE="Separate"


CALL_SUFFIX = '_call'
PUT_SUFFIX = '_put'

STYLESHEET_START = "background-color: rgb(111,255,244); color: black"
STYLESHEET_STOP = "background-color: rgb(255,201,111); color: black"


########################################################################
class OmCell(QtWidgets.QTableWidgetItem):
    """单元格"""

    #----------------------------------------------------------------------
    def __init__(self, text=None, background=None, foreground=None, data=None,fontSize=None):
        """Constructor"""
        super(OmCell, self).__init__()
        self.data = data
        self.background = None
        
        if text:
            self.setText(text)
        if foreground:
            self.setForeground(foreground)
            
        if background:
            self.setBackground(background)
            self.background = background
        if fontSize:
            self.setFont(QtGui.QFont("Roman times", fontSize))

        self.setTextAlignment(QtCore.Qt.AlignCenter)


########################################################################
class OmCellEditText(QtWidgets.QDoubleSpinBox):
    """单元格"""
    # ----------------------------------------------------------------------
    def __init__(self, text=None, kind=None, data=None,key=None):
        """Constructor"""
        super(OmCellEditText, self).__init__()
        if data and key:
            self.key=key
            self.data = data

        if kind:
            if kind=="impv":
                self.setDecimals(2)
                self.setMinimum(0)
                self.setSingleStep(0.01)
                self.setMaximum(100)
            elif kind=='volumn':
                self.setDecimals(0)
                self.setMinimum(0)
                self.setMaximum(1000)
            elif kind=='decimals':
                self.setDecimals(0)
                self.setMinimum(-1000000)
                self.setMaximum(1000000)
        if text:
            self.setValue(float(text))

        self.setFixedWidth(200)
        self.setFont(QtGui.QFont("Roman times", 10))


    def test(self,double):
        print double