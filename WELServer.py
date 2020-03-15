import pandas as pd
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt
import re
import wget
import os
from astral import sun, LocationInfo


class WELData:
    data = None             # pandas dataframe class variable
    beginTime = None        # first and last times in the dataframe
    endTime = None
    figsize = (11,5)        # default figure size
    loc = LocationInfo('Home', 'MA', 'EST', 42.485680, -71.435226) # for sun


    """
    Initialize the Weldata Object.
    If filepath is given, data will be read from the file, otherwise this
    month's log is downloaded and read.
    Columns with all NaNs are dropped.

    ADDED COLUMNS:
    dateandtime : combined datetime object for each row.
    power_tot : TAH_W + HP_W
    T_diff : living_T - outside_T
    eff_ma : day length rolling average of efficiency

    filepath : filepath for data file.
    keepdata : boolean keep downloaded data file. Default False.
    """
    def __init__(self,
                 filepath=None,
                 keepdata=False):
        # Download or import, read and prepare data
        download = False
        if filepath is None:
            download = True
            now = dt.datetime.now()
            dat_url = ('http://www.welserver.com/WEL1060/'
                      F'WEL_log_{now.year}_{now.month:02d}.xls')
            filepath = './temp_WEL_data.xls'
            wget.download(dat_url, filepath)
            print()
        try:
            self.data = pd.read_excel(filepath)
        except:
            self.data = pd.read_csv(filepath, sep='\t',
                                    index_col=False, na_values=['?'])
        if not keepdata and download:
            os.remove(filepath)

        self.data.dropna(axis=1, how='all', inplace=True)

        for col in self.data.columns:
            if ('Date' not in col) and ('Time' not in col):
                self.data[col] = self.data[col].astype(np.float64)

        self.data.Date = self.data.Date.apply(lambda date:
                              dt.datetime.strptime(date, "%m/%d/%Y"))
        self.data.Time = self.data.Time.apply(lambda time:
                              dt.datetime.strptime(time, "%H:%M:%S").time())

        # DAYLIGHT SAVINGS CORRECTOR
        dls = dt.timedelta(hours=1)

        self.data['dateandtime'] = [dt.datetime.combine(date, time) + dls
                                 for date, time in zip(self.data.Date,
                                                       self.data.Time)]
        self.data.index = self.data['dateandtime']

        # Set Class begin and end variables
        self.beginTime = self.data.dateandtime.iloc[0]
        self.endTime = self.data.dateandtime.iloc[-1]

        # Additional calculated columns
        self.data['power_tot'] = self.data.HP_W + self.data.TAH_W
        self.data['T_diff'] = self.data.living_T - self.data.outside_T
        self.data['eff_ma'] = self.data.eff.rolling('12H').mean()


    """
    Returns list of all column names.
    """
    def vars(self):
        return [col for col in self.data.columns]


    """
    WIP
    """
    def dropna(self,
               column):
        self.data.dropna(how='any', inplace=True)


    """
    Takes a list with a start and end time. If either is 'none', defaults to
    start or end time respectively. Converts iso strings to datetime, keeps
    datetime as datetime.
    """
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



    """
    Converts variable name string into object data string, to be evaluated as
    a python expression.

    string: expression string to be modified.
    """
    def varExprParse(self,
                     string):
        splitString = re.split('(\\()|(\\))|(\s)', string)
        splitString = [w for w in splitString if w is not None]

        expr = ""
        for word in splitString:
            possibleVars = [var for var in self.data.columns if var in word]
            if len(possibleVars) > 0:
                foundVar = max(possibleVars, key=len)
                expr += word.replace(foundVar,
                                     "self.data['" + foundVar + "'][mask]")
            else:
                expr += word

        return expr


    """
    Adds day/night background shading based on calculated sunrise/sunset times
    to the specified axes.

    axes : axes to plot on.
    timeRange : timerange to plot on.
    limits : y axis extent of the shading.
    """
    def plotNightime(self,
                     axes,
                     timeRange,
                     limits):
        axes.autoscale(enable=False)
        dayList = [(timeRange[0] + dt.timedelta(days=x - 1)).date()
                    for x in range((timeRange[1] - timeRange[0]).days + 3)]

        for day in dayList:
            day = dt.datetime.combine(day, dt.datetime.min.time())
            sunrise = (sun.sunrise(self.loc.observer, date=day)
                       - dt.timedelta(hours=4))
            sunset = (sun.sunset(self.loc.observer,date=day)
                      - dt.timedelta(hours=4))
            timelist = [day, sunrise - dt.timedelta(seconds=1), sunrise,
                        sunset, sunset + dt.timedelta(seconds=1),
                        day + dt.timedelta(days=1)]

            axes.fill_between(timelist, np.full(len(timelist), limits[0]),
                              np.full(len(timelist), limits[1]),
                              where=[True, True, False, False, True, True],
                              facecolor='black', alpha=0.1)


    """
    Plot two variables against each other.

    y : Single variable or list of variable names to plot on y axis. Math
       operations can be used in a variable string in the list.
    optional x : Defaults to 'dateandtime'. Variable name to plot on x axis.
    optional xunits : Defaults to 'Time'. Variable string to display on x axis.
    optional yunits : Defaults to 'None'. Varaible string to display on y axis.
    optional timerange : 2 length array with start and end time as iso string,
                         datetime object or if 'none' defaults to start/end
                         time in that position.
    optional axes : axes to draw plot on instead of default figure.
    optional nighttime : adds day/night shading to plot.
    """
    def plotVar(self,
                y,
                x='dateandtime',
                xunits='Time',
                yunits='None',
                timerange=None,
                axes=None,
                nighttime=True):
        timeRange = self.timeCondition(timerange)
        if type(y) is not list: y = [y]

        mask = ((self.data.dateandtime > timeRange[0])
               & (self.data.dateandtime < timeRange[1]))
        p_locals = locals()
        plotx = eval(self.varExprParse(x), p_locals)
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

        if nighttime:
            self.plotNightime(axes, timeRange,
                         (np.nanmin(ploty) - 100, np.nanmax(ploty) + 100))

        if yunits is 'None':
            usedVars = [var for var in self.data.columns if var in y[0]]
            if usedVars[0][-1] is 'T':
                yunits = "Temperature [°C]"
            if usedVars[0][-1] is 'W':
                yunits = "Power [W]"
        axes.set_ylabel(yunits)
        axes.yaxis.set_label_position("right")
        axes.yaxis.tick_right()
        axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',
                    ncol=len(y), mode="expand", borderaxespad=0)
        axes.grid(True)
        axes.set_xlim(timeRange)
        plt.tight_layout()


    """
    Plots all hardcoded status variables against time.

    optional timerange : 2 length array with start and end time as iso string,
                         datetime object or if 'none' defaults to start/end
                         time in that position.
    optional axes : axes to draw plot on instead of default figure.
    optional nighttime : adds day/night shading to plot.
    """
    def plotStatus(self,
                   timerange=None,
                   axes=None,
                   nighttime=True):
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

        if nighttime:
            self.plotNightime(axes, timeRange,
                         (np.nanmin(ploty) - 100, np.nanmax(ploty) + 100))

        plt.setp(axes.get_xticklabels(), rotation=20, ha='right')
        axes.set_yticks(np.arange(0, 16, 2))
        axes.set_yticklabels(labels)
        axes.yaxis.set_label_position("right")
        axes.yaxis.tick_right()
        axes.grid(True)
        axes.set_xlim(timeRange)
        plt.tight_layout()
