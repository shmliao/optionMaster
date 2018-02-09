# encoding: UTF-8

from vnpy.event import Event
from uiOmVolatilityManager import VolatilityChart

from vnpy.trader.vtConstant import DIRECTION_LONG, DIRECTION_SHORT, OFFSET_OPEN, OFFSET_CLOSE, PRICETYPE_LIMITPRICE
from vnpy.trader.vtObject import VtOrderReq
from vnpy.trader.vtEvent import EVENT_TICK, EVENT_TRADE, EVENT_ORDER, EVENT_TIMER
from vnpy.trader.uiBasicWidget import WorkingOrderMonitor, BasicMonitor, BasicCell, NameCell, DirectionCell, PnlCell, \
    AccountMonitor
from uiOmBase import *
from omDate import CalendarManager

import json
import csv
import os
import platform
from collections import OrderedDict
from PyQt4.QtCore import Qt

from vnpy.trader.vtFunction import *
from vnpy.trader.vtGateway import *
from vnpy.trader import vtText
from vnpy.trader.vtConstant import *
from vnpy.trader.uiQt import QtGui, QtWidgets, QtCore, BASIC_FONT
from PyQt4.QtGui import QAbstractItemView
from math import (log, pow, sqrt, exp)


# Add by lsm 20180208
class BookChainMonitor(QtWidgets.QTableWidget):
    """期权链监控"""
    headers = [
        u'买价0',
        u'买隐波1',
        u'call买阈值2',
        u'买委托量3',
        u'Impv递增4',
        u'perVol5',
        u'单次量6',
        u'买开关7',

        u'卖开关8',
        u'卖价9',
        u'卖隐波10',
        u'call卖阈值11',
        u'卖委托量12',
        u'Impv递增13',
        u'perVol14',
        u'单次量15',

        u'行权价16',

        u'Impv递增17',
        u'perVol18',
        u'单次量19',
        u'卖委托量20',
        u'put卖阈值21',
        u'卖隐波22',
        u'卖价23',
        u'卖开关24',

        u'买开关25',
        u'Impv递增26',
        u'perVol27',
        u'单次量28',
        u'买委托量29',
        u'put买阈值30',
        u'买隐波31',
        u'买价32',
    ]
    signalTick = QtCore.pyqtSignal(type(Event()))
    signalPos = QtCore.pyqtSignal(type(Event()))
    signalTrade = QtCore.pyqtSignal(type(Event()))

    def __init__(self, chain, omEngine, mainEngine, eventEngine, bookImpvConfig,parent=None):
        """Constructor"""
        super(BookChainMonitor, self).__init__(parent)

        self.omEngine = omEngine
        self.eventEngine = eventEngine
        self.mainEngine = mainEngine
        # 保存代码和持仓的字典

        self.cellBidPrice = {}
        self.cellBidImpv =  {}
        self.cellBookBidImpv=  {}
        self.cellAskPrice =  {}
        self.cellAskImpv =  {}
        self.cellBookAskImpv =  {}

        self.cellBidStepPerVolumn = {}
        self.cellBidImpvChange = {}
        self.cellBidStepVolum = {}
        self.cellAskStepPerVolumn = {}
        self.cellAskImpvChange = {}
        self.cellAskStepVolum = {}

        self.cellBidSwitch =  {}
        self.cellAskSwitch = {}

        self.cellBidEntruthVolumn = {}
        self.cellAskEntruthVolumn = {}

        #合约的波动率报单开关key:symbol,value:off,on
        self.switchBidSymbol={}
        self.switchAskSymbol = {}
        # add by me
        self.chain = chain
        # 保存期权对象的字典
        portfolio = omEngine.portfolio
        self.instrumentDict = {}
        self.instrumentDict.update(portfolio.optionDict)
        self.instrumentDict.update(portfolio.underlyingDict)

        # 打开波动率报单的合约
        self.onBidSymbol = []
        self.onAskSymbol = []

        self.bookBidImpv = {}
        self.bidEntruthVolumn = {}
        self.bidStepPerVolumn = {}
        self.bidImpvChange = {}
        self.bidStepVolum = {}

        self.bookAskImpv = {}
        self.askEntruthVolumn = {}
        self.askStepPerVolumn = {}
        self.askImpvChange = {}
        self.askStepVolum = {}

        # 初始化
        self.initUi()
        self.registerEvent()
        self.setShowGrid(True)
        # ----------------------------------------------------------------------
        self.itemClicked.connect(self.switchVolitity)

        self.eventEngine.register(EVENT_TIMER, self.timingBook)

    def modifyConfig(self):
        self.bookBidImpv = {}
        self.bookAskImpv = {}
        self.bidEntruthVolumn = {}
        self.askEntruthVolumn = {}
        for option in self.chain.optionDict.values():
            self.bookBidImpv[option.symbol]=float(self.cellBookBidImpv[option.symbol].text())
            self.bookAskImpv[option.symbol] = float(self.cellBookAskImpv[option.symbol].text())
            self.bidEntruthVolumn[option.symbol] =float(self.cellBidEntruthVolumn[option.symbol].text())
            self.askEntruthVolumn[option.symbol] = float(self.cellAskEntruthVolumn[option.symbol].text())

    def timingBook(self,event):
        pass
        # for symbol in self.onSymbol:
        #     #  买下单
        #
        #     if self.bookBidImpv[symbol]/100>self.chain.optionDict[symbol].bidImpv and self.bookBidImpv[symbol]>0 and self.chain.optionDict[symbol].bidImpv>0:
        #         print '买'
        #     if self.bookAskImpv[symbol]/100<self.chain.optionDict[symbol].askImpv and self.bookAskImpv[symbol]>0 and self.chain.optionDict[symbol].askImpv>0:
        #         print '卖'

    def backups(self):
        longVolumeDic,shortVolumeDic=self.calcutateOrderBySymbol()
        longOrder=False
        shorOrder=True
        if symbol not in longVolumeDic.keys():
            longOrder=True
        elif longVolumeDic[symbol]<10:
            longOrder=True

        if symbol not in shortVolumeDic.keys():
            shorOrder = True
        elif shortVolumeDic[symbol] < 10:
            shorOrder = True

    def switchVolitity(self,item):
        option = item.data
        print option.symbol
        if item in self.cellBidSwitch.values():
            if option.symbol in self.onBidSymbol:
                self.switchBidSymbol[option.symbol] = 'off'
                self.cellBidSwitch[option.symbol].setText('off')
                self.onBidSymbol.remove(option.symbol)
            else:
                self.switchBidSymbol[option.symbol] = 'on'
                self.cellBidSwitch[option.symbol].setText('on')
                self.onBidSymbol.append(option.symbol)
        elif item in self.cellAskSwitch.values():
            if option.symbol in self.onAskSymbol:
                self.switchAskSymbol[option.symbol] = 'off'
                self.cellAskSwitch[option.symbol].setText('off')
                self.onAskSymbol.remove(option.symbol)
            else:
                self.switchAskSymbol[option.symbol] = 'on'
                self.cellAskSwitch[option.symbol].setText('on')
                self.onAskSymbol.append(option.symbol)
            return

    def initUi(self):
        """初始化界面"""
        portfolio = self.omEngine.portfolio

        # 初始化表格
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        rowCount=0
        for chain in portfolio.chainDict.values():
            if chain == self.chain:
                rowCount += len(chain.callDict)
        self.setRowCount(rowCount)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)


        row = 0

        callRow = row
        # 初始化期权单元格


        for option in self.chain.callDict.values():
            self.bookBidImpv[option.symbol]=0
            self.bidEntruthVolumn[option.symbol]=0
            self.bidStepPerVolumn[option.symbol]=0
            self.bidImpvChange[option.symbol]=0
            self.bidStepVolum[option.symbol]=0

            self.bookAskImpv[option.symbol]=0
            self.askEntruthVolumn[option.symbol]=0
            self.askStepPerVolumn[option.symbol]=0
            self.askImpvChange[option.symbol]=0
            self.askStepVolum[option.symbol]=0

            self.switchBidSymbol[option.symbol]='off'
            self.switchAskSymbol[option.symbol]='off'

            cellBidPrice = OmCell(str("%.4f" % option.bidPrice1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidImpv = OmCell('%.2f' % (option.bidImpv * 100), COLOR_BID, COLOR_BLACK, option, 10)
            cellBookBidImpv = OmCellEditText(self.bookBidImpv[option.symbol], 'impv', option)
            cellBidEntruthVolumn = OmCellEditText(self.bidEntruthVolumn[option.symbol],'volumn' , option)
            cellBidImpvChange = OmCellEditText(self.bidImpvChange[option.symbol], 'impv', option)
            cellBidStepPerVolumn = OmCellEditText(self.bidStepPerVolumn[option.symbol], 'volumn', option)
            cellBidStepVolum = OmCellEditText(self.bidStepVolum[option.symbol], 'volumn', option)

            cellBidSwitch = OmCell(self.switchBidSymbol[option.symbol], COLOR_BID, COLOR_BLACK, option, 10)
            cellAskSwitch = OmCell(self.switchAskSymbol[option.symbol], COLOR_ASK, COLOR_BLACK, option, 10)

            cellAskPrice = OmCell(str("%.4f" % option.askPrice1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskImpv = OmCell('%.2f' % (option.askImpv * 100), COLOR_ASK, COLOR_BLACK, option, 10)
            cellBookAskImpv =OmCellEditText(self.bookAskImpv[option.symbol] , 'impv', option)
            cellAskEntruthVolumn =OmCellEditText(self.askEntruthVolumn[option.symbol] ,'volumn' , option)
            cellAskImpvChange = OmCellEditText(self.askImpvChange[option.symbol], 'impv', option)
            cellAskStepPerVolumn = OmCellEditText(self.askStepPerVolumn[option.symbol], 'volumn', option)
            cellAskStepVolum = OmCellEditText(self.askStepVolum[option.symbol], 'volumn', option)

            cellStrike = OmCell(str(option.k), COLOR_STRIKE)

            self.cellBidPrice[option.symbol] = cellBidPrice
            self.cellBidImpv[option.symbol] = cellBidImpv
            self.cellBookBidImpv[option.symbol] = cellBookBidImpv
            self.cellBidEntruthVolumn[option.symbol] = cellBidEntruthVolumn
            self.cellBidImpvChange[option.symbol] = cellBidImpvChange
            self.cellBidStepPerVolumn[option.symbol] = cellBidStepPerVolumn
            self.cellBidStepVolum[option.symbol] = cellBidStepVolum

            self.cellBidSwitch[option.symbol] = cellBidSwitch
            self.cellAskSwitch[option.symbol] = cellAskSwitch

            self.cellAskPrice[option.symbol] = cellAskImpv
            self.cellAskImpv[option.symbol] = cellAskImpv
            self.cellBookAskImpv[option.symbol] = cellBookAskImpv
            self.cellAskEntruthVolumn[option.symbol] = cellAskEntruthVolumn
            self.cellAskImpvChange[option.symbol] = cellAskImpvChange
            self.cellAskStepPerVolumn[option.symbol] = cellAskStepPerVolumn
            self.cellAskStepVolum[option.symbol] = cellAskStepVolum

            self.setItem(callRow, 0, cellBidPrice)
            self.setItem(callRow, 1, cellBidImpv)
            self.setCellWidget(callRow, 2, cellBookBidImpv)
            self.setCellWidget(callRow, 3, cellBidEntruthVolumn)
            self.setCellWidget(callRow, 4, cellBidImpvChange)
            self.setCellWidget(callRow, 5, cellBidStepPerVolumn)
            self.setCellWidget(callRow, 6, cellBidStepVolum)

            self.setItem(callRow, 7, cellBidSwitch)
            self.setItem(callRow, 8, cellAskSwitch)

            self.setItem(callRow, 9, cellAskPrice)
            self.setItem(callRow, 10, cellAskImpv)
            self.setCellWidget(callRow, 11, cellBookAskImpv)
            self.setCellWidget(callRow, 12, cellAskEntruthVolumn)
            self.setCellWidget(callRow, 13, cellAskImpvChange)
            self.setCellWidget(callRow, 14, cellAskStepPerVolumn)
            self.setCellWidget(callRow, 15, cellAskStepVolum)
            self.setItem(callRow, 16, cellStrike)
            callRow += 1
            # put
        putRow = row

        for option in self.chain.putDict.values():
            self.bookBidImpv[option.symbol] = 0
            self.bidEntruthVolumn[option.symbol] = 0
            self.bidStepPerVolumn[option.symbol] = 0
            self.bidImpvChange[option.symbol] = 0
            self.bidStepVolum[option.symbol] = 0

            self.bookAskImpv[option.symbol] = 0
            self.askEntruthVolumn[option.symbol] = 0
            self.askStepPerVolumn[option.symbol] = 0
            self.askImpvChange[option.symbol] = 0
            self.askStepVolum[option.symbol] = 0

            self.switchBidSymbol[option.symbol] = 'off'
            self.switchAskSymbol[option.symbol] = 'off'

            cellBidPrice = OmCell(str("%.4f" % option.bidPrice1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidImpv = OmCell('%.2f' % (option.bidImpv * 100), COLOR_BID, COLOR_BLACK, option, 10)
            cellBookBidImpv = OmCellEditText(self.bookBidImpv[option.symbol], 'impv', option)
            cellBidEntruthVolumn = OmCellEditText(self.bidEntruthVolumn[option.symbol], 'volumn', option)
            cellBidImpvChange = OmCellEditText(self.bidImpvChange[option.symbol], 'impv', option)
            cellBidStepPerVolumn = OmCellEditText(self.bidStepPerVolumn[option.symbol], 'volumn', option)
            cellBidStepVolum = OmCellEditText(self.bidStepVolum[option.symbol], 'volumn', option)

            cellBidSwitch = OmCell(self.switchBidSymbol[option.symbol], COLOR_BID, COLOR_BLACK, option, 10)
            cellAskSwitch = OmCell(self.switchAskSymbol[option.symbol], COLOR_ASK, COLOR_BLACK, option, 10)

            cellAskPrice = OmCell(str("%.4f" % option.askPrice1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskImpv = OmCell('%.2f' % (option.askImpv * 100), COLOR_ASK, COLOR_BLACK, option, 10)
            cellBookAskImpv = OmCellEditText(self.bookAskImpv[option.symbol], 'impv', option)
            cellAskEntruthVolumn = OmCellEditText(self.askEntruthVolumn[option.symbol], 'volumn', option)
            cellAskImpvChange = OmCellEditText(self.askImpvChange[option.symbol], 'impv', option)
            cellAskStepPerVolumn = OmCellEditText(self.askStepPerVolumn[option.symbol], 'volumn', option)
            cellAskStepVolum = OmCellEditText(self.askStepVolum[option.symbol], 'volumn', option)

            self.cellBidPrice[option.symbol] = cellBidPrice
            self.cellBidImpv[option.symbol] = cellBidImpv
            self.cellBookBidImpv[option.symbol] = cellBookBidImpv
            self.cellBidEntruthVolumn[option.symbol] = cellBidEntruthVolumn
            self.cellBidImpvChange[option.symbol] = cellBidImpvChange
            self.cellBidStepPerVolumn[option.symbol] = cellBidStepPerVolumn
            self.cellBidStepVolum[option.symbol] = cellBidStepVolum

            self.cellBidSwitch[option.symbol] = cellBidSwitch
            self.cellAskSwitch[option.symbol] = cellAskSwitch

            self.cellAskPrice[option.symbol] = cellAskImpv
            self.cellAskImpv[option.symbol] = cellAskImpv
            self.cellBookAskImpv[option.symbol] = cellBookAskImpv
            self.cellAskEntruthVolumn[option.symbol] = cellAskEntruthVolumn
            self.cellAskImpvChange[option.symbol] = cellAskImpvChange
            self.cellAskStepPerVolumn[option.symbol] = cellAskStepPerVolumn
            self.cellAskStepVolum[option.symbol] = cellAskStepVolum


            self.setCellWidget(putRow, 17, cellAskImpvChange)
            self.setCellWidget(putRow, 18, cellAskStepPerVolumn)
            self.setCellWidget(putRow, 19, cellAskStepVolum)
            self.setCellWidget(putRow, 20, cellAskEntruthVolumn)
            self.setCellWidget(putRow, 21, cellBookAskImpv)
            self.setItem(putRow, 22, cellAskImpv)
            self.setItem(putRow, 23, cellAskPrice)

            self.setItem(putRow, 24, cellAskSwitch)
            self.setItem(putRow, 25, cellBidSwitch)

            self.setCellWidget(putRow, 26, cellBidImpvChange)
            self.setCellWidget(putRow, 27, cellBidStepPerVolumn)
            self.setCellWidget(putRow, 28, cellBidStepVolum)
            self.setCellWidget(putRow, 29, cellBidEntruthVolumn)
            self.setCellWidget(putRow, 30, cellBookBidImpv)
            self.setItem(putRow, 31, cellBidImpv)
            self.setItem(putRow, 32, cellBidPrice)

            putRow += 1
        row = putRow + 1

    # ----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signalTick.connect(self.processTickEvent)
        self.signalTrade.connect(self.processTradeEvent)
        portfolio = self.omEngine.portfolio
        for option in self.chain.optionDict.values():
            self.eventEngine.register(EVENT_TICK + option.vtSymbol, self.signalTick.emit)
            self.eventEngine.register(EVENT_TRADE + option.vtSymbol, self.signalTrade.emit)


    # ----------------------------------------------------------------------
    def processTickEvent(self, event):
        """行情更新"""
        tick = event.dict_['data']
        symbol = tick.symbol

        if symbol in self.cellBidImpv:
            option = self.instrumentDict[symbol]
            self.cellBidImpv[symbol].setText('%.2f' % (option.bidImpv * 100))
            self.cellAskImpv[symbol].setText('%.2f' % (option.askImpv * 100))

        self.cellBidPrice[symbol].setText("%.4f" % tick.bidPrice1)
        self.cellAskPrice[symbol].setText("%.4f" % tick.askPrice1)

    # ----------------------------------------------------------------------
    def processTradeEvent(self, event):
        """成交更新"""
        trade = event.dict_['data']
        symbol = trade.symbol
        if symbol not in self.onSymbol:
            return
        continueSendOrder(trade)

    def continueSendOrder(self,trade):
        instrument = self.instrumentDict[symbol]
        if trade.direction == DIRECTION_LONG:
            # long成交量trade.volume
            try:
                self.longTradeVolumn[symbol] += trade.volume
            except:
                self.longTradeVolumn[symbol] = trade.volume
            # 如果总成交量大于设置的总量
            if self.longTradeVolumn[symbol] >= self.bidEntruthVolumn[option.symbol]:
                # 那么需要关闭开关，表示已经全部成交
                return

            elif trade.tradedVolume > 2:
                # 判断本次委托全部成交，才提交下一次委托，假设每次委托量为2
                return

            instrument = self.portfolio.instrumentDict.get(symbol, None)
            if not instrument:
                return
            # 如果空头仓位大于等于买入量，则只需平
            if instrument.shortPos >= volume:
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, volume)
            # 否则先平后开
            else:
                openVolume = volume - instrument.shortPos
                if instrument.shortPos:
                    self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, instrument.shortPos)
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_OPEN, price, openVolume)
        elif trade.direction == DIRECTION_SHORT:
            # short成交量trade.volume
            try:
                self.shortTradeVolumn[symbol] += trade.volume
            except:
                self.shortTradeVolumn[symbol] = trade.volume

            # 如果总成交量大于设置的总量
            if self.longTradeVolumn[symbol] >= self.bidEntruthVolumn[option.symbol]:
                # 那么需要关闭开关，表示已经全部成交
                return
            elif trade.tradedVolume > 2:
                # 判断本次委托全部成交，才提交下一次委托，假设每次委托量为2
                return

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

    def calcutateOrderBySymbol(self):
        """根据symbol来查询合约委托量"""
        return self.mainEngine.calcutateOrderBySymbol()

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

        self.mainEngine.sendOrder(req, contract.gatewayName)

########################################################################
class BookVolatility(QtWidgets.QWidget):
    """手动交易组件"""

    # ----------------------------------------------------------------------
    def __init__(self, omEngine, parent=None):
        """Constructor"""
        super(BookVolatility, self).__init__(parent)

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine = omEngine.eventEngine
        self.tradingWidget = {}
        self.chainMonitorAarry = []
        self.bookImpvConfig = {}
        self.loadJsonConfig()
        self.totalVolumn = 10
        self.stepVolumn = 2
        self.impvUp = 0.5
        self.impvDown = 0.5
        self.impvChange=0.1
        self.stepPerVolumn = 10
        self.initUi()
        self.setMinimumWidth(1450)
    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'波动率报单')

        tab = QtWidgets.QTabWidget()
        for chain in self.omEngine.portfolio.chainDict.values():
            chainMonitor = BookChainMonitor(chain, self.omEngine, self.mainEngine, self.eventEngine,self.bookImpvConfig)
            self.chainMonitorAarry.append(chainMonitor)
            tab.addTab(chainMonitor, chain.symbol)

        vbox = QtWidgets.QVBoxLayout()

        vbox = QtWidgets.QVBoxLayout()
        vhboxButtons = QtWidgets.QHBoxLayout()

        checkBox = QtWidgets.QCheckBox(u'波动率开关')
        checkBox.setChecked(False)
        checkBox.setFixedWidth(120)

        btnModify = QtWidgets.QPushButton(u'确认修改')
        btnModify.setFixedWidth(100)
        btnModify.clicked.connect(self.modifyConfig)


        btnRestore = QtWidgets.QPushButton(u'数据还原')
        btnRestore.setFixedWidth(100)
        btnRestore.clicked.connect(self.dataRestore)

        vhboxButtons.addWidget(checkBox)
        vhboxButtons.addWidget(btnModify)
        vhboxButtons.addWidget(btnRestore)
        vhboxButtons.addStretch()
        # checkBox.clicked.connect(self.changeHeaders)

        vhboxConfig= QtWidgets.QHBoxLayout()
        labelTotal = QtWidgets.QLabel(u'总量')

        editTotal = QtWidgets.QDoubleSpinBox()
        editTotal.setDecimals(0)
        editTotal.setMinimum(0)
        editTotal.setMaximum(100)
        editTotal.setValue(self.totalVolumn)

        labelStep = QtWidgets.QLabel(u'单次')

        editStep = QtWidgets.QDoubleSpinBox()
        editStep.setDecimals(0)
        editStep.setMinimum(0)
        editStep.setMaximum(30)
        editStep.setValue(self.stepVolumn)

        labelUp = QtWidgets.QLabel(u'上移')

        editUp = QtWidgets.QDoubleSpinBox()
        editUp.setDecimals(2)
        editUp.setMinimum(0)
        editUp.setMaximum(10)
        editUp.setSingleStep(0.01)
        editUp.setValue(self.impvUp)

        labelDown = QtWidgets.QLabel(u'下移')

        editDown = QtWidgets.QDoubleSpinBox()
        editDown.setDecimals(2)
        editDown.setMinimum(0)
        editDown.setMaximum(10)
        editDown.setSingleStep(0.01)
        editDown.setValue(self.impvDown)

        labelImpvChange = QtWidgets.QLabel(u'波动率增减')

        editImpvChange = QtWidgets.QDoubleSpinBox()
        editImpvChange.setDecimals(2)
        editImpvChange.setMinimum(0)
        editImpvChange.setMaximum(100)
        editImpvChange.setSingleStep(0.01)
        editImpvChange.setValue(self.impvChange)

        labelPerStep = QtWidgets.QLabel(u'per成交量')

        editPerStep = QtWidgets.QDoubleSpinBox()
        editPerStep.setDecimals(0)
        editPerStep.setMinimum(0)
        editPerStep.setMaximum(100)
        editPerStep.setValue(self.stepPerVolumn)


        vhboxConfig.addWidget(labelTotal)
        vhboxConfig.addWidget(editTotal)
        vhboxConfig.addWidget(labelStep)
        vhboxConfig.addWidget(editStep)
        vhboxConfig.addWidget(labelUp)
        vhboxConfig.addWidget(editUp)
        vhboxConfig.addWidget(labelDown)
        vhboxConfig.addWidget(editDown)

        vhboxConfig.addWidget(labelImpvChange)
        vhboxConfig.addWidget(editImpvChange)
        vhboxConfig.addWidget(labelPerStep)
        vhboxConfig.addWidget(editPerStep)
        vhboxConfig.addStretch()

        riskOfGreeksWidget=RiskOfGreeksWidget(self.omEngine, self.mainEngine, self.eventEngine)

        vbox.addLayout(vhboxButtons)
        vbox.addLayout(vhboxConfig)
        vbox.addWidget(riskOfGreeksWidget)

        vbox.addWidget(tab)
        tab.setMovable(True)
        self.setLayout(vbox)

    def dataRestore(self):
        print "还未实现"
        pass


    def modifyConfig(self):
        self.bookImpvConfig={}

        #买委托波动率
        self.bookBidImpv={}
        #卖委托波动率
        self.bookAskImpv={}
        #买委托量
        self.bidEntruthVolumn={}
        #卖委托量
        self.askEntruthVolumn={}
        #开关off ,on
        self.switchSymbolDict={}
        for chain in self.chainMonitorAarry:
            chain.modifyConfig()
            self.bookBidImpv.update(chain.bookBidImpv)
            self.bookAskImpv.update(chain.bookAskImpv)
            self.bidEntruthVolumn.update(chain.bidEntruthVolumn)
            self.askEntruthVolumn.update(chain.askEntruthVolumn)
            self.switchSymbolDict.update(chain.switchSymbolDict)

        file = open('bookBidImpv.json', 'wb')
        self.bookImpvConfig['bookBidImpv']=self.bookBidImpv
        self.bookImpvConfig['bookAskImpv'] = self.bookAskImpv
        self.bookImpvConfig['bidEntruthVolumn'] = self.bidEntruthVolumn
        self.bookImpvConfig['askEntruthVolumn'] = self.askEntruthVolumn
        self.bookImpvConfig['switchSymbolDict'] = self.switchSymbolDict
        json.dump(self.bookImpvConfig, file, ensure_ascii=False)
        file.close()

    def loadJsonConfig(self):
        try:
            f = file('bookBidImpv.json')
            s = json.load(f)
            self.bookImpvConfig['bookBidImpv'] = s['bookBidImpv']
            self.bookImpvConfig['bookAskImpv'] = s['bookAskImpv']
            self.bookImpvConfig['bidEntruthVolumn'] = s['bidEntruthVolumn']
            self.bookImpvConfig['askEntruthVolumn'] = s['askEntruthVolumn']
            self.bookImpvConfig['switchSymbolDict'] = s['switchSymbolDict']
            print s
        except Exception:
            print Exception.message


class RiskOfGreeksWidget(QtWidgets.QTableWidget):
    """期权链监控"""
    headers = [
        u'希腊值',
        u'当前值',
        u'开关',
        u'下限偏移',
        u'目标值',
        u'上限偏移',
        u'目标值',
        u'开关',
    ]

    def __init__(self, omEngine, mainEngine, eventEngine,parent=None):
        """Constructor"""
        super(RiskOfGreeksWidget, self).__init__(parent)

        self.omEngine = omEngine
        self.eventEngine = eventEngine
        self.mainEngine = mainEngine
        # 保存代码和持仓的字典
        self.portfolio = self.omEngine.portfolio

        self.cellPosDelta = {}
        self.cellPosGamma =  {}
        self.cellPosVega=  {}
        self.cellDeltaConfig =  {}
        self.cellGammaConfig =  {}
        self.cellVegaConfig =  {}

        self.initUi()

        self.eventEngine.register(EVENT_TIMER, self.timingChange)

    def timingChange(self,event):
        self.totalCellGamma.setText(str(self.portfolio.posGamma))
        self.totalCellDelta.setText(str(self.portfolio.posDelta))
        self.totalCellVega.setText(str(self.portfolio.posDelta))

    def initUi(self):
        """初始化界面"""


        # 初始化表格
        self.setFixedHeight(180)
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.setRowCount(3)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

        self.setItem(0, 0, OmCell(u"delta", None, COLOR_POS))
        self.setItem(1, 0, OmCell(u"gamma", None, COLOR_POS))
        self.setItem(2, 0, OmCell(u"vega", None, COLOR_POS))

        self.totalCellGamma = OmCell(str(self.portfolio.posGamma), None, COLOR_POS)
        self.totalCellDelta= OmCell(str(self.portfolio.posDelta), None, COLOR_POS)
        self.totalCellVega = OmCell(str(self.portfolio.posVega), None, COLOR_POS)

        self.setItem(0, 1, self.totalCellDelta)
        self.setItem(1, 1, self.totalCellGamma )
        self.setItem(2, 1, self.totalCellVega)

        self.setItem(0, 2, OmCell('off', None, COLOR_POS))
        self.setItem(1, 2, OmCell('off', None, COLOR_POS))
        self.setItem(2, 2,OmCell('off', None, COLOR_POS))

        self.setCellWidget(0, 3,OmCellEditText(0,'volumn'))
        self.setCellWidget(1, 3, OmCellEditText(0,'volumn'))
        self.setCellWidget(2, 3, OmCellEditText(0,'volumn'))

        self.setCellWidget(0, 4, OmCellEditText(0,'volumn'))
        self.setCellWidget(1, 4,OmCellEditText(0,'volumn'))
        self.setCellWidget(2, 4,OmCellEditText(0,'volumn'))

        self.setCellWidget(0, 5,OmCellEditText(0,'volumn'))
        self.setCellWidget(1, 5, OmCellEditText(0,'volumn'))
        self.setCellWidget(2, 5, OmCellEditText(0,'volumn'))

        self.setCellWidget(0, 6, OmCellEditText(0,'volumn'))
        self.setCellWidget(1, 6, OmCellEditText(0,'volumn'))
        self.setCellWidget(2, 6, OmCellEditText(0,'volumn'))

        self.setItem(0, 7, OmCell('off', None, COLOR_POS))
        self.setItem(1, 7, OmCell('off', None, COLOR_POS))
        self.setItem(2, 7, OmCell('off', None, COLOR_POS))