import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sys
import datetime as dt
import traceback
import urllib3
import xmltodict


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
        self.data['DateTime'] = [dt.datetime.combine(date, time)
                    for date, time in zip(self.data.Date, self.data.Time)]
        self.beginTime = self.data.DateTime.iloc[0]
        self.endTime = self.data.DateTime.iloc[-1]


    def vars(self):
        return [col for col in self.data.columns]


    def timeCondition(self,
                      timeRange):
        if timeRange[0] is None:
            timeRange[0] = self.beginTime
        else: timeRange[0] = dt.datetime.fromisoformat(timeRange[0])
        if timeRange[1] is None:
            timeRange[1] = self.endTime
        else: timeRange[1] = dt.datetime.fromisoformat(timeRange[1])

        return timeRange


    def plotVTime(self,
                  vars,
                  unit,
                  timeRange=[None, None]):
        timeRange = self.timeCondition(timeRange)

        mindex = self.data.DateTime > timeRange[0]
        maxdex = self.data.DateTime < timeRange[1]
        plotTime = self.data.DateTime[mindex & maxdex]
        plotData = [self.data[var][mindex & maxdex] for var in vars]

        plt.figure(figsize=self.figsize)
        [plt.plot_date(plotTime, plotDatum, fmt='-') for plotDatum in plotData]
        plt.gcf().autofmt_xdate()
        plt.xlabel("Time")
        plt.ylabel(unit)
        plt.grid(True)
        # plt.show()


    def plotVVar(self,
                 var1,
                 var2,
                 unit1,
                 unit2,
                 timeRange=[None, None]):
        timeRange = self.timeCondition(timeRange)

        mindex = self.data.DateTime > timeRange[0]
        maxdex = self.data.DateTime < timeRange[1]

        plotVar1 = self.data[var1][mindex & maxdex]
        plotVar2 = self.data[var2][mindex & maxdex]

        plt.figure(figsize=self.figsize)
        plt.plot(plotVar1, plotVar2, '-')
        plt.xlabel(unit1)
        plt.ylabel(unit2)
        plt.grid()
        # plt.show()

class LiveWELData:
    url = "http://192.168.68.101:5150/wel.xml"
    http = urllib3.PoolManager()
    data = None
    beginTime = None


    def __init__(self):
        initData = self.getLiveData()
        row = {}
        for item in initData:
            row[item['name']] = item['value']

        row['date'] = dt.datetime.strptime(row['date'], "%m/%d/%Y")
        row['time'] = dt.datetime.strptime(row['time'], "%H:%M:%S")
        row['DateTime'] = dt.datetime.combine(row['date'].date(),
                                              row['time'].time())
        del row['date'], row['time']
        self.data = pd.DataFrame(row, index=[0])
        self.beginTime = row['DateTime']


    def getLiveData(self):
        response = self.http.request('GET', self.url)

        try:
            liveData = xmltodict.parse(response.data)['devices']['device']
        except:
            print("Failed to parse xml from response (%s)" % traceback.format_exc())

        return liveData


    def addData(self,
                liveData):
        row = {}
        for item in liveData:
            row[item['name']] = item['value']

        row['date'] = dt.datetime.strptime(row['date'], "%m/%d/%Y")
        row['time'] = dt.datetime.strptime(row['time'], "%H:%M:%S")
        row['DateTime'] = dt.datetime.combine(row['date'].date(),
                                              row['time'].time())
        del row['date'], row['time']
        self.data = self.data.append(row, ignore_index=True)


    def livePlot(self,
                 var,
                 unit,
                 delay):
        import matplotlib.animation as animation

        fig = plt.figure(figsize=(7,5))
        ax = fig.add_subplot(1,1,1)
        plt.xlabel("Time")
        plt.ylabel(unit)
        plt.grid(True)
        fig.autofmt_xdate()

        def animate(i):
            self.addData(self.getLiveData())
            ax.clear()
            ax.plot_date(self.data.DateTime, self.data[var])

        ani = animation.Animation(fig, animate, 1000 * delay)
        plt.show()
