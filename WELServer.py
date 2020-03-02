import pandas as pd
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
import matplotlib.pyplot as plt
import numpy as np
# import sys
import datetime as dt
# import traceback
# import urllib3
# import xmltodict


class WELData:
    data = None
    beginTime = None
    endTime = None
    figsize = (10,5)


    def __init__(self,
                 dataPath):
        self.data = pd.read_excel(dataPath)
        self.data.Date = self.data.Date.apply(
                            lambda date: dt.datetime.strptime(date, "%m/%d/%Y"))
        self.data['dateTime'] = [dt.datetime.combine(date, time)
                    for date, time in zip(self.data.Date, self.data.Time)]
        self.beginTime = self.data.dateTime.iloc[0]
        self.endTime = self.data.dateTime.iloc[-1]


    def vars(self):
        return [col for col in self.data.columns]


    def timeCondition(self,
                      timeRange):
        if timeRange[0] == None:
            timeRange[0] = self.beginTime
        else: timeRange[0] = dt.datetime.fromisoformat(timeRange[0])
        if timeRange[1] == None:
            timeRange[1] = self.endTime
        else: timeRange[1] = dt.datetime.fromisoformat(timeRange[1])

        return timeRange


    def plot(self,
             x,
             y,
             xunits='time',
             yunits='',
             timeRange=[None, None]):
        timeRange = self.timeCondition(timeRange)

        mindex = self.data.dateTime > timeRange[0]
        maxdex = self.data.dateTime < timeRange[1]
        plotx = self.data[x][mindex & maxdex]
        ploty = [self.data[var][mindex & maxdex] for var in y]

        plt.figure(figsize=self.figsize)

        if x == 'time' or 'date' or 'dateTime':
            [plt.plot_date(plotx, plotDatum, fmt='-', label=label)
                for label, plotDatum in zip(y, ploty)]
            plt.gcf().autofmt_xdate()
        else:
            [plt.scatter(plotx, plotDatum, fmt='-', label=label)
                for label, plotDatum in zip(y, ploty)]

        plt.xlabel(xunits)
        plt.ylabel(yunits)
        plt.legend()
        plt.grid(True)
        # plt.show()
