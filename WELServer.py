import pandas as pd
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt
from dateutil.relativedelta import relativedelta
import re
import wget
import os
import shutil
from astral import sun, LocationInfo


class WELData:
    data = None             # pandas dataframe class variable
    figsize = (11,5)        # default figure size
    loc = LocationInfo('Home', 'MA', 'EST', 42.485680, -71.435226) # for sun
    db_path = './log_db/'


    """
    Initialize the Weldata Object.
    If filepath is given, data will be read from the file, otherwise this
    month's log is downloaded and read.
    """
    def __init__(self,
                 download=True):
        now = dt.datetime.now()

        if download:
            self.check_db()
            dat_url = ('http://www.welserver.com/WEL1060/'
                       F'WEL_log_{now.year}_{now.month:02d}.xls')
            filepath = (self.db_path + F'WEL_log_{now.year}_{now.month:02d}.xls')
            downfile = wget.download(dat_url, filepath)
            print()
            if os.path.exists(filepath):
                shutil.move(downfile, filepath)

        self.stitch([now, now])


    """
    From a filepath, load that data.
    Columns with all NaNs are dropped.

    ADDED COLUMNS:
    dateandtime : combined datetime object for each row.
    power_tot : TAH_W + HP_W
    T_diff : living_T - outside_T
    eff_ma : day length rolling average of efficiency

    filepath : filepath for data file.
    keepdata : boolean keep downloaded data file. Default False.
    """
    def read_log(self,
                  filepath):
        try:
            data = pd.read_excel(filepath)
        except:
            data = pd.read_csv(filepath, sep='\t',
                                    index_col=False, na_values=['?'])

        for col in data.columns:
            if ('Date' not in col) and ('Time' not in col):
                data[col] = data[col].astype(np.float64)

        data.Date = data.Date.apply(lambda date:
                                    dt.datetime.strptime(date, "%m/%d/%Y"))
        data.Time = data.Time.apply(lambda time:
                                    dt.datetime.strptime(time,
                                                         "%H:%M:%S").time())

        # DAYLIGHT SAVINGS CORRECTOR
        dls = dt.timedelta(hours=1)

        data['dateandtime'] = [dt.datetime.combine(date, time) + dls
                                 for date, time in zip(data.Date,
                                                       data.Time)]
        data.index = data['dateandtime']

        # Shift power meter data by one sample for better alignment with others
        data.HP_W  = data.HP_W.shift(-1)
        data.TAH_W  = data.TAH_W.shift(-1)

        # Additional calculated columns
        data['power_tot'] = data.HP_W + data.TAH_W
        data['T_diff'] = data.living_T - data.outside_T
        data['eff_ma'] = data.eff.rolling('12H').mean()
        cops = (((1.15 * 0.37 * data.TAH_fpm)
                  * (np.abs(data.TAH_out_T - data.TAH_in_T)))
                  / (data.HP_W / 1000))
        cops[cops > 10] = np.nan
        data['COP'] = cops
        data['well_W'] = ((0.0008517177 * 1e3) * 4.186
                          * (np.abs(data.loop_out_T - data.loop_in_T)))
        well_COP = data.well_W / (data.HP_W / 1000)
        well_COP[well_COP > 10] = np.nan
        data['well_COP'] = well_COP

        return data


    """
    Check if the last month's log has been downloaded, and download if not.

    month : specify month to download to db. If no month is specified, download
            the previous month.

    returns a string with the downloaded month.
    """
    def check_db(self,
                 month=None,
                 forcedl=False):
        if not os.path.exists(self.db_path):
            os.mkdir(self.db_path)
        if month is None:
            month = dt.datetime.now() - relativedelta(months=1)
        prev_url = ('http://www.welserver.com/WEL1060/'
                    F'WEL_log_{month.year}_{month.month:02d}.xls')
        prev_db_path = (self.db_path + F'WEL_log_{month.year}'
                                       F'_{month.month:02d}.xls')
        if (not os.path.exists(prev_db_path)) or forcedl:
            try:
                print(F'{month.year}-{month.month}:')
                wget.download(prev_url, prev_db_path)
                print()
            except:
                print('Not available for download')
                

    """
    Redownload all months since 2020-2-1 to db.
    """
    def refresh_db(self):
        first = dt.date(2020, 2, 1)
        now = dt.datetime.now().date()
        num_months = (now.year - first.year) * 12 + now.month - first.month
        monthlist = [first + relativedelta(months=x)
                     for x in range(num_months + 1)]
        [self.check_db(month=month, forcedl=True) for month in monthlist]


    """
    Load correct months of data based on timerange.
    """
    def stitch(self,
               timerange):
        load_new = False
        if self.data is not None:
            if ((self.data.dateandtime.iloc[0] > timerange[0]) or
                (self.data.dateandtime.iloc[-1] < timerange[1])):
                load_new = True
        else:
            load_new = True
        if load_new:
            num_months = ((timerange[1].year - timerange[0].year) * 12
                          + timerange[1].month - timerange[0].month)
            monthlist = [timerange[0] + relativedelta(months=x)
                         for x in range(num_months + 1)]
            loadedstring = [F'{month.year}-{month.month}'
                              for month in monthlist]
            print(F'loaded: {loadedstring}')
            datalist = [self.read_log(self.db_path + F'WEL_log_{month.year}'
                                       F'_{month.month:02d}.xls')
                        for month in monthlist]
            self.data = pd.concat(datalist)


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
                      timerange):
        if timerange == None:
            timerange = [self.data.dateandtime.iloc[0],
                         self.data.dateandtime.iloc[-1]]
            return timerange
        if timerange[0] == 'none':
            timerange[0] = self.data.dateandtime.iloc[0]
        else:
            if type(timerange[0]) is str:
                timerange[0] = dt.datetime.fromisoformat(timerange[0])
        if timerange[1] == 'none':
            timerange[1] = self.data.dateandtime.iloc[-1]
        else:
            if type(timerange[1]) is str:
                timerange[1] = dt.datetime.fromisoformat(timerange[1])

        return timerange



    """
    Converts variable name string into object data string, to be evaluated as
    a python expression.

    string : expression string to be modified.
    optional mask : indicates this is for status mask data, including a call to
                    remOffset
    """
    def varExprParse(self,
                     string,
                     mask=False):
        splitString = re.split('(\\()|(\\))|(\s)', string)
        splitString = [w for w in splitString if w is not None]

        expr = ""
        for word in splitString:
            possibleVars = [var for var in self.data.columns if var in word]
            if len(possibleVars) > 0:
                foundVar = max(possibleVars, key=len)
                if mask:
                    rst = ("self.remOffset(self.data['"
                           + foundVar + "'][tmask])")
                else:
                    rst = "self.data['" + foundVar + "'][tmask]"
                expr += word.replace(foundVar, rst)
            else:
                expr += word

        return expr


    """
    Adds day/night background shading based on calculated sunrise/sunset times
    to the specified axes.

    axes : axes to plot on.
    timerange : timerange to plot on.
    """
    def plotNightime(self,
                     axes,
                     timerange):
        axes.autoscale(enable=False)
        dayList = [(timerange[0] + dt.timedelta(days=x - 1)).date()
                    for x in range((timerange[1] - timerange[0]).days + 3)]

        for day in dayList:
            day = dt.datetime.combine(day, dt.datetime.min.time())
            sunrise = (sun.sunrise(self.loc.observer, date=day)
                       - dt.timedelta(hours=4))
            sunset = (sun.sunset(self.loc.observer,date=day)
                      - dt.timedelta(hours=4))
            timelist = [day, sunrise - dt.timedelta(seconds=1), sunrise,
                        sunset, sunset + dt.timedelta(seconds=1),
                        day + dt.timedelta(days=1)]
            limits = axes.get_ylim()
            axes.fill_between(timelist, np.full(len(timelist), limits[0]),
                              np.full(len(timelist), limits[1]),
                              where=[True, True, False, False, True, True],
                              facecolor='black', alpha=0.1)


    """
    Remove plotting offset from status channel data
    status : data from which to remove offset
    """
    def remOffset(self,
                  status):
        mask = np.array(status) % 2
        mask[mask == 0.] = np.nan
        return mask


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
    optional statusmask : string describing which binary channels to use as a
                          mask for all plotted variables.
    optional axes : axes to draw plot on instead of default figure.
    optional nighttime : adds day/night shading to plot.
    optional **kwargs : passed on to plot function

    returns plotted data as dictionary of dataframes
    """
    def plotVar(self,
                y,
                x='dateandtime',
                xunits='Time',
                yunits='None',
                timerange=None,
                statusmask=None,
                axes=None,
                nighttime=True,
                **kwargs):
        timerange = self.timeCondition(timerange)
        self.stitch(timerange)
        if type(y) is not list: y = [y]

        tmask = ((self.data.dateandtime > timerange[0])
                 & (self.data.dateandtime < timerange[1]))
        p_locals = locals()
        if statusmask is not None:
            smask = eval(self.varExprParse(statusmask, mask=True), p_locals)
        else: smask = np.full(tmask.sum(), True)

        plotx = eval(self.varExprParse(x), p_locals)
        ploty = [eval(self.varExprParse(expr), p_locals) for expr in y]

        if axes is None:
            fig = plt.figure(figsize=self.figsize)
            axes = plt.gca()

        if ('time' or 'date') in x:
            lines = {label:axes.plot_date(plotx, plotDatum * smask, '-',
                                          label=label, **kwargs)
                     for label, plotDatum in zip(y, ploty)}
            if statusmask is not None:
                [axes.plot_date(plotx, plotDatum, fmt='-', alpha=0.3,
                                color=lines[label][0].get_color(), **kwargs)
                 for label, plotDatum in zip(y, ploty)]
            plt.setp(axes.get_xticklabels(), rotation=20, ha='right')
            axes.set_xlim(timerange)

            if nighttime:
                self.plotNightime(axes, timerange)
        else:
            [plt.plot(plotx, plotDatum, '.', label=label, **kwargs)
             for label, plotDatum in zip(y, ploty)]
            axes.set_xlabel(xunits)
            axes.set_xlim((np.nanmin(plotx), np.nanmax(plotx)))

        if yunits is 'None':
            usedVars = [var for var in self.data.columns if var in y[0]]
            if usedVars[0][-1] is 'T':
                yunits = "Temperature [°C]"
            if usedVars[0][-1] is 'W':
                yunits = "Power [W]"
            if usedVars[0][-3:] is 'fpm':
                yunits = "Windspeed [m/s]"
        axes.set_ylabel(yunits)
        axes.yaxis.set_label_position("right")
        axes.yaxis.tick_right()
        # axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',
        #             ncol=len(y), mode="expand", borderaxespad=0)
        axes.legend(bbox_to_anchor=(-0.01, 1,), loc='upper right',
                    borderaxespad=0)
        axes.grid(True)
        plt.tight_layout()

        return {label:datum * smask for label, datum in zip(y, ploty)}


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
        timerange = self.timeCondition(timerange)
        self.stitch(timerange)

        tmask = ((self.data.dateandtime > timerange[0])
               & (self.data.dateandtime < timerange[1]))

        p_locals = locals()
        plotx = eval(self.varExprParse('dateandtime'), p_locals)
        ploty = [eval(self.varExprParse(stat), p_locals)
                    for stat in status_list]

        if axes is None:
            fig = plt.figure(figsize=(self.figsize[0], self.figsize[1] * 0.75))
            axes = plt.gca()

        [axes.plot_date(plotx, plotDatum, fmt='-', label=label)
            for label, plotDatum in zip(labels, ploty)]

        axes.set_ylim((-0.75, 2 * (len(status_list) - 1) + 1.75))
        if nighttime:
            self.plotNightime(axes, timerange)

        plt.setp(axes.get_xticklabels(), rotation=20, ha='right')
        axes.set_yticks(np.arange(0, 16, 2))
        axes.set_yticklabels(labels)
        axes.yaxis.set_label_position("right")
        axes.yaxis.tick_right()
        axes.grid(True)
        axes.set_xlim(timerange)
        plt.tight_layout()
