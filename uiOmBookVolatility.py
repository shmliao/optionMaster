# encoding: UTF-8

from vnpy.event import Event
from uiOmVolatilityManager import VolatilityChart

from vnpy.trader.vtConstant import DIRECTION_LONG, DIRECTION_SHORT, OFFSET_OPEN, OFFSET_CLOSE, PRICETYPE_LIMITPRICE,OPTION_CALL,OPTION_PUT
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
import time
from threading import Timer


# Add by lsm 20180208
class BookChainMonitor(QtWidgets.QTableWidget):
    """期权链监控"""
    headers = [
        u'买价',
        u'买隐波',
        u'买阈值',
        u'买  量',
        u'IV递增',
        u'perVol',
        u'单次量',
        u'买开关',

        u'卖开关',
        u'卖价',
        u'卖隐波',
        u'卖阈值',
        u'卖委托量',
        u'IV递增',
        u'perVol',
        u'单次量',
        u'净持仓',
        u'行权价',
        u'净持仓',

        u'IV递增',
        u'perVol',
        u'单次量',
        u'卖  量',
        u'卖阈值',
        u'卖隐波',
        u'卖价',
        u'卖开关',

        u'买开关',
        u'IV递增',
        u'perVol',
        u'单次量',
        u'买  量',
        u'买阈值',
        u'买隐波',
        u'买价',
    ]
    signalTick = QtCore.pyqtSignal(type(Event()))
    signalPos = QtCore.pyqtSignal(type(Event()))
    signalTrade = QtCore.pyqtSignal(type(Event()))

    def __init__(self, chain, omEngine, mainEngine, eventEngine, bookImpvConfig,riskOfGreeksWidget,parent=None):
        """Constructor"""
        super(BookChainMonitor, self).__init__(parent)
        self.parentWidget=parent
        self.riskOfGreeksWidget=riskOfGreeksWidget
        self.omEngine = omEngine
        self.eventEngine = eventEngine
        self.mainEngine = mainEngine
        # 保存代码和持仓的字典
        self.cellBidPrice = {}
        self.cellBidImpv =  {}
        self.cellAskPrice =  {}
        self.cellAskImpv =  {}

        self.cellBidSwitch =  {}
        self.cellAskSwitch = {}
        self.optionPriceFormat={}

        #合约的波动率报单开关key:symbol,value:off,on,仅仅用于显示开关off 或者on
        self.switchBidSymbol={}
        self.switchAskSymbol = {}

        self.chain = chain
        # 保存期权对象的字典
        portfolio = omEngine.portfolio
        self.instrumentDict = {}
        self.instrumentDict.update(portfolio.optionDict)
        self.instrumentDict.update(portfolio.underlyingDict)

        # 打开波动率报单的合约，存储开关打开的合约，这样是为了避免每次都循环所有的合约，影响速度！
        self.onBidSymbol = []
        self.onAskSymbol = []

        # 波动率买阈值
        self.originalBookBidImpv={}
        self.originalBookAskImpv = {}
        self.bookBidImpv = {}
        # 买总量
        self.bidEntruthVolumn = {}
        #买成交量
        self.bidTradedVolumn = {}
        # 每次成交一定数量以后，需要改变波动率的值
        self.bidStepPerVolumn = {}
        # 波动率每次变化的值
        self.bidImpvChange = {}
        # 单次下单的数量
        self.bidStepVolum = {}

        self.firstBid={}
        self.firstAsk={}

        self.cellBookBidImpv = {}
        self.cellBidEntruthVolumn = {}
        self.cellBidTradedVolumn={}
        self.cellBidStepPerVolumn = {}
        self.cellBidImpvChange = {}
        self.cellBidStepVolum = {}

        self.bookAskImpv = {}
        self.askEntruthVolumn = {}
        self.askTradedVolumn = {}
        self.askStepPerVolumn = {}
        self.askImpvChange = {}
        self.askStepVolum = {}

        self.cellBookAskImpv = {}
        self.cellAskEntruthVolumn = {}
        self.cellAskTradedVolumn={}
        self.cellAskStepPerVolumn = {}
        self.cellAskImpvChange = {}
        self.cellAskStepVolum = {}

        self.cellNetPosVol={}

        self.entrustVolumn=2
        self.stepVolumn=1
        self.impvUp=0.05
        self.impvDown=0.05
        self.impvChange=0.1
        self.stepPerVolumn=1

        # 初始化
        self.initUi()
        self.registerEvent()
        self.setShowGrid(True)
        # ----------------------------------------------------------------------
        self.itemClicked.connect(self.switchVolitity)


    def firstSenderOrder(self,symbol,direct):
        # 1.假设设置的波动率为v，盘口买隐波率为bidv，卖隐波率为askv
        # 2.假设是买入波动率
        # 3.如果v <= bidv，不报单
        # 4.如果bidv < v < askv，那么直接报bidprice1 + 1tick
        # 5.如果v >= aksv那么直接报askprice1
        if not self.parentWidget.masterSwitch:
            return

        instrument = self.omEngine.portfolio.instrumentDict.get(symbol, None)
        if not instrument:
            return
        if direct==DIRECTION_LONG:
            if self.bookBidImpv[symbol]/100<=instrument.bidImpv or self.bookBidImpv[symbol]<=0:
                print 'v <= bidv，不报单'
                return
            elif instrument.bidImpv<self.bookBidImpv[symbol]/100<instrument.askImpv:
                print 'bidv < v < askv，那么直接报bidprice1 + 1tick'
                price=instrument.bidPrice1+instrument.priceTick
            else:
                print 'v >= aksv 那么直接报askprice1'
                price = instrument.askPrice1

            orderVolumn = self.bidStepVolum[symbol]
            price = round(price, instrument.remainDecimalPlaces)
            orderVolumn = int(orderVolumn)
            print '首次买委托量'+str(orderVolumn)
            print '首次买价格' + str(price)
            # 如果空头仓位大于等于买入量，则只需平
            if instrument.shortPos >= orderVolumn:
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, orderVolumn)
             # 否则先平后开
            else:
                openVolume = orderVolumn - instrument.shortPos
                if instrument.shortPos:
                    self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, instrument.shortPos)
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_OPEN, price, openVolume)
            self.firstBid[symbol] = True
        else:
            if self.bookAskImpv[symbol]/100>=instrument.askImpv or self.bookAskImpv[symbol]<=0:
                print 'v >= askv，不报单'
                return
            elif instrument.bidImpv<self.bookAskImpv[symbol]/100<instrument.askImpv:
                print 'bidv < v < askv，那么直接报askprice1 - 1tick'
                price=instrument.askPrice1-instrument.priceTick
            else:
                print '如果 v <= bidv 那么直接报bidprice1'
                price = instrument.bidPrice1

            orderVolumn = self.askStepVolum[symbol]
            price=round(price,instrument.remainDecimalPlaces)
            orderVolumn=int(orderVolumn)
            print '首次卖委托量' + str(orderVolumn)
            print '首次卖价格' + str(price)
            if self.parentWidget.shortDirection == OFFSET_OPEN:
                print '卖开'
                self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_OPEN, price, orderVolumn)
            else:
                print '卖平'
                if instrument.longPos >= orderVolumn:
                    self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, orderVolumn)
                else:
                    openVolume = orderVolumn - instrument.longPos
                    if instrument.longPos:
                        self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price,instrument.longPos)
                    self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_OPEN, price, openVolume)
            self.firstAsk[symbol] = True
    #----------------------------行情每次更新都下单
    def tickSendOrder(self,symbol,direct):
        #6.行情更新，假设没有成交，假设v <= bidv，撤单
        #7.假设bidv < v <= askv，判断bidvol1和自己报单量是否相等，不相等则不动，如果相等，判断bidprice1 - bidprice2 = 1,tick，如果成立，则不动，如果不成立，则撤单，报bidprice2 + 1tick
        #8.假设v >= aksv如果没成交，不处理，成交了，直接报askprice1
        if not self.parentWidget.masterSwitch:
            return
        instrument = self.omEngine.portfolio.instrumentDict.get(symbol, None)
        if not instrument:
            return

        # 获得当前时间各个合约的委托量和委托价格，用来判断是否还需要继续发送委托和撤单！！
        longVolumeDic, shortVolumeDic, longPriceDic, shortPriceDic= self.calcutateOrderBySymbol()
        if direct == DIRECTION_LONG:
            if self.bookBidImpv[symbol]/100<=instrument.bidImpv:
                print '行情更新，假设没有成交，假设v <= bidv，撤单'
                self.cancelOrder(symbol, direct)
                return
            elif instrument.bidImpv<self.bookBidImpv[symbol]/100<instrument.askImpv:
                price = instrument.bidPrice1 + instrument.priceTick
                if symbol in longVolumeDic.keys():
                    if longPriceDic[symbol]==instrument.bidPrice1:
                        print '判断bidPrice1和委托价格是否相等，相等则不动'
                        return
                    else:
                        print "有人抢单了！撤单,抢单！"
                        self.cancelOrder(symbol, direct)
            else:
                if symbol in longVolumeDic.keys():
                    print '假设v >= aksv如果没成交，不处理'
                    return
                else:
                    print '假设v >= aksv成交了，直接报askprice1'
                    price = instrument.askPrice1

            # 报单
            orderVolumn = self.bidStepVolum[symbol]
            price = round(price, instrument.remainDecimalPlaces)
            orderVolumn = int(orderVolumn)
            print '买委托量' + str(orderVolumn)
            print '买价格' + str(price)
            # 如果空头仓位大于等于买入量，则只需平
            if instrument.shortPos >= orderVolumn:
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, orderVolumn)
                # 否则先平后开
            else:
                openVolume = orderVolumn - instrument.shortPos
                if instrument.shortPos:
                    self.fastTrade(symbol, DIRECTION_LONG, OFFSET_CLOSE, price, instrument.shortPos)
                self.fastTrade(symbol, DIRECTION_LONG, OFFSET_OPEN, price, openVolume)

        else:
            if self.bookAskImpv[symbol]/100>=instrument.askImpv or self.bookAskImpv[symbol]<=0:
                print '行情更新，假设没有成交，假设 v >= askv，撤单'
                self.cancelOrder(symbol, direct)
                return
            elif instrument.bidImpv<self.bookAskImpv[symbol]/100<instrument.askImpv:
                price = instrument.askPrice1 - instrument.priceTick
                if symbol in shortVolumeDic.keys():
                    if shortPriceDic[symbol]==instrument.askPrice1:
                        print '判断askPrice1和委托价格是否相等，相等则不动'
                        return
                    else:
                        print "有人抢单了！撤单,抢单！"
                        self.cancelOrder(symbol, direct)
            else:
                if symbol in shortVolumeDic.keys():
                    print '假设v <= bidv 如果没成交，不处理'
                    return
                else:
                    print '假设v <= bidv 成交了，直接报bidprice1'
                    price = instrument.bidPrice1

            orderVolumn = self.askStepVolum[symbol]
            price = round(price, instrument.remainDecimalPlaces)
            orderVolumn = int(orderVolumn)
            print '卖委托量' + str(orderVolumn)
            print '卖价格'+str(price)
            if self.parentWidget.shortDirection == OFFSET_OPEN:
                print '卖开'
                self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_OPEN, price, orderVolumn)
            else:
                print '卖平'
                if instrument.longPos >= orderVolumn:
                    self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, orderVolumn)
                else:
                    openVolume = orderVolumn - instrument.longPos
                    if instrument.longPos:
                        self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_CLOSE, price, instrument.longPos)
                    self.fastTrade(symbol, DIRECTION_SHORT, OFFSET_OPEN, price, openVolume)

    def getOrder(self, vtOrderID):
        """查询单个合约的委托"""
        return self.mainEngine.getOrder(vtOrderID)
    # ----------------------------------------------------------------------每个合约的开关设置
    def switchVolitity(self,item):
        option = item.data
        print option.symbol
        if item in self.cellBidSwitch.values():
            if option.symbol in self.onBidSymbol:
                self.switchBidSymbol[option.symbol] = 'off'
                self.cellBidSwitch[option.symbol].setText('off')
                self.onBidSymbol.remove(option.symbol)
                self.cancelOrder(option.symbol,DIRECTION_LONG)
            else:
                self.switchBidSymbol[option.symbol] = 'on'
                self.cellBidSwitch[option.symbol].setText('on')
                self.onBidSymbol.append(option.symbol)
                greekControl=self.judgeGreeksConfig(option.symbol, DIRECTION_LONG)
                if greekControl:
                    self.firstSenderOrder(option.symbol, DIRECTION_LONG)
            self.bidTradedVolumn[option.symbol]=0
            self.cellBidTradedVolumn[option.symbol].setText('0')

        elif item in self.cellAskSwitch.values():
            if option.symbol in self.onAskSymbol:
                self.switchAskSymbol[option.symbol] = 'off'
                self.cellAskSwitch[option.symbol].setText('off')
                self.onAskSymbol.remove(option.symbol)
                self.cancelOrder(option.symbol,DIRECTION_SHORT)
            else:
                self.switchAskSymbol[option.symbol] = 'on'
                self.cellAskSwitch[option.symbol].setText('on')
                self.onAskSymbol.append(option.symbol)
                greekControl = self.judgeGreeksConfig(option.symbol, DIRECTION_SHORT)
                if greekControl:
                    self.firstSenderOrder(option.symbol, DIRECTION_SHORT)

            self.askTradedVolumn[option.symbol] = 0
            self.cellAskTradedVolumn[option.symbol].setText('0')

    def judgeGreeksConfig(self,symbol,direct):
        if symbol in self.chain.callDict.keys():
            putOrCall = OPTION_CALL
        elif symbol in self.chain.putDict.keys():
            putOrCall =OPTION_PUT
        #判断delta：
        if self.riskOfGreeksWidget.greeksSwitch['delta']=="on" and self.riskOfGreeksWidget.greeksSwitch['delta'+self.chain.symbol]=="on":
            if self.riskOfGreeksWidget.upGreeksSwitch['delta'] == 'off':
                if (putOrCall==OPTION_CALL and direct==DIRECTION_LONG) or (putOrCall==OPTION_PUT and direct==DIRECTION_SHORT):
                    print  "如果没有开启delta增报单，所有delta增大的交易关闭"
                    return False
            elif self.riskOfGreeksWidget.downGreeksSwitch['delta'] == 'off':
                if (putOrCall==OPTION_CALL and direct==DIRECTION_SHORT) or (putOrCall==OPTION_PUT and direct==DIRECTION_LONG):
                    print  "如果没有开启delta减报单，所有delta减小的交易关闭"
                    return False

        # 判断gamma：
        if self.riskOfGreeksWidget.greeksSwitch['gamma'] == "on" and self.riskOfGreeksWidget.greeksSwitch['gamma'+self.chain.symbol]=="on":
            if self.riskOfGreeksWidget.upGreeksSwitch['gamma'] == 'off':
                if direct == DIRECTION_LONG:
                    print "如果没有开启gamma增报单，所有gamma增大的交易关闭"
                    return False
            elif self.riskOfGreeksWidget.downGreeksSwitch['gamma'] == 'off':
                if direct ==DIRECTION_SHORT:
                    print "如果没有开启gamma减报单，所有gamma减小的交易关闭"
                    return False
        # 判断vega：
        if self.riskOfGreeksWidget.greeksSwitch['vega'] == "on"  and self.riskOfGreeksWidget.greeksSwitch['vega'+self.chain.symbol]=="on":
            if self.riskOfGreeksWidget.upGreeksSwitch['vega'] == 'off':
                if direct == DIRECTION_LONG:
                    print "如果没有开启vega增报单，所有vega增大的交易关闭"
                    return False
            elif self.riskOfGreeksWidget.downGreeksSwitch['vega'] == 'off':
                if direct == DIRECTION_SHORT:
                    print "如果没有开启vega减报单，所有delta减小的交易关闭"
                    return False
        return True

    def cancelOrder(self,symbol,direct):
        """点击成off就撤单"""
        l = self.mainEngine.getAllWorkingOrders()
        for order in l:
            if symbol==order.symbol and order.direction==direct:
                req = VtCancelOrderReq()
                req.symbol = order.symbol
                req.exchange = order.exchange
                req.frontID = order.frontID
                req.sessionID = order.sessionID
                req.orderID = order.orderID
                self.mainEngine.cancelOrder(req, order.gatewayName)


    def initUi(self):
        """初始化界面"""
        portfolio = self.omEngine.portfolio
        self.horizontalHeader().setDefaultSectionSize(70)

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
            priceFormat = "%" + "." + str(option.remainDecimalPlaces) + "f"
            self.optionPriceFormat[option.symbol] = priceFormat

            self.firstBid[option.symbol]=False
            self.firstAsk[option.symbol] = False
            self.bookBidImpv[option.symbol]=0
            self.originalBookBidImpv[option.symbol]=0
            self.bidEntruthVolumn[option.symbol]=self.entrustVolumn
            self.bidTradedVolumn[option.symbol]=0
            self.bidStepPerVolumn[option.symbol]=self.stepPerVolumn
            self.bidImpvChange[option.symbol]=self.impvChange
            self.bidStepVolum[option.symbol]=self.stepVolumn

            self.bookAskImpv[option.symbol]=0
            self.askEntruthVolumn[option.symbol]=self.entrustVolumn
            self.askTradedVolumn[option.symbol] = 0
            self.askStepPerVolumn[option.symbol]=self.stepPerVolumn
            self.askImpvChange[option.symbol]=self.impvChange
            self.askStepVolum[option.symbol]=self.stepVolumn

            self.switchBidSymbol[option.symbol]='off'
            self.switchAskSymbol[option.symbol]='off'

            cellBidPrice = OmCell(str(priceFormat % option.bidPrice1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidImpv = OmCell('%.2f' % (option.bidImpv * 100), COLOR_BID, COLOR_BLACK, option, 10)
            cellBookBidImpv = OmCellEditText(self.bookBidImpv[option.symbol], 'impv', self.bookBidImpv,option.symbol)
            cellBidEntruthVolumn = OmCellEditText(self.bidEntruthVolumn[option.symbol],'volumn' , self.bidEntruthVolumn,option.symbol)
            cellBidTradedVolumn = OmCell(str(self.bidTradedVolumn[option.symbol]), COLOR_BID, COLOR_BLACK, option, 10)


            cellBidImpvChange = OmCellEditText(self.bidImpvChange[option.symbol], 'impv', self.bidImpvChange,option.symbol)
            cellBidStepPerVolumn = OmCellEditText(self.bidStepPerVolumn[option.symbol], 'volumn', self.bidStepPerVolumn,option.symbol)
            cellBidStepVolum = OmCellEditText(self.bidStepVolum[option.symbol], 'volumn', self.bidStepVolum,option.symbol)

            cellBidSwitch = OmCell(self.switchBidSymbol[option.symbol], COLOR_BID, COLOR_BLACK, option, 10)
            cellAskSwitch = OmCell(self.switchAskSymbol[option.symbol], COLOR_ASK, COLOR_BLACK, option, 10)

            cellAskPrice = OmCell(str(priceFormat % option.askPrice1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskImpv = OmCell('%.2f' % (option.askImpv * 100), COLOR_ASK, COLOR_BLACK, option, 10)
            cellBookAskImpv =OmCellEditText(self.bookAskImpv[option.symbol] , 'impv', self.bookAskImpv,option.symbol)
            cellAskEntruthVolumn =OmCellEditText(self.askEntruthVolumn[option.symbol] ,'volumn' , self.askEntruthVolumn,option.symbol)
            cellAskTradedVolumn = OmCell(str(self.askTradedVolumn[option.symbol]), COLOR_ASK, COLOR_BLACK, option, 10)

            cellAskImpvChange = OmCellEditText(self.askImpvChange[option.symbol], 'impv', self.askImpvChange,option.symbol)
            cellAskStepPerVolumn = OmCellEditText(self.askStepPerVolumn[option.symbol], 'volumn', self.askStepPerVolumn,option.symbol)
            cellAskStepVolum = OmCellEditText(self.askStepVolum[option.symbol], 'volumn', self.askStepVolum,option.symbol)
            cellNetPosVol = OmCell(str(option.netPos), COLOR_POS, COLOR_BLACK, option, 10)
            cellStrike = OmCell(str(option.k), COLOR_STRIKE)

            self.cellBidPrice[option.symbol] = cellBidPrice
            self.cellBidImpv[option.symbol] = cellBidImpv
            self.cellBookBidImpv[option.symbol] = cellBookBidImpv
            self.cellBidEntruthVolumn[option.symbol] = cellBidEntruthVolumn
            self.cellBidTradedVolumn[option.symbol] = cellBidTradedVolumn
            self.cellBidImpvChange[option.symbol] = cellBidImpvChange
            self.cellBidStepPerVolumn[option.symbol] = cellBidStepPerVolumn
            self.cellBidStepVolum[option.symbol] = cellBidStepVolum

            self.cellBidSwitch[option.symbol] = cellBidSwitch
            self.cellAskSwitch[option.symbol] = cellAskSwitch

            self.cellAskPrice[option.symbol] = cellAskPrice
            self.cellAskImpv[option.symbol] = cellAskImpv
            self.cellBookAskImpv[option.symbol] = cellBookAskImpv
            self.cellAskEntruthVolumn[option.symbol] = cellAskEntruthVolumn
            self.cellAskTradedVolumn[option.symbol] = cellAskTradedVolumn
            self.cellAskImpvChange[option.symbol] = cellAskImpvChange
            self.cellAskStepPerVolumn[option.symbol] = cellAskStepPerVolumn
            self.cellAskStepVolum[option.symbol] = cellAskStepVolum
            self.cellNetPosVol[option.symbol] = cellNetPosVol

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
            self.setItem(callRow, 16, cellNetPosVol)
            self.setItem(callRow, 17, cellStrike)
            callRow += 1
            # put
        putRow = row

        for option in self.chain.putDict.values():
            priceFormat = "%" + "." + str(option.remainDecimalPlaces) + "f"
            self.optionPriceFormat[option.symbol] = priceFormat
            self.firstBid[option.symbol] = False
            self.firstAsk[option.symbol] = False
            self.bookBidImpv[option.symbol] = 0
            self.originalBookAskImpv[option.symbol] = 0
            self.bidEntruthVolumn[option.symbol] = self.entrustVolumn
            self.bidTradedVolumn[option.symbol] = 0
            self.bidStepPerVolumn[option.symbol] = self.stepPerVolumn
            self.bidImpvChange[option.symbol] = self.impvChange
            self.bidStepVolum[option.symbol] = self.stepVolumn

            self.bookAskImpv[option.symbol] = 0
            self.askEntruthVolumn[option.symbol] = self.entrustVolumn
            self.askTradedVolumn[option.symbol] = 0
            self.askStepPerVolumn[option.symbol] = self.stepPerVolumn
            self.askImpvChange[option.symbol] = self.impvChange
            self.askStepVolum[option.symbol] = self.stepVolumn

            self.switchBidSymbol[option.symbol] = 'off'
            self.switchAskSymbol[option.symbol] = 'off'
            cellNetPosVol = OmCell(str(option.netPos), COLOR_POS, COLOR_BLACK, option, 10)
            cellBidPrice = OmCell(str(priceFormat % option.bidPrice1), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidImpv = OmCell('%.2f' % (option.bidImpv * 100), COLOR_BID, COLOR_BLACK, option, 10)
            cellBookBidImpv = OmCellEditText(self.bookBidImpv[option.symbol], 'impv', self.bookBidImpv,option.symbol)
            cellBidEntruthVolumn = OmCellEditText(self.bidEntruthVolumn[option.symbol], 'volumn', self.bidEntruthVolumn,option.symbol)
            cellBidTradedVolumn = OmCell(str(self.bidTradedVolumn[option.symbol]), COLOR_BID, COLOR_BLACK, option, 10)
            cellBidImpvChange = OmCellEditText(self.bidImpvChange[option.symbol], 'impv', self.bidImpvChange,option.symbol)
            cellBidStepPerVolumn = OmCellEditText(self.bidStepPerVolumn[option.symbol], 'volumn', self.bidStepPerVolumn,option.symbol)
            cellBidStepVolum = OmCellEditText(self.bidStepVolum[option.symbol], 'volumn', self.bidStepVolum,option.symbol)

            cellBidSwitch = OmCell(self.switchBidSymbol[option.symbol], COLOR_BID, COLOR_BLACK, option, 10)
            cellAskSwitch = OmCell(self.switchAskSymbol[option.symbol], COLOR_ASK, COLOR_BLACK, option, 10)

            cellAskPrice = OmCell(str(priceFormat % option.askPrice1), COLOR_ASK, COLOR_BLACK, option, 10)
            cellAskImpv = OmCell('%.2f' % (option.askImpv * 100), COLOR_ASK, COLOR_BLACK, option, 10)
            cellBookAskImpv = OmCellEditText(self.bookAskImpv[option.symbol], 'impv', self.bookAskImpv,option.symbol)
            cellAskEntruthVolumn = OmCellEditText(self.askEntruthVolumn[option.symbol], 'volumn', self.askEntruthVolumn,option.symbol)
            cellAskTradedVolumn = OmCell(str(self.askTradedVolumn[option.symbol]), COLOR_ASK, COLOR_BLACK, option, 10)

            cellAskImpvChange = OmCellEditText(self.askImpvChange[option.symbol], 'impv', self.askImpvChange,option.symbol)
            cellAskStepPerVolumn = OmCellEditText(self.askStepPerVolumn[option.symbol], 'volumn', self.askStepPerVolumn,option.symbol)
            cellAskStepVolum = OmCellEditText(self.askStepVolum[option.symbol], 'volumn', self.askStepVolum,option.symbol)

            self.cellNetPosVol[option.symbol] = cellNetPosVol
            self.cellBidPrice[option.symbol] = cellBidPrice
            self.cellBidImpv[option.symbol] = cellBidImpv
            self.cellBookBidImpv[option.symbol] = cellBookBidImpv
            self.cellBidEntruthVolumn[option.symbol] = cellBidEntruthVolumn
            self.cellBidTradedVolumn[option.symbol] = cellBidTradedVolumn

            self.cellBidImpvChange[option.symbol] = cellBidImpvChange
            self.cellBidStepPerVolumn[option.symbol] = cellBidStepPerVolumn
            self.cellBidStepVolum[option.symbol] = cellBidStepVolum

            self.cellBidSwitch[option.symbol] = cellBidSwitch
            self.cellAskSwitch[option.symbol] = cellAskSwitch

            self.cellAskPrice[option.symbol] = cellAskPrice
            self.cellAskImpv[option.symbol] = cellAskImpv
            self.cellBookAskImpv[option.symbol] = cellBookAskImpv
            self.cellAskEntruthVolumn[option.symbol] = cellAskEntruthVolumn
            self.cellAskTradedVolumn[option.symbol] = cellAskTradedVolumn

            self.cellAskImpvChange[option.symbol] = cellAskImpvChange
            self.cellAskStepPerVolumn[option.symbol] = cellAskStepPerVolumn
            self.cellAskStepVolum[option.symbol] = cellAskStepVolum

            self.setItem(putRow, 18, cellNetPosVol)
            self.setCellWidget(putRow, 19, cellAskImpvChange)
            self.setCellWidget(putRow, 20, cellAskStepPerVolumn)
            self.setCellWidget(putRow, 21, cellAskStepVolum)
            self.setCellWidget(putRow, 22, cellAskEntruthVolumn)
            self.setCellWidget(putRow, 23, cellBookAskImpv)
            self.setItem(putRow, 24, cellAskImpv)
            self.setItem(putRow, 25, cellAskPrice)

            self.setItem(putRow, 26, cellAskSwitch)
            self.setItem(putRow, 27, cellBidSwitch)

            self.setCellWidget(putRow, 28, cellBidImpvChange)
            self.setCellWidget(putRow, 29, cellBidStepPerVolumn)
            self.setCellWidget(putRow, 30, cellBidStepVolum)
            self.setCellWidget(putRow, 31, cellBidEntruthVolumn)
            self.setCellWidget(putRow, 32, cellBookBidImpv)
            self.setItem(putRow, 33, cellBidImpv)
            self.setItem(putRow, 34, cellBidPrice)

            putRow += 1
        row = putRow + 1

        for key,value in self.cellBidImpvChange.items():
            self.cellBookBidImpv[key].editingFinished.connect(self.modifyConfig)
            self.cellBidEntruthVolumn[key].editingFinished.connect(self.modifyConfig)
            self.cellBidStepPerVolumn[key].editingFinished.connect(self.modifyConfig)
            self.cellBidImpvChange[key].editingFinished.connect(self.modifyConfig)
            self.cellBidStepVolum[key].editingFinished.connect(self.modifyConfig)

            self.cellBookAskImpv[key].editingFinished.connect(self.modifyConfig)
            self.cellAskEntruthVolumn[key].editingFinished.connect(self.modifyConfig)
            self.cellAskStepPerVolumn[key].editingFinished.connect(self.modifyConfig)
            self.cellAskImpvChange[key].editingFinished.connect(self.modifyConfig)
            self.cellAskStepVolum[key].editingFinished.connect(self.modifyConfig)

    # ----------------------------------------------------------------------修改单个输入框
    def modifyConfig(self):
        print 'modifyConfig'
        editText = self.sender()
        double=editText.value()
        editText.data[editText.key]=double
        print self.bidStepVolum[editText.key]
        if editText in self.cellBookBidImpv.values():
            self.originalBookBidImpv[editText.key]=double
        elif editText in self.cellBookAskImpv.values():
            self.originalBookAskImpv[editText.key] = double

    # ----------------------------------------------------------------------整体修改设置
    def modifyConfigBatch(self,variable,double):
        print 'modifyConfigBatch'
        if variable=='EntruthVolumn':
            self.entrustVolum = double
            for key,value in self.cellAskEntruthVolumn.items():
                self.cellAskEntruthVolumn[key].setValue(double)
                self.cellBidEntruthVolumn[key].setValue(double)
                self.cellAskEntruthVolumn[key].data[key]=double
                self.cellBidEntruthVolumn[key].data[key]=double
        elif variable=='StepVolum':
            self.stepVolumn=double
            for key,value in self.cellBidStepVolum.items():
                self.cellBidStepVolum[key].setValue(double)
                self.cellAskStepVolum[key].setValue(double)
                self.cellBidStepVolum[key].data[key] = double
                self.cellAskStepVolum[key].data[key] = double
        elif variable == 'StepPerVolumn':
            self.stepPerVolumn=double
            for key, value in self.cellBidStepVolum.items():
                self.cellBidStepPerVolumn[key].setValue(double)
                self.cellAskStepPerVolumn[key].setValue(double)
                self.cellBidStepPerVolumn[key].data[key] = double
                self.cellAskStepPerVolumn[key].data[key] = double
        elif variable == 'ImpvChange':
            self.impvChange=double
            for key, value in self.cellBidStepVolum.items():
                self.cellAskImpvChange[key].setValue(double)
                self.cellBidImpvChange[key].setValue(double)
                self.cellAskImpvChange[key].data[key] = double
                self.cellBidImpvChange[key].data[key] = double
        elif variable == 'ImpvDown':
            self.impvUp=double
            for key, value in self.cellBidStepVolum.items():
                self.originalBookBidImpv[key]=(self.chain.optionDict[key].bidImpv*100+self.chain.optionDict[key].askImpv*100)/2-double
                self.cellBookBidImpv[key].setValue(self.originalBookBidImpv[key])
                self.cellBookBidImpv[key].data[key] = self.originalBookBidImpv[key]

        elif variable == 'ImpvUp':
            self.impvDown = double
            for key, value in self.cellBidStepVolum.items():
                self.originalBookAskImpv[key]=(self.chain.optionDict[key].bidImpv*100+self.chain.optionDict[key].askImpv*100)/2+double
                self.cellBookAskImpv[key].setValue(self.originalBookAskImpv[key])
                self.cellBookAskImpv[key].data[key] = self.originalBookAskImpv[key]

    # ----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signalTick.connect(self.processTickEvent)
        self.signalTrade.connect(self.processTradeEvent)
        portfolio = self.omEngine.portfolio
        for option in self.chain.optionDict.values():
            self.eventEngine.register(EVENT_TICK + option.vtSymbol, self.signalTick.emit)
            self.eventEngine.register(EVENT_TRADE + option.vtSymbol, self.signalTrade.emit)

        self.eventEngine.register(EVENT_TICK + self.chain.underlying.vtSymbol, self.signalTick.emit)



    # ----------------------------------------------------------------------
    def processTickEvent(self, event):
        """行情更新"""
        tick = event.dict_['data']
        symbol = tick.symbol

        if symbol==self.chain.underlying.symbol:
            return

        if symbol in self.cellBidImpv:
            option = self.instrumentDict[symbol]
            self.cellBidImpv[symbol].setText('%.2f' % (option.bidImpv * 100))
            self.cellAskImpv[symbol].setText('%.2f' % (option.askImpv * 100))

        self.cellBidPrice[symbol].setText(self.optionPriceFormat[symbol]% tick.bidPrice1)
        self.cellAskPrice[symbol].setText(self.optionPriceFormat[symbol] % tick.askPrice1)

        if symbol in self.onBidSymbol:
            if self.firstBid[symbol]:
                # t = Timer(0.4, self.tickSendOrder, (symbol, DIRECTION_LONG))
                self.firstBid[symbol] = False
                # t.start()
            else:
                greekControl = self.judgeGreeksConfig(symbol, DIRECTION_LONG)
                if greekControl:
                    self.tickSendOrder(symbol, DIRECTION_LONG)
        elif symbol in self.onAskSymbol:
            if self.firstAsk[symbol]:
                # t=Timer(0.4,self.tickSendOrder,(symbol, DIRECTION_SHORT))
                self.firstAsk[symbol] = False
                # t.start()
            else:
                greekControl = self.judgeGreeksConfig(symbol, DIRECTION_SHORT)
                if greekControl:
                    self.tickSendOrder(symbol, DIRECTION_SHORT)
    # ----------------------------------------------------------------------
    def processTradeEvent(self, event):
        """成交更新"""
        trade = event.dict_['data']

        symbol = trade.symbol
        instrument = self.instrumentDict[symbol]

        if trade.direction==DIRECTION_LONG:
            # if  trade.symbol not in self.onBidSymbol:
            #     return
            self.bidTradedVolumn[trade.symbol]+= trade.volume
            #每次成交以后需要更改波动率阈值,以便下次委托
            # print "成交量"+str(self.bidTradedVolumn[trade.symbol])
            # print '原始值'+str(self.originalBookBidImpv[trade.symbol])
            # print "改变量"+str(self.originalBookBidImpv[trade.symbol]-(self.bidTradedVolumn[trade.symbol]//self.bidStepPerVolumn[trade.symbol])*self.bidImpvChange[trade.symbol])
            self.bookBidImpv[trade.symbol]=self.originalBookBidImpv[trade.symbol]-self.bidTradedVolumn[trade.symbol]//self.bidStepPerVolumn[trade.symbol]*self.bidImpvChange[trade.symbol]
            self.cellBookBidImpv[trade.symbol].setValue(self.bookBidImpv[trade.symbol])
            #如果该symbol在self.onBidSymbol里面，switchBidSymbol[option.symbol]='on'的时候才更新页面
            #if trade.symbol in self.onBidSymbol:
            self.cellBidEntruthVolumn[trade.symbol].setValue(self.bidEntruthVolumn[trade.symbol]-self.bidTradedVolumn[trade.symbol])

            #如果总成交量大于总委托量，那么设置成off，并且更新页面
            if self.bidTradedVolumn[trade.symbol]>=self.bidEntruthVolumn[trade.symbol]:
                self.switchBidSymbol[trade.symbol] = 'off'
                self.cellBidSwitch[trade.symbol].setText('off')
                self.onBidSymbol.remove(trade.symbol)

        elif trade.direction== DIRECTION_SHORT:
            # if  trade.symbol not in self.onAskSymbol:
            #     return
            self.askTradedVolumn[trade.symbol]+=trade.volume

            self.bookAskImpv[trade.symbol] = self.originalBookAskImpv[trade.symbol]+self.askTradedVolumn[trade.symbol] // self.askStepPerVolumn[trade.symbol] * self.askImpvChange[trade.symbol]
            self.cellBookAskImpv[trade.symbol].setValue(self.bookAskImpv[trade.symbol])
            # 如果该symbol在self.onAskSymbol里面，switchAskSymbol[option.symbol]='on'的时候才更新页面
            #if trade.symbol in self.onAskSymbol:
            self.cellAskEntruthVolumn[trade.symbol].setValue(self.askEntruthVolumn[trade.symbol] - self.askTradedVolumn[trade.symbol])

            # 如果总成交量大于总委托量，那么设置成off，并且更新页面
            if self.askTradedVolumn[trade.symbol]>=self.askEntruthVolumn[trade.symbol]:
                self.switchAskSymbol[trade.symbol] = 'off'
                self.cellAskSwitch[trade.symbol].setText('off')
                self.onAskSymbol.remove(trade.symbol)

    # ----------------------------------------------------------------------根据symbol来查询合约委托量
    def calcutateOrderBySymbol(self):
        """根据symbol来查询合约委托量"""
        return self.mainEngine.calcutateOrderBySymbol()

    # ----------------------------------------------------------------------封装下单函数
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
        self.masterSwitch = False

        self.omEngine = omEngine
        self.mainEngine = omEngine.mainEngine
        self.eventEngine = omEngine.eventEngine

        self.deltaControl = False
        self.gammaControl = False
        self.vegaControl = False
        #卖逻辑：卖开，卖平
        self.shortDirection=OFFSET_OPEN

        #是否开启现货对冲
        self.underlyingHedging=False

        self.tradingWidget = {}
        self.chainMonitorAarry = []
        self.bookImpvConfig = {}
        self.loadJsonConfig()
        self.totalVolumn = 2
        self.stepVolumn = 1
        self.impvUp = 0.05
        self.impvDown = 0.05
        self.impvChange=0.1
        self.stepPerVolumn = 1
        self.initUi()
        self.setMinimumWidth(1450)
    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'波动率报单')

        tab = QtWidgets.QTabWidget()
        riskOfGreeksWidget = RiskOfGreeksWidget(self.omEngine, self.mainEngine, self.eventEngine, self)
        for chain in self.omEngine.portfolio.chainDict.values():
            chainMonitor = BookChainMonitor(chain, self.omEngine, self.mainEngine, self.eventEngine,self.bookImpvConfig,riskOfGreeksWidget,self)
            self.chainMonitorAarry.append(chainMonitor)
            tab.addTab(chainMonitor, chain.symbol)

        vbox = QtWidgets.QVBoxLayout()

        vbox = QtWidgets.QVBoxLayout()
        vhboxButtons = QtWidgets.QHBoxLayout()

        checkBox = QtWidgets.QCheckBox(u'波动率开关')
        checkBox.setChecked(self.masterSwitch)
        checkBox.setFixedWidth(120)
        checkBox.clicked.connect(self.changeMasterControl)

        underlyingHedgingCheckBox = QtWidgets.QCheckBox(u'现货对冲')
        underlyingHedgingCheckBox.setChecked(self.underlyingHedging)
        underlyingHedgingCheckBox.setFixedWidth(120)
        underlyingHedgingCheckBox.clicked.connect(self.changeUnderlyingHedging)


        btnRestore = QtWidgets.QPushButton(u'数据还原')
        btnRestore.setFixedWidth(100)
        btnRestore.clicked.connect(self.dataRestore)

        vhboxButtons.addWidget(checkBox)
        vhboxButtons.addWidget(underlyingHedgingCheckBox)
        vhboxButtons.addWidget(btnRestore)
        vhboxButtons.addStretch()

        vhboxConfig= QtWidgets.QHBoxLayout()
        labelTotal = QtWidgets.QLabel(u'总量')

        editTotal = QtWidgets.QDoubleSpinBox()
        editTotal.setDecimals(0)
        editTotal.setMinimum(0)
        editTotal.setMaximum(100)
        editTotal.setValue(self.totalVolumn)
        editTotal.variable = 'EntruthVolumn'
        editTotal.valueChanged.connect(self.modifyConfigBatch)

        labelStep = QtWidgets.QLabel(u'单次')

        editStep = QtWidgets.QDoubleSpinBox()
        editStep.setDecimals(0)
        editStep.setMinimum(0)
        editStep.setMaximum(30)
        editStep.variable = 'StepVolum'
        editStep.setValue(self.stepVolumn)
        editStep.valueChanged.connect(self.modifyConfigBatch)

        labelUp = QtWidgets.QLabel(u'上移')

        editUp = QtWidgets.QDoubleSpinBox()
        editUp.setDecimals(2)
        editUp.setMinimum(0)
        editUp.setMaximum(100)
        editUp.variable = 'ImpvUp'
        editUp.setSingleStep(0.01)
        editUp.setValue(self.impvUp)
        editUp.valueChanged.connect(self.modifyConfigBatch)

        labelDown = QtWidgets.QLabel(u'下移')

        editDown = QtWidgets.QDoubleSpinBox()
        editDown.setDecimals(2)
        editDown.setMinimum(0)
        editDown.setMaximum(100)
        editDown.variable = 'ImpvDown'
        editDown.setSingleStep(0.01)
        editDown.setValue(self.impvDown)
        editDown.valueChanged.connect(self.modifyConfigBatch)

        labelImpvChange = QtWidgets.QLabel(u'波动率增减')

        editImpvChange = QtWidgets.QDoubleSpinBox()
        editImpvChange.setDecimals(2)
        editImpvChange.setMinimum(0)
        editImpvChange.variable = 'ImpvChange'
        editImpvChange.setMaximum(100)
        editImpvChange.setSingleStep(0.01)
        editImpvChange.setValue(self.impvChange)
        editImpvChange.valueChanged.connect(self.modifyConfigBatch)

        labelPerStep = QtWidgets.QLabel(u'per成交量')

        editPerStep = QtWidgets.QDoubleSpinBox()
        editPerStep.setDecimals(0)
        editPerStep.setMinimum(0)
        editPerStep.setMaximum(100)
        editPerStep.variable = 'StepPerVolumn'
        editPerStep.setValue(self.stepPerVolumn)
        editPerStep.valueChanged.connect(self.modifyConfigBatch)

        # 卖开逻辑问题，加一个卖开选项来开关卖开还是卖平，如果选择打开卖开选项，则不管是否有多头仓位都选择卖开，如果关掉卖开选项，则按正常逻辑卖平卖开
        shortDirectionHorizontalLayoutWidget = QtWidgets.QHBoxLayout()
        shortOpenRadio = QtWidgets.QRadioButton(u"卖开")
        shortOpenRadio.setChecked(True)
        shortCloseRadio = QtWidgets.QRadioButton(u"卖平")
        shortDirectionHorizontalLayoutWidget.addWidget(shortOpenRadio)
        shortDirectionHorizontalLayoutWidget.addWidget(shortCloseRadio)
        shortOpenRadio.clicked.connect(self.changeShortDirectionToOFFSET_OPEN)
        shortCloseRadio.clicked.connect(self.changeShortDirectionToOFFSET_CLOSE)

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
        vhboxConfig.addLayout(shortDirectionHorizontalLayoutWidget)
        vhboxConfig.addStretch()


        vbox.addLayout(vhboxButtons)
        vbox.addLayout(vhboxConfig)
        vbox.addWidget(riskOfGreeksWidget)

        vbox.addWidget(tab)
        tab.setMovable(True)
        self.setLayout(vbox)

    # ----------------------------------------------------------------------
    def switchDirection(self,direct,switch):
        """希腊值控制开关,比如delta设定在某一范围内，如果当前delta低于设定值，那么需要停止一些委托，如果高于设定值，那么需要停止另外一些委托"""
        if direct==DIRECTION_LONG:
            for chain in self.chainMonitorAarry:
                pass
        elif direct==DIRECTION_SHORT:
            for chain in self.chainMonitorAarry:
                pass

    def changeShortDirectionToOFFSET_OPEN(self,isChecked):
        print OFFSET_OPEN
        self.shortDirection=OFFSET_OPEN

    def changeShortDirectionToOFFSET_CLOSE(self,isChecked):
        print OFFSET_CLOSE
        self.shortDirection=OFFSET_CLOSE

    def changeMasterControl(self, isChecked):
        print "masterSwitch"
        print isChecked
        self.masterSwitch=isChecked
        if not isChecked:
            self.cancelAll()
            print "全撤成功"

    def changeUnderlyingHedging(self, isChecked):
        self.underlyingHedging=isChecked


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


    def modifyConfigBatch(self,double):
        editText=self.sender()
        variable=editText.variable
        for chain in self.chainMonitorAarry:
            chain.modifyConfigBatch(variable,double)


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
        self.parentWidget=parent

        self.cellTargetValue={}
        self.cellDownDeviationValue = {}
        self.cellUpDeviationValue={}
        self.cellGreeksSwitch={}

        for chainkey in self.omEngine.portfolio.chainDict.keys():
            self.headers.append(chainkey)

        for row, underlying in enumerate(self.omEngine.portfolio.underlyingDict.values()):
            self.underlying = underlying
            self.eventEngine.register(EVENT_TICK + underlying.vtSymbol, self.processTickEvent)
            break

        # 希腊值总开关,on off 按钮!默认不控制
        self.deltaControl=False
        self.gammaControl = False
        self.vegaControl = False

        # Greeks 总开关
        self.greeksSwitch={}
        self.greeksSwitch['delta']='off'
        self.greeksSwitch['gamma'] = 'off'
        self.greeksSwitch['vega'] = 'off'

        # Greeks on，交易，off，不交易
        self.upGreeksSwitch = {}
        self.upGreeksSwitch['delta'] = 'on'
        self.upGreeksSwitch['gamma'] = 'on'
        self.upGreeksSwitch['vega'] = 'on'

        # Greeks on，交易，off，不交易
        self.downGreeksSwitch = {}
        self.downGreeksSwitch['delta'] = 'on'
        self.downGreeksSwitch['gamma'] = 'on'
        self.downGreeksSwitch['vega'] = 'on'

        # 最小值
        self.downDeviationValue={}
        self.downDeviationValue['delta'] = 0
        self.downDeviationValue['gamma'] = 0
        self.downDeviationValue['vega'] = 0
        # 目标值
        self.targetValue={}
        self.targetValue['delta'] = 0
        self.targetValue['gamma'] = 0
        self.targetValue['vega'] = 0

        #  最大值
        self.upDeviationValue = {}
        self.upDeviationValue['delta'] = 0
        self.upDeviationValue['gamma'] = 0
        self.upDeviationValue['vega'] = 0

        self.posDelta=self.portfolio.posDelta

        self.initUi()
        self.itemClicked.connect(self.switchDownAndUp)
        self.eventEngine.register(EVENT_TIMER, self.timingChange)

    # ----------------------------------------------------------------------
    #现货或者标的物行情返回，用于现货对冲判断!
    def processTickEvent(self, event):
        """行情更新，价格列表,五档数据"""
        tick = event.dict_['data']
        if not self.parentWidget.underlyingHedging or not self.parentWidget.masterSwitch:
            print '现货对冲没开或者没开启波动率报单'
            return

        # 单向delta减报单
        if self.greeksSwitch['delta'] == 'on' and self.upGreeksSwitch['delta'] == 'off' and self.downGreeksSwitch['delta'] == 'on':
            # 获得当前时间各个合约的委托量和委托价格，用来判断是否还需要继续发送委托和撤单！！
            longVolumeDic, shortVolumeDic, longPriceDic, shortPriceDic = self.calcutateOrderBySymbol()
            if tick.symbol in longVolumeDic.keys() or tick.symbol in shortVolumeDic.keys():
                print '目前现货有未成交的委托'
                return

            req = VtOrderReq()
            contract = self.mainEngine.getContract(tick.vtSymbol)
            req.symbol = tick.symbol
            req.exchange = contract.exchange
            req.vtSymbol = tick.vtSymbol
            req.price = tick.bidPrice1
            if req.symbol=='510050':
                req.volume = 10000
            else:
                req.volume = 1
            req.direction = DIRECTION_SHORT
            req.priceType = PRICETYPE_LIMITPRICE
            req.offset = OFFSET_OPEN
            self.mainEngine.sendOrder(req, contract.gatewayName)

        # 单向delta增报单
        elif self.greeksSwitch['delta'] == 'on' and self.upGreeksSwitch['delta'] == 'on' and self.downGreeksSwitch['delta'] == 'off':
            # 获得当前时间各个合约的委托量和委托价格，用来判断是否还需要继续发送委托和撤单！！
            longVolumeDic, shortVolumeDic, longPriceDic, shortPriceDic = self.calcutateOrderBySymbol()
            if tick.symbol in longVolumeDic.keys() or tick.symbol in shortVolumeDic.keys():
                print '目前现货有未成交的委托'
                return
            req = VtOrderReq()
            contract = self.mainEngine.getContract(tick.vtSymbol)
            req.symbol = tick.symbol
            req.exchange = contract.exchange
            req.vtSymbol = tick.vtSymbol
            req.price = tick.askPrice1
            if req.symbol=='510050':
                req.volume = 10000
            else:
                req.volume = 1
            req.direction = DIRECTION_LONG
            req.priceType = PRICETYPE_LIMITPRICE
            req.offset = OFFSET_OPEN
            self.mainEngine.sendOrder(req, contract.gatewayName)




    # ----------------------------------------------------------------------根据symbol来查询合约委托量
    def calcutateOrderBySymbol(self):
        """根据symbol来查询合约委托量"""
        return self.mainEngine.calcutateOrderBySymbol()

    def switchDownAndUp(self,item):
        if item in self.cellGreeksSwitch.values():
            if self.greeksSwitch[item.data]=='off':
                self.greeksSwitch[item.data]='on'
            elif self.greeksSwitch[item.data]=='on':
                self.greeksSwitch[item.data]='off'
            item.setText(self.greeksSwitch[item.data])

    def timingChange(self,event):
        self.posDelta = self.portfolio.posDelta
        if self.greeksSwitch['delta'] == 'on':
            #如果之前是单向delta减报单
            if  self.upGreeksSwitch['delta']=='off' and self.downGreeksSwitch['delta'] == 'on':
                #实时delta变化到目标值和最小值之间，开启双向报单
                if self.downDeviationValue['delta']<self.posDelta<self.targetValue['delta']:
                    self.upGreeksSwitch['delta'] = 'on'
                    self.downGreeksSwitch['delta'] = 'on'
                #实时delta小于最小值,单向增报单
                elif self.posDelta<self.downDeviationValue['delta']:
                    self.upGreeksSwitch['delta'] = 'on'
                    self.downGreeksSwitch['delta'] = 'off'
            # 如果之前是单向delta增报单
            elif self.upGreeksSwitch['delta'] == 'on' and self.downGreeksSwitch['delta'] == 'off':
                # 实时delta变化到目标值和最大值之间，开启双向报单
                if self.upDeviationValue['delta'] > self.posDelta > self.targetValue['delta']:
                    self.upGreeksSwitch['delta'] = 'on'
                    self.downGreeksSwitch['delta'] = 'on'
                # 实时delta大于最大值,单向减报单
                elif self.posDelta > self.upDeviationValue['delta']:
                    self.upGreeksSwitch['delta'] = 'off'
                    self.downGreeksSwitch['delta'] = 'on'
            # 如果之前是双向报单
            elif self.upGreeksSwitch['delta'] == 'on' and self.downGreeksSwitch['delta'] == 'on':
                # 实时delta大于最大值,单向减报单
                if self.posDelta>self.upDeviationValue['delta'] :
                    self.upGreeksSwitch['delta'] = 'off'
                    self.downGreeksSwitch['delta'] = 'on'
                # 实时delta小于最小值,单向增报单
                elif self.posDelta < self.downDeviationValue['delta']:
                    self.upGreeksSwitch['delta'] = 'on'
                    self.downGreeksSwitch['delta'] = 'off'

        if self.greeksSwitch['gamma'] == 'on':
            # 如果之前是单向gamma减报单
            if self.upGreeksSwitch['gamma'] == 'off' and self.downGreeksSwitch['gamma'] == 'on':
                # 实时gamma变化到目标值和最小值之间，开启双向报单
                if self.downDeviationValue['gamma'] < self.portfolio.posgamma < self.targetValue['gamma']:
                    self.upGreeksSwitch['gamma'] = 'on'
                    self.downGreeksSwitch['gamma'] = 'on'
                # 实时gamma小于最小值,单向增报单
                elif self.portfolio.posgamma < self.downDeviationValue['gamma']:
                    self.upGreeksSwitch['gamma'] = 'on'
                    self.downGreeksSwitch['gamma'] = 'off'
            # 如果之前是单向gamma增报单
            elif self.upGreeksSwitch['gamma'] == 'on' and self.downGreeksSwitch['gamma'] == 'off':
                # 实时gamma变化到目标值和最大值之间，开启双向报单
                if self.upDeviationValue['gamma'] > self.portfolio.posgamma >  self.targetValue['gamma']:
                    self.upGreeksSwitch['gamma'] = 'on'
                    self.downGreeksSwitch['gamma'] = 'on'
                # 实时gamma大于最大值,单向减报单
                elif self.portfolio.posgamma >self.upDeviationValue['gamma']:
                    self.upGreeksSwitch['gamma'] = 'off'
                    self.downGreeksSwitch['gamma'] = 'on'
            # 如果之前是双向报单
            elif self.upGreeksSwitch['gamma'] == 'on' and self.downGreeksSwitch['gamma'] == 'on':
                # 实时gamma大于最大值,单向减报单
                if self.portfolio.posgamma > self.upDeviationValue['gamma']:
                    self.upGreeksSwitch['gamma'] = 'off'
                    self.downGreeksSwitch['gamma'] = 'on'
                # 实时gamma小于最小值,单向增报单
                elif self.portfolio.posgamma <  self.downDeviationValue['gamma']:
                    self.upGreeksSwitch['gamma'] = 'on'
                    self.downGreeksSwitch['gamma'] = 'off'

        if self.greeksSwitch['vega'] == 'on':
            # 如果之前是单向vega减报单
            if self.upGreeksSwitch['vega'] == 'off' and self.downGreeksSwitch['vega'] == 'on':
                # 实时vega变化到目标值和最小值之间，开启双向报单
                if self.downDeviationValue['vega'] < self.portfolio.posvega < self.targetValue['vega']:
                    self.upGreeksSwitch['vega'] = 'on'
                    self.downGreeksSwitch['vega'] = 'on'
                # 实时vega小于最小值,单向增报单
                elif self.portfolio.posvega < self.downDeviationValue['vega']:
                    self.upGreeksSwitch['vega'] = 'on'
                    self.downGreeksSwitch['vega'] = 'off'
            # 如果之前是单向vega增报单
            elif self.upGreeksSwitch['vega'] == 'on' and self.downGreeksSwitch['vega'] == 'off':
                # 实时vega变化到目标值和最大值之间，开启双向报单
                if self.upDeviationValue['vega'] > self.portfolio.posvega > self.targetValue['vega']:
                    self.upGreeksSwitch['vega'] = 'on'
                    self.downGreeksSwitch['vega'] = 'on'
                # 实时vega大于最大值,单向减报单
                elif self.portfolio.posvega > self.upDeviationValue['vega']:
                    self.upGreeksSwitch['vega'] = 'off'
                    self.downGreeksSwitch['vega'] = 'on'
            # 如果之前是双向报单
            elif self.upGreeksSwitch['vega'] == 'on' and self.downGreeksSwitch['vega'] == 'on':
                # 实时vega大于最大值,单向减报单
                if self.portfolio.posvega >  self.upDeviationValue['vega']:
                    self.upGreeksSwitch['vega'] = 'off'
                    self.downGreeksSwitch['vega'] = 'on'
                # 实时vega小于最小值,单向增报单
                elif self.portfolio.posvega < self.downDeviationValue['vega']:
                    self.upGreeksSwitch['vega'] = 'on'
                    self.downGreeksSwitch['vega'] = 'off'

        self.parentWidget.deltaControl = self.deltaControl
        self.parentWidget.gammaControl = self.gammaControl
        self.parentWidget.vegaControl = self.vegaControl

        self.totalCellGamma.setText(str(self.portfolio.posGamma))
        self.totalCellDelta.setText(str(self.posDelta))
        self.totalCellVega.setText(str(self.portfolio.posVega))

    def initUi(self):
        """初始化界面"""
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
        self.totalCellDelta= OmCell(str(self.posDelta), None, COLOR_POS)
        self.totalCellVega = OmCell(str(self.portfolio.posVega), None, COLOR_POS)

        self.setItem(0, 1, self.totalCellDelta)
        self.setItem(1, 1, self.totalCellGamma )
        self.setItem(2, 1, self.totalCellVega)

        self.cellGreeksSwitch["delta"]=OmCell(self.greeksSwitch['delta'], None, COLOR_POS, 'delta')
        self.cellGreeksSwitch["gamma"] = OmCell(self.greeksSwitch['gamma'], None, COLOR_POS, 'gamma')
        self.cellGreeksSwitch["vega"] = OmCell(self.greeksSwitch['vega'], None, COLOR_POS, 'vega')
        self.setItem(0, 2,self.cellGreeksSwitch["delta"])
        self.setItem(1, 2, self.cellGreeksSwitch["gamma"])
        self.setItem(2, 2,self.cellGreeksSwitch["vega"])

        self.cellDownDeviationValue['delta']=OmCellEditText(str(self.downDeviationValue['delta']),'decimals',self.downDeviationValue,'delta')
        self.cellDownDeviationValue['gamma']=OmCellEditText(str(self.downDeviationValue['gamma']),'decimals',self.downDeviationValue,'gamma')
        self.cellDownDeviationValue['vega']=OmCellEditText(str(self.downDeviationValue['vega']),'decimals',self.downDeviationValue,'vega')
        self.setCellWidget(0, 3,self.cellDownDeviationValue['delta'])
        self.setCellWidget(1, 3, self.cellDownDeviationValue['gamma'])
        self.setCellWidget(2, 3,self.cellDownDeviationValue['vega'])

        self.cellTargetValue['delta'] =OmCellEditText(str(self.targetValue['delta']),'decimals',self.targetValue,'delta')
        self.cellTargetValue['gamma'] =OmCellEditText(str(self.targetValue['gamma']),'decimals',self.targetValue,'gamma')
        self.cellTargetValue['vega'] =OmCellEditText(str(self.targetValue['vega']),'decimals',self.targetValue,'vega')

        self.setCellWidget(0, 4, self.cellTargetValue['delta'])
        self.setCellWidget(1, 4,self.cellTargetValue['gamma'])
        self.setCellWidget(2, 4,self.cellTargetValue['vega'])

        self.cellUpDeviationValue['delta'] = OmCellEditText(str(self.upDeviationValue['delta']), 'decimals',self.upDeviationValue,'delta')
        self.cellUpDeviationValue['gamma'] = OmCellEditText(str(self.upDeviationValue['gamma']), 'decimals',self.upDeviationValue,'gamma')
        self.cellUpDeviationValue['vega'] = OmCellEditText(str(self.upDeviationValue['vega']), 'decimals',self.upDeviationValue,'vega')

        self.setCellWidget(0, 5,self.cellUpDeviationValue['delta'] )
        self.setCellWidget(1, 5, self.cellUpDeviationValue['gamma'] )
        self.setCellWidget(2, 5, self.cellUpDeviationValue['vega'] )

        for row,chain in enumerate(self.omEngine.portfolio.chainDict.values()):
            self.greeksSwitch['delta' + chain.symbol]='off'
            self.greeksSwitch['gamma' + chain.symbol]='off'
            self.greeksSwitch['vega' + chain.symbol]='off'

            self.cellGreeksSwitch["delta"+chain.symbol] = OmCell(self.greeksSwitch['delta'+chain.symbol], None, COLOR_POS, 'delta'+chain.symbol)
            self.cellGreeksSwitch["gamma"+chain.symbol] = OmCell(self.greeksSwitch['gamma'+chain.symbol], None, COLOR_POS, 'gamma'+chain.symbol)
            self.cellGreeksSwitch["vega"+chain.symbol] = OmCell(self.greeksSwitch['vega'+chain.symbol], None, COLOR_POS, 'vega'+chain.symbol)
            self.setItem(0, 6+row, self.cellGreeksSwitch["delta"+chain.symbol])
            self.setItem(1, 6+row, self.cellGreeksSwitch["gamma"+chain.symbol])
            self.setItem(2, 6+row, self.cellGreeksSwitch["vega"+chain.symbol])


        for key,value in self.cellDownDeviationValue.items():
            self.cellDownDeviationValue[key].valueChanged.connect(self.modifyConfig)
            self.cellTargetValue[key].valueChanged.connect(self.modifyConfig)
            self.cellUpDeviationValue[key].valueChanged.connect(self.modifyConfig)

    def modifyConfig(self,double):
        editText=self.sender()
        editText.data[editText.key]=double

        if editText.key=='delta':
            positionTarget=self.posDelta
        elif editText.key=='gamma':
            positionTarget = self.portfolio.posGamma
        else:
            positionTarget = self.portfolio.posVega


        if positionTarget>self.upDeviationValue[editText.key]:
            print editText.key
            print '突破上限了'
            self.upGreeksSwitch[editText.key]='off'
            self.downGreeksSwitch[editText.key] = 'on'
        elif positionTarget<self.downDeviationValue[editText.key]:
            print editText.key
            print '跌破下限了'
            self.upGreeksSwitch[editText.key] = 'on'
            self.downGreeksSwitch[editText.key] = 'off'
        else:
            print editText.key
            print '在中间'
            self.upGreeksSwitch[editText.key] = 'on'
            self.downGreeksSwitch[editText.key] = 'on'


