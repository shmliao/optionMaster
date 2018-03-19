# encoding: UTF-8

from vnpy.event import Event
from uiOmVolatilityManager import VolatilityChart

from vnpy.trader.vtConstant import DIRECTION_LONG, DIRECTION_SHORT, OFFSET_OPEN, OFFSET_CLOSE, PRICETYPE_LIMITPRICE,PRODUCT_OPTION
from vnpy.trader.vtObject import VtOrderReq
from vnpy.trader.vtEvent import EVENT_TICK, EVENT_TRADE, EVENT_ORDER, EVENT_TIMER
from vnpy.trader.uiBasicWidget import WorkingOrderMonitor, BasicMonitor, BasicCell, NameCell, DirectionCell, PnlCell, \
    AccountMonitor,NumCell
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
from uiOmBookVolatility import BookVolatility


# Add by lsm 20180125
class NewChainMonitor(QtWidgets.QTableWidget):
    """期权链监控"""
    headers = [
        u'合约名称0',
        u'买价1',
        u'买量2',
        u'买隐波3',
        u'卖价4',
        u'卖量5',
        u'卖隐波6',
        u'隐波7',
        u'delta8',
        u'gamma9',
        u'theta10',
        u'vega11',
        u'多仓12',
        u'空仓13',
        u'净仓14',
        u'买远期15',
        u'行权价16',
        u'卖远期17',
        u'净仓18',
        u'空仓19',
        u'多仓20',
        u'vega21',
        u'theta22',
        u'gamma23',
        u'delta24',
        u'隐波25',
        u'卖隐波26',
        u'卖量27',
        u'卖价28',
        u'买隐波29',
        u'买量30',
        u'买价31',
        u'合约名称32'
    ]
    signalTick = QtCore.pyqtSignal(type(Event()))
    signalPos = QtCore.pyqtSignal(type(Event()))
    signalTrade = QtCore.pyqtSignal(type(Event()))

    def __init__(self, chain, omEngine, mainEngine, eventEngine, headerSelectWidget, parent=None):
        """Constructor"""
        super(NewChainMonitor, self).__init__(parent)

        self.omEngine = omEngine
        self.eventEngine = eventEngine
        self.mainEngine = mainEngine
        # 保存代码和持仓的字典
        self.bidPriceDict = {}
        self.bidVolumeDict = {}
        self.bidImpvDict = {}
        self.askPriceDict = {}
        self.askVolumeDict = {}
        self.askImpvDict = {}
        self.midImpvDict = {}
        self.longPosDict = {}
        self.shortPosDict = {}
        self.deltaDict = {}
        self.gammaDict = {}
        self.thetaDict = {}
        self.vegaDict = {}

        self.posDict = {}
        self.futureDic = {}
        self.optionPriceFormat={}
        self.headerSelectWidget = headerSelectWidget
        # add by me
        self.chain = chain
        self.future = self.chain.future
        # 保存期权对象的字典
        portfolio = omEngine.portfolio

        self.instrumentDict = {}
        self.instrumentDict.update(portfolio.optionDict)
        self.instrumentDict.update(portfolio.underlyingDict)

        # 初始化
        self.initUi()
        self.registerEvent()
        self.verticalHeader().setDefaultSectionSize(20)
        self.setShowGrid(True)
        # ----------------------------------------------------------------------

    def initUi(self):
        """初始化界面"""
        portfolio = self.omEngine.portfolio

        # 初始化表格
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        rowCount = 2
        rowCount += len(portfolio.underlyingDict)
        # rowCount += len(portfolio.chainDict)
        for chain in portfolio.chainDict.values():
            if chain == self.chain:
                rowCount += len(chain.callDict)
        self.setRowCount(rowCount)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

        # for i in range(self.columnCount()):
        #     self.horizontalHeader().setResizeMode(i, QtWidgets.QHeaderView.Stretch)
        # self.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # self.horizontalHeader().setResizeMode(self.columnCount() - 1, QtWidgets.QHeaderView.ResizeToContents)

        # 初始化标的单元格
        row = 0

        for underlying in portfolio.underlyingDict.values():
            symbol = underlying.symbol
            priceFormat="%"+"."+str(underlying.remainDecimalPlaces)+"f"
            self.optionPriceFormat[symbol] = priceFormat
            cellSymbol = OmCell(symbol, COLOR_SYMBOL, COLOR_BLACK, underlying, 10)
            cellBidPrice = OmCell(str(underlying.bidPrice1), COLOR_BID, COLOR_BLACK, underlying, 10)
            cellBidVolume = OmCell(str(underlying.bidVolume1), COLOR_BID, COLOR_BLACK, underlying, 10)
            cellAskPrice = OmCell(str(underlying.askPrice1), COLOR_ASK, COLOR_BLACK, underlying, 10)
            cellAskVolume = OmCell(str(underlying.askVolume1), COLOR_ASK, COLOR_BLACK, underlying, 10)
            cellPos = OmCell(str(underlying.netPos), COLOR_POS, COLOR_BLACK, underlying, 10)

            self.posDict[symbol]= cellPos
            self.longPosDict[symbol]= OmCell(str(underlying.longPos), COLOR_BID, COLOR_BLACK, underlying, 10)
            self.shortPosDict[symbol]= OmCell(str(underlying.shortPos), COLOR_BID, COLOR_BLACK, underlying, 10)

            self.setItem(row, 0, cellSymbol)
            self.setItem(row, 1, cellBidPrice)
            self.setItem(row, 2, cellBidVolume)
            self.setItem(row, 4, cellAskPrice)
            self.setItem(row, 5, cellAskVolume)
            self.setItem(row, 12,  self.longPosDict[symbol])
            self.setItem(row, 13,  self.shortPosDict[symbol])
            self.setItem(row, 14, cellPos)

            self.bidPriceDict[symbol] = cellBidPrice
            self.bidVolumeDict[symbol] = cellBidVolume
            self.askPriceDict[symbol] = cellAskPrice
            self.askVolumeDict[symbol] = cellAskVolume
            self.posDict[symbol] = cellPos

            row += 1

        row += 1
        self.initFutureCell()
        row += 1
        callRow = row
        # 初始化期权单元格


        for option in self.chain.callDict.values():
            # cellSymbol = OmCell(option.symbol, COLOR_SYMBOL, COLOR_BLACK, option)
            priceFormat="%"+"."+str(option.remainDecimalPlaces)+"f"
            self.optionPriceFormat[option.symbol] = priceFormat
            cellSymbol = OmCell(self.mainEngine.getContract(option.vtSymbol).name, COLOR_SYMBOL, COLOR_BLACK, option,
                                10)
            cellBidPrice = OmCell(str(priceFormat % option.bidPrice1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidVolume = OmCell(str(option.bidVolume1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidImpv = OmCell('%.2f' % (option.bidImpv * 100), COLOR_BID, COLOR_BLACK, option, 10)
            cellAskPrice = OmCell(str(priceFormat % option.askPrice1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskVolume = OmCell(str(option.askVolume1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskImpv = OmCell('%.2f' % (option.askImpv * 100), COLOR_ASK, COLOR_BLACK, option, 10)
            cellMidImpv = OmCell('%.2f' % (option.midImpv * 100), COLOR_ASK, COLOR_BLACK, option, 10)

            cellPos = OmCell(str(option.netPos), COLOR_POS, COLOR_BLACK, option, 10)
            cellLongPos = OmCell(str(option.longPos), COLOR_POS, COLOR_BLACK, option, 10)
            cellshortPos = OmCell(str(option.shortPos), COLOR_POS, COLOR_BLACK, option, 10)

            # cellDelta = OmCell(str(round(option.dgammaDS, 4)), COLOR_POS, COLOR_BLACK, option, 10)
            # cellGamma = OmCell(str(round(option.dvegaDS, 4)), COLOR_POS, COLOR_BLACK, option, 10)
            # cellTheta = OmCell(str(round(option.vomma, 4)), COLOR_POS, COLOR_BLACK, option, 10)
            # cellVega = OmCell(str(round(option.vonna, 4)), COLOR_POS, COLOR_BLACK, option, 10)
            cellDelta = OmCell(str(round(option.delta, 4)), COLOR_POS, COLOR_BLACK, option, 10)
            cellGamma = OmCell(str(round(option.gamma, 4)), COLOR_POS, COLOR_BLACK, option, 10)
            cellTheta = OmCell(str(round(option.theta, 4)), COLOR_POS, COLOR_BLACK, option, 10)
            cellVega = OmCell(str(round(option.vega, 4)), COLOR_POS, COLOR_BLACK, option, 10)

            cellfuture = OmCell(str(option.futurePrice), COLOR_STRIKE)
            cellStrike = OmCell(str(option.k), COLOR_STRIKE)
            self.setItem(callRow, 0, cellSymbol)
            self.setItem(callRow, 1, cellBidPrice)
            self.setItem(callRow, 2, cellBidVolume)
            self.setItem(callRow, 3, cellBidImpv)
            self.setItem(callRow, 4, cellAskPrice)
            self.setItem(callRow, 5, cellAskVolume)
            self.setItem(callRow, 6, cellAskImpv)
            self.setItem(callRow, 7, cellMidImpv)

            self.setItem(callRow, 8, cellDelta)
            self.setItem(callRow, 9, cellGamma)
            self.setItem(callRow, 10, cellTheta)
            self.setItem(callRow, 11, cellVega)

            self.setItem(callRow, 12, cellLongPos)
            self.setItem(callRow, 13, cellshortPos)
            self.setItem(callRow, 14, cellPos)
            self.setItem(callRow, 15, cellfuture)
            self.setItem(callRow, 16, cellStrike)

            self.bidPriceDict[option.symbol] = cellBidPrice
            self.bidVolumeDict[option.symbol] = cellBidVolume
            self.bidImpvDict[option.symbol] = cellBidImpv
            self.askPriceDict[option.symbol] = cellAskPrice
            self.askVolumeDict[option.symbol] = cellAskVolume
            self.askImpvDict[option.symbol] = cellAskImpv
            self.posDict[option.symbol] = cellPos

            self.midImpvDict[option.symbol] = cellMidImpv
            self.longPosDict[option.symbol] = cellLongPos
            self.shortPosDict[option.symbol] = cellshortPos

            self.deltaDict[option.symbol] = cellDelta
            self.gammaDict[option.symbol] = cellGamma
            self.thetaDict[option.symbol] = cellTheta
            self.vegaDict[option.symbol] = cellVega
            self.futureDic[option.symbol] = cellfuture

            callRow += 1

            # put
        putRow = row

        for option in self.chain.putDict.values():
            # cellSymbol = OmCell(option.symbol, COLOR_SYMBOL, COLOR_BLACK, option)
            priceFormat = "%" +"."+ str(option.remainDecimalPlaces) + "f"
            self.optionPriceFormat[option.symbol] = priceFormat
            cellSymbol = OmCell(self.mainEngine.getContract(option.vtSymbol).name, COLOR_SYMBOL, COLOR_BLACK, option,
                                10)
            cellBidPrice = OmCell(str(priceFormat % option.bidPrice1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidVolume = OmCell(str(option.bidVolume1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidImpv = OmCell('%.2f' % (option.bidImpv * 100), COLOR_BID, COLOR_BLACK, option, 10)
            cellAskPrice = OmCell(str(priceFormat % option.askPrice1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskVolume = OmCell(str(option.askVolume1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskImpv = OmCell('%.2f' % (option.askImpv * 100), COLOR_ASK, COLOR_BLACK, option, 10)
            cellPos = OmCell(str(option.netPos), COLOR_POS, COLOR_BLACK, option, 10)
            cellMidImpv = OmCell('%.2f' % (option.midImpv * 100), COLOR_ASK, COLOR_BLACK, option, 10)

            cellLongPos = OmCell(str(option.longPos), COLOR_POS, COLOR_BLACK, option, 10)
            cellshortPos = OmCell(str(option.shortPos), COLOR_POS, COLOR_BLACK, option, 10)

            cellDelta = OmCell(str(round(option.delta,4)), COLOR_POS, COLOR_BLACK, option, 10)
            cellGamma = OmCell(str(round(option.gamma,4)), COLOR_POS, COLOR_BLACK, option, 10)
            cellTheta = OmCell(str(round(option.theta,4)), COLOR_POS, COLOR_BLACK, option, 10)
            cellVega = OmCell(str(round(option.vega,4)), COLOR_POS, COLOR_BLACK, option, 10)
            
            cellfuture = OmCell(str(option.futurePrice), COLOR_STRIKE)
            # u'净仓16',
            # u'空仓17',
            # u'多仓18',
            # u'vega19',
            # u'theta20',
            # u'gamma21',
            # u'delta22',
            # u'隐波23',
            # u'卖隐波24',
            # u'卖量25',
            # u'卖价26',
            # u'买隐波27',
            # u'买量28',
            # u'买价29',
            # u'合约名称30'


            self.setItem(putRow, 32, cellSymbol)
            self.setItem(putRow, 31, cellBidPrice)
            self.setItem(putRow, 30, cellBidVolume)
            self.setItem(putRow, 29, cellBidImpv)
            self.setItem(putRow, 28, cellAskPrice)
            self.setItem(putRow, 27, cellAskVolume)
            self.setItem(putRow, 26, cellAskImpv)
            self.setItem(putRow, 25, cellMidImpv)

            self.setItem(putRow, 24, cellDelta)
            self.setItem(putRow, 23, cellGamma)
            self.setItem(putRow, 22, cellTheta)
            self.setItem(putRow, 21, cellVega)

            self.setItem(putRow, 20, cellLongPos)
            self.setItem(putRow, 19, cellshortPos)
            self.setItem(putRow, 18, cellPos)
            self.setItem(putRow, 17, cellfuture)

            self.bidPriceDict[option.symbol] = cellBidPrice
            self.bidVolumeDict[option.symbol] = cellBidVolume
            self.bidImpvDict[option.symbol] = cellBidImpv
            self.askPriceDict[option.symbol] = cellAskPrice
            self.askVolumeDict[option.symbol] = cellAskVolume
            self.askImpvDict[option.symbol] = cellAskImpv
            self.posDict[option.symbol] = cellPos
            self.midImpvDict[option.symbol] = cellMidImpv
            self.longPosDict[option.symbol] = cellLongPos
            self.shortPosDict[option.symbol] = cellshortPos

            self.deltaDict[option.symbol] = cellDelta
            self.gammaDict[option.symbol] = cellGamma
            self.thetaDict[option.symbol] = cellTheta
            self.vegaDict[option.symbol] = cellVega
            self.futureDic[option.symbol] = cellfuture
            putRow += 1

        row = putRow + 1
        self.selectShowColumn()

    def initFutureCell(self):
        symbol = self.future.symbol
        priceFormat = "%" + "." + str(self.future.remainDecimalPlaces) + "f"
        self.optionPriceFormat[symbol]=priceFormat
        cellSymbol = OmCell(symbol, COLOR_SYMBOL, COLOR_BLACK, self.future, 10)
        cellBidPrice = OmCell(str(self.future.bidPrice1), COLOR_BID, COLOR_BLACK, self.future, 10)
        cellBidVolume = OmCell(str(self.future.bidVolume1), COLOR_BID, COLOR_BLACK, self.future, 10)
        cellAskPrice = OmCell(str(self.future.askPrice1), COLOR_ASK, COLOR_BLACK, self.future, 10)
        cellAskVolume = OmCell(str(self.future.askVolume1), COLOR_ASK, COLOR_BLACK, self.future, 10)
        cellPos = OmCell(str(self.future.netPos), COLOR_POS, COLOR_BLACK, self.future, 10)


        # etf50=self.omEngine.portfolio.underlyingDict[symbol]
        # self.cellUpsAndDowns=OmCell('%.2f' % ((etf50.lastPrice-etf50.preClosePrice)/etf50.preClosePrice * 100)+"%", COLOR_POS, COLOR_BLACK, etf50, 10)

        self.setItem(1, 0, cellSymbol)
        self.setItem(1, 1, cellBidPrice)
        self.setItem(1, 2, cellBidVolume)
        #self.setItem(1, 3,  self.cellUpsAndDowns)
        self.setItem(1, 4, cellAskPrice)
        self.setItem(1, 5, cellAskVolume)
        self.setItem(1, 14, cellPos)

        self.bidPriceDict[symbol] = cellBidPrice
        self.bidVolumeDict[symbol] = cellBidVolume
        self.askPriceDict[symbol] = cellAskPrice
        self.askVolumeDict[symbol] = cellAskVolume
        self.posDict[symbol] = cellPos

    def selectShowColumn(self):
        headersDic = self.headerSelectWidget.headersDic.values()
        lenDic = len(self.headers)
        print lenDic
        for index, item in enumerate(headersDic):
            if item['show'] == False:
                print index
                self.hideColumn(index)
                self.hideColumn(lenDic - 1 - index)

    # ----------------------------------------------------------------------
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

        self.eventEngine.register(EVENT_TICK + self.chain.future.vtSymbol, self.signalTick.emit)
        self.eventEngine.register(EVENT_TRADE + self.chain.future.vtSymbol, self.signalTrade.emit)

    # ----------------------------------------------------------------------
    def processTickEvent(self, event):
        """行情更新"""
        tick = event.dict_['data']
        symbol = tick.symbol

        if symbol in self.bidImpvDict:
            option = self.instrumentDict[symbol]
            self.bidImpvDict[symbol].setText('%.2f' % (option.bidImpv * 100))
            self.askImpvDict[symbol].setText('%.2f' % (option.askImpv * 100))
            self.midImpvDict[symbol].setText('%.2f' % (option.midImpv * 100))

            self.deltaDict[symbol].setText(str(round(option.delta, 4)))
            self.gammaDict[symbol].setText(str(round(option.gamma, 4)))
            self.thetaDict[symbol].setText(str(round(option.theta, 4)))
            self.vegaDict[symbol].setText(str(round(option.vega, 4)))
            self.futureDic[symbol].setText(str(round(option.futurePrice, 4)))

        # if symbol==self.future.symbol:
        #     self.cellUpsAndDowns.setText('%.2f' % ((tick.lastPrice - tick.preClosePrice) / tick.preClosePrice * 100) + "%")

        self.bidPriceDict[symbol].setText(self.optionPriceFormat[symbol]  % tick.bidPrice1)
        self.bidVolumeDict[symbol].setText(str(tick.bidVolume1))
        self.askPriceDict[symbol].setText(self.optionPriceFormat[symbol]  % tick.askPrice1)
        self.askVolumeDict[symbol].setText(str(tick.askVolume1))

    # ----------------------------------------------------------------------
    def processTradeEvent(self, event):
        """成交更新"""
        trade = event.dict_['data']

        symbol = trade.symbol
        instrument = self.instrumentDict[symbol]
        self.posDict[symbol].setText(str(instrument.netPos))
        self.longPosDict[symbol].setText(str(instrument.longPos))
        self.shortPosDict[symbol].setText(str(instrument.shortPos))


# change by lsm 20180104
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

    def __init__(self, chain, omEngine, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(ChainMonitor, self).__init__(parent)

        self.omEngine = omEngine
        self.eventEngine = eventEngine
        self.mainEngine = mainEngine
        # 保存代码和持仓的字典
        self.bidPriceDict = {}
        self.bidVolumeDict = {}
        self.bidImpvDict = {}
        self.askPriceDict = {}
        self.askVolumeDict = {}
        self.askImpvDict = {}
        self.posDict = {}

        # add by me
        self.chain = chain
        # 保存期权对象的字典
        portfolio = omEngine.portfolio

        self.instrumentDict = {}
        self.instrumentDict.update(portfolio.optionDict)
        self.instrumentDict.update(portfolio.underlyingDict)

        # 初始化
        self.initUi()
        self.registerEvent()
        self.verticalHeader().setDefaultSectionSize(20)
        self.setShowGrid(True)
        # ----------------------------------------------------------------------

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
            if chain == self.chain:
                rowCount += len(chain.callDict)
        self.setRowCount(rowCount)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

        for i in range(self.columnCount()):
            self.horizontalHeader().setResizeMode(i, QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.horizontalHeader().setResizeMode(self.columnCount() - 1, QtWidgets.QHeaderView.ResizeToContents)

        # 初始化标的单元格
        row = 0

        for underlying in portfolio.underlyingDict.values():
            symbol = underlying.symbol

            cellSymbol = OmCell(symbol, COLOR_SYMBOL, COLOR_BLACK, underlying, 10)
            cellBidPrice = OmCell(str(underlying.bidPrice1), COLOR_BID, COLOR_BLACK, underlying, 10)
            cellBidVolume = OmCell(str(underlying.bidVolume1), COLOR_BID, COLOR_BLACK, underlying, 10)
            cellAskPrice = OmCell(str(underlying.askPrice1), COLOR_ASK, COLOR_BLACK, underlying, 10)
            cellAskVolume = OmCell(str(underlying.askVolume1), COLOR_ASK, COLOR_BLACK, underlying, 10)
            cellPos = OmCell(str(underlying.netPos), COLOR_POS, COLOR_BLACK, underlying, 10)

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
            cellSymbol = OmCell(self.mainEngine.getContract(option.vtSymbol).name, COLOR_SYMBOL, COLOR_BLACK, option,
                                10)
            cellBidPrice = OmCell(str(option.bidPrice1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidVolume = OmCell(str(option.bidVolume1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidImpv = OmCell('%.1f' % (option.bidImpv * 100), COLOR_BID, COLOR_BLACK, option, 10)
            cellAskPrice = OmCell(str(option.askPrice1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskVolume = OmCell(str(option.askVolume1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskImpv = OmCell('%.1f' % (option.askImpv * 100), COLOR_ASK, COLOR_BLACK, option, 10)
            cellPos = OmCell(str(option.netPos), COLOR_POS, COLOR_BLACK, option, 10)
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
            cellSymbol = OmCell(self.mainEngine.getContract(option.vtSymbol).name, COLOR_SYMBOL, COLOR_BLACK, option,
                                10)
            cellBidPrice = OmCell(str(option.bidPrice1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidVolume = OmCell(str(option.bidVolume1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidImpv = OmCell('%.1f' % (option.bidImpv * 100), COLOR_BID, COLOR_BLACK, option, 10)
            cellAskPrice = OmCell(str(option.askPrice1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskVolume = OmCell(str(option.askVolume1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskImpv = OmCell('%.1f' % (option.askImpv * 100), COLOR_ASK, COLOR_BLACK, option, 10)
            cellPos = OmCell(str(option.netPos), COLOR_POS, COLOR_BLACK, option, 10)
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

    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------
    def processTickEvent(self, event):
        """行情更新"""
        tick = event.dict_['data']
        symbol = tick.symbol

        if symbol in self.bidImpvDict:
            option = self.instrumentDict[symbol]
            self.bidImpvDict[symbol].setText('%.1f' % (option.bidImpv * 100))
            self.askImpvDict[symbol].setText('%.1f' % (option.askImpv * 100))

        self.bidPriceDict[symbol].setText(str(tick.bidPrice1))
        self.bidVolumeDict[symbol].setText(str(tick.bidVolume1))
        self.askPriceDict[symbol].setText(str(tick.askPrice1))
        self.askVolumeDict[symbol].setText(str(tick.askVolume1))

    # ----------------------------------------------------------------------
    def processTradeEvent(self, event):
        """成交更新"""
        trade = event.dict_['data']

        symbol = trade.symbol
        instrument = self.instrumentDict[symbol]
        self.posDict[symbol].setText(str(instrument.netPos))


########################################################################
class NewTradingWidget(QtWidgets.QWidget):
    """交易组件"""

    # ----------------------------------------------------------------------
    def __init__(self, omEngine, parent=None):
        """Constructor"""
        super(NewTradingWidget, self).__init__(parent)

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.portfolio = omEngine.portfolio

        self.initUi()

    # ----------------------------------------------------------------------
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

    # ----------------------------------------------------------------------根据symbol来查询合约委托量
    def calcutateOrderBySymbol(self):
        """根据symbol来查询合约委托量"""
        return self.mainEngine.calcutateOrderBySymbol()

    # ----------------------------------------------------------------------
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

        # 获得当前时间各个合约的委托量和委托价格，用来判断平仓量！！
        longVolumeDic, shortVolumeDic, longPriceDic, shortPriceDic = self.calcutateOrderBySymbol()
        # 做多
        if direction == DIRECTION_LONG:
            # 如果空头仓位减去空头委托量大于等于买入量，则只需平
            if symbol in shortVolumeDic.keys():
                orderVolumn = shortVolumeDic[symbol]
            else:
                orderVolumn = 0
            if instrument.shortPos - orderVolumn >= volume:
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, volume)
            # 否则先平后开
            else:
                openVolume = volume - (instrument.shortPos - orderVolumn)
                if instrument.shortPos - orderVolumn:
                    self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, instrument.shortPos - orderVolumn)
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_OPEN, price, openVolume)
        # 做空
        else:

            if symbol in longVolumeDic.keys():
                orderVolumn = longVolumeDic[symbol]
            else:
                orderVolumn = 0
            if self.shortOpenRadio.isChecked():
                self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_OPEN, price, volume-orderVolumn)
            else:
                if instrument.longPos-orderVolumn >= volume:
                    self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, volume-orderVolumn)
                else:
                    openVolume = volume - (instrument.longPos-orderVolumn)
                    if instrument.longPos-orderVolumn:
                        self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, instrument.longPos-orderVolumn)
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


# change by lsm 20180119
class TradingWidget(QtWidgets.QFrame):
    """简单交易组件"""
    signal = QtCore.Signal(type(Event()))
    directionList = [DIRECTION_LONG,
                     DIRECTION_SHORT]

    offsetList = [OFFSET_OPEN,
                  OFFSET_CLOSE,
                  OFFSET_CLOSEYESTERDAY,
                  OFFSET_CLOSETODAY]

    priceTypeList = [PRICETYPE_LIMITPRICE,
                     PRICETYPE_MARKETPRICE,
                     PRICETYPE_FAK,
                     PRICETYPE_FOK]

    exchangeList = [EXCHANGE_NONE,
                    EXCHANGE_CFFEX,
                    EXCHANGE_SHFE,
                    EXCHANGE_DCE,
                    EXCHANGE_CZCE,
                    EXCHANGE_SSE,
                    EXCHANGE_SZSE,
                    EXCHANGE_SGE,
                    EXCHANGE_HKEX,
                    EXCHANGE_HKFE,
                    EXCHANGE_SMART,
                    EXCHANGE_ICE,
                    EXCHANGE_CME,
                    EXCHANGE_NYMEX,
                    EXCHANGE_LME,
                    EXCHANGE_GLOBEX,
                    EXCHANGE_IDEALPRO]

    currencyList = [CURRENCY_NONE,
                    CURRENCY_CNY,
                    CURRENCY_HKD,
                    CURRENCY_USD]

    productClassList = [PRODUCT_NONE,
                        PRODUCT_EQUITY,
                        PRODUCT_FUTURES,
                        PRODUCT_OPTION,
                        PRODUCT_FOREX]

    gatewayList = ['']

    # ----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(TradingWidget, self).__init__(parent)
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine

        self.symbol = ''

        # 添加交易接口
        l = mainEngine.getAllGatewayDetails()
        gatewayNameList = [d['gatewayName'] for d in l]
        self.gatewayList.extend(gatewayNameList)

        self.initUi()
        self.connectSignal()

    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(vtText.TRADING)
        self.setMaximumWidth(400)
        self.setFrameShape(self.Box)  # 设置边框
        self.setLineWidth(1)

        # 左边部分
        labelSymbol = QtWidgets.QLabel(vtText.CONTRACT_SYMBOL)
        labelName = QtWidgets.QLabel(vtText.CONTRACT_NAME)
        labelDirection = QtWidgets.QLabel(vtText.DIRECTION)
        labelOffset = QtWidgets.QLabel(vtText.OFFSET)
        labelPrice = QtWidgets.QLabel(vtText.PRICE)
        self.checkFixed = QtWidgets.QCheckBox(u'')  # 价格固定选择框
        labelVolume = QtWidgets.QLabel(vtText.VOLUME)
        labelPriceType = QtWidgets.QLabel(vtText.PRICE_TYPE)
        labelExchange = QtWidgets.QLabel(vtText.EXCHANGE)
        labelCurrency = QtWidgets.QLabel(vtText.CURRENCY)
        labelProductClass = QtWidgets.QLabel(vtText.PRODUCT_CLASS)
        labelGateway = QtWidgets.QLabel(vtText.GATEWAY)

        self.lineSymbol = QtWidgets.QLineEdit()
        self.lineName = QtWidgets.QLineEdit()

        self.comboDirection = QtWidgets.QComboBox()
        self.comboDirection.addItems(self.directionList)

        self.comboOffset = QtWidgets.QComboBox()
        self.comboOffset.addItems(self.offsetList)

        self.spinPrice = QtWidgets.QDoubleSpinBox()
        self.spinPrice.setDecimals(4)
        self.spinPrice.setMinimum(0)
        self.spinPrice.setMaximum(100000)

        self.spinVolume = QtWidgets.QSpinBox()
        self.spinVolume.setMinimum(0)
        self.spinVolume.setMaximum(1000000)

        self.comboPriceType = QtWidgets.QComboBox()
        self.comboPriceType.addItems(self.priceTypeList)

        self.comboExchange = QtWidgets.QComboBox()
        self.comboExchange.addItems(self.exchangeList)

        self.comboCurrency = QtWidgets.QComboBox()
        self.comboCurrency.addItems(self.currencyList)

        self.comboProductClass = QtWidgets.QComboBox()
        self.comboProductClass.addItems(self.productClassList)

        self.comboGateway = QtWidgets.QComboBox()
        self.comboGateway.addItems(self.gatewayList)

        gridleft = QtWidgets.QGridLayout()
        gridleft.addWidget(labelSymbol, 0, 0)
        gridleft.addWidget(labelName, 1, 0)
        gridleft.addWidget(labelDirection, 2, 0)
        gridleft.addWidget(labelOffset, 3, 0)
        gridleft.addWidget(labelPrice, 4, 0)
        gridleft.addWidget(labelVolume, 5, 0)
        gridleft.addWidget(labelPriceType, 6, 0)
        gridleft.addWidget(labelExchange, 7, 0)
        gridleft.addWidget(labelCurrency, 8, 0)
        gridleft.addWidget(labelProductClass, 9, 0)
        gridleft.addWidget(labelGateway, 10, 0)

        gridleft.addWidget(self.lineSymbol, 0, 1, 1, -1)
        gridleft.addWidget(self.lineName, 1, 1, 1, -1)
        gridleft.addWidget(self.comboDirection, 2, 1, 1, -1)
        gridleft.addWidget(self.comboOffset, 3, 1, 1, -1)
        gridleft.addWidget(self.checkFixed, 4, 1)
        gridleft.addWidget(self.spinPrice, 4, 2)
        gridleft.addWidget(self.spinVolume, 5, 1, 1, -1)
        gridleft.addWidget(self.comboPriceType, 6, 1, 1, -1)
        gridleft.addWidget(self.comboExchange, 7, 1, 1, -1)
        gridleft.addWidget(self.comboCurrency, 8, 1, 1, -1)
        gridleft.addWidget(self.comboProductClass, 9, 1, 1, -1)
        gridleft.addWidget(self.comboGateway, 10, 1, 1, -1)

        # 右边部分
        labelBid1 = QtWidgets.QLabel(vtText.BID_1)
        labelBid2 = QtWidgets.QLabel(vtText.BID_2)
        labelBid3 = QtWidgets.QLabel(vtText.BID_3)
        labelBid4 = QtWidgets.QLabel(vtText.BID_4)
        labelBid5 = QtWidgets.QLabel(vtText.BID_5)

        labelAsk1 = QtWidgets.QLabel(vtText.ASK_1)
        labelAsk2 = QtWidgets.QLabel(vtText.ASK_2)
        labelAsk3 = QtWidgets.QLabel(vtText.ASK_3)
        labelAsk4 = QtWidgets.QLabel(vtText.ASK_4)
        labelAsk5 = QtWidgets.QLabel(vtText.ASK_5)

        self.labelBidPrice1 = QtWidgets.QLabel()
        self.labelBidPrice2 = QtWidgets.QLabel()
        self.labelBidPrice3 = QtWidgets.QLabel()
        self.labelBidPrice4 = QtWidgets.QLabel()
        self.labelBidPrice5 = QtWidgets.QLabel()
        self.labelBidVolume1 = QtWidgets.QLabel()
        self.labelBidVolume2 = QtWidgets.QLabel()
        self.labelBidVolume3 = QtWidgets.QLabel()
        self.labelBidVolume4 = QtWidgets.QLabel()
        self.labelBidVolume5 = QtWidgets.QLabel()

        self.labelAskPrice1 = QtWidgets.QLabel()
        self.labelAskPrice2 = QtWidgets.QLabel()
        self.labelAskPrice3 = QtWidgets.QLabel()
        self.labelAskPrice4 = QtWidgets.QLabel()
        self.labelAskPrice5 = QtWidgets.QLabel()
        self.labelAskVolume1 = QtWidgets.QLabel()
        self.labelAskVolume2 = QtWidgets.QLabel()
        self.labelAskVolume3 = QtWidgets.QLabel()
        self.labelAskVolume4 = QtWidgets.QLabel()
        self.labelAskVolume5 = QtWidgets.QLabel()

        labelLast = QtWidgets.QLabel(vtText.LAST)
        self.labelLastPrice = QtWidgets.QLabel()
        self.labelReturn = QtWidgets.QLabel()

        self.labelLastPrice.setMinimumWidth(60)
        self.labelReturn.setMinimumWidth(60)

        gridRight = QtWidgets.QGridLayout()
        gridRight.addWidget(labelAsk5, 0, 0)
        gridRight.addWidget(labelAsk4, 1, 0)
        gridRight.addWidget(labelAsk3, 2, 0)
        gridRight.addWidget(labelAsk2, 3, 0)
        gridRight.addWidget(labelAsk1, 4, 0)
        gridRight.addWidget(labelLast, 5, 0)
        gridRight.addWidget(labelBid1, 6, 0)
        gridRight.addWidget(labelBid2, 7, 0)
        gridRight.addWidget(labelBid3, 8, 0)
        gridRight.addWidget(labelBid4, 9, 0)
        gridRight.addWidget(labelBid5, 10, 0)

        gridRight.addWidget(self.labelAskPrice5, 0, 1)
        gridRight.addWidget(self.labelAskPrice4, 1, 1)
        gridRight.addWidget(self.labelAskPrice3, 2, 1)
        gridRight.addWidget(self.labelAskPrice2, 3, 1)
        gridRight.addWidget(self.labelAskPrice1, 4, 1)
        gridRight.addWidget(self.labelLastPrice, 5, 1)
        gridRight.addWidget(self.labelBidPrice1, 6, 1)
        gridRight.addWidget(self.labelBidPrice2, 7, 1)
        gridRight.addWidget(self.labelBidPrice3, 8, 1)
        gridRight.addWidget(self.labelBidPrice4, 9, 1)
        gridRight.addWidget(self.labelBidPrice5, 10, 1)

        gridRight.addWidget(self.labelAskVolume5, 0, 2)
        gridRight.addWidget(self.labelAskVolume4, 1, 2)
        gridRight.addWidget(self.labelAskVolume3, 2, 2)
        gridRight.addWidget(self.labelAskVolume2, 3, 2)
        gridRight.addWidget(self.labelAskVolume1, 4, 2)
        gridRight.addWidget(self.labelReturn, 5, 2)
        gridRight.addWidget(self.labelBidVolume1, 6, 2)
        gridRight.addWidget(self.labelBidVolume2, 7, 2)
        gridRight.addWidget(self.labelBidVolume3, 8, 2)
        gridRight.addWidget(self.labelBidVolume4, 9, 2)
        gridRight.addWidget(self.labelBidVolume5, 10, 2)

        # 发单按钮
        buttonSendOrder = QtWidgets.QPushButton(vtText.SEND_ORDER)
        buttonCancelAll = QtWidgets.QPushButton(vtText.CANCEL_ALL)

        size = buttonSendOrder.sizeHint()
        buttonSendOrder.setMinimumHeight(size.height())  # 把按钮高度设为默认两倍
        buttonCancelAll.setMinimumHeight(size.height())

        # 整合布局
        hbox = QtWidgets.QHBoxLayout()
        hbox.addLayout(gridleft)
        hbox.addLayout(gridRight)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(buttonSendOrder)
        vbox.addWidget(buttonCancelAll)
        vbox.addStretch()

        self.setLayout(vbox)

        # 关联更新
        buttonSendOrder.clicked.connect(self.sendOrder)
        buttonCancelAll.clicked.connect(self.cancelAll)
        self.lineSymbol.returnPressed.connect(self.updateSymbol)

    def slotWarningSendOrder(self):
        button = QtWidgets.QMessageBox.warning(self, "Warning",
                                               u"确认交易",
                                               u"确认",
                                               u"取消")
        if button == 0:
            self.sendOrder()
        elif button == 1:
            pass
        else:
            return

    def slotWarningCancelAllOrder(self):
        button = QtWidgets.QMessageBox.warning(self, "Warning",
                                               u"确认撤销全部委托？",
                                               u"确认",
                                               u"取消")
        if button == 0:
            self.cancelAll()
        elif button == 1:
            pass
        else:
            return

    # ----------------------------------------------------------------------
    def updateSymbol(self):
        """合约变化"""
        # 读取组件数据
        symbol = str(self.lineSymbol.text())
        exchange = unicode(self.comboExchange.currentText())
        currency = unicode(self.comboCurrency.currentText())
        productClass = unicode(self.comboProductClass.currentText())
        gatewayName = unicode(self.comboGateway.currentText())

        # 查询合约
        if exchange:
            vtSymbol = '.'.join([symbol, exchange])
            contract = self.mainEngine.getContract(vtSymbol)
        else:
            vtSymbol = symbol
            contract = self.mainEngine.getContract(symbol)

        if contract:
            vtSymbol = contract.vtSymbol
            gatewayName = contract.gatewayName
            self.lineName.setText(contract.name)
            exchange = contract.exchange  # 保证有交易所代码

        # 清空价格数量
        self.spinPrice.setValue(0)
        self.spinVolume.setValue(0)

        # 清空行情显示
        self.labelBidPrice1.setText('')
        self.labelBidPrice2.setText('')
        self.labelBidPrice3.setText('')
        self.labelBidPrice4.setText('')
        self.labelBidPrice5.setText('')
        self.labelBidVolume1.setText('')
        self.labelBidVolume2.setText('')
        self.labelBidVolume3.setText('')
        self.labelBidVolume4.setText('')
        self.labelBidVolume5.setText('')
        self.labelAskPrice1.setText('')
        self.labelAskPrice2.setText('')
        self.labelAskPrice3.setText('')
        self.labelAskPrice4.setText('')
        self.labelAskPrice5.setText('')
        self.labelAskVolume1.setText('')
        self.labelAskVolume2.setText('')
        self.labelAskVolume3.setText('')
        self.labelAskVolume4.setText('')
        self.labelAskVolume5.setText('')
        self.labelLastPrice.setText('')
        self.labelReturn.setText('')

        # 重新注册事件监听
        self.eventEngine.unregister(EVENT_TICK + self.symbol, self.signal.emit)
        self.eventEngine.register(EVENT_TICK + vtSymbol, self.signal.emit)

        # 订阅合约
        req = VtSubscribeReq()
        req.symbol = symbol
        req.exchange = exchange
        req.currency = currency
        req.productClass = productClass

        # 默认跟随价
        self.checkFixed.setChecked(False)

        self.mainEngine.subscribe(req, gatewayName)

        # 更新组件当前交易的合约
        self.symbol = vtSymbol

    # ----------------------------------------------------------------------
    def updateTick(self, event):
        """更新行情"""
        tick = event.dict_['data']

        if tick.vtSymbol == self.symbol:
            if not self.checkFixed.isChecked():
                self.spinPrice.setValue(tick.lastPrice)
            self.labelBidPrice1.setText(str(tick.bidPrice1))
            self.labelAskPrice1.setText(str(tick.askPrice1))
            self.labelBidVolume1.setText(str(tick.bidVolume1))
            self.labelAskVolume1.setText(str(tick.askVolume1))

            if tick.bidPrice2:
                self.labelBidPrice2.setText(str(tick.bidPrice2))
                self.labelBidPrice3.setText(str(tick.bidPrice3))
                self.labelBidPrice4.setText(str(tick.bidPrice4))
                self.labelBidPrice5.setText(str(tick.bidPrice5))

                self.labelAskPrice2.setText(str(tick.askPrice2))
                self.labelAskPrice3.setText(str(tick.askPrice3))
                self.labelAskPrice4.setText(str(tick.askPrice4))
                self.labelAskPrice5.setText(str(tick.askPrice5))

                self.labelBidVolume2.setText(str(tick.bidVolume2))
                self.labelBidVolume3.setText(str(tick.bidVolume3))
                self.labelBidVolume4.setText(str(tick.bidVolume4))
                self.labelBidVolume5.setText(str(tick.bidVolume5))

                self.labelAskVolume2.setText(str(tick.askVolume2))
                self.labelAskVolume3.setText(str(tick.askVolume3))
                self.labelAskVolume4.setText(str(tick.askVolume4))
                self.labelAskVolume5.setText(str(tick.askVolume5))

            self.labelLastPrice.setText(str(tick.lastPrice))

            if tick.preClosePrice:
                rt = (tick.lastPrice / tick.preClosePrice) - 1
                self.labelReturn.setText(('%.2f' % (rt * 100)) + '%')
            else:
                self.labelReturn.setText('')

    # ----------------------------------------------------------------------
    def connectSignal(self):
        """连接Signal"""
        self.signal.connect(self.updateTick)

    # ----------------------------------------------------------------------
    def sendOrder(self):
        """发单"""
        symbol = str(self.lineSymbol.text())
        exchange = unicode(self.comboExchange.currentText())
        currency = unicode(self.comboCurrency.currentText())
        productClass = unicode(self.comboProductClass.currentText())
        gatewayName = unicode(self.comboGateway.currentText())

        # 查询合约
        if exchange:
            vtSymbol = '.'.join([symbol, exchange])
            contract = self.mainEngine.getContract(vtSymbol)
        else:
            vtSymbol = symbol
            contract = self.mainEngine.getContract(symbol)

        if contract:
            gatewayName = contract.gatewayName
            exchange = contract.exchange  # 保证有交易所代码

        req = VtOrderReq()
        req.symbol = symbol
        req.exchange = exchange
        req.vtSymbol = contract.vtSymbol
        req.price = self.spinPrice.value()
        req.volume = self.spinVolume.value()
        req.direction = unicode(self.comboDirection.currentText())
        req.priceType = unicode(self.comboPriceType.currentText())
        req.offset = unicode(self.comboOffset.currentText())
        req.currency = currency
        req.productClass = productClass

        self.mainEngine.sendOrder(req, gatewayName)

    # ----------------------------------------------------------------------
    def cancelAll(self):
        """一键撤销所有委托"""
        l = self.mainEngine.getAllWorkingOrders()
        for order in l:
            req = VtCancelOrderReq()
            req.symbol = order.symbol
            req.exchange = order.exchange
            req.frontID = order.frontID
            req.sessionID = order.sessionID
            req.orderID = order.orderID
            self.mainEngine.cancelOrder(req, order.gatewayName)

    # ----------------------------------------------------------------------
    def closePosition(self, cell):
        """根据持仓信息自动填写交易组件"""
        # 读取持仓数据，cell是一个表格中的单元格对象
        pos = cell.data
        symbol = pos.symbol

        # 更新交易组件的显示合约
        self.lineSymbol.setText(symbol)
        self.updateSymbol()

        # 自动填写信息
        self.comboPriceType.setCurrentIndex(self.priceTypeList.index(PRICETYPE_LIMITPRICE))
        self.comboOffset.setCurrentIndex(self.offsetList.index(OFFSET_CLOSE))
        self.spinVolume.setValue(pos.position)

        if pos.direction == DIRECTION_LONG or pos.direction == DIRECTION_NET:
            self.comboDirection.setCurrentIndex(self.directionList.index(DIRECTION_SHORT))
        else:
            self.comboDirection.setCurrentIndex(self.directionList.index(DIRECTION_LONG))

            # 价格留待更新后由用户输入，防止有误操作


# add by lsm 20180104
class FloatTradingWidget(QtWidgets.QWidget):
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    """管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))

    def __init__(self, omEngine, item, symbol, parent=None):
        """Constructor"""
        super(FloatTradingWidget, self).__init__(parent)

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine = self.mainEngine.eventEngine
        self.portfolio = omEngine.portfolio
        self.symbol = symbol
        self.initUi(item)
        self.setGeometry(1470,30,420,990)
        self.setFixedHeight(1000)
        self.setFixedWidth(420)

    # ----------------------------------------------------------------------
    def initUi(self, item):
        """初始化界面"""
        self.setWindowTitle(u'委托快捷下单')

        positionDetail = self.getPositionDetail()
        labelTradingWidget = QtWidgets.QLabel(u'期权名称:')
        labelSymbol = QtWidgets.QLabel(u'合约代码')
        self.labelOptionName = QtWidgets.QLabel(self.mainEngine.getContract(item.vtSymbol).name)
        self.labelOptionName.setFixedWidth(120)
        self.labelOptionName.setFont(QtGui.QFont("Roman times", 10))
        self.shortDirectionHorizontalLayoutWidget = QtWidgets.QHBoxLayout()

        # 卖开逻辑问题，加一个卖开选项来开关卖开还是卖平，如果选择打开卖开选项，则不管是否有多头仓位都选择卖开，如果关掉卖开选项，则按正常逻辑卖平卖开
        self.shortOpenRadio = QtWidgets.QRadioButton(u"卖开")
        self.shortCloseRadio = QtWidgets.QRadioButton(u"卖平")
        self.shortOpenRadio.setChecked(True)
        self.shortDirectionHorizontalLayoutWidget.addWidget(self.shortOpenRadio)
        self.shortDirectionHorizontalLayoutWidget.addWidget(self.shortCloseRadio)

        self.fiveMarketWidget = FiveMarketWidget(self.omEngine, item, item.vtSymbol)

        grid = QtWidgets.QGridLayout()
        grid.addWidget(labelTradingWidget, 0, 0)
        grid.addWidget(self.labelOptionName, 1, 0, 1, 2)

        grid.addLayout(self.shortDirectionHorizontalLayoutWidget, 0, 2, 1, 2)
        grid.addWidget(self.fiveMarketWidget, 1, 2, 3, 2)
        self.lineSymbol = QtWidgets.QLabel(item.symbol)
        grid.addWidget(labelSymbol, 2, 0)
        grid.addWidget(self.lineSymbol, 3, 0, 1, 2)

        self.quicklineVolume = QtWidgets.QDoubleSpinBox()
        self.quicklineVolume.setFixedWidth(40)
        self.quicklineVolume.setDecimals(0)
        self.quicklineVolume.setMinimum(0)
        self.quicklineVolume.setMaximum(1000)
        self.quicklineVolume.setMinimum(1)
        grid.addWidget(self.quicklineVolume, 9, 0)
        labelShortVolumeKey = QtWidgets.QLabel(u'空仓')
        self.labelShortVolumeValue = QtWidgets.QLabel(str(positionDetail.shortPos))
        labelShortVolumeKey.setFixedWidth(40)
        self.labelShortVolumeValue.setFixedWidth(40)

        grid.addWidget(labelShortVolumeKey, 10, 0)
        grid.addWidget(self.labelShortVolumeValue, 11, 0)

        labelLongVolumeKey = QtWidgets.QLabel(u'多仓')
        self.labelLongVolumeValue = QtWidgets.QLabel(str(positionDetail.longPos))
        grid.addWidget(labelLongVolumeKey, 12, 0)
        grid.addWidget(self.labelLongVolumeValue, 13, 0)
        labelLongVolumeKey.setFixedWidth(40)
        self.labelLongVolumeValue.setFixedWidth(40)

        labelNetVolumeKey = QtWidgets.QLabel(u'净仓')
        self.labelNetVolumeValue = QtWidgets.QLabel(str(positionDetail.longPos - positionDetail.shortPos))

        grid.addWidget(labelNetVolumeKey, 14, 0)
        grid.addWidget(self.labelNetVolumeValue, 15, 0)
        labelNetVolumeKey.setFixedWidth(40)
        self.labelNetVolumeValue.setFixedWidth(40)

        self.QuickTradeTable = QuickTradeTable(self, self.omEngine, item, item.vtSymbol)
        grid.addWidget(self.QuickTradeTable, 9, 1, 10, 3)

        self.eventEngine.register(EVENT_TRADE + self.symbol, self.processTradeEvent)
        self.setLayout(grid)

    # ----------------------------------------------------------------------
    def sendOrder(self, direction, price):
        """发送委托"""
        try:
            symbol = str(self.lineSymbol.text())
            volume = int(self.quicklineVolume.text())
        except:
            return

        instrument = self.portfolio.instrumentDict.get(symbol, None)
        if not instrument:
            return

        #如果不是期权
        if instrument.productClass<>PRODUCT_OPTION:
            self.fastTrade(symbol, direction, OFFSET_OPEN, price, volume)
            return

        # 获得当前时间各个合约的委托量和委托价格，用来判断平仓量！！
        longVolumeDic, shortVolumeDic, longPriceDic, shortPriceDic = self.calcutateOrderBySymbol()
        # 做多
        if direction == DIRECTION_LONG:
            # 如果空头仓位减去空头委托量大于等于买入量，则只需平
            if symbol in shortVolumeDic.keys():
                orderVolumn = shortVolumeDic[symbol]
            else:
                orderVolumn = 0
            if instrument.shortPos - orderVolumn >= volume:
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, volume)
            # 否则先平后开
            else:
                openVolume = volume - (instrument.shortPos - orderVolumn)
                if instrument.shortPos - orderVolumn:
                    self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, instrument.shortPos - orderVolumn)
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_OPEN, price, openVolume)
        # 做空
        else:
            if symbol in longVolumeDic.keys():
                orderVolumn = longVolumeDic[symbol]
            else:
                orderVolumn = 0
            if self.shortOpenRadio.isChecked():
                self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_OPEN, price, volume-orderVolumn)
            else:
                if instrument.longPos-orderVolumn >= volume:
                    self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, volume-orderVolumn)
                else:
                    openVolume = volume - (instrument.longPos-orderVolumn)
                    if instrument.longPos-orderVolumn:
                        self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, instrument.longPos-orderVolumn)
                    self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_OPEN, price, openVolume)


    # ----------------------------------------------------------------------根据symbol来查询合约委托量
    def calcutateOrderBySymbol(self):
        """根据symbol来查询合约委托量"""
        return self.mainEngine.calcutateOrderBySymbol()
    # ----------------------------------------------------------------------
    def fastTrade(self, symbol, direction, offset, price, volume):
        """封装下单函数"""
        contract = self.mainEngine.getContract(symbol)
        print "下单函数" + symbol
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
    def registerEvent(self, item, symbol):
        """注册事件监听,同时通知页面其他的控件更新"""
        # print "同时通知页面其他的控件更新"
        # print symbol
        if symbol == self.symbol:
            self.QuickTradeTable.registerEvent(item, item.vtSymbol)
            return
        else:
            self.labelOptionName.setText(self.mainEngine.getContract(item.vtSymbol).name)
            self.lineSymbol.setText(item.symbol)
            self.fiveMarketWidget.registerEvent(item, item.vtSymbol)
            self.QuickTradeTable.registerEvent(item, item.vtSymbol)

            self.eventEngine.unregister(EVENT_TRADE + self.symbol, self.processTradeEvent)
            self.eventEngine.register(EVENT_TRADE + item.vtSymbol, self.processTradeEvent)
            self.symbol = symbol

            positionDetail = self.getPositionDetail()
            self.labelShortVolumeValue.setText(str(positionDetail.shortPos))
            self.labelLongVolumeValue.setText(str(positionDetail.longPos))
            self.labelNetVolumeValue.setText(str(positionDetail.longPos - positionDetail.shortPos))

    def processTradeEvent(self, event):
        """成交更新"""
        trade = event.dict_['data']
        positionDetail = self.portfolio.instrumentDict[trade.symbol]
        self.labelShortVolumeValue.setText(str(positionDetail.shortPos))
        self.labelLongVolumeValue.setText(str(positionDetail.longPos))
        self.labelNetVolumeValue.setText(str(positionDetail.longPos - positionDetail.shortPos))

    def processTickEvent(self, event):
        """行情事件"""
        tick = event.dict_['data']

    def getPositionDetail(self):
        return self.mainEngine.getPositionDetail(self.symbol)


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
    def __init__(self, omEngine, item, vtSymbol, parent=None):
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
        self.setFixedHeight(200)
        self.verticalHeader().setDefaultSectionSize(15)
        self.eventEngine.register(EVENT_TICK + vtSymbol, self.processTickEvent)

    # ----------------------------------------------------------------------
    def initUi(self, item):
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


        arrayBidPrice = [item.bidPrice1, item.bidPrice2, item.bidPrice3, item.bidPrice4, item.bidPrice5]
        arrayBidVolume = [item.bidVolume1, item.bidVolume2, item.bidVolume3, item.bidVolume4, item.bidVolume5]

        arrayaskPrice = [item.askPrice5, item.askPrice4, item.askPrice3, item.askPrice2, item.askPrice1]
        arrayaskVolume = [item.askVolume5, item.askVolume4, item.askVolume3, item.askVolume2, item.askVolume1]

        for row in range(0, 5, 1):
            cellAskPrice = OmCell(str(arrayaskPrice[row]), COLOR_ASK, COLOR_BLACK,None,10)
            cellAskVolume = OmCell(str(arrayaskVolume[row]), COLOR_ASK, COLOR_BLACK,None,10)
            self.setItem(row, 2, cellAskPrice)
            self.setItem(row, 3, cellAskVolume)
            self.askPriceDict[row] = cellAskPrice
            self.askVolumeDict[row] = cellAskVolume

            cellBidPrice = OmCell(str(arrayBidPrice[row]), COLOR_BID, COLOR_BLACK,None,10)
            cellBidVolume = OmCell(str(arrayBidVolume[row]), COLOR_BID, COLOR_BLACK,None,10)
            self.setItem(row + 5, 0, cellBidPrice)
            self.setItem(row + 5, 1, cellBidVolume)
            self.bidPriceDict[row] = cellBidPrice
            self.bidVolumeDict[row] = cellBidVolume

    # ----------------------------------------------------------------------
    def registerEvent(self, item, vtSymbol):
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

    def changeFiveMarket(self, tick):
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
        u'委托量',
        u'买量',
        u'价  格',
        u'卖量',
        u'委托量',
    ]

    # ----------------------------------------------------------------------
    def __init__(self, parentMonitor, omEngine, item, vtSymbol, parent=None):
        """Constructor"""
        super(QuickTradeTable, self).__init__(parent)
        self.parentMonitor = parentMonitor
        # 保存代码和持仓,委托的Cell字典
        self.cellAskVolume = {}
        self.cellPriceDict = {}
        self.cellBidVolume = {}

        self.cellAskEntrust = {}
        self.cellBidEntrust = {}

        # 保存当前代码的五档行情字典，一档价格：一档持仓量
        self.bidDict = []
        self.askDict = []

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine = self.mainEngine.eventEngine

        # item.lastPrice
        self.vtSymbol = vtSymbol
        self.portfolio = omEngine.portfolio

        #qt区分左键还是右键
        self.mousePress=Qt.RightButton
        # 初始化
        self.initUi(item)
        self.eventEngine.register(EVENT_TICK + self.vtSymbol, self.processTickEvent)
        self.eventEngine.register(EVENT_ORDER, self.processOrderEvent)
        self.itemClicked.connect(self.MyClick)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.customContextMenuRequested.connect(self.MyClick)
        self.verticalHeader().setDefaultSectionSize(12)
        # ----------------------------------------------------------------------

    def MyClick(self,event):
        if self.mousePress == Qt.LeftButton:
            self.quickTrade(event)
        elif self.mousePress == Qt.RightButton:
            self.cancelOrder(event)



    def mousePressEvent(self,e):
        if e.button() == Qt.LeftButton:
            self.mousePress = Qt.LeftButton
        elif e.button() == Qt.RightButton:
            self.mousePress = Qt.RightButton
        elif e.button() == Qt.MidButton:
            self.mousePress = Qt.MidButton
        super(QuickTradeTable, self).mousePressEvent(e)
            

    def initUi(self, item):
        """初始化界面"""
        # 初始化表格
        self.setColumnCount(len(self.headers))

        self.setHorizontalHeaderLabels(self.headers)

        self.setRowCount(60)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

        for i in range(self.columnCount()):
            self.horizontalHeader().setResizeMode(i, QtWidgets.QHeaderView.Stretch)
        self.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        self.horizontalHeader().setResizeMode(self.columnCount() - 1, QtWidgets.QHeaderView.ResizeToContents)

        # 初始化标的单元格
        self.bidDict = dict(zip(
            [str(item.bidPrice1), str(item.bidPrice2), str(item.bidPrice3), str(item.bidPrice4), str(item.bidPrice5)],
            [item.bidVolume1, item.bidVolume2, item.bidVolume3, item.bidVolume4, item.bidVolume5]))
        self.askDict = dict(zip(
            [str(item.askPrice5), str(item.askPrice4), str(item.askPrice3), str(item.askPrice2), str(item.askPrice1)],
            [item.askVolume5, item.askVolume4, item.askVolume3, item.askVolume2, item.askVolume1]))

        self.price = item.lastPrice

        for row in range(-30, 30, 1):
            price = str(item.lastPrice - row * item.priceTick)
            cellPrice = OmCell(str(price), COLOR_BLACK, COLOR_SYMBOL, None, 8)

            if price in self.bidDict.keys():
                cellBid = OmCell(str(self.bidDict[price]), COLOR_BID, COLOR_BLACK, None, 8)
            else:
                cellBid = OmCell("", COLOR_BID, COLOR_BLACK, None, 8)

            if price in self.askDict.keys():
                askBid = OmCell(str(self.askDict[price]), COLOR_ASK, COLOR_BLACK, None, 8)
            else:
                askBid = OmCell("", COLOR_ASK, COLOR_BLACK, None, 8)

            self.cellPriceDict[row + 30] = cellPrice
            self.cellBidVolume[row + 30] = cellBid

            self.cellAskVolume[row + 30] = askBid

            self.setItem(row + 30, 2, cellPrice)
            self.setItem(row + 30, 1, cellBid)
            self.setItem(row + 30, 3, askBid)

        self.initOrderCell()

    def initOrderCell(self):
        # 委托量展示
        longVolumeDic, longLocalIDDic, shortVolumeDic, shortLocalIDDic = self.calculateOrderDict()
        if longVolumeDic:
            for row in range(0, 60, 1):
                priceAndVtSymbol = self.cellPriceDict[row].text() + self.vtSymbol
                if priceAndVtSymbol in longVolumeDic.keys():
                    bidEntrust = OmCell(str(longVolumeDic[priceAndVtSymbol]), COLOR_BID, COLOR_BLACK,
                                        longLocalIDDic[priceAndVtSymbol], 8)
                else:
                    bidEntrust = OmCell("", COLOR_BID, COLOR_BLACK, None, 8)
                if priceAndVtSymbol in shortVolumeDic.keys():
                    askEntrust = OmCell(str(shortVolumeDic[priceAndVtSymbol]), COLOR_ASK, COLOR_BLACK,
                                        shortLocalIDDic[priceAndVtSymbol], 8)
                else:
                    askEntrust = OmCell("", COLOR_ASK, COLOR_BLACK, None, 8)
                self.cellBidEntrust[row] = bidEntrust
                self.cellAskEntrust[row] = askEntrust

                self.setItem(row, 0, bidEntrust)
                self.setItem(row, 4, askEntrust)
        else:
            for row in range(0, 60, 1):
                bidEntrust = OmCell("", COLOR_BID, COLOR_BLACK, None, 8)
                askEntrust = OmCell("", COLOR_ASK, COLOR_BLACK, None, 8)
                self.cellBidEntrust[row] = bidEntrust
                self.cellAskEntrust[row] = askEntrust
                self.setItem(row, 0, bidEntrust)
                self.setItem(row, 4, askEntrust)

    # ----------------------------------------------------------------------
    def registerEvent(self, item, vtSymbol):
        """注册事件监听"""
        if vtSymbol == self.vtSymbol:
            self.changePriceData(item,True)
            return
        else:
            self.eventEngine.unregister(EVENT_TICK + self.vtSymbol, self.processTickEvent)
            self.eventEngine.unregister(EVENT_ORDER, self.processOrderEvent)
            self.changePriceData(item,True)
            self.eventEngine.register(EVENT_TICK + vtSymbol, self.processTickEvent)
            self.eventEngine.register(EVENT_ORDER, self.processOrderEvent)

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

    def quickTrade(self,event):
        '''左击事件:快速下单!'''
        print "左击事件"
        print self.currentRow()
        longPrice = float(self.cellPriceDict[self.currentRow()].text())
        if self.currentColumn() == 0:
            self.parentMonitor.sendOrder(DIRECTION_LONG, longPrice)
        elif self.currentColumn() == 4:
            self.parentMonitor.sendOrder(DIRECTION_SHORT, longPrice)
            # self.contextMenuEvent

    def cancelOrder(self,event):
        print "邮件时间??"
        if self.currentColumn() == 0:
            localIDs = self.cellBidEntrust[self.currentRow()].data
        elif self.currentColumn() == 4:
            localIDs = self.cellAskEntrust[self.currentRow()].data
        else:
            return
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
                    print '1111111111111'
                    contract = self.mainEngine.getContract(self.vtSymbol)
                    print req.symbol, req.exchange, req.frontID, req.sessionID, req.orderID
                    self.mainEngine.cancelOrder(req, contract.gatewayName)
                else:
                    print "没找到"
                    print vtOrderID
        else:
            print "没有东西"

    # ---------------------------------------------------------------------
    def changePriceData(self, item,refresh=False):
        """行情更新，价格列表,五档数据"""
        # 初始化标的单元格
        if refresh:
            self.price=item.lastPrice

        self.bidDict = dict(zip([str(item.bidPrice1), str(item.bidPrice2), str(item.bidPrice3), str(item.bidPrice4), str(item.bidPrice5)],
                                [item.bidVolume1, item.bidVolume2, item.bidVolume3, item.bidVolume4, item.bidVolume5]))
        self.askDict = dict(zip([str(item.askPrice5), str(item.askPrice4), str(item.askPrice3), str(item.askPrice2), str(item.askPrice1)],
                                [item.askVolume5, item.askVolume4, item.askVolume3, item.askVolume2, item.askVolume1]))
        #
        # bidPrice=[item.bidPrice1, item.bidPrice2, item.bidPrice3, item.bidPrice4, item.bidPrice5]
        # bidVolumn=[item.bidVolume1, item.bidVolume2, item.bidVolume3, item.bidVolume4, item.bidVolume5]
        # askPrice=[item.askPrice5, item.askPrice4, item.askPrice3, item.askPrice2, item.askPrice1]
        # askVolumn=[item.askVolume5, item.askVolume4, item.askVolume3, item.askVolume2, item.askVolume1]
        #
        # k.index(min(k))

        instrument=self.portfolio.instrumentDict[item.symbol]

        for row in range(-30, 30, 1):
            price = str(round(self.price - row *instrument.priceTick,instrument.remainDecimalPlaces))
            self.cellPriceDict[row + 30].setText(str(price))
            self.cellBidVolume[row + 30].setText("")
            self.cellAskVolume[row + 30].setText("")

            # if abs(price-item.bidPrice1)<instrument.priceTick/2:
            #     self.cellBidVolume[row + 30].setText(str(item.bidVolume1))
            #     continue
            # elif abs(price-item.bidPrice2)<instrument.priceTick/2:
            #     self.cellBidVolume[row + 30].setText(str(item.bidVolume2))
            #     continue
            # elif  abs(price - item.bidPrice3) < instrument.priceTick/2:
            #     self.cellBidVolume[row + 30].setText(str(item.bidVolume3))
            #     continue
            # elif abs(price - item.bidPrice4) < instrument.priceTick/2:
            #     self.cellBidVolume[row + 30].setText(str(item.bidVolume4))
            #     continue
            # elif abs(price - item.bidPrice5) < instrument.priceTick/2:
            #     self.cellBidVolume[row + 30].setText(str(item.bidVolume5))
            #     continue
            # elif abs(price - item.askPrice1) < instrument.priceTick/2:
            #     self.cellAskVolume[row + 30].setText(str(item.askVolume1))
            #     continue
            # elif abs(price - item.askPrice2) < instrument.priceTick/2:
            #     self.cellAskVolume[row + 30].setText(str(item.askVolume2))
            #     continue
            # elif abs(price - item.askPrice3) < instrument.priceTick/2:
            #     self.cellAskVolume[row + 30].setText(str(item.askVolume3))
            #     continue
            # elif abs(price - item.askPrice4) < instrument.priceTick/2:
            #     self.cellAskVolume[row + 30].setText(str(item.askVolume4))
            #     continue
            # elif abs(price - item.askPrice5) < instrument.priceTick/2:
            #     self.cellAskVolume[row + 30].setText(str(item.askVolume5))
            #     continue
            if price in self.bidDict.keys():
                self.cellBidVolume[row + 30].setText(str(self.bidDict[price]))
            elif price in self.askDict.keys():
                self.cellAskVolume[row + 30].setText(str(self.askDict[price]))

        self.changeOrderData()

    def changeOrderData(self, item=None):
        """委托数据更新"""
        longVolumeDic, longLocalIDDic, shortVolumeDic, shortLocalIDDic = self.calculateOrderDict()
        if longVolumeDic or shortVolumeDic:
            for row in range(0, 60, 1):
                priceAndVtSymbol = self.cellPriceDict[row].text() + self.vtSymbol

                if priceAndVtSymbol in longVolumeDic.keys():
                    self.cellBidEntrust[row].setText(str(longVolumeDic[priceAndVtSymbol]))
                    self.cellBidEntrust[row].data = longLocalIDDic[priceAndVtSymbol]
                else:
                    self.cellBidEntrust[row].setText("")
                    self.cellBidEntrust[row].data = None

                if priceAndVtSymbol in shortVolumeDic.keys():
                    self.cellAskEntrust[row].setText(str(shortVolumeDic[priceAndVtSymbol]))
                    self.cellAskEntrust[row].data = shortLocalIDDic[priceAndVtSymbol]
                else:
                    self.cellAskEntrust[row].setText("")
                    self.cellAskEntrust[row].data = None
        else:
            for row in range(0, 60, 1):
                self.cellAskEntrust[row].setText("")
                self.cellAskEntrust[row].data = None
                self.cellBidEntrust[row].setText("")
                self.cellBidEntrust[row].data = None

    #
    def getOrder(self, vtOrderID):
        """查询单个合约的委托"""
        return self.mainEngine.getOrder(vtOrderID)

    def calculateOrderDict(self, event=None):
        """查询单个合约的委托"""
        return self.mainEngine.calculateOrderDict()


########################################################################
class ManualTrader(QtWidgets.QWidget):
    """手动交易组件"""

    # ----------------------------------------------------------------------
    def __init__(self, omEngine, parent=None):
        """Constructor"""
        super(ManualTrader, self).__init__(parent)

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine = omEngine.eventEngine
        self.tradingWidget = {}
        self.chainMonitorAarry = []
        self.initUi()

        self.setGeometry(0,30,1450,990)
        self.setFixedWidth(1450)
        self.setFixedHeight(1000)
    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'手动交易')
        posMonitor = PositionMonitor(self.mainEngine, self.eventEngine)
        tradeMonitor=TradeMonitor(self.mainEngine, self.eventEngine)
        accountMonitor = AccountMonitor(self.mainEngine, self.eventEngine)

        optionAnalysisTable = OptionAnalysisTable(self.omEngine,'position')
        optionAnalysisTable2 = OptionAnalysisTable(self.omEngine, 'tick')
        # for i in range(OptionAnalysisTable.columnCount()):
        #     OptionAnalysisTable.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        #     OptionAnalysisTable.setSorting(False)

        orderMonitor = WorkingOrderMonitor(self.mainEngine, self.eventEngine)
        for i in range(orderMonitor.columnCount()):
            orderMonitor.horizontalHeader().setResizeMode(QtWidgets.QHeaderView.Stretch)
        orderMonitor.setSorting(False)

        calendarManager = CalendarManager()
        # 持仓双击调到交易页面，方便平仓showTradeWidget
        posMonitor.itemDoubleClicked.connect(self.showTradeWidget)

        tab2 = QtWidgets.QTabWidget()
        tab2.addTab(optionAnalysisTable, u'greeks汇总')
        tab2.addTab(optionAnalysisTable2, u'行情统计')
        tab2.addTab(posMonitor, u'持仓')
        tab2.addTab(tradeMonitor, u'成交')
        tab2.addTab(orderMonitor, u'可撤委托')
        tab2.addTab(accountMonitor, u'账户')
        tab2.addTab(calendarManager, u'到期日管理')

        tab = QtWidgets.QTabWidget()

        headerSelectButton = QtWidgets.QPushButton(u'列表选择')
        self.headerSelectWidget = HeaderSelectWidget(self.omEngine, self)
        headerSelectButton.clicked.connect(self.showHeaderSelectWidget)
        headerSelectButton.setFixedWidth(100)

        ivButton = QtWidgets.QPushButton(u'IV图表')
        ivButton.clicked.connect(self.openVolatilityChart)
        ivButton.setFixedWidth(100)

        ivBookButton = QtWidgets.QPushButton(u'IV报单')
        ivBookButton.clicked.connect(self.openBookVolatility)
        ivBookButton.setFixedWidth(100)

        cancelAllButton = QtWidgets.QPushButton(u'全撤')
        cancelAllButton.clicked.connect(self.cancelAll)
        cancelAllButton.setFixedWidth(100)

        # IV算法
        # ivAlgorithmHorizontalLayoutWidget = QtWidgets.QHBoxLayout()
        # self.ivAlgorithmRadio1 = QtWidgets.QRadioButton(u"波动率算法1")
        # self.ivAlgorithmRadio2 = QtWidgets.QRadioButton(u"波动率算法2")
        # self.ivAlgorithmRadio1.setChecked(True)
        # self.ivAlgorithmRadio1.clicked.connect(self.changeMainEngineIVAlgorithm1)
        # self.ivAlgorithmRadio2.clicked.connect(self.changeMainEngineIVAlgorithm2)
        #
        # ivAlgorithmHorizontalLayoutWidget.addWidget(self.ivAlgorithmRadio1)
        # ivAlgorithmHorizontalLayoutWidget.addWidget(self.ivAlgorithmRadio2)


        for chain in self.omEngine.portfolio.chainDict.values():
            chainMonitor = NewChainMonitor(chain, self.omEngine, self.mainEngine, self.eventEngine,
                                           self.headerSelectWidget)
            chainMonitor.itemDoubleClicked.connect(self.showFastTradeWidget)
            self.chainMonitorAarry.append(chainMonitor)
            tab.addTab(chainMonitor, chain.symbol)

        vbox = QtWidgets.QVBoxLayout()
        vhboxButtons = QtWidgets.QHBoxLayout()
        vhboxButtons.addWidget(headerSelectButton)
        vhboxButtons.addWidget(ivButton)
        vhboxButtons.addWidget(ivBookButton)
        vhboxButtons.addWidget(cancelAllButton)
        vhboxButtons.addStretch()
        vbox.addLayout(vhboxButtons)
        vbox.addWidget(tab)
        tab.setFixedHeight(620)
        tab.setMovable(True)
        tab2.setMovable(True)
        vbox.addWidget(tab2)
        self.setLayout(vbox)

    def changeMainEngineIVAlgorithm1(self, isChecked):
        self.mainEngine.ivAlgorithm = 1

    def changeMainEngineIVAlgorithm2(self, isChecked):
        self.mainEngine.ivAlgorithm = 2
    # ----------------------------------------------------------------------
    def cancelAll(self):
        """一键撤销所有委托"""
        l = self.mainEngine.getAllWorkingOrders()
        for order in l:
            req = VtCancelOrderReq()
            req.symbol = order.symbol
            req.exchange = order.exchange
            req.frontID = order.frontID
            req.sessionID = order.sessionID
            req.orderID = order.orderID
            self.mainEngine.cancelOrder(req, order.gatewayName)

        # ----------------------------------------------------------------------
    def openBookVolatility(self):
        """打开波动率图表组件"""
        try:
            self.bookVolatility.showMaximized()
        except:
            self.bookVolatility = BookVolatility(self.omEngine)
            self.bookVolatility.showMaximized()

    # ----------------------------------------------------------------------
    def openVolatilityChart(self):
        """打开波动率图表组件"""
        try:
            self.volatilityChart.showMaximized()
        except:
            self.volatilityChart = VolatilityChart(self.omEngine)
            self.volatilityChart.showMaximized()

    def showColumn(self, index, isShow):
        for item in self.chainMonitorAarry:
            if isShow:
                item.showColumn(index)
                item.showColumn(len(item.headers) - 1 - index)
            else:
                item.hideColumn(index)
                item.hideColumn(len(item.headers) - 1 - index)

    def showHeaderSelectWidget(self):
        try:
            self.headerSelectWidget.show()
        except:
            self.headerSelectWidget = HeaderSelectWidget(self.omEngine)
            self.headerSelectWidget.show()

    def showTradeWidget(self, item):
        try:
            self.tradingWidget['tradingWidget'].show()
        except KeyError:
            self.tradingWidget['tradingWidget'] = TradingWidget(self.mainEngine, self.eventEngine)
            self.tradingWidget['tradingWidget'].show()
        self.tradingWidget['tradingWidget'].closePosition(item)

    def showFastTradeWidget(self, item):
        instrument = item.data
        try:
            self.tradingWidget['floatTradingWidget'].show()
            self.tradingWidget['floatTradingWidget'].registerEvent(instrument, instrument.vtSymbol)
        except KeyError:
            self.tradingWidget['floatTradingWidget'] = FloatTradingWidget(self.omEngine, instrument,
                                                                          instrument.vtSymbol)
            self.tradingWidget['floatTradingWidget'].show()

            # ----------------------------------------------------------------------

    def saveWindowSettings(self):
        """保存窗口设置"""
        settings = QtCore.QSettings("ManualTrader", "ManualTrader")
        # settings.setValue('state', self.saveState())
        settings.setValue('geometry', self.saveGeometry())

# ----------------------------------------------------------------------
    def loadWindowSettings(self):
            """载入窗口设置"""
            settings = QtCore.QSettings("ManualTrader", "ManualTrader")
            # state = settings.value('state')
            geometry = settings.value('geometry')
            # 尚未初始化
            if geometry is None:
                print "return"
                return
            # 老版PyQt
            elif isinstance(geometry, QtCore.QVariant):
                # self.restoreState(state.toByteArray())
                self.restoreGeometry(geometry.toByteArray())
            # 新版PyQt
            elif isinstance(geometry, QtCore.QByteArray):
                # self.restoreState(state)
                self.restoreGeometry(geometry)
            # 异常
            else:
                content = u'载入窗口配置异常，请检查'
                self.mainEngine.writeLog(content)


# add by lsm 20180111
class OptionAnalysisTable(QtWidgets.QTableWidget):
    """持仓统计列表""",
    headers = [
        u'到期日',
        u'到期时间',
        u'隐含利率',
<<<<<<< HEAD
        u'Delta',
=======
        u'Delt',
>>>>>>> ca56d046fc017e5a917888ef695a7af02cf4116a
        u'Gamma',
        u'Vega',
        u'Theta',
        u'dgammaDS',
        u'dvegaDS',
        u'vomma',
        u'vonna',
        u'凸度',
        u'偏度',
        u'CallImpv',
        u'Impv',
        u'PutImpv',
        u'远期波动率',
        u'Call成交',
        u'Put成交',
        u'总成交',
        u'Call持仓',
        u'Put持仓',
        u'总持仓',
<<<<<<< HEAD
        u'Vega分解',
        u'远期2'
=======
>>>>>>> ca56d046fc017e5a917888ef695a7af02cf4116a
    ]

    def __init__(self, omEngine,kind,parent=None):
        """Constructor"""
        super(OptionAnalysisTable, self).__init__(parent)

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine = self.mainEngine.eventEngine
        self.portfolio = omEngine.portfolio

        # cellArray定义
        self.cellDueDate = {}
        # 到期时间
        self.cellDueTime = {}

        self.cellRate = {}


        self.cellDelta = {}
        self.cellGamma = {}
        self.cellVega = {}
        self.cellTheta = {}
        self.cellConvexity = {}
        self.cellSkew = {}
        self.cellCallImpv = {}
        self.cellPutImpv = {}
        self.cellImpv = {}

        self.cellPosDgammaDS = {}
        self.cellPosDvegaDS = {}
        self.cellPosVomma = {}
        self.cellPosVonna = {}

        self.cellPosDgammaDS = {}
        self.cellPosDvegaDS = {}
        self.cellPosVomma = {}
        self.cellPosVonna = {}

        self.cellCallPosition = {}
        self.cellPutPosition = {}
        self.cellTotalPosition = {}
        self.cellCallVolumn = {}
        self.cellPutVolumn = {}
        self.cellTotalVolumn = {}

        self.totalPosDgammaDS = None
        self.totalPosDvegaDS = None
        self.totalPosVomma = None
        self.totalPosVonna = None

        self.totalCellDelta = None
        self.totalCellGamma = None
        self.totalCellVega = None
        self.totalCellTheta = None
        self.impvCellDecompose = {}
        self.impvCellDecompose2 = {}
        self.forwardImpv = {}
        self.forwardImpv2 = {}
        self.dueTime = {}
        self.impv = {}
        self.impv2={}
        self.underlying = None

        self.callVolumn = None
        self.putVolumn = None
        self.totalVolumn = None

<<<<<<< HEAD
        self.cellDecomposeVega={}
        self.decomposeVega={}
        self.atTheMoneyVega={}
        self.chainPosVega={}

=======
>>>>>>> ca56d046fc017e5a917888ef695a7af02cf4116a
        self.callPosition = None
        self.putPosition = None
        self.totalPosition = None

        self.initUi()
        self.eventEngine.register(EVENT_TIMER, self.timingCalculate)
        if kind=='position':
            for i in range(11,16):
                self.hideColumn(i)
            for i in range(17,23):
                self.hideColumn(i)
        else:
            for i in range(0,11):
                self.hideColumn(i)
            self.hideColumn(23)

    def initUi(self):
        """初始化界面"""
        # 初始化表格
        self.setColumnCount(len(self.headers))

        self.setHorizontalHeaderLabels(self.headers)

        self.setRowCount(7)

        self.verticalHeader().setVisible(False)
        self.setEditTriggers(self.NoEditTriggers)

        # for i in range(self.columnCount()):
        #     self.horizontalHeader().setResizeMode(i, QtWidgets.QHeaderView.Stretch)
        # self.horizontalHeader().setResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        # self.horizontalHeader().setResizeMode(self.columnCount() - 1, QtWidgets.QHeaderView.ResizeToContents)
        # 初始化标的单元格
        for row, underlying in enumerate(self.portfolio.underlyingDict.values()):
            self.underlying = underlying
            break
        self.totalCellDelta = OmCell(
            str(self.portfolio.posDelta), None, COLOR_POS)
        self.totalCellGamma = OmCell(str(self.portfolio.posGamma), None, COLOR_POS)
        self.totalCellVega = OmCell(str(self.portfolio.posVega), None, COLOR_POS)
        self.totalCellTheta = OmCell(str(self.portfolio.posTheta), None, COLOR_POS)
        self.totalPosDgammaDS = OmCell(str(self.portfolio.posDgammaDS), None, COLOR_POS)
        self.totalPosDvegaDS = OmCell(str(self.portfolio.posDvegaDS), None, COLOR_POS)
        self.totalPosVomma = OmCell(str(self.portfolio.posVomma), None, COLOR_POS)
        self.totalPosVonna = OmCell(str(self.portfolio.posVonna), None, COLOR_POS)

        self.callVolumn = OmCell(str(self.portfolio.callVolume), None, COLOR_POS)
        self.putVolumn = OmCell(str(self.portfolio.putVolume), None, COLOR_POS)
        self.totalVolumn = OmCell(str(self.portfolio.callVolume+self.portfolio.putVolume), None, COLOR_POS)

        self.callPosition = OmCell(str(self.portfolio.callPostion), None, COLOR_POS)
        self.putPosition = OmCell(str(self.portfolio.putPostion), None, COLOR_POS)
        self.totalPosition = OmCell(str(self.portfolio.callPostion+self.portfolio.putPostion), None, COLOR_POS)

        self.setItem(4, 0, OmCell(u"汇总", None, COLOR_POS))
        self.setItem(5, 0, OmCell(u"标的物", None, COLOR_POS))

        self.underlyingDelta = OmCell(str(int(self.underlying.netPos * self.underlying.lastPrice * 0.01)), None,
                                      COLOR_POS)
        self.setItem(5, 3, self.underlyingDelta)
<<<<<<< HEAD

        self.setItem(4, 3, self.totalCellDelta)
        self.setItem(4, 4, self.totalCellGamma)
        self.setItem(4, 5, self.totalCellVega)
        self.setItem(4, 6, self.totalCellTheta)

        self.setItem(4, 7, self.totalPosDgammaDS)
        self.setItem(4, 8, self.totalPosDvegaDS)
        self.setItem(4, 9, self.totalPosVomma)
        self.setItem(4, 10, self.totalPosVonna)

=======

        self.setItem(4, 3, self.totalCellDelta)
        self.setItem(4, 4, self.totalCellGamma)
        self.setItem(4, 5, self.totalCellVega)
        self.setItem(4, 6, self.totalCellTheta)

        self.setItem(4, 7, self.totalPosDgammaDS)
        self.setItem(4, 8, self.totalPosDvegaDS)
        self.setItem(4, 9, self.totalPosVomma)
        self.setItem(4, 10, self.totalPosVonna)

>>>>>>> ca56d046fc017e5a917888ef695a7af02cf4116a
        self.setItem(4, 17, self.callVolumn)
        self.setItem(4, 18, self.putVolumn)
        self.setItem(4, 19, self.totalVolumn)

        self.setItem(4, 20, self.callPosition)
        self.setItem(4, 21, self.putPosition)
        self.setItem(4, 22, self.totalPosition)
<<<<<<< HEAD

        self.setItem(5, 17, OmCell(u"权利仓", None, COLOR_POS))
        self.setItem(5, 18, OmCell(u"义务仓", None, COLOR_POS))
        self.setItem(5, 19, OmCell(u"总持仓", None, COLOR_POS))

        self.setItem(5, 20, OmCell(u"买成交", None, COLOR_POS))
        self.setItem(5, 21, OmCell(u"卖成交", None, COLOR_POS))
        self.setItem(5, 22, OmCell(u"总成交", None, COLOR_POS))

        self.myLongVolumn = OmCell(str(self.portfolio.longPos), None, COLOR_POS)
        self.myShortVolumn = OmCell(str(self.portfolio.shortPos), None, COLOR_POS)
        self.myTotalVolumn = OmCell(str(self.portfolio.longPos+self.portfolio.shortPos), None, COLOR_POS)

        self.myLongTrade = OmCell(str(self.portfolio.longTrade+self.mainEngine.dataEngine.longTradedVolumn), None, COLOR_POS)
        self.myshortTrade = OmCell(str(self.portfolio.shortTrade+self.mainEngine.dataEngine.shortTradedVolumn), None, COLOR_POS)
        self.myTotalTrade = OmCell(str(self.portfolio.longTrade+self.portfolio.shortTrade+self.mainEngine.dataEngine.longTradedVolumn+self.mainEngine.dataEngine.shortTradedVolumn), None, COLOR_POS)

        self.setItem(6, 17, self.myLongVolumn)
        self.setItem(6, 18,self.myShortVolumn )
        self.setItem(6, 19, self.myTotalVolumn)

        self.setItem(6, 20,self.myLongTrade)
        self.setItem(6, 21,  self.myshortTrade)
        self.setItem(6, 22, self.myTotalTrade)
=======
>>>>>>> ca56d046fc017e5a917888ef695a7af02cf4116a

        for row, chain in enumerate(self.portfolio.chainDict.values()):
            cellDueDate = OmCell(str(chain.optionDict[chain.atTheMoneySymbol].expiryDate), None, COLOR_POS)
            cellDueTime = OmCell(str(round(chain.optionDict[chain.atTheMoneySymbol].t, 4)), None, COLOR_POS)
            self.dueTime[row] = chain.optionDict[chain.atTheMoneySymbol].t

            cellRate = OmCell(str(chain.chainRate), COLOR_BID, COLOR_POS)


            cellDelta = OmCell(str(chain.posDelta), None, COLOR_POS)
            cellGamma = OmCell(str(chain.posGamma), None, COLOR_POS)
            cellVega = OmCell(str(chain.posVega), None, COLOR_POS)
            cellTheta = OmCell(str(chain.posTheta), None, COLOR_POS)
            cellConvexity = OmCell(str(chain.convexity), None, COLOR_POS)
            cellSkew = OmCell(str(chain.skew), None, COLOR_POS)
            cellCallImpv = OmCell('%.2f' % (chain.callImpv * 100), None, COLOR_POS)
            cellPutImpv = OmCell('%.2f' % (chain.putImpv * 100), None, COLOR_POS)
            cellImpv = OmCell('%.2f' % ((chain.putImpv / 2 + chain.callImpv / 2) * 100), None, COLOR_POS)
            self.impv[row] = chain.putImpv / 2 + chain.callImpv / 2
            self.impv2[row] = chain.putImpv2 / 2 + chain.callImpv2 / 2

            cellDelta = OmCell(str(chain.posDelta), None, COLOR_POS)
            cellGamma = OmCell(str(chain.posGamma), None, COLOR_POS)
            cellVega = OmCell(str(chain.posVega), None, COLOR_POS)
            cellTheta = OmCell(str(chain.posTheta), None, COLOR_POS)

            cellPosDgammaDS = OmCell(str(chain.posDgammaDS), None, COLOR_POS)
            cellPosDvegaDS = OmCell(str(chain.posDvegaDS), None, COLOR_POS)
            cellPosVomma = OmCell(str(chain.posVomma), None, COLOR_POS)
            cellPosVonna = OmCell(str(chain.posVonna), None, COLOR_POS)

            cellCallPosition = OmCell(str(chain.callPostion), None, COLOR_POS)
            cellPutPosition = OmCell(str(chain.putPostion), None, COLOR_POS)
            cellTotalPosition = OmCell(str(chain.callPostion+chain.putPostion), None, COLOR_POS)
            cellCallVolumn = OmCell(str(chain.callVolume), None, COLOR_POS)
            cellPutVolumn = OmCell(str(chain.putVolume), None, COLOR_POS)
            cellTotalVolumn = OmCell(str(chain.callVolume+chain.putVolume), None, COLOR_POS)
            self.cellCallVolumn[row] = cellCallVolumn
            self.cellPutVolumn[row] = cellPutVolumn
            self.cellTotalVolumn[row] = cellTotalVolumn
            self.cellCallPosition[row] =cellCallPosition
            self.cellPutPosition[row] = cellPutPosition
            self.cellTotalPosition[row] = cellTotalPosition


            self.cellPosDgammaDS[row] = cellPosDgammaDS
            self.cellPosDvegaDS[row] = cellPosDvegaDS
            self.cellPosVomma[row] = cellPosVomma
            self.cellPosVonna[row] = cellPosVonna

            self.cellDelta[row] = cellDelta
            self.cellGamma[row] = cellGamma
            self.cellVega[row] = cellVega
            self.cellTheta[row] = cellTheta

            self.cellDueDate[row] = cellDueDate
            # 到期时间
            self.cellDueTime[row] = cellDueTime


            self.cellRate[row] = cellRate

            self.cellConvexity[row] = cellConvexity
            self.cellSkew[row] = cellSkew

            self.cellCallImpv[row] = cellCallImpv
            self.cellImpv[row] = cellImpv
            self.cellPutImpv[row] = cellPutImpv



            self.setItem(row, 0, cellDueDate)
            self.setItem(row, 1, cellDueTime)
            self.setItem(row, 2, cellRate)
            self.setItem(row, 3, cellDelta)
            self.setItem(row, 4, cellGamma)
            self.setItem(row, 5, cellVega)
            self.setItem(row, 6, cellTheta)
            self.setItem(row, 7, cellPosDgammaDS)
            self.setItem(row, 8, cellPosDvegaDS)
            self.setItem(row, 9, cellPosVomma)
            self.setItem(row, 10, cellPosVonna)

            self.setItem(row, 11, cellConvexity)
            self.setItem(row, 12, cellSkew)

            self.setItem(row, 13, cellCallImpv)
            self.setItem(row, 14, cellImpv)
            self.setItem(row, 15, cellPutImpv)

            self.setItem(row, 17, cellCallVolumn)
            self.setItem(row, 18, cellPutVolumn)
            self.setItem(row, 19, cellTotalVolumn)
            self.setItem(row, 20, cellCallPosition)
            self.setItem(row, 21, cellPutPosition)
            self.setItem(row, 22, cellTotalPosition)

<<<<<<< HEAD
            self.atTheMoneyVega[row]=chain.optionDict[chain.atTheMoneySymbol].vega
            self.chainPosVega[row]=chain.posVega

        if self.underlying.symbol=='510050':
            self.calculateForwardImpv()
            self.impvCellDecompose[0] = OmCell('%.2f' % (self.impv[0] * 100), None, COLOR_POS)
            self.impvCellDecompose[1] = OmCell('%.2f' % (self.forwardImpv[0] * 100), None, COLOR_POS)
            self.impvCellDecompose[2] = OmCell('%.2f' % (self.forwardImpv[1] * 100), None, COLOR_POS)
            self.impvCellDecompose[3] = OmCell('%.2f' % (self.forwardImpv[2] * 100), None, COLOR_POS)
            self.impvCellDecompose2[0] = OmCell('%.2f' % (self.impv2[0] * 100), None, COLOR_POS)
            self.impvCellDecompose2[1] = OmCell('%.2f' % (self.forwardImpv2[0] * 100), None, COLOR_POS)
            self.impvCellDecompose2[2] = OmCell('%.2f' % (self.forwardImpv2[1] * 100), None, COLOR_POS)
            self.impvCellDecompose2[3] = OmCell('%.2f' % (self.forwardImpv2[2] * 100), None, COLOR_POS)

            self.setItem(0, 16, self.impvCellDecompose[0])
            self.setItem(1, 16, self.impvCellDecompose[1])
            self.setItem(2, 16, self.impvCellDecompose[2])
            self.setItem(3, 16, self.impvCellDecompose[3])

            self.setItem(0, 24, self.impvCellDecompose2[0])
            self.setItem(1, 24, self.impvCellDecompose2[1])
            self.setItem(2, 24, self.impvCellDecompose2[2])
            self.setItem(3, 24, self.impvCellDecompose2[3])

            self.calculateDecomposeGreeks()
            self.cellDecomposeVega[0] = OmCell('%.0f' % (self.decomposeVega[0]), None, COLOR_POS)
            self.cellDecomposeVega[1] = OmCell('%.0f' % (self.decomposeVega[1]), None, COLOR_POS)
            self.cellDecomposeVega[2] = OmCell('%.0f' % (self.decomposeVega[2]), None, COLOR_POS)
            self.cellDecomposeVega[3] = OmCell('%.0f' % (self.decomposeVega[3]), None, COLOR_POS)

            self.setItem(0, 23, self.cellDecomposeVega[0])
            self.setItem(1, 23, self.cellDecomposeVega[1])
            self.setItem(2, 23, self.cellDecomposeVega[2])
            self.setItem(3, 23, self.cellDecomposeVega[3])


    #add by lsm 20180212
    def calculateDecomposeGreeks(self):
        # 更新算法2018.02.28
        # 1取四个不同到期日的到期时间T1 T2 T3 T4
        # 2对到期时间开根号，结果为t1 t2 t3 t4计算t12 = t2 - t1,t23 = t3 - t2,t34 = t4 - t3
        # 3四个到期日的持仓vega分别为pos1,pos2,pos3,pos4
        # 4分解后的持仓希腊值
        # VegaⅠ = pos1 + pos2 * (t1 / t2) + pos3 * (t1 / t3) + pos4 * (t1 / t4)
        # VegaⅡ = pos2 * (t12 / t2) + pos3 * (t12 / t3) + pos4 * (t12 / t4)
        # VegaⅢ = pos3 * (t23 / t3) + pos4 * (t23 / t4)
        # VegaⅣ = pos4 * (t34 / t4) self.dueTime[row]

        t1 = sqrt(self.dueTime[0])
        t2 = sqrt(self.dueTime[1])
        t3 = sqrt(self.dueTime[2])
        t4 = sqrt(self.dueTime[3])
        t12 = t2-t1
        t23 = t3-t2
        t34 = t4-t3

        try:
            self.decomposeVega[0] = self.chainPosVega[0] + \
                                    self.chainPosVega[1] * (t1 / t2) + \
                                    self.chainPosVega[2] * (t1 / t3) + \
                                    self.chainPosVega[3] * (t1 / t4)
        except:
            self.decomposeVega[0] = 0

        try:
            self.decomposeVega[1] = self.chainPosVega[1] * (t12 /t2) + \
                                    self.chainPosVega[2] * (t12 / t3) + \
                                    self.chainPosVega[3] * (t12 / t4)
        except:
            self.decomposeVega[1] = 0

        try:
            self.decomposeVega[2] = self.chainPosVega[2] * (t23 /  t3) + \
                                    self.chainPosVega[3] * (t23 /  t4)
        except:
            self.decomposeVega[2] = 0

        try:
            self.decomposeVega[3] = self.chainPosVega[3] * (t34/  t4)
        except:
            self.decomposeVega[3] = 0

        # 1.取四个不同到期日的，找到平值执行价K = min | Delta(K) - 0.5 |   ，计算四个平值的vega1,vega2, vega3,vega4
        # 2.即期vega01 = vega1远期vega12 = vega2 - vega1,vega23 = vega3 - vega2,vega34 = vega4 - vega3
        # 3.四个到期日的持仓vega分别为pos1,pos2,pos3,pos4
        # 4.分解后的持仓希腊值
        # VegaⅠ = pos1 + pos2 * (vega01 / vega2) + pos3 * (vega01 / vega3) + pos4 * (vega01 / vega4)
        # VegaⅡ = pos2 * (vega12 / vega2) + pos3 * (vega12 / vega3) + pos4 * (vega12 / vega4)
        # VegaⅢ = pos3 * (vega23 / vega3) + pos4 * (vega23 / vega4)
        # VegaⅣ = pos4 * (vega34 / vega4)
        # forwordVega={}
        # forwordVega[0]=self.atTheMoneyVega[0]
        # forwordVega[1] =self.atTheMoneyVega[1]-self.atTheMoneyVega[0]
        # forwordVega[2] = self.atTheMoneyVega[2] - self.atTheMoneyVega[1]
        # forwordVega[3] = self.atTheMoneyVega[3] - self.atTheMoneyVega[2]
        #
        # try:
        #     self.decomposeVega[0]=self.chainPosVega[0]+\
        #                       self.chainPosVega[1]*(forwordVega[0]/self.atTheMoneyVega[1])+\
        #                       self.chainPosVega[2]*(forwordVega[0]/self.atTheMoneyVega[2])+\
        #                       self.chainPosVega[3]*(forwordVega[0]/self.atTheMoneyVega[3])
        # except:
        #     self.decomposeVega[0]=0
        #
        # try:
        #     self.decomposeVega[1] = self.chainPosVega[1] * (forwordVega[1] / self.atTheMoneyVega[1]) + \
        #                         self.chainPosVega[2] * (forwordVega[1] / self.atTheMoneyVega[2]) + \
        #                         self.chainPosVega[3] * (forwordVega[1] / self.atTheMoneyVega[3])
        # except:
        #     self.decomposeVega[1]=0
        #
        # try:
        #     self.decomposeVega[2] = self.chainPosVega[2] * (forwordVega[2] / self.atTheMoneyVega[2]) + \
        #                         self.chainPosVega[3] * (forwordVega[2] / self.atTheMoneyVega[3])
        # except:
        #     self.decomposeVega[2]=0
        #
        # try:
        #     self.decomposeVega[3] =self.chainPosVega[3] * (forwordVega[3] / self.atTheMoneyVega[3])
        # except:
        #     self.decomposeVega[3]=0
=======
        self.calculateForwardImpv()
        self.impvCellDecompose[0] = OmCell('%.1f' % (self.forwardImpv[0] * 100), None, COLOR_POS)
        self.impvCellDecompose[1] = OmCell('%.1f' % (self.forwardImpv[1] * 100), None, COLOR_POS)
        self.impvCellDecompose[2] = OmCell('%.1f' % (self.forwardImpv[2] * 100), None, COLOR_POS)
        self.setItem(1, 16, self.impvCellDecompose[0])
        self.setItem(2, 16, self.impvCellDecompose[1])
        self.setItem(3, 16, self.impvCellDecompose[2])
>>>>>>> ca56d046fc017e5a917888ef695a7af02cf4116a

    def calculateForwardImpv(self):
        for index in self.dueTime.keys():
            if index < 3:
                try:
                    self.forwardImpv[index] = sqrt((self.impv[index + 1] ** 2 * self.dueTime[index + 1] - self.impv[
                        index] ** 2 * self.dueTime[index]) / (self.dueTime[index + 1] - self.dueTime[index]))
                except:
                    self.forwardImpv[index] = 0
        self.forwardImpv[3] = 0

<<<<<<< HEAD

        for index in self.dueTime.keys():
            if index < 3:
                try:
                    self.forwardImpv2[index] = sqrt((self.impv2[index + 1] ** 2 * self.dueTime[index + 1] - self.impv2[
                        index] ** 2 * self.dueTime[index]) / (self.dueTime[index + 1] - self.dueTime[index]))
                except:
                    self.forwardImpv2[index] = 0
        self.forwardImpv2[3] = 0

=======
>>>>>>> ca56d046fc017e5a917888ef695a7af02cf4116a
    def timingCalculate(self, event):
        for row, chain in enumerate(self.portfolio.chainDict.values()):
            self.cellDueTime[row].setText(str(round(chain.optionDict[chain.atTheMoneySymbol].t, 4)))
            self.dueTime[row] = chain.optionDict[chain.atTheMoneySymbol].t
            self.cellRate[row].setText(str(chain.chainRate))
            self.cellDelta[row].setText(str(chain.posDelta))
            self.cellGamma[row].setText(str(chain.posGamma))
            self.cellVega[row].setText(str(chain.posVega))
            self.cellTheta[row].setText(str(chain.posTheta))

            self.cellConvexity[row].setText(str(chain.convexity))
            self.cellSkew[row].setText(str(chain.skew))

            self.cellCallImpv[row].setText('%.2f' % (chain.callImpv * 100))
            self.cellPutImpv[row].setText('%.2f' % (chain.putImpv * 100))
            self.cellImpv[row].setText('%.2f' % ((chain.putImpv / 2 + chain.callImpv / 2) * 100))

            self.impv[row] = chain.putImpv / 2 + chain.callImpv / 2
            self.impv2[row] = chain.putImpv2 / 2 + chain.callImpv2 / 2

            self.cellPosDgammaDS[row].setText(str(chain.posDgammaDS))
            self.cellPosDvegaDS[row].setText(str(chain.posDvegaDS))
            self.cellPosVomma[row].setText(str(chain.posVomma))
            self.cellPosVonna[row].setText(str(chain.posVonna))

            self.cellCallPosition[row].setText(str(chain.callPostion))
            self.cellPutPosition[row].setText(str(chain.putPostion))
            self.cellTotalPosition[row].setText(str(chain.callPostion + chain.putPostion))
            self.cellCallVolumn[row].setText(str(chain.callVolume))
            self.cellPutVolumn[row].setText(str(chain.putVolume))
            self.cellTotalVolumn[row].setText(str(chain.callVolume + chain.putVolume))

<<<<<<< HEAD
            self.atTheMoneyVega[row] = chain.optionDict[chain.atTheMoneySymbol].vega
            self.chainPosVega[row] = chain.posVega


        self.totalCellDelta.setText(str(self.portfolio.posDelta ))
=======

        self.totalCellDelta.setText(str(self.portfolio.posDelta + self.underlying.netPos * self.underlying.lastPrice * 0.01))
>>>>>>> ca56d046fc017e5a917888ef695a7af02cf4116a
        self.totalCellGamma.setText(str(self.portfolio.posGamma))
        self.totalCellVega.setText(str(self.portfolio.posVega))
        self.totalCellTheta.setText(str(self.portfolio.posTheta))

        self.totalPosDgammaDS.setText(str(self.portfolio.posDgammaDS))
        self.totalPosDvegaDS.setText(str(self.portfolio.posDvegaDS))
        self.totalPosVomma.setText(str(self.portfolio.posVomma))
        self.totalPosVonna.setText(str(self.portfolio.posVonna))
        self.underlyingDelta.setText(str(int(self.underlying.netPos * self.underlying.lastPrice * 0.01)))

        if self.underlying.symbol == '510050':
            self.calculateForwardImpv()
            self.impvCellDecompose[0].setText('%.2f' % (self.impv[0] * 100))
            self.impvCellDecompose[1].setText('%.2f' % (self.forwardImpv[0] * 100))
            self.impvCellDecompose[2].setText('%.2f' % (self.forwardImpv[1] * 100))
            self.impvCellDecompose[3].setText('%.2f' % (self.forwardImpv[2] * 100))

            self.impvCellDecompose2[0].setText('%.2f' % (self.impv2[0] * 100))
            self.impvCellDecompose2[1].setText('%.2f' % (self.forwardImpv2[0] * 100))
            self.impvCellDecompose2[2].setText('%.2f' % (self.forwardImpv2[1] * 100))
            self.impvCellDecompose2[3].setText('%.2f' % (self.forwardImpv2[2] * 100))

            self.calculateDecomposeGreeks()
            self.cellDecomposeVega[0].setText('%.0f' % (self.decomposeVega[0]))
            self.cellDecomposeVega[1].setText('%.0f' % (self.decomposeVega[1]))
            self.cellDecomposeVega[2].setText('%.0f' % (self.decomposeVega[2]))
            self.cellDecomposeVega[3].setText('%.0f' % (self.decomposeVega[3]))

        self.callVolumn.setText(str(self.portfolio.callVolume))
        self.putVolumn.setText(str(self.portfolio.putVolume))
        self.totalVolumn.setText(str(self.portfolio.callVolume+self.portfolio.putVolume))
        self.callPosition.setText(str(self.portfolio.callPostion))
        self.putPosition.setText(str(self.portfolio.putPostion))
        self.totalPosition.setText(str(self.portfolio.callPostion+self.portfolio.putPostion))


        self.myLongVolumn.setText(str(self.portfolio.longPos))
        self.myShortVolumn.setText(str(self.portfolio.shortPos))
        self.myTotalVolumn.setText(str(self.portfolio.longPos + self.portfolio.shortPos))
        self.myLongTrade.setText(str(self.portfolio.longTrade+self.mainEngine.dataEngine.longTradedVolumn))
        self.myshortTrade.setText(str(self.portfolio.shortTrade+self.mainEngine.dataEngine.shortTradedVolumn))
        self.myTotalTrade.setText(str(self.portfolio.longTrade + self.portfolio.shortTrade+self.mainEngine.dataEngine.longTradedVolumn+self.mainEngine.dataEngine.shortTradedVolumn))


        self.callVolumn.setText(str(self.portfolio.callVolume))
        self.putVolumn.setText(str(self.portfolio.putVolume))
        self.totalVolumn.setText(str(self.portfolio.callVolume+self.portfolio.putVolume))
        self.callPosition.setText(str(self.portfolio.callPostion))
        self.putPosition.setText(str(self.portfolio.putPostion))
        self.totalPosition.setText(str(self.portfolio.callPostion+self.portfolio.putPostion))


# add by lsm 20180117
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
        self.shouldRefresh = False

        self.initTable()
        # 注册事件监听
        self.registerEvent()
        self.eventEngine.register(EVENT_TRADE, self.changeShouldRefresh)

    def registerEvent(self):
        self.signal.connect(self.deleteAllRows)
        self.signal.connect(self.updateEvent)
        self.eventEngine.register(self.eventType, self.signal.emit)

    def changeShouldRefresh(self, data):
        self.shouldRefresh = True

    def deleteAllRows(self, data):
        if self.shouldRefresh:
            iLen = len(self.dataDict.values())
            for i in range(0, iLen):
                self.removeRow(0)
            self.dataDict.clear()
            self.shouldRefresh = False


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
    def __init__(self, omEngine, parent=None):
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
        self.bidDict = dict(zip([item.bidPrice1, item.bidPrice2, item.bidPrice3, item.bidPrice4, item.bidPrice5],
                                [item.bidVolume1, item.bidVolume2, item.bidVolume3, item.bidVolume4, item.bidVolume5]))
        self.askDict = dict(zip([item.askPrice5, item.askPrice4, item.askPrice3, item.askPrice2, item.askPrice1],
                                [item.askVolume5, item.askVolume4, item.askVolume3, item.askVolume2, item.askVolume1]))

        for row in range(-20, 20, 1):
            price = item.lastPrice - row / 10000.0
            cellPrice = OmCell(str(price), COLOR_BLACK, COLOR_SYMBOL)

            if price in self.bidDict.keys():
                cellBid = OmCell(str(self.bidDict[price]), COLOR_BID, COLOR_BLACK)
            else:
                cellBid = OmCell("", COLOR_BID, COLOR_BLACK)

            if price in self.askDict.keys():
                askBid = OmCell(str(self.askDict[price]), COLOR_ASK, COLOR_BLACK)
            else:
                askBid = OmCell("", COLOR_ASK, COLOR_BLACK)

            self.cellPriceDict[row + 20] = cellPrice
            self.cellBidVolume[row + 20] = cellBid

            self.cellAskVolume[row + 20] = askBid

            self.setItem(row + 20, 2, cellPrice)
            self.setItem(row + 20, 1, cellBid)
            self.setItem(row + 20, 3, askBid)

        self.initOrderCell()
        self.itemDoubleClicked.connect(self.quickTrade)

    def initOrderCell(self):
        # 委托量展示
        longVolumeDic, longLocalIDDic, shortVolumeDic, shortLocalIDDic = self.calculateOrderDict()
        if longVolumeDic:
            for row in range(0, 40, 1):
                priceAndVtSymbol = self.cellPriceDict[row].text() + self.vtSymbol
                if priceAndVtSymbol in longVolumeDic.keys():
                    bidEntrust = OmCell(str(longVolumeDic[priceAndVtSymbol]), COLOR_BID, COLOR_BLACK,
                                        longLocalIDDic[priceAndVtSymbol])
                else:
                    bidEntrust = OmCell("", COLOR_BID, COLOR_BLACK)
                if priceAndVtSymbol in shortVolumeDic.keys():
                    askEntrust = OmCell(str(shortVolumeDic[priceAndVtSymbol]), COLOR_ASK, COLOR_BLACK,
                                        shortLocalIDDic[priceAndVtSymbol])
                else:
                    askEntrust = OmCell("", COLOR_ASK, COLOR_BLACK)
                self.cellBidEntrust[row] = bidEntrust
                self.cellAskEntrust[row] = askEntrust

                self.setItem(row, 0, bidEntrust)
                self.setItem(row, 4, askEntrust)
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
            print '一样22222222222222222'
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
        longPrice = float(self.cellPriceDict[self.currentRow()].text())
        if self.currentColumn() == 0:
            self.parentMonitor.sendOrder(DIRECTION_LONG, longPrice)
        elif self.currentColumn() == 4:
            self.parentMonitor.sendOrder(DIRECTION_SHORT, longPrice)

    def contextMenuEvent(self, event):
        if self.currentColumn() == 0:
            localIDs = self.cellBidEntrust[self.currentRow()].data
        elif self.currentColumn() == 4:
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
                    contract = self.mainEngine.getContract(order.symbol)
                    self.mainEngine.cancelOrder(req, contract.gatewayName)
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

    def changeOrderData(self, item=None):
        """委托数据更新"""
        longVolumeDic, longLocalIDDic, shortVolumeDic, shortLocalIDDic = self.calculateOrderDict()
        if longVolumeDic:
            for row in range(0, 40, 1):
                priceAndVtSymbol = self.cellPriceDict[row].text() + self.vtSymbol
                if priceAndVtSymbol in longVolumeDic.keys():
                    self.cellBidEntrust[row].setText(str(longVolumeDic[priceAndVtSymbol]))
                    self.cellBidEntrust[row].data = longLocalIDDic[priceAndVtSymbol]
                else:
                    self.cellBidEntrust[row].setText("")
                    self.cellBidEntrust[row].data = None

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
    def getOrder(self, vtOrderID):
        """查询单个合约的委托"""
        return self.mainEngine.getOrder(vtOrderID)

    def calculateOrderDict(self, event=None):
        """查询单个合约的委托"""
        return self.mainEngine.calculateOrderDict()


# add by lsm 20180124 用来选择tableheader列表，只展示选择的列表！
class HeaderSelectWidget(QtWidgets.QWidget):
    # add by lsm 20180124 用来选择tableheader列表，只展示选择的列表！
    headersDic = OrderedDict()

    u'合约名称0',
    u'买价1',
    u'买量2',
    u'买隐波3',
    u'卖价4',
    u'卖量5',
    u'卖隐波6',
    u'隐波7',
    u'delta8',
    u'gamma9',
    u'theta10',
    u'vega11',
    u'多仓12',
    u'空仓13',
    u'净仓14',
    u'买远期15',
    u'行权价16',


    headersDic['name'] = {'chinese': u'合约名称', 'show': True}
    headersDic['bidPrice1'] = {'chinese': u'买价', 'show': True}
    headersDic['bidVolume1'] = {'chinese': u'买量', 'show': True}
    headersDic['bidImpv'] = {'chinese': u'买隐波', 'show': True}
    headersDic['askPrice1'] = {'chinese': u'卖价', 'show': True}
    headersDic['askVolume1'] = {'chinese': u'卖量', 'show': True}
    headersDic['askImpv'] = {'chinese': u'卖隐波', 'show': True}
    headersDic['midImpv'] = {'chinese': u'隐波', 'show': False}
    headersDic['theoDelta'] = {'chinese': u'delta', 'show': False}
    headersDic['theoGamma'] = {'chinese': u'gamma', 'show': False}
    headersDic['theoTheta'] = {'chinese': u'theta', 'show': False}
    headersDic['theoVega'] = {'chinese': u'vega', 'show': False}
    headersDic['longPos'] = {'chinese': u'多仓', 'show': False}
    headersDic['shortPos'] = {'chinese': u'空仓', 'show': False}
    headersDic['netPos'] = {'chinese': u'净仓', 'show': True}
    headersDic['longFuture'] = {'chinese': u'买远期', 'show': False}
    headersDic['k'] = {'chinese': u'行权价', 'show': True}

    def loadJson(self):
        try:
            f = file('headerSelect.json')
            s = json.load(f)
            print s
            for index, item in enumerate(self.headersDic.keys()):
                self.headersDic[item]['show']=s[item]
        except Exception:
            print Exception.message
            pass

    def saveJson(self):
        file = open('headerSelect.json', 'wb')
        data={}
        for index, item in enumerate(self.headersDic.keys()):
            data[item]=self.headersDic[item]['show']
        json.dump(data, file, ensure_ascii=False)
        file.close()

    def __init__(self, omEngine, manualTrader, parent=None):
        """Constructor"""
        super(HeaderSelectWidget, self).__init__(parent)

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine = omEngine.eventEngine
        self.manualTrader = manualTrader
        self.checkAarry = []
        self.loadJson()
        self.initUi()

    def close(self):
        print 'save'
        self.saveJson()



    def initUi(self):
        self.grid = QtWidgets.QGridLayout()
        for index, item in enumerate(self.headersDic.keys()):
            checkBox = QtWidgets.QCheckBox(self.headersDic[item]['chinese'])
            checkBox.setChecked(self.headersDic[item]['show'])
            self.checkAarry.append(checkBox)
            checkBox.clicked.connect(self.changeHeaders)
            self.grid.addWidget(checkBox, index, 0)
        saveBtn = QtWidgets.QPushButton(u'保存')
        saveBtn.clicked.connect(self.saveJson)
        self.grid.addWidget(saveBtn, index+1, 0)
        self.setLayout(self.grid)
        self.setWindowTitle(u'列表选择')

    def changeHeaders(self, isChecked):
        checkbox = self.sender()
        print self.checkAarry.index(checkbox)
        self.showColumn(self.checkAarry.index(checkbox), isChecked)

    def showColumn(self, index, isShow):
        for i, item in enumerate(self.headersDic.keys()):
            if index==i:
                self.headersDic[item]['show']=isShow
                break
        self.manualTrader.showColumn(index, isShow)


# add by lsm 20180313
class TradeMonitor(BasicMonitor):
    """成交监控"""

    # ----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(TradeMonitor, self).__init__(mainEngine, eventEngine, parent)

        d = OrderedDict()
        d['tradeID'] = {'chinese': vtText.TRADE_ID, 'cellType': NumCell}
        d['orderID'] = {'chinese': vtText.ORDER_ID, 'cellType': NumCell}
        d['symbol'] = {'chinese': vtText.CONTRACT_SYMBOL, 'cellType': BasicCell}
        d['vtSymbol'] = {'chinese': vtText.CONTRACT_NAME, 'cellType': NameCell}
        d['direction'] = {'chinese': vtText.DIRECTION, 'cellType': DirectionCell}
        d['offset'] = {'chinese': vtText.OFFSET, 'cellType': BasicCell}
        d['price'] = {'chinese': vtText.PRICE, 'cellType': BasicCell}
        d['volume'] = {'chinese': vtText.VOLUME, 'cellType': BasicCell}
        d['tradeTime'] = {'chinese': vtText.TRADE_TIME, 'cellType': BasicCell}
        d['gatewayName'] = {'chinese': vtText.GATEWAY, 'cellType': BasicCell}
        self.setHeaderDict(d)

        self.setEventType(EVENT_TRADE)
        self.setFont(BASIC_FONT)
        self.setSorting(True)

        self.initTable()
        self.registerEvent()
