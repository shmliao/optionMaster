# encoding: UTF-8

from vnpy.event import Event

from vnpy.trader.vtConstant import DIRECTION_LONG, DIRECTION_SHORT, OFFSET_OPEN, OFFSET_CLOSE, PRICETYPE_LIMITPRICE
from vnpy.trader.vtObject import VtOrderReq
from vnpy.trader.vtEvent import EVENT_TICK, EVENT_TRADE,EVENT_ORDER,EVENT_TIMER
from vnpy.trader.uiBasicWidget import WorkingOrderMonitor,BasicMonitor,BasicCell,NameCell,DirectionCell,PnlCell,AccountMonitor
from uiOmBase import *

import json
import csv
import os
import platform
from collections import OrderedDict

from vnpy.trader.vtFunction import *
from vnpy.trader.vtGateway import *
from vnpy.trader import vtText
from vnpy.trader.vtConstant import *
from vnpy.trader.uiQt import QtGui, QtWidgets, QtCore, BASIC_FONT


#change by lsm 20180104
class ChainMonitor(QtWidgets.QTableWidget):
    """期权链监控"""
    headers = [
        u'合约名称',
        u'买价',
        u'买量',
        u'买隐波',
        u'卖价',
        u'卖量',
        u'卖隐波',
        u'净仓',
        u'行权价',
        u'净仓',
        u'买价',
        u'买量',
        u'买隐波',
        u'卖价',
        u'卖量',
        u'卖隐波',
        u'合约名称'
    ]
    
    signalTick = QtCore.pyqtSignal(type(Event()))
    signalPos = QtCore.pyqtSignal(type(Event()))
    signalTrade = QtCore.pyqtSignal(type(Event()))

    def __init__(self, chain,omEngine,mainEngine,eventEngine, parent=None):
        """Constructor"""
        super(ChainMonitor, self).__init__(parent)
        
        self.omEngine = omEngine
        self.eventEngine = eventEngine
        self.mainEngine=mainEngine
        # 保存代码和持仓的字典
        self.bidPriceDict = {}
        self.bidVolumeDict = {}
        self.bidImpvDict = {}
        self.askPriceDict = {}
        self.askVolumeDict = {}
        self.askImpvDict = {}
        self.posDict = {}

        #add by me
        self.chain=chain
        # 保存期权对象的字典
        portfolio = omEngine.portfolio
        
        self.instrumentDict = {}
        self.instrumentDict.update(portfolio.optionDict)
        self.instrumentDict.update(portfolio.underlyingDict)
        
        # 初始化
        self.initUi()
        self.registerEvent()
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        portfolio = self.omEngine.portfolio
        
        # 初始化表格
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)

        rowCount = 0
        rowCount += len(portfolio.underlyingDict)
        # rowCount += len(portfolio.chainDict)
        for chain in portfolio.chainDict.values():
            if chain==self.chain:
                rowCount += len(chain.callDict)
        self.setRowCount(rowCount)
        
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)
        
        for i in range(self.columnCount()):
            self.horizontalHeader().setResizeMode(i, QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.horizontalHeader().setResizeMode(self.columnCount()-1, QtWidgets.QHeaderView.ResizeToContents)
        
        # 初始化标的单元格
        row = 0
        
        for underlying in portfolio.underlyingDict.values():
            symbol = underlying.symbol
            
            cellSymbol = OmCell(symbol, COLOR_SYMBOL, COLOR_BLACK, underlying)
            cellBidPrice = OmCell(str(underlying.bidPrice1), COLOR_BID, COLOR_BLACK, underlying)
            cellBidVolume = OmCell(str(underlying.bidVolume1), COLOR_BID, COLOR_BLACK, underlying)
            cellAskPrice = OmCell(str(underlying.askPrice1), COLOR_ASK, COLOR_BLACK, underlying)
            cellAskVolume = OmCell(str(underlying.askVolume1), COLOR_ASK, COLOR_BLACK, underlying)
            cellPos = OmCell(str(underlying.netPos), COLOR_POS, COLOR_BLACK, underlying)
            
            self.setItem(row, 0, cellSymbol)
            self.setItem(row, 1, cellBidPrice)
            self.setItem(row, 2, cellBidVolume)
            self.setItem(row, 4, cellAskPrice)
            self.setItem(row, 5, cellAskVolume)
            self.setItem(row, 7, cellPos)
            
            self.bidPriceDict[symbol] = cellBidPrice
            self.bidVolumeDict[symbol] = cellBidVolume
            self.askPriceDict[symbol] = cellAskPrice
            self.askVolumeDict[symbol] = cellAskVolume
            self.posDict[symbol] = cellPos
            
            row += 1
            
        row += 1
        callRow = row
        # 初始化期权单元格


        for option in self.chain.callDict.values():
            # cellSymbol = OmCell(option.symbol, COLOR_SYMBOL, COLOR_BLACK, option)
            cellSymbol = OmCell(self.mainEngine.getContract(option.vtSymbol).name, COLOR_SYMBOL, COLOR_BLACK, option)
            cellBidPrice = OmCell(str(option.bidPrice1), COLOR_BID, COLOR_BLACK, option)
            cellBidVolume = OmCell(str(option.bidVolume1), COLOR_BID, COLOR_BLACK, option)
            cellBidImpv = OmCell('%.1f' % (option.bidImpv * 100), COLOR_BID, COLOR_BLACK, option)
            cellAskPrice = OmCell(str(option.askPrice1), COLOR_ASK, COLOR_BLACK, option)
            cellAskVolume = OmCell(str(option.askVolume1), COLOR_ASK, COLOR_BLACK, option)
            cellAskImpv = OmCell('%.1f' % (option.askImpv * 100), COLOR_ASK, COLOR_BLACK, option)
            cellPos = OmCell(str(option.netPos), COLOR_POS, COLOR_BLACK, option)
            cellStrike = OmCell(str(option.k), COLOR_STRIKE)
            self.setItem(callRow, 0, cellSymbol)
            self.setItem(callRow, 1, cellBidPrice)
            self.setItem(callRow, 2, cellBidVolume)
            self.setItem(callRow, 3, cellBidImpv)
            self.setItem(callRow, 4, cellAskPrice)
            self.setItem(callRow, 5, cellAskVolume)
            self.setItem(callRow, 6, cellAskImpv)
            self.setItem(callRow, 7, cellPos)
            self.setItem(callRow, 8, cellStrike)

            self.bidPriceDict[option.symbol] = cellBidPrice
            self.bidVolumeDict[option.symbol] = cellBidVolume
            self.bidImpvDict[option.symbol] = cellBidImpv
            self.askPriceDict[option.symbol] = cellAskPrice
            self.askVolumeDict[option.symbol] = cellAskVolume
            self.askImpvDict[option.symbol] = cellAskImpv
            self.posDict[option.symbol] = cellPos

            callRow += 1
            
            # put
        putRow = row

        for option in self.chain.putDict.values():
            # cellSymbol = OmCell(option.symbol, COLOR_SYMBOL, COLOR_BLACK, option)
            cellSymbol = OmCell(self.mainEngine.getContract(option.vtSymbol).name, COLOR_SYMBOL, COLOR_BLACK, option)
            cellBidPrice = OmCell(str(option.bidPrice1), COLOR_BID, COLOR_BLACK, option)
            cellBidVolume = OmCell(str(option.bidVolume1), COLOR_BID, COLOR_BLACK, option)
            cellBidImpv = OmCell('%.1f' % (option.bidImpv * 100), COLOR_BID, COLOR_BLACK, option)
            cellAskPrice = OmCell(str(option.askPrice1), COLOR_ASK, COLOR_BLACK, option)
            cellAskVolume = OmCell(str(option.askVolume1), COLOR_ASK, COLOR_BLACK, option)
            cellAskImpv = OmCell('%.1f' % (option.askImpv * 100), COLOR_ASK, COLOR_BLACK, option)
            cellPos = OmCell(str(option.netPos), COLOR_POS, COLOR_BLACK, option)
            self.setItem(putRow, 9, cellPos)
            self.setItem(putRow, 10, cellBidPrice)
            self.setItem(putRow, 11, cellBidVolume)
            self.setItem(putRow, 12, cellBidImpv)
            self.setItem(putRow, 13, cellAskPrice)
            self.setItem(putRow, 14, cellAskVolume)
            self.setItem(putRow, 15, cellAskImpv)
            self.setItem(putRow, 16, cellSymbol)

            self.bidPriceDict[option.symbol] = cellBidPrice
            self.bidVolumeDict[option.symbol] = cellBidVolume
            self.bidImpvDict[option.symbol] = cellBidImpv
            self.askPriceDict[option.symbol] = cellAskPrice
            self.askVolumeDict[option.symbol] = cellAskVolume
            self.askImpvDict[option.symbol] = cellAskImpv
            self.posDict[option.symbol] = cellPos

            putRow += 1
            
        row = putRow + 1
            
    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signalTick.connect(self.processTickEvent)
        self.signalTrade.connect(self.processTradeEvent)
        
        portfolio = self.omEngine.portfolio
        
        for underlying in portfolio.underlyingDict.values():
            self.eventEngine.register(EVENT_TICK + underlying.vtSymbol, self.signalTick.emit)
            self.eventEngine.register(EVENT_TRADE + underlying.vtSymbol, self.signalTrade.emit)
        

        for option in self.chain.optionDict.values():
            self.eventEngine.register(EVENT_TICK + option.vtSymbol, self.signalTick.emit)
            self.eventEngine.register(EVENT_TRADE + option.vtSymbol, self.signalTrade.emit)
    
    #----------------------------------------------------------------------
    def processTickEvent(self, event):
        """行情更新"""
        tick = event.dict_['data']
        symbol = tick.symbol
        
        if symbol in self.bidImpvDict:
            option = self.instrumentDict[symbol]
            self.bidImpvDict[symbol].setText('%.1f' %(option.bidImpv*100))
            self.askImpvDict[symbol].setText('%.1f' %(option.askImpv*100))
        
        self.bidPriceDict[symbol].setText(str(tick.bidPrice1))
        self.bidVolumeDict[symbol].setText(str(tick.bidVolume1))
        self.askPriceDict[symbol].setText(str(tick.askPrice1))
        self.askVolumeDict[symbol].setText(str(tick.askVolume1))
    
    #----------------------------------------------------------------------
    def processTradeEvent(self, event):
        """成交更新"""
        trade = event.dict_['data']
        
        symbol = trade.symbol
        instrument = self.instrumentDict[symbol]
        self.posDict[symbol].setText(str(instrument.netPos))


########################################################################
class TradingWidget(QtWidgets.QWidget):
    """交易组件"""

    #----------------------------------------------------------------------
    def __init__(self, omEngine, parent=None):
        """Constructor"""
        super(TradingWidget, self).__init__(parent)
        
        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.portfolio = omEngine.portfolio
        
        self.initUi()
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setFixedWidth(200)
        
        labelTradingWidget = QtWidgets.QLabel(u'期权交易')
        labelSymbol = QtWidgets.QLabel(u'代码')
        labelDirection = QtWidgets.QLabel(u'方向')
        labelPrice = QtWidgets.QLabel(u'价格')
        labelVolume = QtWidgets.QLabel(u'数量')
        
        self.lineSymbol = QtWidgets.QLineEdit()
        self.comboDirection = QtWidgets.QComboBox()
        self.comboDirection.addItems([DIRECTION_LONG, DIRECTION_SHORT])
        self.linePrice = QtWidgets.QLineEdit()
        self.lineVolume = QtWidgets.QLineEdit()
        self.buttonSendOrder = QtWidgets.QPushButton(u'发单')
        self.buttonSendOrder.clicked.connect(self.sendOrder)
        
        grid = QtWidgets.QGridLayout()
        grid.addWidget(labelTradingWidget, 0, 0, 1, 2)
        grid.addWidget(labelSymbol, 1, 0)
        grid.addWidget(labelDirection, 2, 0)
        grid.addWidget(labelPrice, 3, 0)
        grid.addWidget(labelVolume, 4, 0)
        grid.addWidget(self.lineSymbol, 1, 1)
        grid.addWidget(self.comboDirection, 2, 1)
        grid.addWidget(self.linePrice, 3, 1)
        grid.addWidget(self.lineVolume, 4, 1)
        grid.addWidget(self.buttonSendOrder, 5, 0, 1, 2)
        self.setLayout(grid)

    #----------------------------------------------------------------------
    def sendOrder(self):
        """发送委托"""
        try:
            symbol = str(self.lineSymbol.text())
            direction = str(self.comboDirection.currentText())
            price = float(self.linePrice.text())
            volume = int(self.lineVolume.text())
        except:
            return
        
        instrument = self.portfolio.instrumentDict.get(symbol, None)
        if not instrument:
            return
        
        # 做多
        if direction == DIRECTION_LONG:
            # 如果空头仓位大于等于买入量，则只需平
            if instrument.shortPos >= volume:
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, volume)
            # 否则先平后开
            else:
                openVolume = volume - instrument.shortPos
                if instrument.shortPos:
                    self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, instrument.shortPos)
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_OPEN, price, openVolume)
        # 做空
        else:
            if instrument.longPos >= volume:
                self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, volume)
            else:
                openVolume = volume - instrument.longPos
                if instrument.longPos:
                    self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, instrument.longPos)
                self.fastTrade(symbol ,DIRECTION_SHORT, OFFSET_OPEN, price, openVolume)
    
    #----------------------------------------------------------------------
    def fastTrade(self, symbol, direction, offset, price, volume):
        """封装下单函数"""
        contract = self.mainEngine.getContract(symbol)
        if not contract:
            return
        
        req = VtOrderReq()
        req.symbol = symbol
        req.exchange = contract.exchange
        req.direction = direction
        req.offset = offset
        req.price = price
        req.volume = volume
        req.priceType = PRICETYPE_LIMITPRICE
        print "下单vtOrderID"+str(self.mainEngine.sendOrder(req, contract.gatewayName))
    
    #----------------------------------------------------------------------
    def updateWidget(self, item):
        """双击监控组件单元格后自动更新组件"""
        instrument = item.data
        if not instrument:
            return

        self.lineSymbol.setText(instrument.symbol)
        
        # short
        if item.background is COLOR_BID:
            self.comboDirection.setCurrentIndex(1)
            self.linePrice.setText(str(instrument.bidPrice1))
            self.lineVolume.setText(str(instrument.bidVolume1))
        # long
        elif item.background is COLOR_ASK:
            self.comboDirection.setCurrentIndex(0)
            self.linePrice.setText(str(instrument.askPrice1))
            self.lineVolume.setText(str(instrument.askVolume1))

# add by lsm 20180104
class FloatTradingWidget(QtWidgets.QWidget):
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    """管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))
    def __init__(self, omEngine,item,symbol, parent=None):
        """Constructor"""
        super(FloatTradingWidget,self).__init__(parent)

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine=self.mainEngine.eventEngine
        self.portfolio = omEngine.portfolio
        self.symbol=symbol
        self.initUi(item)

    # ----------------------------------------------------------------------
    def initUi(self,item):
        """初始化界面"""
        self.setMinimumHeight(500)
        self.setFixedWidth(500)
        self.setWindowTitle(u'委托快捷下单')
        labelTradingWidget = QtWidgets.QLabel(u'期权名称:')
        # labelTradingWidget.setFixedHeight(50)
        labelTickWidget = QtWidgets.QLabel(u'五档行情:')
        # labelTickWidget.setFixedHeight(50)
        labelSymbol = QtWidgets.QLabel(u'合约代码')
        self.labelOptionName= QtWidgets.QLabel(self.mainEngine.getContract(item.vtSymbol).name)
        self.shortDirectionHorizontalLayoutWidget = QtWidgets.QHBoxLayout()

        # 卖开逻辑问题，加一个卖开选项来开关卖开还是卖平，如果选择打开卖开选项，则不管是否有多头仓位都选择卖开，如果关掉卖开选项，则按正常逻辑卖平卖开
        self.shortOpenRadio = QtWidgets.QRadioButton(u"卖开")
        self.shortCloseRadio = QtWidgets.QRadioButton(u"卖平")
        self.shortOpenRadio.setChecked(True)
        self.shortDirectionHorizontalLayoutWidget.addWidget(self.shortOpenRadio)
        self.shortDirectionHorizontalLayoutWidget.addWidget(self.shortCloseRadio)

        labelDirection = QtWidgets.QLabel(u'方向')
        labelPrice = QtWidgets.QLabel(u'价格')
        labelVolume = QtWidgets.QLabel(u'数量')

        self.fiveMarketWidget=FiveMarketWidget(self.omEngine,item,item.vtSymbol)

        self.lineSymbol = QtWidgets.QLineEdit()
        self.lineSymbol.setText(item.symbol)
        self.comboDirection = QtWidgets.QComboBox()
        self.comboDirection.addItems([DIRECTION_LONG, DIRECTION_SHORT])
        self.linePrice = QtWidgets.QDoubleSpinBox()
        self.linePrice.setDecimals(4)
        self.linePrice.setMinimum(0)
        self.linePrice.setMaximum(1000)

        self.lineVolume = QtWidgets.QDoubleSpinBox()
        self.lineVolume.setDecimals(0)
        self.lineVolume.setMinimum(0)
        self.lineVolume.setMaximum(1000)

        self.quotationHorizontalLayoutWidget=QtWidgets.QHBoxLayout()
        self.limitPriceRadio=QtWidgets.QRadioButton(u"限价")
        self.fokPriceRadio = QtWidgets.QRadioButton(u"fok")
        self.fakPriceRadio = QtWidgets.QRadioButton(u"fak")
        self.quotationHorizontalLayoutWidget.addWidget(self.limitPriceRadio)
        self.quotationHorizontalLayoutWidget.addWidget(self.fokPriceRadio)
        self.quotationHorizontalLayoutWidget.addWidget(self.fakPriceRadio)

        self.directHorizontalLayoutWidget = QtWidgets.QHBoxLayout()
        self.buyRadio = QtWidgets.QRadioButton(u"买")
        self.sellRadio = QtWidgets.QRadioButton(u"卖")

        self.directHorizontalLayoutWidget.addWidget(self.buyRadio)
        self.directHorizontalLayoutWidget.addWidget(self.sellRadio)


        self.buttonSendOrder = QtWidgets.QPushButton(u'发单')
        self.buttonSendOrder.clicked.connect(self.sendOrder)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(labelTradingWidget,0,0)
        grid.addWidget(self.labelOptionName, 0, 1)


        grid.addLayout(self.shortDirectionHorizontalLayoutWidget, 0, 2, 1, 2)
        grid.addWidget(self.fiveMarketWidget, 1, 2, 8, 2)

        grid.addWidget(labelSymbol, 1, 0)
        grid.addWidget(labelDirection, 2, 0)
        grid.addWidget(labelPrice, 3, 0)
        grid.addWidget(labelVolume, 4, 0)
        grid.addWidget(self.lineSymbol, 1, 1)
        grid.addWidget(self.comboDirection, 2, 1)
        grid.addWidget(self.linePrice, 3, 1)
        grid.addWidget(self.lineVolume, 4, 1)
        grid.addLayout(self.quotationHorizontalLayoutWidget, 5, 0, 1, 2)
        grid.addLayout(self.directHorizontalLayoutWidget, 6, 0, 1, 2)
        grid.addWidget(self.buttonSendOrder, 7, 0, 1, 2)


        self.btnHorizontalLayoutWidget = QtWidgets.QHBoxLayout()
        self.buBtn = QtWidgets.QPushButton(u"快买")
        self.sellBtn = QtWidgets.QPushButton(u"快卖")
        self.btnHorizontalLayoutWidget.addWidget(self.buBtn)
        self.btnHorizontalLayoutWidget.addWidget(self.sellBtn)
        grid.addLayout(self.btnHorizontalLayoutWidget, 8, 0, 1, 2)

        self.quicklineVolume = QtWidgets.QDoubleSpinBox()
        self.quicklineVolume.setDecimals(0)
        self.quicklineVolume.setMinimum(0)
        self.quicklineVolume.setMaximum(1000)
        self.quicklineVolume.setMinimum(1)
        grid.addWidget(self.quicklineVolume, 9, 0)

        self.QuickTradeTable = QuickTradeTable(self,self.omEngine, item, item.vtSymbol)
        grid.addWidget(self.QuickTradeTable, 9, 1, 10, 3)

        self.setLayout(grid)

    # ----------------------------------------------------------------------
    def sendOrder(self,direction,price):
        """发送委托"""
        try:
            symbol = str(self.lineSymbol.text())
            volume = int(self.quicklineVolume.text())
        except:
            return

        instrument = self.portfolio.instrumentDict.get(symbol, None)
        if not instrument:
            return

        # 做多
        if direction == DIRECTION_LONG:
            # 如果空头仓位大于等于买入量，则只需平
            if instrument.shortPos >= volume:
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, volume)
            # 否则先平后开
            else:
                openVolume = volume - instrument.shortPos
                if instrument.shortPos:
                    self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, instrument.shortPos)
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_OPEN, price, openVolume)
        # 做空
        else:
            if self.shortOpenRadio.isChecked():
                self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_OPEN, price, volume)
            else:
                if instrument.longPos >= volume:
                    self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, volume)
                else:
                    openVolume = volume - instrument.longPos
                    if instrument.longPos:
                        self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, instrument.longPos)
                    self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_OPEN, price, openVolume)

    # ----------------------------------------------------------------------
    def fastTrade(self, symbol, direction, offset, price, volume):
        """封装下单函数"""
        contract = self.mainEngine.getContract(symbol)
        if not contract:
            return

        req = VtOrderReq()
        req.symbol = symbol
        req.exchange = contract.exchange
        req.direction = direction
        req.offset = offset
        req.price = price
        req.volume = volume
        req.priceType = PRICETYPE_LIMITPRICE

        print "下单vtOrderID" + str(self.mainEngine.sendOrder(req, contract.gatewayName))
        # self.mainEngine.sendOrder(req, contract.gatewayName)

    # ----------------------------------------------------------------------
    def updateWidget(self, item):
        """双击监控组件单元格后自动更新组件"""
        instrument = item.data
        if not instrument:
            return

        self.lineSymbol.setText(instrument.symbol)

        # short
        if item.background is COLOR_BID:
            self.comboDirection.setCurrentIndex(1)
            self.linePrice.setText(str(instrument.bidPrice1))
            self.lineVolume.setText(str(instrument.bidVolume1))
        # long
        elif item.background is COLOR_ASK:
            self.comboDirection.setCurrentIndex(0)
            self.linePrice.setText(str(instrument.askPrice1))
            self.lineVolume.setText(str(instrument.askVolume1))

    # ----------------------------------------------------------------------
    def registerEvent(self,item,symbol):
        """注册事件监听,同时通知页面其他的控件更新"""
        print "同时通知页面其他的控件更新"
        if symbol == self.symbol:
            print '一样'
            return
        else:
            self.labelOptionName.setText(self.mainEngine.getContract(item.vtSymbol).name)
            self.lineSymbol.setText(item.symbol)
            self.fiveMarketWidget.registerEvent(item, item.vtSymbol)
            self.QuickTradeTable.registerEvent(item, item.vtSymbol)
            self.symbol= symbol


    def processTickEvent(self, event):
        """行情事件"""
        tick = event.dict_['data']

# add by lsm 20180104
class FiveMarketWidget(QtWidgets.QTableWidget):
        """五档行情列表"""
        headers = [
            u'买价',
            u'买量',
            u'卖价',
            u'卖量',
        ]

        # ----------------------------------------------------------------------
        def __init__(self, omEngine,item,vtSymbol, parent=None):
            """Constructor"""
            super(FiveMarketWidget, self).__init__(parent)

            # 保存代码和持仓的字典
            self.bidPriceDict = {}
            self.bidVolumeDict = {}
            self.askPriceDict = {}
            self.askVolumeDict = {}
            self.posDict = {}

            self.omEngine = omEngine
            self.mainEngine = omEngine.mainEngine
            self.eventEngine = self.mainEngine.eventEngine

            self.vtSymbol = vtSymbol
            self.portfolio = omEngine.portfolio

            # 初始化
            self.initUi(item)
            self.setFixedHeight(350)
            self.eventEngine.register(EVENT_TICK + vtSymbol, self.processTickEvent)

        # ----------------------------------------------------------------------
        def initUi(self,item):
            """初始化界面"""
            # 初始化表格
            self.setColumnCount(len(self.headers))

            self.setHorizontalHeaderLabels(self.headers)

            self.setRowCount(10)

            self.verticalHeader().setVisible(False)
            self.setEditTriggers(self.NoEditTriggers)

            for i in range(self.columnCount()):
                self.horizontalHeader().setResizeMode(i, QtWidgets.QHeaderView.Stretch)
            self.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            self.horizontalHeader().setResizeMode(self.columnCount() - 1, QtWidgets.QHeaderView.ResizeToContents)
            # 初始化标的单元格


            arrayBidPrice = [item.bidPrice1,item.bidPrice2,item.bidPrice3,item.bidPrice4,item.bidPrice5]
            arrayBidVolume = [item.bidVolume1, item.bidVolume2, item.bidVolume3, item.bidVolume4, item.bidVolume5]

            arrayaskPrice = [item.askPrice5, item.askPrice4, item.askPrice3, item.askPrice2, item.askPrice1]
            arrayaskVolume = [item.askVolume5, item.askVolume4, item.askVolume3, item.askVolume2, item.askVolume1]


            for row in range(0, 5, 1):
                cellAskPrice = OmCell(str(arrayaskPrice[row]), COLOR_ASK, COLOR_BLACK)
                cellAskVolume = OmCell(str(arrayaskVolume[row]), COLOR_ASK, COLOR_BLACK)
                self.setItem(row, 2, cellAskPrice)
                self.setItem(row, 3, cellAskVolume)
                self.askPriceDict[row] = cellAskPrice
                self.askVolumeDict[row] = cellAskVolume

                cellBidPrice = OmCell(str(arrayBidPrice[row]), COLOR_BID, COLOR_BLACK)
                cellBidVolume = OmCell(str(arrayBidVolume[row]), COLOR_BID, COLOR_BLACK)
                self.setItem(row+5, 0, cellBidPrice)
                self.setItem(row+5, 1, cellBidVolume)
                self.bidPriceDict[row] = cellBidPrice
                self.bidVolumeDict[row] = cellBidVolume

        # ----------------------------------------------------------------------
        def registerEvent(self,item,vtSymbol):
            """注册事件监听"""
            if vtSymbol == self.vtSymbol:
                print '一样'
                return
            else:
                print '合约改了'
                self.eventEngine.unregister(EVENT_TICK + self.vtSymbol, self.processTickEvent)
                self.changeFiveMarket(item)
                self.eventEngine.register(EVENT_TICK + vtSymbol, self.processTickEvent)
                self.vtSymbol = vtSymbol

        # ----------------------------------------------------------------------
        def processTickEvent(self, event):
            """行情更新，更新五档行情"""
            tick = event.dict_['data']
            symbol = tick.vtSymbol
            self.changeFiveMarket(tick)
        # ---------------------------------------------------------------------

        def changeFiveMarket(self,tick):
            '''五档行情列表数据更新'''
            self.bidPriceDict[0].setText(str(tick.bidPrice1))
            self.bidPriceDict[1].setText(str(tick.bidPrice2))
            self.bidPriceDict[2].setText(str(tick.bidPrice3))
            self.bidPriceDict[3].setText(str(tick.bidPrice4))
            self.bidPriceDict[4].setText(str(tick.bidPrice5))

            self.bidVolumeDict[0].setText(str(tick.bidVolume1))
            self.bidVolumeDict[1].setText(str(tick.bidVolume2))
            self.bidVolumeDict[2].setText(str(tick.bidVolume3))
            self.bidVolumeDict[3].setText(str(tick.bidVolume4))
            self.bidVolumeDict[4].setText(str(tick.bidVolume5))

            self.askPriceDict[0].setText(str(tick.askPrice5))
            self.askPriceDict[1].setText(str(tick.askPrice4))
            self.askPriceDict[2].setText(str(tick.askPrice3))
            self.askPriceDict[3].setText(str(tick.askPrice2))
            self.askPriceDict[4].setText(str(tick.askPrice1))

            self.askVolumeDict[0].setText(str(tick.askVolume5))
            self.askVolumeDict[1].setText(str(tick.askVolume4))
            self.askVolumeDict[2].setText(str(tick.askVolume3))
            self.askVolumeDict[3].setText(str(tick.askVolume2))
            self.askVolumeDict[4].setText(str(tick.askVolume1))


# add by lsm 20180105
class QuickTradeTable(QtWidgets.QTableWidget):
    """快捷下单的价格列表，目前显示最新成交价的前后20档价位""",
    headers = [
        u'委托',
        u'买量',
        u'价格',
        u'卖量',
        u'委托',
    ]

    # ----------------------------------------------------------------------
    def __init__(self, parentMonitor,omEngine, item, vtSymbol, parent=None):
        """Constructor"""
        super(QuickTradeTable, self).__init__(parent)
        self.parentMonitor=parentMonitor
        # 保存代码和持仓,委托的Cell字典
        self.cellAskVolume = {}
        self.cellPriceDict={}
        self.cellBidVolume={}

        self.cellAskEntrust={}
        self.cellBidEntrust = {}

        #保存当前代码的五档行情字典，一档价格：一档持仓量
        self.bidDict=[]
        self.askDict=[]

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine = self.mainEngine.eventEngine

        # item.lastPrice
        self.vtSymbol = vtSymbol
        self.portfolio = omEngine.portfolio

        # 初始化
        self.initUi(item)
        self.eventEngine.register(EVENT_TICK + self.vtSymbol, self.processTickEvent)
        self.eventEngine.register(EVENT_ORDER , self.processOrderEvent)

    # ----------------------------------------------------------------------
    def initUi(self, item):
        """初始化界面"""
        # 初始化表格
        self.setColumnCount(len(self.headers))

        self.setHorizontalHeaderLabels(self.headers)

        self.setRowCount(40)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

        for i in range(self.columnCount()):
            self.horizontalHeader().setResizeMode(i, QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.horizontalHeader().setResizeMode(self.columnCount() - 1, QtWidgets.QHeaderView.ResizeToContents)

        # 初始化标的单元格
        self.bidDict=dict(zip([item.bidPrice1, item.bidPrice2, item.bidPrice3, item.bidPrice4, item.bidPrice5],[item.bidVolume1, item.bidVolume2, item.bidVolume3, item.bidVolume4, item.bidVolume5]))
        self.askDict=dict(zip( [item.askPrice5, item.askPrice4, item.askPrice3, item.askPrice2, item.askPrice1],[item.askVolume5, item.askVolume4, item.askVolume3, item.askVolume2, item.askVolume1]))

        for row in range(-20,20,1):
            price=item.lastPrice-row/10000.0
            cellPrice = OmCell(str(price),COLOR_BLACK,COLOR_SYMBOL)

            if price in self.bidDict.keys():
                cellBid=OmCell(str(self.bidDict[price]),COLOR_BID,COLOR_BLACK)
            else:
                cellBid = OmCell("", COLOR_BID, COLOR_BLACK)

            if price in self.askDict.keys():
                askBid = OmCell(str(self.askDict[price]), COLOR_ASK, COLOR_BLACK)
            else:
                askBid = OmCell("", COLOR_ASK, COLOR_BLACK)

            self.cellPriceDict[row+20]=cellPrice
            self.cellBidVolume[row + 20] = cellBid

            self.cellAskVolume[row + 20] = askBid

            self.setItem(row+20, 2, cellPrice)
            self.setItem(row + 20, 1, cellBid)
            self.setItem(row + 20, 3, askBid)

        self.initOrderCell()
        self.itemDoubleClicked.connect(self.quickTrade)

    def initOrderCell(self):
        #委托量展示
        longVolumeDic, longLocalIDDic, shortVolumeDic, shortLocalIDDic=self.calculateOrderDict()
        if longVolumeDic:
            for row in range(0, 40, 1):
                priceAndVtSymbol = self.cellPriceDict[row].text()+self.vtSymbol
                if priceAndVtSymbol in longVolumeDic.keys():
                    bidEntrust=OmCell(str(longVolumeDic[priceAndVtSymbol]),COLOR_BID,COLOR_BLACK,longLocalIDDic[priceAndVtSymbol])
                else:
                    bidEntrust = OmCell("", COLOR_BID, COLOR_BLACK)
                if priceAndVtSymbol in shortVolumeDic.keys():
                    askEntrust = OmCell(str(shortVolumeDic[priceAndVtSymbol]), COLOR_ASK, COLOR_BLACK,shortLocalIDDic[priceAndVtSymbol])
                else:
                    askEntrust = OmCell("", COLOR_ASK, COLOR_BLACK)
                self.cellBidEntrust[row]=bidEntrust
                self.cellAskEntrust[row]=askEntrust

                self.setItem(row,0, bidEntrust)
                self.setItem(row,4, askEntrust)
        else:
            for row in range(0, 40, 1):
                bidEntrust = OmCell("", COLOR_BID, COLOR_BLACK)
                askEntrust = OmCell("", COLOR_ASK, COLOR_BLACK)
                self.cellBidEntrust[row] = bidEntrust
                self.cellAskEntrust[row] = askEntrust
                self.setItem(row, 0, bidEntrust)
                self.setItem(row, 4, askEntrust)



    # ----------------------------------------------------------------------
    def registerEvent(self, item, vtSymbol):
        """注册事件监听"""
        if vtSymbol == self.vtSymbol:
            print '一样'
            return
        else:
            print '合约改了'
            self.eventEngine.unregister(EVENT_TICK + self.vtSymbol, self.processTickEvent)
            self.eventEngine.unregister(EVENT_ORDER , self.processOrderEvent)
            self.changePriceData(item)
            self.eventEngine.register(EVENT_TICK + vtSymbol, self.processTickEvent)
            self.eventEngine.register(EVENT_ORDER , self.processOrderEvent)

            self.vtSymbol = vtSymbol

    # ----------------------------------------------------------------------
    def processTickEvent(self, event):
        """行情更新，价格列表,五档数据"""
        tick = event.dict_['data']
        print "更新行情数据"
        self.changePriceData(tick)

    def processOrderEvent(self, event):
        """行情更新,委托列表"""
        tick = event.dict_['data']
        symbol = tick.vtSymbol
        print "委托更新"
        self.changeOrderData(tick)

    def quickTrade(self):
        '''左击事件:快速下单!'''
        longPrice=float(self.cellPriceDict[self.currentRow()].text())
        if self.currentColumn()==0:
            print longPrice
            self.parentMonitor.sendOrder(DIRECTION_LONG,longPrice)
        elif self.currentColumn()==4:
            self.parentMonitor.sendOrder(DIRECTION_SHORT, longPrice)



    def contextMenuEvent(self,event):
        if self.currentColumn()==0:
            localIDs = self.cellBidEntrust[self.currentRow()].data
        elif self.currentColumn()==4:
            localIDs = self.cellAskEntrust[self.currentRow()].data
        print localIDs
        print self.cellPriceDict[self.currentRow()].text()
        if localIDs:
            for vtOrderID in localIDs:
                order = self.getOrder(vtOrderID)
                if order:
                    print "找到了"
                    print vtOrderID
                    req = VtCancelOrderReq()
                    req.symbol = order.symbol
                    req.exchange = order.exchange
                    req.frontID = order.frontID
                    req.sessionID = order.sessionID
                    req.orderID = order.orderID
                    print req.symbol,req.exchange,req.frontID,req.sessionID,req.orderID
                    self.mainEngine.cancelOrder(req, 'SEC')
                else:
                    print "没找到"
                    print vtOrderID
        else:
            print "没有东西"

    # ---------------------------------------------------------------------
    def changePriceData(self, item):
        """行情更新，价格列表,五档数据"""
        # 初始化标的单元格
        self.bidDict = dict(zip([item.bidPrice1, item.bidPrice2, item.bidPrice3, item.bidPrice4, item.bidPrice5],
                                [item.bidVolume1, item.bidVolume2, item.bidVolume3, item.bidVolume4, item.bidVolume5]))
        self.askDict = dict(zip([item.askPrice5, item.askPrice4, item.askPrice3, item.askPrice2, item.askPrice1],
                                [item.askVolume5, item.askVolume4, item.askVolume3, item.askVolume2, item.askVolume1]))

        for row in range(-20, 20, 1):
            price = item.lastPrice - row / 10000.0
            self.cellPriceDict[row + 20].setText(str(price))
            if price in self.bidDict.keys():
                self.cellBidVolume[row + 20].setText(str(self.bidDict[price]))
            else:
                self.cellBidVolume[row + 20].setText("")


            if price in self.askDict.keys():
                self.cellAskVolume[row + 20].setText(str(self.askDict[price]))
            else:
                self.cellAskVolume[row + 20].setText("")
        self.changeOrderData()

    def changeOrderData(self,item=None):
        """委托数据更新"""
        longVolumeDic, longLocalIDDic, shortVolumeDic, shortLocalIDDic = self.calculateOrderDict()
        print "更新委托数据"
        print longVolumeDic, longLocalIDDic, shortVolumeDic, shortLocalIDDic
        if longVolumeDic or shortVolumeDic:
            for row in range(0, 40, 1):
                priceAndVtSymbol = self.cellPriceDict[row].text() + self.vtSymbol

                print priceAndVtSymbol
                if priceAndVtSymbol in longVolumeDic.keys():
                    self.cellBidEntrust[row].setText(str(longVolumeDic[priceAndVtSymbol]))
                    self.cellBidEntrust[row].data=longLocalIDDic[priceAndVtSymbol]
                else:
                    self.cellBidEntrust[row].setText("")
                    self.cellBidEntrust[row].data=None

                if priceAndVtSymbol in shortVolumeDic.keys():
                    self.cellAskEntrust[row].setText(str(shortVolumeDic[priceAndVtSymbol]))
                    self.cellAskEntrust[row].data = shortLocalIDDic[priceAndVtSymbol]
                else:
                    self.cellAskEntrust[row].setText("")
                    self.cellAskEntrust[row].data = None
        else:
            for row in range(0, 40, 1):
                self.cellAskEntrust[row].setText("")
                self.cellAskEntrust[row].data = None
                self.cellBidEntrust[row].setText("")
                self.cellBidEntrust[row].data = None
    #
    def getOrder(self,vtOrderID):
        """查询单个合约的委托"""
        return self.mainEngine.getOrder(vtOrderID)

    def calculateOrderDict(self,event=None):
        """查询单个合约的委托"""
        return self.mainEngine.calculateOrderDict()
########################################################################
class ManualTrader(QtWidgets.QWidget):
    """手动交易组件"""

    #----------------------------------------------------------------------
    def __init__(self, omEngine, parent=None):
        """Constructor"""
        super(ManualTrader, self).__init__(parent)
        
        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine = omEngine.eventEngine
        self.tradingWidget={}
        self.initUi()
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'手动交易')
        
        posMonitor = PositionMonitor(self.mainEngine, self.eventEngine)
        accountMonitor=AccountMonitor(self.mainEngine, self.eventEngine)

        optionAnalysisTable=OptionAnalysisTable(self.omEngine)
        # for i in range(OptionAnalysisTable.columnCount()):
        #     OptionAnalysisTable.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        #     OptionAnalysisTable.setSorting(False)
        
        orderMonitor = WorkingOrderMonitor(self.mainEngine, self.eventEngine)
        for i in range(orderMonitor.columnCount()):
            orderMonitor.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        orderMonitor.setSorting(False)
            

        
        # chainMonitor = ChainMonitor(self.omEngine, self.eventEngine)
        # chainMonitor.itemDoubleClicked.connect(tradingWidget.updateWidget)
        tradingWidget = TradingWidget(self.omEngine)

        # chainMonitor = ChainMonitor(self.omEngine, self.eventEngine)
        # chainMonitor.itemDoubleClicked.connect(tradingWidget.updateWidget)

        vbox1 = QtWidgets.QVBoxLayout()
        tab2 = QtWidgets.QTabWidget()
        tab2.addTab(posMonitor, u'持仓')
        tab2.addTab(orderMonitor, u'可撤委托')
        tab2.addTab(accountMonitor,u'账户')
        vbox1.addWidget(tab2)
        vbox1.addWidget(optionAnalysisTable)
        
        vbox2 = QtWidgets.QVBoxLayout()
        vbox2.addWidget(tradingWidget)
        vbox2.addStretch()

        self.setWindowTitle(u'手动交易')

        tab = QtWidgets.QTabWidget()
        for chain in self.omEngine.portfolio.chainDict.values():
            # chainManager = ChainVolatilityManager(chain)
            chainMonitor = ChainMonitor(chain,self.omEngine, self.mainEngine,self.eventEngine)
            # chainMonitor.itemDoubleClicked.connect(tradingWidget.updateWidget)
            chainMonitor.itemDoubleClicked.connect(self.showTradeWidget)

            tab.addTab(chainMonitor,chain.symbol)


        
        hbox = QtWidgets.QHBoxLayout()
        hbox.addLayout(vbox1)
        hbox.addLayout(vbox2)
        
        vbox3 = QtWidgets.QVBoxLayout()
        vbox3.addWidget(tab)
        # vbox3.addWidget(chainMonitor)
        vbox3.addLayout(hbox)
        
        self.setLayout(vbox3)

    def showTradeWidget(self,item):
        instrument = item.data
        try:
            self.tradingWidget['tradingWidget'].show()
            self.tradingWidget['tradingWidget'].registerEvent(instrument,instrument.vtSymbol)
        except KeyError:
            self.tradingWidget['tradingWidget'] = FloatTradingWidget(self.omEngine,instrument,instrument.vtSymbol)
            self.tradingWidget['tradingWidget'].show()

# add by lsm 20180111
class OptionAnalysisTable(QtWidgets.QTableWidget):
    """持仓统计列表""",
    headers = [
        u'到期日',
        u'到期时间',
        u'CPrice',
        u'CBidVol',
        u'CAskVol',
        u'CallImv',
        u'执行价格',
        u'隐含利率',
        u'PutImv',
        u'PAskVol',
        u'PBidVol',
        u'PPrice',

        u'Delta',
        u'Gamma',
        u'Vega',
        u'Theta',
        u'凸度',
        u'偏度',
        u'CallImpv',
        u'PutImpv'

    ]

    def __init__(self, omEngine, parent=None):
        """Constructor"""
        super(OptionAnalysisTable,self).__init__(parent)

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine=self.mainEngine.eventEngine
        self.portfolio = omEngine.portfolio

        # cellArray定义
        self.cellDueDate={}
        # 到期时间
        self.cellDueTime={}
        self.cellCallPrice={}
        self.cellCallBidVol={}
        self.cellCallAskVol={}
        self.cellCallImv={}
        self.cellK = {}
        self.cellRate={}
        self.cellPutImv={}
        self.cellPutAskVol={}
        self.cellPutBidVol={}
        self.cellPutPrice={}

        self.cellDelta = {}
        self.cellGamma = {}
        self.cellVega = {}
        self.cellTheta = {}
        self.cellConvexity={}
        self.cellSkew = {}
        self.cellCallImpv={}
        self.cellPutImpv={}

        self.totalCellDelta=None
        self.totalCellGamma=None
        self.totalCellVega=None
        self.totalCellTheta=None

        self.initUi()
        self.eventEngine.register(EVENT_TIMER, self.timingCalculate)

    def initUi(self):
        """初始化界面"""
        # 初始化表格
        self.setColumnCount(len(self.headers))

        self.setHorizontalHeaderLabels(self.headers)

        self.setRowCount(5)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)


        # for i in range(self.columnCount()):
        #     self.horizontalHeader().setResizeMode(i, QtWidgets.QHeaderView.Stretch)
        # self.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # self.horizontalHeader().setResizeMode(self.columnCount() - 1, QtWidgets.QHeaderView.ResizeToContents)
        # 初始化标的单元格
        self.totalCellDelta = OmCell(str(self.portfolio.posDelta), None, COLOR_POS)
        self.totalCellGamma =OmCell(str(self.portfolio.posGamma), None, COLOR_POS)
        self.totalCellVega = OmCell(str(self.portfolio.posVega), None, COLOR_POS)
        self.totalCellTheta = OmCell(str(self.portfolio.posTheta), None, COLOR_POS)
        self.setItem(4, 0, OmCell(u"汇总", None, COLOR_POS))
        self.setItem(4, 12,  self.totalCellDelta)
        self.setItem(4, 13,  self.totalCellGamma)
        self.setItem(4, 14, self.totalCellVega)
        self.setItem(4, 15,self.totalCellTheta)

        for row,chain in enumerate(self.portfolio.chainDict.values()):
            cellDueDate = OmCell(str(chain.optionDict[chain.atTheMoneySymbol].expiryDate), None, COLOR_POS)
            cellDueTime= OmCell(str(round(chain.optionDict[chain.atTheMoneySymbol].t,4)), None, COLOR_POS)

            cellCallPrice = OmCell(str(chain.optionDict[chain.atTheMoneySymbol].midPrice), None, COLOR_POS)
            cellCallBidVol = OmCell(str(chain.optionDict[chain.atTheMoneySymbol].bidVolume1), None, COLOR_POS)

            cellCallAskVol = OmCell(str(chain.optionDict[chain.atTheMoneySymbol].askVolume1), None, COLOR_POS)
            cellCallImv = OmCell(str(chain.optionDict[chain.atTheMoneySymbol].midImpv), None, COLOR_POS)

            cellK = OmCell(str(chain.optionDict[chain.atTheMoneySymbol].k), None, COLOR_POS)
            cellRate = OmCell(str(chain.chainRate), COLOR_BID, COLOR_POS)

            cellPutImv = OmCell(str(chain.relativeOption[chain.atTheMoneySymbol].midImpv), None, COLOR_POS)
            cellPutAskVol = OmCell(str(chain.relativeOption[chain.atTheMoneySymbol].askVolume1), None, COLOR_POS)
            cellPutBidVol = OmCell(str(chain.relativeOption[chain.atTheMoneySymbol].bidVolume1), None, COLOR_POS)
            cellPutPrice = OmCell(str(chain.relativeOption[chain.atTheMoneySymbol].midPrice), None, COLOR_POS)

            cellDelta = OmCell(str(chain.posDelta), None, COLOR_POS)
            cellGamma = OmCell(str(chain.posGamma), None, COLOR_POS)
            cellVega = OmCell(str(chain.posVega), None, COLOR_POS)
            cellTheta = OmCell(str(chain.posTheta), None, COLOR_POS)
            cellConvexity=OmCell(str(chain.convexity), None, COLOR_POS)
            cellSkew=OmCell(str(chain.skew), None, COLOR_POS)
            cellCallImpv =OmCell(str(chain.callImpv), None, COLOR_POS)
            cellPutImpv = OmCell(str(chain.putImpv), None, COLOR_POS)

            self.cellDelta[row]=cellDelta
            self.cellGamma[row]=cellGamma
            self.cellVega[row]=cellVega
            self.cellTheta[row]=cellTheta

            self.cellDueDate[row]=cellDueDate
            # 到期时间
            self.cellDueTime[row]=cellDueTime

            self.cellCallPrice[row] = cellCallPrice
            self.cellCallBidVol[row] = cellCallBidVol
            self.cellCallAskVol[row] = cellCallAskVol
            self.cellCallImv[row] = cellCallImv

            self.cellK[row] = cellK
            self.cellRate[row] = cellRate

            self.cellPutImv[row] = cellPutImv
            self.cellPutAskVol[row] = cellPutAskVol
            self.cellPutBidVol[row] = cellPutBidVol
            self.cellPutPrice[row] = cellPutPrice

            self.cellConvexity[row] = cellConvexity
            self.cellSkew[row] = cellSkew

            self.cellCallImpv[row] = cellCallImpv

            self.cellPutImpv[row] = cellPutImpv

            self.setItem(row , 0, cellDueDate)
            self.setItem(row , 1, cellDueTime)
            self.setItem(row, 2, cellCallPrice)
            self.setItem(row, 3, cellCallBidVol)
            self.setItem(row, 4, cellCallAskVol)
            self.setItem(row, 5, cellCallImv)
            self.setItem(row, 6, cellK)
            self.setItem(row, 7, cellRate)
            self.setItem(row, 8, cellPutImv)
            self.setItem(row, 9, cellPutAskVol)
            self.setItem(row, 10, cellPutBidVol)
            self.setItem(row, 11, cellPutPrice)

            self.setItem(row, 12, cellDelta)
            self.setItem(row, 13, cellGamma)
            self.setItem(row, 14, cellVega)
            self.setItem(row, 15, cellTheta)
            self.setItem(row, 16, cellConvexity)
            self.setItem(row, 17, cellSkew)

            self.setItem(row, 18, cellCallImpv)
            self.setItem(row, 19, cellPutImpv)



    def timingCalculate(self,event):
        for row, chain in enumerate(self.portfolio.chainDict.values()):

            self.cellCallPrice[row].setText(str(chain.optionDict[chain.atTheMoneySymbol].midPrice))

            self.cellCallBidVol[row].setText(str(chain.optionDict[chain.atTheMoneySymbol].bidVolume1))

            self.cellCallAskVol[row].setText(str(chain.optionDict[chain.atTheMoneySymbol].askVolume1))

            self.cellCallImv[row].setText(str(chain.optionDict[chain.atTheMoneySymbol].midImpv))

            self.cellK[row].setText(str(chain.optionDict[chain.atTheMoneySymbol].k))
            self.cellRate[row].setText(str(chain.chainRate))

            self.cellPutPrice[row].setText(str(chain.relativeOption[chain.atTheMoneySymbol].midPrice))

            self.cellPutBidVol[row].setText(str(chain.relativeOption[chain.atTheMoneySymbol].bidVolume1))

            self.cellPutAskVol[row].setText(str(chain.relativeOption[chain.atTheMoneySymbol].askVolume1))

            self.cellPutImv[row].setText(str(chain.relativeOption[chain.atTheMoneySymbol].midImpv))

            self.cellDelta[row].setText(str(chain.posDelta))
            self.cellGamma[row].setText(str(chain.posGamma))
            self.cellVega[row].setText(str(chain.posVega))
            self.cellTheta[row].setText(str(chain.posTheta))

            self.cellConvexity[row].setText(str(chain.convexity))
            self.cellSkew[row].setText(str(chain.skew))

            self.cellCallImpv[row].setText(str(chain.callImpv))
            self.cellPutImpv[row].setText(str(chain.putImpv))

        self.totalCellDelta.setText(str(self.portfolio.posDelta))
        self.totalCellGamma.setText(str(self.portfolio.posGamma))
        self.totalCellVega.setText(str(self.portfolio.posVega))
        self.totalCellTheta.setText(str(self.portfolio.posTheta))

# add by lsm 20180117
########################################################################
class PositionMonitor(BasicMonitor):
    """持仓监控"""

    # ----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(PositionMonitor, self).__init__(mainEngine, eventEngine, parent)

        d = OrderedDict()
        d['symbol'] = {'chinese': vtText.CONTRACT_SYMBOL, 'cellType': BasicCell}
        d['vtSymbol'] = {'chinese': vtText.CONTRACT_NAME, 'cellType': NameCell}
        d['direction'] = {'chinese': vtText.DIRECTION, 'cellType': DirectionCell}
        d['position'] = {'chinese': vtText.POSITION, 'cellType': BasicCell}
        d['ydPosition'] = {'chinese': vtText.YD_POSITION, 'cellType': BasicCell}
        d['frozen'] = {'chinese': vtText.FROZEN, 'cellType': BasicCell}
        d['price'] = {'chinese': vtText.PRICE, 'cellType': BasicCell}
        d['positionProfit'] = {'chinese': vtText.POSITION_PROFIT, 'cellType': PnlCell}
        d['gatewayName'] = {'chinese': vtText.GATEWAY, 'cellType': BasicCell}
        self.setHeaderDict(d)

        self.setDataKey('vtPositionName')
        self.setEventType(EVENT_POSITION)
        self.setFont(BASIC_FONT)
        self.setSaveData(True)
        self.shouldRefresh=False

        self.initTable()
        # 注册事件监听
        self.registerEvent()
        self.eventEngine.register(EVENT_TRADE,self.changeShouldRefresh)

    def registerEvent(self):
        self.signal.connect(self.deleteAllRows)
        self.signal.connect(self.updateEvent)
        self.eventEngine.register(self.eventType, self.signal.emit)


    def changeShouldRefresh(self,data):
        self.shouldRefresh = True

    def deleteAllRows(self,data):
        if self.shouldRefresh:
            iLen = len(self.dataDict.values())
            for i in range(0,iLen):
                self.removeRow(0)
            self.dataDict.clear()
            self.shouldRefresh=False


# add by lsm 20180118
class AccountTable(QtWidgets.QTableWidget):
    """账户信息显示""",
    headers = [
        u'委托',
        u'买量',
        u'价格',
        u'卖量',
        u'委托',
    ]

    # ----------------------------------------------------------------------
    def __init__(self,omEngine, parent=None):
        """Constructor"""
        super(AccountTable, self).__init__(parent)


        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine = self.mainEngine.eventEngine

        # 初始化
        self.initUi(item)
        self.eventEngine.register(EVENT_ACCOUNT, self.processAccountEvent)

    # ----------------------------------------------------------------------
    def initUi(self, item):
        """初始化界面"""
        # 初始化表格
        self.setColumnCount(len(self.headers))

        self.setHorizontalHeaderLabels(self.headers)

        self.setRowCount(1)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

        for i in range(self.columnCount()):
            self.horizontalHeader().setResizeMode(i, QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.horizontalHeader().setResizeMode(self.columnCount() - 1, QtWidgets.QHeaderView.ResizeToContents)

        # 初始化标的单元格
        self.bidDict=dict(zip([item.bidPrice1, item.bidPrice2, item.bidPrice3, item.bidPrice4, item.bidPrice5],[item.bidVolume1, item.bidVolume2, item.bidVolume3, item.bidVolume4, item.bidVolume5]))
        self.askDict=dict(zip( [item.askPrice5, item.askPrice4, item.askPrice3, item.askPrice2, item.askPrice1],[item.askVolume5, item.askVolume4, item.askVolume3, item.askVolume2, item.askVolume1]))

        for row in range(-20,20,1):
            price=item.lastPrice-row/10000.0
            cellPrice = OmCell(str(price),COLOR_BLACK,COLOR_SYMBOL)

            if price in self.bidDict.keys():
                cellBid=OmCell(str(self.bidDict[price]),COLOR_BID,COLOR_BLACK)
            else:
                cellBid = OmCell("", COLOR_BID, COLOR_BLACK)

            if price in self.askDict.keys():
                askBid = OmCell(str(self.askDict[price]), COLOR_ASK, COLOR_BLACK)
            else:
                askBid = OmCell("", COLOR_ASK, COLOR_BLACK)

            self.cellPriceDict[row+20]=cellPrice
            self.cellBidVolume[row + 20] = cellBid

            self.cellAskVolume[row + 20] = askBid

            self.setItem(row+20, 2, cellPrice)
            self.setItem(row + 20, 1, cellBid)
            self.setItem(row + 20, 3, askBid)

        self.initOrderCell()
        self.itemDoubleClicked.connect(self.quickTrade)

    def initOrderCell(self):
        #委托量展示
        longVolumeDic, longLocalIDDic, shortVolumeDic, shortLocalIDDic=self.calculateOrderDict()
        if longVolumeDic:
            for row in range(0, 40, 1):
                priceAndVtSymbol = self.cellPriceDict[row].text()+self.vtSymbol
                if priceAndVtSymbol in longVolumeDic.keys():
                    bidEntrust=OmCell(str(longVolumeDic[priceAndVtSymbol]),COLOR_BID,COLOR_BLACK,longLocalIDDic[priceAndVtSymbol])
                else:
                    bidEntrust = OmCell("", COLOR_BID, COLOR_BLACK)
                if priceAndVtSymbol in shortVolumeDic.keys():
                    askEntrust = OmCell(str(shortVolumeDic[priceAndVtSymbol]), COLOR_ASK, COLOR_BLACK,shortLocalIDDic[priceAndVtSymbol])
                else:
                    askEntrust = OmCell("", COLOR_ASK, COLOR_BLACK)
                self.cellBidEntrust[row]=bidEntrust
                self.cellAskEntrust[row]=askEntrust

                self.setItem(row,0, bidEntrust)
                self.setItem(row,4, askEntrust)
        else:
            for row in range(0, 40, 1):
                bidEntrust = OmCell("", COLOR_BID, COLOR_BLACK)
                askEntrust = OmCell("", COLOR_ASK, COLOR_BLACK)
                self.cellBidEntrust[row] = bidEntrust
                self.cellAskEntrust[row] = askEntrust
                self.setItem(row, 0, bidEntrust)
                self.setItem(row, 4, askEntrust)



    # ----------------------------------------------------------------------
    def registerEvent(self, item, vtSymbol):
        """注册事件监听"""
        if vtSymbol == self.vtSymbol:
            print '一样'
            return
        else:
            print '合约改了'
            self.eventEngine.unregister(EVENT_TICK + self.vtSymbol, self.processTickEvent)
            self.eventEngine.unregister(EVENT_ORDER + self.vtSymbol, self.calculateOrderDict)
            self.changePriceData(item)
            self.eventEngine.register(EVENT_TICK + vtSymbol, self.processTickEvent)
            self.eventEngine.register(EVENT_ORDER + self.vtSymbol, self.calculateOrderDict)

            self.vtSymbol = vtSymbol

    # ----------------------------------------------------------------------
    def processTickEvent(self, event):
        """行情更新，价格列表,五档数据"""
        tick = event.dict_['data']
        self.changePriceData(tick)

    def processOrderEvent(self, event):
        """行情更新,委托列表"""
        tick = event.dict_['data']
        symbol = tick.vtSymbol
        self.changeOrderData(tick)

    def quickTrade(self):
        '''左击事件:快速下单!'''
        longPrice=float(self.cellPriceDict[self.currentRow()].text())
        if self.currentColumn()==0:
            self.parentMonitor.sendOrder(DIRECTION_LONG,longPrice)
        elif self.currentColumn()==4:
            self.parentMonitor.sendOrder(DIRECTION_SHORT, longPrice)



    def contextMenuEvent(self,event):
        if self.currentColumn()==0:
            localIDs = self.cellBidEntrust[self.currentRow()].data
        elif self.currentColumn()==4:
            localIDs = self.cellAskEntrust[self.currentRow()].data
        if localIDs:
            for vtOrderID in localIDs:
                order = self.getOrder(vtOrderID)
                if order:
                    req = VtCancelOrderReq()
                    req.symbol = order.symbol
                    req.exchange = order.exchange
                    req.frontID = order.frontID
                    req.sessionID = order.sessionID
                    req.orderID = order.orderID
                    self.mainEngine.cancelOrder(req, 'SEC')
        else:
            print "没有东西"

    # ---------------------------------------------------------------------
    def changePriceData(self, item):
        """行情更新，价格列表,五档数据"""
        # 初始化标的单元格
        self.bidDict = dict(zip([item.bidPrice1, item.bidPrice2, item.bidPrice3, item.bidPrice4, item.bidPrice5],
                                [item.bidVolume1, item.bidVolume2, item.bidVolume3, item.bidVolume4, item.bidVolume5]))
        self.askDict = dict(zip([item.askPrice5, item.askPrice4, item.askPrice3, item.askPrice2, item.askPrice1],
                                [item.askVolume5, item.askVolume4, item.askVolume3, item.askVolume2, item.askVolume1]))

        for row in range(-20, 20, 1):
            price = item.lastPrice - row / 10000.0
            self.cellPriceDict[row + 20].setText(str(price))
            if price in self.bidDict.keys():
                self.cellBidVolume[row + 20].setText(str(self.bidDict[price]))
            else:
                self.cellBidVolume[row + 20].setText("")


            if price in self.askDict.keys():
                self.cellAskVolume[row + 20].setText(str(self.askDict[price]))
            else:
                self.cellAskVolume[row + 20].setText("")
        self.changeOrderData()

    def changeOrderData(self,item=None):
        """委托数据更新"""
        longVolumeDic, longLocalIDDic, shortVolumeDic, shortLocalIDDic = self.calculateOrderDict()
        if longVolumeDic:
            for row in range(0, 40, 1):
                priceAndVtSymbol = self.cellPriceDict[row].text() + self.vtSymbol
                if priceAndVtSymbol in longVolumeDic.keys():
                    self.cellBidEntrust[row].setText(str(longVolumeDic[priceAndVtSymbol]))
                    self.cellBidEntrust[row].data=longLocalIDDic[priceAndVtSymbol]
                else:
                    self.cellBidEntrust[row].setText("")
                    self.cellBidEntrust[row].data=None

                if priceAndVtSymbol in shortVolumeDic.keys():
                    self.cellAskEntrust[row].setText(str(shortVolumeDic[priceAndVtSymbol]))
                    self.cellAskEntrust[row].data = shortLocalIDDic[priceAndVtSymbol]
                else:
                    self.cellAskEntrust[row].setText("")
                    self.cellAskEntrust[row].data = None
        else:
            for row in range(0, 40, 1):
                self.cellAskEntrust[row].setText("")
                self.cellAskEntrust[row].data = None
                self.cellBidEntrust[row].setText("")
                self.cellBidEntrust[row].data = None
    #
    def getOrder(self,vtOrderID):
        """查询单个合约的委托"""
        return self.mainEngine.getOrder(vtOrderID)

    def calculateOrderDict(self,event=None):
        """查询单个合约的委托"""
        return self.mainEngine.calculateOrderDict()