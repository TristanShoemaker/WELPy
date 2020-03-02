import pandas as pd
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
import matplotlib.pyplot as plt
import numpy as np
# import sys
import datetime as dt
import parser


class WELData:
    data = None
    beginTime = None
    endTime = None
    figsize = (11,5)


    def __init__(self,
                 dataPath):
        self.data = pd.read_excel(dataPath)

        self.data.Date = self.data.Date.apply(
                            lambda date: dt.datetime.strptime(date, "%m/%d/%Y"))
        self.data['dateandtime'] = [dt.datetime.combine(date, time)
                    for date, time in zip(self.data.Date, self.data.Time)]
        self.data.index = self.data['dateandtime']
        self.beginTime = self.data.dateandtime.iloc[0]
        self.endTime = self.data.dateandtime.iloc[-1]

        self.data['power_tot'] = self.data.HP_W + self.data.TAH_W
        self.data['T_diff'] = self.data.inside_T - self.data.outside_T

        self.data['eff_ma'] = self.data.eff.rolling('D').std()


    def vars(self):
        return [col for col in self.data.columns]


    def timeCondition(self,
                      timeRange):
        if timeRange == None:
            timeRange = [self.beginTime, self.endTime]
            return timeRange
        if timeRange[0] == 'none':
            timeRange[0] = self.beginTime
        else: timeRange[0] = dt.datetime.fromisoformat(timeRange[0])
        if timeRange[1] == 'none':
            timeRange[1] = self.endTime
        else: timeRange[1] = dt.datetime.fromisoformat(timeRange[1])

        return timeRange


    def varExprParse(self,
                 string):
        for var in self.data.columns:
            string = string.replace(var, "self.data['" + var + "']")
        # print(string)
        return compile(string, 'plotInput', 'eval')


    def plot(self,
             x,
             y,
             xunits='Time',
             yunits='None',
             timerange=None):
        timeRange = self.timeCondition(timerange)
        if type(y) is not list: y = [y]

        mindex = self.data.dateandtime > timeRange[0]
        maxdex = self.data.dateandtime < timeRange[1]
        plotx = eval(self.varExprParse(x))[mindex & maxdex]
        ploty = [eval(self.varExprParse(expr))[mindex & maxdex] for expr in y]

        plt.figure(figsize=self.figsize)

        if 'time' or 'date' in x:
            [plt.plot_date(plotx, plotDatum, fmt='-', label=label)
                for label, plotDatum in zip(y, ploty)]
            plt.gcf().autofmt_xdate()
        else:
            [plt.plot(plotx, plotDatum, '.', label=label)
                for label, plotDatum in zip(y, ploty)]

        plt.xlabel(xunits)
        if yunits is 'None':
            usedVars = [var for var in self.data.columns if var in y[0]]
            if usedVars[0][-1] is 'T':
                yunits = "Temperature [°C]"
            if usedVars[0][-1] is 'W':
                yunits = "Power [W]"
        plt.ylabel(yunits)
        plt.legend()
        plt.grid(True)
        # plt.show()
