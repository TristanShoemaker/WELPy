import pandas as pd
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
import matplotlib.pyplot as plt
import numpy as np
# import sys
import datetime as dt
import parser
import wget
import os

class WELData:
    data = None
    beginTime = None
    endTime = None
    figsize = (11,5)


    def __init__(self,
                 dataPath=None):
        if dataPath is None:

            dat_file_url = 'http://www.welserver.com/WEL1060/WEL_log_2020_03.xls'
            dataPath = './temp_WEL_data.xls'
            wget.download(dat_file_url, dataPath)

        try:
            self.data = pd.read_excel(dataPath)
        except:
            self.data = pd.read_csv(dataPath, sep='\t',
                                    index_col=False, na_values=['?'])
        os.remove(dataPath)
        self.data.dropna(axis=1, how='all', inplace=True)
        for col in self.data.columns:
            if ('Date' not in col) and ('Time' not in col):
                self.data[col] = self.data[col].astype(np.float64)

        self.data.Date = self.data.Date.apply(lambda date:
                              dt.datetime.strptime(date, "%m/%d/%Y"))
        self.data.Time = self.data.Time.apply(lambda time:
                              dt.datetime.strptime(time, "%H:%M:%S").time())
        self.data['dateandtime'] = [dt.datetime.combine(date, time)
                              for date, time in zip(self.data.Date,
                                                    self.data.Time)]
        self.data.index = self.data['dateandtime']

        self.beginTime = self.data.dateandtime.iloc[0]
        self.endTime = self.data.dateandtime.iloc[-1]

        self.data['power_tot'] = self.data.HP_W + self.data.TAH_W
        self.data['T_diff'] = self.data.living_T - self.data.outside_T
        self.data['eff_ma'] = self.data.eff.rolling('D').std()


    def vars(self):
        return [col for col in self.data.columns]


    def dropna(self):
        self.data.dropna(inplace=True)


    def timeCondition(self,
                      timeRange):
        if timeRange == None:
            timeRange = [self.beginTime, self.endTime]
            return timeRange
        if timeRange[0] == 'none':
            timeRange[0] = self.beginTime
        else:
            if type(timeRange[0]) is str:
                timeRange[0] = dt.datetime.fromisoformat(timeRange[0])
        if timeRange[1] == 'none':
            timeRange[1] = self.endTime
        else:
            if type(timeRange[0]) is str:
                timeRange[1] = dt.datetime.fromisoformat(timeRange[1])

        return timeRange


    def varExprParse(self,
                     string):
        string = string.replace(string, "self.data['" + string + "'][mask]")
        # print(string)
        return string


    def plotVar(self,
                x,
                y,
                xunits='Time',
                yunits='None',
                timerange=None,
                axes=None):
        timeRange = self.timeCondition(timerange)
        if type(y) is not list: y = [y]

        mask = ((self.data.dateandtime > timeRange[0])
               & (self.data.dateandtime < timeRange[1]))
        p_locals = locals()
        plotx = eval(self.varExprParse(x), p_locals)
        # print(plotx)
        ploty = [eval(self.varExprParse(expr), p_locals) for expr in y]

        if axes is None:
            fig = plt.figure(figsize=self.figsize)
            axes = plt.gca()

        if ('time' or 'date') in x:
            [axes.plot_date(plotx, plotDatum, fmt='-', label=label)
                for label, plotDatum in zip(y, ploty)]
            plt.setp(axes.get_xticklabels(), rotation=20, ha='right')
        else:
            [plt.plot(plotx, plotDatum, '.', label=label)
                for label, plotDatum in zip(y, ploty)]
            axes.set_xlabel(xunits)

        if yunits is 'None':
            usedVars = [var for var in self.data.columns if var in y[0]]
            if usedVars[0][-1] is 'T':
                yunits = "Temperature [°C]"
            if usedVars[0][-1] is 'W':
                yunits = "Power [W]"
        axes.set_ylabel(yunits)
        axes.legend()
        axes.grid(True)
        plt.tight_layout()


    def plotStatus(self,
                   timerange=None,
                   axes=None):
        status_list = ['aux_heat_b',
                       'heat_1_b',
                       'heat_2_b',
                       'rev_valve_b',
                       'TAH_fan_b',
                       'zone_1_b',
                       'zone_2_b',
                       'humid_b']
        labels = [stat[:-2] for stat in status_list]
        timeRange = self.timeCondition(timerange)

        mask = ((self.data.dateandtime > timeRange[0])
               & (self.data.dateandtime < timeRange[1]))

        p_locals = locals()
        plotx = eval(self.varExprParse('dateandtime'), p_locals)
        ploty = [eval(self.varExprParse(stat), p_locals)
                    for stat in status_list]

        if axes is None:
            fig = plt.figure(figsize=(self.figsize[0], self.figsize[1] * 0.75))
            axes = plt.gca()

        [axes.plot_date(plotx, plotDatum, fmt='-', label=label)
            for label, plotDatum in zip(labels, ploty)]

        plt.setp(axes.get_xticklabels(), rotation=20, ha='right')
        axes.set_yticks(np.arange(0, 16, 2))
        axes.set_yticklabels(labels)
        axes.yaxis.set_label_position("right")
        axes.yaxis.tick_right()
        axes.grid(True)
        plt.tight_layout()
