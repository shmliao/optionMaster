# encoding: UTF-8

from __future__ import division

from copy import copy
from collections import OrderedDict

from vnpy.trader.vtConstant import *
from vnpy.trader.vtObject import VtTickData
from vnpy.trader.vtEvent import EVENT_TIMER, EVENT_TRADE, EVENT_ORDER

from .omDate import getTimeToMaturity,ANNUAL_TRADINGDAYS
from math import (log, pow, sqrt, exp)
import time

# 常量定义
CALL = 1
PUT = -1

# 事件定义
EVENT_OM_LOG = 'eOmLog'


########################################################################
class OmInstrument(VtTickData):
    """交易合约对象"""

    #----------------------------------------------------------------------
    def __init__(self, contract, detail):
        """Constructor"""
        super(OmInstrument, self).__init__()

        self.tickInited = False

        # 初始化合约信息
        self.symbol = contract.symbol
        self.exchange = contract.exchange
        self.vtSymbol = contract.vtSymbol

        self.size = contract.size
        self.priceTick = contract.priceTick

        # 小数点位数保留
        self.remainDecimalPlaces=int(len(str(self.priceTick)))-2

        if self.remainDecimalPlaces<0:
            self.remainDecimalPlaces=0

        self.gatewayName = contract.gatewayName

        # 中间价
        self.midPrice = EMPTY_FLOAT

        # 持仓数据
        self.longPos = 0
        self.shortPos = 0
        self.netPos = 0

        # 交易数据
        self.longTrade = 0
        self.shortTrade = 0

        if detail:
            self.longPos = detail.longPos
            self.shortPos = detail.shortPos
            self.netPos = self.longPos - self.shortPos
    #----------------------------------------------------------------------
    def newTick(self, tick):
        """行情更新"""
        if not self.tickInited:
            self.date = tick.date
            self.openPrice = tick.openPrice
            self.preClosePrice=tick.preClosePrice
            self.upperLimit = tick.upperLimit
            self.lowerLimit = tick.lowerLimit
            self.tickInited = True

        self.lastPrice = tick.lastPrice
        self.volume = tick.volume
        self.openInterest = tick.openInterest
        self.time = tick.time

        self.bidPrice1 = tick.bidPrice1
        self.askPrice1 = tick.askPrice1
        self.bidVolume1 = tick.bidVolume1
        self.askVolume1 = tick.askVolume1
        self.midPrice = (self.bidPrice1 + self.askPrice1) / 2

        self.bidPrice2 =tick.bidPrice2
        self.bidPrice3 =tick.bidPrice3
        self.bidPrice4 =tick.bidPrice4
        self.bidPrice5 =tick.bidPrice5

        self.askPrice2 =tick.askPrice2
        self.askPrice3 =tick.askPrice3
        self.askPrice4 =tick.askPrice4
        self.askPrice5 =tick.askPrice5

        self.bidVolume2 =tick.bidVolume2
        self.bidVolume3 =tick.bidVolume3
        self.bidVolume4 =tick.bidVolume4
        self.bidVolume5 =tick.bidVolume5

        self.askVolume2 =tick.askVolume2
        self.askVolume3 =tick.askVolume3
        self.askVolume4 =tick.askVolume4
        self.askVolume5 =tick.askVolume5

    #----------------------------------------------------------------------
    def newTrade(self, trade):
        """成交更新"""
        if trade.direction is DIRECTION_LONG:
            self.longTrade+= trade.volume
            if trade.offset is OFFSET_OPEN:
                self.longPos += trade.volume
            else:
                self.shortPos -= trade.volume
        else:
            self.shortTrade+= trade.volume
            if trade.offset is OFFSET_OPEN:
                self.shortPos += trade.volume
            else:
                self.longPos -= trade.volume

        self.calculateNetPos()

    #----------------------------------------------------------------------
    def calculateNetPos(self):
        """计算净持仓"""
        newNetPos = self.longPos - self.shortPos

        # 检查净持仓是否发生变化
        if newNetPos != self.netPos:
            netPosChanged = True
            self.netPos = newNetPos
        else:
            netPosChanged = False

        return netPosChanged


########################################################################
class OmUnderlying(OmInstrument):
    """标的物"""

    #----------------------------------------------------------------------
    def __init__(self, contract, detail, chainList=None):
        """Constructor"""
        super(OmUnderlying, self).__init__(contract, detail)

        # 以该合约为标的物的期权链字典
        self.chainDict = OrderedDict()

        # 希腊值
        self.theoDelta = EMPTY_FLOAT    # 理论delta值
        self.posDelta = EMPTY_FLOAT     # 持仓delta值

        self.callVolume=EMPTY_FLOAT
        self.putVolume = EMPTY_FLOAT
        self.callPostion = EMPTY_FLOAT
        self.putPostion = EMPTY_FLOAT

    #----------------------------------------------------------------------
    def addChain(self, chain):
        """添加以该合约为标的的期权链"""
        self.chainDict[chain.symbol] = chain

    #----------------------------------------------------------------------
    def newTick(self, tick):
        """行情更新"""
        super(OmUnderlying, self).newTick(tick)

        self.theoDelta = self.size * self.midPrice / 100

        # 遍历推送自己的行情到期权链中
        for chain in self.chainDict.values():
            chain.newUnderlyingTick()

    #----------------------------------------------------------------------
    def newTrade(self, trade):
        """成交更新"""
        super(OmUnderlying, self).newTrade(trade)
        self.calculatePosGreeks()

    #----------------------------------------------------------------------
    def calculatePosGreeks(self):
        """计算持仓希腊值"""
        self.posDelta = self.theoDelta * self.netPos


########################################################################
class OmOption(OmInstrument):
    """期权"""

    #----------------------------------------------------------------------
    def __init__(self, contract, detail, underlying, model, r):
        """Constructor"""
        super(OmOption, self).__init__(contract, detail)

        # 期权属性
        self.underlying = underlying    # 标的物对象
        self.k = contract.strikePrice   # 行权价
        self.r = r                      # 利率

        if contract.optionType == OPTION_CALL:
            self.cp = CALL              # 期权类型
        else:
            self.cp = PUT

        self.expiryDate = contract.expiryDate       # 到期日（字符串）
        self.t = getTimeToMaturity(self.expiryDate) # 剩余时间
        self.originT=self.t
        # 波动率属性
        self.bidImpv = EMPTY_FLOAT
        self.askImpv = EMPTY_FLOAT
        self.midImpv = EMPTY_FLOAT

        # 定价公式
        self.calculatePrice = model.calculatePrice
        self.calculateGreeks = model.calculateGreeks
        self.calculateImpv = model.calculateImpv
        self.calculateVega=model.calculateVega

        # 模型定价
        self.pricingImpv = EMPTY_FLOAT

        self.theoPrice = EMPTY_FLOAT    # 理论价
        self.theoDelta = EMPTY_FLOAT    # 合约的希腊值（乘以了合约大小）
        self.theoGamma = EMPTY_FLOAT
        self.theoTheta = EMPTY_FLOAT
        self.theoVega = EMPTY_FLOAT

        self.posValue = EMPTY_FLOAT     # 持仓市值
        self.posDelta = EMPTY_FLOAT     # 持仓的希腊值（乘以了持仓）
        self.posGamma = EMPTY_FLOAT
        self.posTheta = EMPTY_FLOAT
        self.posVega = EMPTY_FLOAT

        self.theoPrice = EMPTY_FLOAT
        self.delta = EMPTY_FLOAT
        self.gamma = EMPTY_FLOAT
        self.theta = EMPTY_FLOAT
        self.vega = EMPTY_FLOAT

        #如果是call，买远期价格，如果是put，卖远期价格
        self.futurePrice=EMPTY_FLOAT

        # 期权链
        self.chain = None

        self.dgammaDS=EMPTY_FLOAT
        self.dvegaDS=EMPTY_FLOAT
        self.vomma=EMPTY_FLOAT
        self.vonna=EMPTY_FLOAT

        self.posDgammaDS = EMPTY_FLOAT
        self.posDvegaDS = EMPTY_FLOAT
        self.posVomma = EMPTY_FLOAT
        self.posVonna = EMPTY_FLOAT

    #----------------------------------------------------------------------
    def calculateOptionImpv(self):
        """计算隐含波动率"""
        underlyingPrice = self.underlying.midPrice

        if not underlyingPrice:
            return

        askImpv = self.calculateImpv(self.askPrice1, underlyingPrice, self.k,
                                          self.r, self.t, self.cp)
        bidImpv = self.calculateImpv(self.bidPrice1, underlyingPrice, self.k,
                                          self.r, self.t, self.cp)

        if askImpv>0:
            self.askImpv=askImpv
        if bidImpv:
            self.bidImpv = bidImpv

        # self.midImpv = self.calculateImpv(self.midPrice, underlyingPrice, self.k,
        #                                   self.r, self.t, self.cp)
        self.midImpv = (self.askImpv + self.bidImpv) / 2

    #----------------------------------------------------------------------
    def calculateTheoVega(self,atTheMoneyOptionImv):
        underlyingPrice = self.underlying.midPrice
        if not underlyingPrice:
            return

        self.vega = self.calculateVega(underlyingPrice,self.k, self.r,self.t,atTheMoneyOptionImv,self.cp)

    def calculateTheoGreeksAndPosGreeks(self,callorPutImpv):
        underlyingPrice = self.underlying.midPrice
        if not underlyingPrice:
            return

        self.delta, self.gamma, self.theta ,self.dgammaDS,self.dvegaDS,self.vomma,self.vonna= self.calculateGreeks(underlyingPrice,
                                                                                  self.k,
                                                                                  self.r,
                                                                                  self.t,
                                                                                  callorPutImpv,
                                                                                  self.cp)
        # delta f * 0.01
        # vega * 0.01
        self.theoDelta = self.delta * self.size*underlyingPrice*0.01
        self.theoGamma = self.gamma * self.size*pow(underlyingPrice, 2) * 0.0001
        self.theoTheta = self.theta * self.size/ANNUAL_TRADINGDAYS
        self.theoVega = self.vega * self.size*0.01

        self.theoDgammaDS = self.dgammaDS * self.size * underlyingPrice * 0.01*pow(underlyingPrice, 2) * 0.0001
        self.theoDvegaDS= self.dvegaDS * self.size * underlyingPrice * 0.01*0.01
        self.theoVomma = self.vomma * self.size *0.01*pow(underlyingPrice, 2) * 0.0001
        self.theoVonna = self.vonna * self.size *0.01*0.01

        self.calculatePosGreeks()

    def calculateTheoGreeks(self):
        """计算理论希腊值"""
        underlyingPrice = self.underlying.midPrice
        if not underlyingPrice:
            return

        self.theoPrice, self.delta, self.gamma, self.theta = self.calculateGreeks(underlyingPrice,
                                                                         self.k,
                                                                         self.r,
                                                                         self.t,
                                                                         self.midImpv,
                                                                         self.cp)

        self.theoDelta = self.delta * self.size
        self.theoGamma = self.gamma * self.size
        self.theoTheta = self.theta * self.size
        self.theoVega = self.vega * self.size



    #----------------------------------------------------------------------
    def calculatePosGreeks(self):
        """计算持仓希腊值"""
        self.posValue = self.lastPrice * self.netPos * self.size
        self.posDelta = int(self.theoDelta * self.netPos)
        self.posGamma = int(self.theoGamma * self.netPos)
        self.posTheta = int(self.theoTheta * self.netPos)
        self.posVega = int(self.theoVega * self.netPos)

        self.posDgammaDS = int(self.theoDgammaDS * self.netPos)
        self.posDvegaDS = int(self.theoDvegaDS * self.netPos)
        self.posVomma = int(self.theoVomma * self.netPos)
        self.posVonna = int(self.theoVonna * self.netPos)

    #----------------------------------------------------------------------
    def newTick(self, tick):
        """行情更新"""
        super(OmOption, self).newTick(tick)
        if self.cp == CALL:
            self.futurePrice=self.k+tick.askPrice1-self.chain.relativeOption[self.symbol].bidPrice1
        else:
            self.futurePrice = self.k + self.chain.relativeOption[self.symbol].bidPrice1-tick.askPrice1
        # self.r=self.chain.calculateChainRate()
        # self.calculateOptionImpv()

    #----------------------------------------------------------------------
    def newUnderlyingTick(self):
        """标的行情更新"""
        pass
        # self.calculateOptionImpv()
        # self.calculateTheoGreeks()
        # self.calculatePosGreeks()

    #----------------------------------------------------------------------
    def newTrade(self, trade):
        """成交更新"""
        super(OmOption, self).newTrade(trade)
        #self.calculatePosGreeks()

    #----------------------------------------------------------------------
    def setUnderlying(self, underlying):
        """设置标的物对象"""
        self.underlying = underlying


########################################################################
class OmChain(object):
    """期权链"""

    #----------------------------------------------------------------------
    def __init__(self,underlying,symbol, callList, putList,future):
        """Constructor"""
        self.symbol = symbol

        # 原始容器
        self.callDict = OrderedDict()
        self.putDict = OrderedDict()
        self.optionDict = OrderedDict()
        self.future=future

        self.underlying=underlying

        # 用来记录平值期权的
        self.chainRate=0

        # 平值期权的CallSymbol
        self.atTheMoneySymbol=None

        #期权凸度计算
        self.convexity=100

        # 期权偏度计算
        self.skew = 100

        # put期权的综合波动率:vega权重作为系数，put期权波动率作为数值，累计叠加

        self.putImpv=0

        #call期权的综合波动率:vega权重作为系数，call期权波动率作为数值，累计叠加
        self.callImpv=0

        # put期权的综合波动率:vega权重作为系数，put期权波动率作为数值，累计叠加

        self.putImpv2 = 0

        # call期权的综合波动率:vega权重作为系数，call期权波动率作为数值，累计叠加
        self.callImpv2 = 0


        # 根据call或者put合约的symbol快速找到相同执行价的put或者call的合约
        self.relativeOption={}


        for index,option in enumerate(callList):
            option.chain = self
            self.callDict[option.symbol] = option
            self.relativeOption[option.symbol]=putList[index]
            self.optionDict[option.symbol] = option


        for index,option in enumerate(putList):
            option.chain = self
            self.putDict[option.symbol] = option
            self.relativeOption[option.symbol] = callList[index]
            self.optionDict[option.symbol] = option

        # 持仓数据
        self.longPos = EMPTY_INT
        self.shortPos = EMPTY_INT
        self.netPos = EMPTY_INT

        self.longTrade=EMPTY_INT
        self.shortTrade = EMPTY_INT

        self.posValue = EMPTY_FLOAT
        self.posDelta = EMPTY_FLOAT
        self.posGamma = EMPTY_FLOAT
        self.posTheta = EMPTY_FLOAT
        self.posVega = EMPTY_FLOAT

        self.posDgammaDS = EMPTY_FLOAT
        self.posDvegaDS = EMPTY_FLOAT
        self.posVomma = EMPTY_FLOAT
        self.posVonna = EMPTY_FLOAT

        self.callVolume=EMPTY_FLOAT
        self.putVolume = EMPTY_FLOAT
        self.callPostion = EMPTY_FLOAT
        self.putPostion = EMPTY_FLOAT

    #----------------------------------------------------------------------
    def calculatePosGreeks(self):
        """计算持仓希腊值"""
        # 清空数据
        self.longPos = 0
        self.shortPos = 0
        self.netPos = 0

        self.longTrade = 0
        self.shortTrade = 0

        self.posDelta = 0
        self.posGamma = 0
        self.posTheta = 0
        self.posVega = 0

        self.posDgammaDS = 0
        self.posDvegaDS = 0
        self.posVomma = 0
        self.posVonna = 0

        self.volume = 0
        self.openInterest = 0

        self.callVolume = 0
        self.callPostion = 0
        self.putVolume = 0
        self.putPostion = 0
        # 遍历汇总
        for option in self.callDict.values():
            self.longPos += option.longPos
            self.shortPos += option.shortPos

            self.longTrade += option.longTrade
            self.shortTrade  += option.shortTrade

            self.posValue += option.posValue
            self.posDelta += option.posDelta
            self.posGamma += option.posGamma
            self.posTheta += option.posTheta
            self.posVega += option.posVega

            self.posDgammaDS += option.posDgammaDS
            self.posDvegaDS += option.posDvegaDS
            self.posVomma += option.posVomma
            self.posVonna += option.posVonna

            self.callVolume += option.volume
            self.callPostion += option.openInterest

        for option in self.putDict.values():
            self.longPos += option.longPos
            self.shortPos += option.shortPos

            self.longTrade += option.longTrade
            self.shortTrade += option.shortTrade

            self.posValue += option.posValue
            self.posDelta += option.posDelta
            self.posGamma += option.posGamma
            self.posTheta += option.posTheta
            self.posVega += option.posVega

            self.posDgammaDS += option.posDgammaDS
            self.posDvegaDS += option.posDvegaDS
            self.posVomma += option.posVomma
            self.posVonna += option.posVonna

            self.putVolume += option.volume
            self.putPostion += option.openInterest

        self.netPos = self.longPos - self.shortPos

    #----------------------------------------------------------------------
    def newTick(self, tick):
        """期权行情更新"""
        option = self.optionDict[tick.symbol]
        option.newTick(tick)
        # rate = self.calculateChainRate()
        # for option in self.optionDict.values():
        #     option.r = rate
    #----------------------------------------------------------------------
    def newUnderlyingTick(self):
        """期货行情更新"""
        # rate=self.calculateChainRate()
        # for option in self.optionDict.values():
        #     option.r = rate
        # self.calculatePosGreeks()

    def outOfTheMoneyImpv(self,atTheMoneyKPrice,callOption,putOption):
        if callOption.k<atTheMoneyKPrice:
            return self.relativeOption[callOption.symbol].midImpv
        else:
            return callOption.midImpv

    def outOfTheMoneyVega(self, atTheMoneyKPrice, callOption):
        if callOption.k < atTheMoneyKPrice:
            if self.relativeOption[callOption.symbol].midPrice>0.001:
                return self.relativeOption[callOption.symbol].vega
            else:
                return 0
        else:
            if callOption.midPrice>0.001:
                return callOption.vega
            else:
                return 0

    def outOfTheMoneyVega2(self, atTheMoneyKPrice, callOption):
        if callOption.k < atTheMoneyKPrice:
            if self.relativeOption[callOption.symbol].midPrice>0.001 and 0.3<=self.relativeOption[callOption.symbol].delta<=0.7:
                return self.relativeOption[callOption.symbol].vega
            else:
                return 0
        else:
            if callOption.midPrice>0.001 and 0.3<=callOption.delta<=0.7:
                return callOption.vega
            else:
                return 0


    def calculateChainRate(self):
        """计算利率，选择平值期权的前后两档，五档行情的利率平均值作为最终的利率"""
        """首先计算利率，然后用这个利率算每个月份的call和put的波动率和vega(波动率用平值期权的波动率)，利用vega算权重，取每个执行价的虚值期权波动率作为每个月份的隐含波动率，算出chain的综合波动率,再算其他的希腊值"""
        s=self.underlying.midPrice
        k=[abs(callOption.k-s) for callOption in self.callDict.values()]
        minIndex= k.index(min(k))
        rateArray=[]
        atTheMoneyKPrice=self.putDict.values()[minIndex].k
        for index in range(-2+minIndex,3+minIndex,1):
            try:
                callPrice = self.callDict.values()[index].midPrice
                putPrice=self.putDict.values()[index].midPrice
                f = callPrice - putPrice+ self.putDict.values()[index].k
                r = log(f / self.underlying.midPrice) / self.putDict.values()[index].t
                rateArray.append(r)
            except Exception:
                pass
                # rateArray.append(self.chainRate)
        try:
            self.chainRate=round(sum(rateArray)/len(rateArray),4)
        except Exception:
            self.chainRate=0
        self.atTheMoneySymbol=self.callDict.values()[minIndex].symbol

        #计算平值期权的impv，用来计算每个期权的vega,vega加权!
        nowTime = time.time()
        atTheMoneyOption=self.callDict.values()[minIndex]
        atTheMoneyOption.t = atTheMoneyOption.originT - self.calculateDueTime(nowTime,self.underlying.symbol)
        atTheMoneyOption.r = self.chainRate
        atTheMoneyOption.calculateOptionImpv()
        atTheMoneyOptionImv=atTheMoneyOption.midImpv
        # 计算每个合约的vega和隐含波动率

        for option in self.optionDict.values():
            option.t=option.originT-self.calculateDueTime(nowTime,self.underlying.symbol)
            option.r =self.chainRate
            if not option.midPrice and not option.lastPrice:
                continue
            option.calculateOptionImpv()
            option.calculateTheoVega(atTheMoneyOptionImv)


        # 取每个执行价的虚值期权波动率作为每个合约的综合波动率,取每个执行价的虚值期权vega作为每个合约的综合vega
        comprehensiveVega=[self.outOfTheMoneyVega(atTheMoneyKPrice,callOption)  for callOption in self.callDict.values()]

        totalVega=sum(comprehensiveVega)

        try:
            weightVega=[item/totalVega for item in comprehensiveVega]
        except Exception:
            return

        self.callImpv=sum([vega*impv for vega, impv in zip(weightVega,[callOption.midImpv for callOption in self.callDict.values()])])
        self.putImpv=sum([vega*impv for vega, impv in zip(weightVega,[putOption.midImpv for putOption in self.putDict.values()])])

        self.callImpv=round(self.callImpv,4)
        self.putImpv = round(self.putImpv, 4)

        [callOption.calculateTheoGreeksAndPosGreeks(self.callImpv) for callOption in self.callDict.values()]
        [putOption.calculateTheoGreeksAndPosGreeks(self.putImpv) for putOption in self.putDict.values()]

            # 计算凸度和偏度
        try:
            delta = [abs(callOption.delta - 0.25) for callOption in self.callDict.values()]
            index1 = delta.index(min(delta))
            delta = [abs(callOption.delta - 0.75) for callOption in self.callDict.values()]
            index2 = delta.index(min(delta))
            delta = [abs(callOption.delta - (self.callDict.values()[index1].delta+self.callDict.values()[index2].delta)/2) for callOption in self.callDict.values()]
            index0 = delta.index(min(delta))
            # (((IV1 + IV2) - (IV0.call + IV0.put)) / 2 * (0.5 / (D2 - D1)) ^ 2 + 1) * 100
            self.convexity=round((((self.callDict.values()[index1].midImpv+self.putDict.values()[index2].midImpv)
                                   -(self.callDict.values()[index0].midImpv+self.putDict.values()[index0].midImpv))/2
                                  *pow((0.5/(self.callDict.values()[index2].delta-self.callDict.values()[index1].delta)),2)+1)*100,2)

            # ((IV2 - IV1） / (IV1 + IV2) * (0.5 / (D2 - D1)) + 1)*100
            self.skew = round(((self.putDict.values()[index2].midImpv-self.callDict.values()[index1].midImpv)
                               /(self.putDict.values()[index2].midImpv+self.callDict.values()[index1].midImpv)
                               *(0.5/(self.callDict.values()[index2].delta-self.callDict.values()[index1].delta))+1)*100,2)
        except Exception:
            self.convexity=100
            self.skew = 100


        # 第二种算法
        comprehensiveVega = [self.outOfTheMoneyVega2(atTheMoneyKPrice, callOption) for callOption in
                             self.callDict.values()]

        totalVega = sum(comprehensiveVega)

        try:
            weightVega = [item / totalVega for item in comprehensiveVega]
        except Exception:
            return

        self.callImpv2 = sum([vega * impv for vega, impv in
                             zip(weightVega, [callOption.midImpv for callOption in self.callDict.values()])])
        self.putImpv2 = sum(
            [vega * impv for vega, impv in zip(weightVega, [putOption.midImpv for putOption in self.putDict.values()])])

        self.callImpv2 = round(self.callImpv2, 4)
        self.putImpv2 = round(self.putImpv2, 4)

    def calculateChainRate2(self):
        """计算利率，选择平值期权的前后两档，五档行情的利率平均值作为最终的利率"""
        # 1.算综合利率，按之前算法
        # 2.用综合利率算r，用每个合约的隐含波动率计算希腊字母
        # 3.选出delta在0.3 - 0.7的合约
        # 4.计算每个合约对应vega的权重
        # 5.用Vega权重加权隐含波动率计算出综合波动率
        s = self.underlying.midPrice
        k = [abs(callOption.k - s) for callOption in self.callDict.values()]
        minIndex = k.index(min(k))
        rateArray = []
        atTheMoneyKPrice = self.putDict.values()[minIndex].k
        for index in range(-2 + minIndex, 3 + minIndex, 1):
            try:
                callPrice = self.callDict.values()[index].midPrice
                putPrice = self.putDict.values()[index].midPrice
                f = callPrice - putPrice + self.putDict.values()[index].k
                r = log(f / self.underlying.midPrice) / self.putDict.values()[index].t
                rateArray.append(r)
            except Exception:
                pass
                # rateArray.append(self.chainRate)
        try:
            self.chainRate = round(sum(rateArray) / len(rateArray), 4)
        except Exception:
            self.chainRate = 0
        self.atTheMoneySymbol = self.callDict.values()[minIndex].symbol

        nowTime = time.time()
        atTheMoneyOption = self.callDict.values()[minIndex]
        atTheMoneyOption.t = atTheMoneyOption.originT - self.calculateDueTime(nowTime, self.underlying.symbol)
        atTheMoneyOption.r = self.chainRate
        atTheMoneyOptionImv = atTheMoneyOption.midImpv
        for option in self.optionDict.values():
            option.r =self.chainRate
            option.t = option.originT - self.calculateDueTime(nowTime, self.underlying.symbol)
            option.calculateOptionImpv()
            option.calculateTheoVega(atTheMoneyOptionImv)
            option.calculateTheoGreeksAndPosGreeks(atTheMoneyOptionImv)


        # 取每个执行价的虚值期权波动率作为每个合约的综合波动率,取每个执行价的虚值期权vega作为每个合约的综合vega
        comprehensiveVega = [self.outOfTheMoneyVega2(atTheMoneyKPrice, callOption) for callOption in
                             self.callDict.values()]

        totalVega = sum(comprehensiveVega)

        try:
            weightVega = [item / totalVega for item in comprehensiveVega]
        except Exception:
            return

        self.callImpv = sum([vega * impv for vega, impv in
                             zip(weightVega, [callOption.midImpv for callOption in self.callDict.values()])])
        self.putImpv = sum(
            [vega * impv for vega, impv in zip(weightVega, [putOption.midImpv for putOption in self.putDict.values()])])

        self.callImpv = round(self.callImpv, 4)
        self.putImpv = round(self.putImpv, 4)

        # 计算凸度和偏度
        try:
            delta = [abs(callOption.delta - 0.25) for callOption in self.callDict.values()]
            index1 = delta.index(min(delta))
            delta = [abs(callOption.delta - 0.75) for callOption in self.callDict.values()]
            index2 = delta.index(min(delta))
            delta = [abs(
                callOption.delta - (self.callDict.values()[index1].delta + self.callDict.values()[index2].delta) / 2)
                     for callOption in self.callDict.values()]
            index0 = delta.index(min(delta))
            # (((IV1 + IV2) - (IV0.call + IV0.put)) / 2 * (0.5 / (D2 - D1)) ^ 2 + 1) * 100
            self.convexity = round((((self.callDict.values()[index1].midImpv + self.putDict.values()[index2].midImpv)
                                     - (self.callDict.values()[index0].midImpv + self.putDict.values()[
                index0].midImpv)) / 2
                                    * pow(
                (0.5 / (self.callDict.values()[index2].delta - self.callDict.values()[index1].delta)), 2) + 1) * 100, 2)

            # ((IV2 - IV1） / (IV1 + IV2) * (0.5 / (D2 - D1)) + 1)*100
            self.skew = round(((self.putDict.values()[index2].midImpv - self.callDict.values()[index1].midImpv)
                               / (self.putDict.values()[index2].midImpv + self.callDict.values()[index1].midImpv)
                               * (0.5 / (
            self.callDict.values()[index2].delta - self.callDict.values()[index1].delta)) + 1) * 100, 2)
        except Exception:
            self.convexity = 100
            self.skew = 100


    #----------------------------------------------------------------------
    def newTrade(self, trade):
        """期权成交更新"""
        option = self.optionDict[trade.symbol]

        # 缓存旧数据
        # oldLongPos = option.longPos
        # oldShortPos = option.shortPos
        #
        # oldPosValue = option.posValue
        # oldPosDelta = option.posDelta
        # oldPosGamma = option.posGamma
        # oldPosTheta = option.posTheta
        # oldPosVega = option.posVega

        # 更新到期权s中
        option.newTrade(trade)

        # # 计算持仓希腊值
        # self.longPos = self.longPos - oldLongPos + option.longPos
        # self.shortPos = self.shortPos - oldShortPos+ option.shortPos
        # self.netPos = self.longPos - self.shortPos
        #
        # self.posValue = self.posValue - oldPosValue + option.posValue
        # self.posDelta = self.posDelta - oldPosDelta + option.posDelta
        # self.posGamma = self.posGamma - oldPosGamma + option.posGamma
        # self.posTheta = self.posTheta - oldPosTheta + option.posTheta
        # self.posVega = self.posVega - oldPosVega + option.posVega

    def calculateDueTime(self,nowTime,symbol):
        hours = time.localtime(nowTime)[3]
        minutes = time.localtime(nowTime)[4]
        pastMinute = hours * 60 + minutes
        adjustmentTime = 0.0
        if symbol=='510050':
            if pastMinute < 570:
                adjustmentTime = 0
            elif 570 <= pastMinute and pastMinute < 690:
                adjustmentTime = (pastMinute - 570) / 240.0 / ANNUAL_TRADINGDAYS
            elif 690 <= pastMinute and pastMinute < 780:
                adjustmentTime = 0.5 / ANNUAL_TRADINGDAYS
            elif 780 <= pastMinute and pastMinute < 900:
                adjustmentTime = (pastMinute - 780) / 240 / ANNUAL_TRADINGDAYS+ 0.5 / ANNUAL_TRADINGDAYS
            else:
                adjustmentTime = 1.0 / ANNUAL_TRADINGDAYS
            return adjustmentTime
        else:
            if pastMinute < 540:
                adjustmentTime = 150.0 / 375 / ANNUAL_TRADINGDAYS
            elif 540 <= pastMinute and pastMinute < 615:
                adjustmentTime = (pastMinute - 540 + 150) / 375.0 / ANNUAL_TRADINGDAYS
            elif 615 <= pastMinute and pastMinute < 630:
                adjustmentTime = 225.0 / 375 / ANNUAL_TRADINGDAYS
            elif 630 <= pastMinute and pastMinute < 690:
                adjustmentTime = (pastMinute - 630 + 225) / 375.0 / ANNUAL_TRADINGDAYS
            elif 690 <= pastMinute and pastMinute < 810:
                adjustmentTime = 285.0 / 375 / ANNUAL_TRADINGDAYS
            elif 810 <= pastMinute and pastMinute < 900:
                adjustmentTime = (pastMinute - 810 + 285) / 375.0 / ANNUAL_TRADINGDAYS
            elif 900 <= pastMinute and pastMinute < 1260:
                adjustmentTime = 1.0 / ANNUAL_TRADINGDAYS
            elif 1260 <= pastMinute and pastMinute < 1410:
                adjustmentTime = (1.0 + (pastMinute - 1260) / 375.0) / ANNUAL_TRADINGDAYS
            else:
                adjustmentTime = (1.0 + 150.0 / 375) / ANNUAL_TRADINGDAYS
            return adjustmentTime

########################################################################
class OmPortfolio(object):
    """持仓组合"""

    #----------------------------------------------------------------------
    def __init__(self,mainEngine,eventEngine, name, model, underlyingList, chainList,futureList):
        """Constructor"""
        self.name = name
        self.model = model
        self.eventEngine=eventEngine
        self.mainEngine=mainEngine
        self.futureList=futureList

        # 原始容器
        self.underlyingDict = OrderedDict()
        self.chainDict = OrderedDict()
        self.futureDict= OrderedDict()
        self.optionDict = {}
        self.instrumentDict = {}

        for future in futureList:
            self.futureDict[future.symbol] = future

        for underlying in underlyingList:
            self.underlyingDict[underlying.symbol] = underlying

        for chain in chainList:
            self.chainDict[chain.symbol] = chain
            self.optionDict.update(chain.callDict)
            self.optionDict.update(chain.putDict)

        self.instrumentDict.update(self.underlyingDict)
        self.instrumentDict.update(self.optionDict)

        # 持仓数据
        self.longPos = EMPTY_INT
        self.shortPos = EMPTY_INT
        self.netPos = EMPTY_INT

        self.longTrade = EMPTY_INT
        self.shortTrade = EMPTY_INT

        self.posValue = EMPTY_FLOAT
        self.posDelta = EMPTY_FLOAT
        self.posGamma = EMPTY_FLOAT
        self.posTheta = EMPTY_FLOAT
        self.posVega = EMPTY_FLOAT

        self.posDgammaDS = EMPTY_FLOAT
        self.posDvegaDS = EMPTY_FLOAT
        self.posVomma = EMPTY_FLOAT
        self.posVonna = EMPTY_FLOAT
        """启动连续计算波动率和持仓统计"""
        self.eventEngine.register(EVENT_TIMER, self.timingCalculate)
    #----------------------------------------------------------------------
    def calculatePosGreeks(self):
        """计算持仓希腊值"""
        self.longPos = 0
        self.shortPos = 0
        self.netPos = 0

        self.longTrade = 0
        self.shortTrade = 0

        self.posValue = 0
        self.posDelta = 0
        self.posGamma = 0
        self.posTheta = 0
        self.posVega = 0

        self.posDgammaDS =0
        self.posDvegaDS =0
        self.posVomma =0
        self.posVonna =0

        self.callVolume = 0
        self.putVolume = 0
        self.callPostion = 0
        self.putPostion = 0

        for underlying in self.underlyingDict.values():
            self.posDelta += underlying.posDelta

        for chain in self.chainDict.values():
            self.longPos += chain.longPos
            self.shortPos += chain.shortPos

            self.longTrade  += chain.longTrade
            self.shortTrade  += chain.shortTrade

            self.posValue += chain.posValue
            self.posDelta += chain.posDelta
            self.posGamma += chain.posGamma
            self.posTheta += chain.posTheta
            self.posVega += chain.posVega

            self.posDgammaDS += chain.posDgammaDS
            self.posDvegaDS += chain.posDvegaDS
            self.posVomma += chain.posVomma
            self.posVonna += chain.posVonna

            self.callVolume += chain.callVolume
            self.putVolume += chain.putVolume
            self.callPostion += chain.callPostion
            self.putPostion += chain.putPostion

        self.netPos = self.longPos - self.shortPos

    #----------------------------------------------------------------------
    def newTick(self, tick):
        """行情推送"""
        symbol = tick.symbol

        if symbol in self.optionDict:
            chain = self.optionDict[symbol].chain
            chain.newTick(tick)
        elif symbol in self.underlyingDict:
            underlying = self.underlyingDict[symbol]
            underlying.newTick(tick)
        elif symbol in self.futureDict:
            future = self.futureDict[symbol]
            future.newTick(tick)


    def timingCalculate(self,event):
        """定时计算希腊字母和波动率，不实时更新的是因为数据是一条一条返回过来的，比如服务器可能在0.5秒内就返回10多组数据给我，无法实时更新"""
        start = time.time()
        for chain in self.chainDict.values():
            chain.calculateChainRate()
            chain.calculatePosGreeks()
        self.calculatePosGreeks()
        end= time.time()
        # print end-start
    #----------------------------------------------------------------------
    def newTrade(self, trade):
        """成交推送"""
        symbol = trade.symbol
        if symbol in self.optionDict:
            chain = self.optionDict[symbol].chain
            chain.newTrade(trade)
            #self.calculatePosGreeks()
        elif symbol in self.underlyingDict:
            underlying = self.underlyingDict[symbol]
            underlying.newTrade(trade)
            #self.calculatePosGreeks()
