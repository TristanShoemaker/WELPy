import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt
from dateutil.relativedelta import relativedelta
import re
from wget import download
import os
import sys
from shutil import move
import argparse
from astral import sun, LocationInfo
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dateutil import tz


class WELData:
    figsize = (11, 5)        # default matplotlib figure size
    loc = LocationInfo('Home', 'MA', 'America/New_York', 42.485557, -71.433445)
    dl_db_path = './log_db/'
    db_tzone = tz.gettz('UTC')
    to_tzone = tz.gettz('America/New_York')
    mongo_db = None
    data_source = None
    now = None
    data = None
    timerange = None

    """
    Initialize the Weldata Object.
    If filepath is given, data will be read from the file, otherwise this
    month's log is downloaded and read.
    """
    def __init__(self,
                 data_source='Pi',
                 timerange=None,
                 WEL_download=False):
        self.data_source = data_source
        self.now = dt.datetime.now().astimezone(self.to_tzone)
        if timerange is None:
            self.timerange = self.time_from_args()
        elif type(timerange[0]) is str:
            self.timerange = self.time_from_args(timerange)
        else:
            self.timerange = self.timeCondition(timerange)
        self.timerange = [time.replace(tzinfo=self.to_tzone)
                          for time in self.timerange]

        if self.data_source == 'WEL':
            if WEL_download:
                self.check_dl_db()
                dat_url = ("http://www.welserver.com/WEL1060/"
                           + F"WEL_log_{self.now.year}"
                           + F"_{self.now.month:02d}.xls")
                downfilepath = (self.dl_db_path
                                + F"WEL_log_{self.now.year}"
                                + F"_{self.now.month:02d}.xls")
                downfile = download(dat_url, downfilepath)
                print()
                if os.path.exists(downfilepath):
                    move(downfile, downfilepath)

            self.stitch()
        elif self.data_source == 'Pi':
            if sys.platform == 'linux':
                address = "mongodb://localhost:27017"
                client = MongoClient(address)
            elif ConnectionFailure:
                address = "mongodb://192.168.68.101:27017"
                client = MongoClient(address)
            else:
                raise("Unrecognized platform")
            self.mongo_db = client.WEL
            self.stitch()
        else:
            print("Valid data sources are 'Pi' or 'WEL'")
            quit()

    def time_from_args(self,
                       arg_string=None):
        parser = argparse.ArgumentParser()
        parser.add_argument('-t', type=int, action='store',
                            help='specify number of hours into past to plot. '
                                 'Example: <-t 12> plots the past 12 hours.')
        parser.add_argument('-r', type=str, action='store', nargs=2,
                            help='specify start and end time to plot as two '
                                 'strings in iso format. Example: '
                                 '<-r \'2020-03-22 12:00\' '
                                 '\'2020-03-22 15:00\'>')

        args = parser.parse_args(arg_string)
        timerange = None

        if args.t:
            timerange = [self.now - dt.timedelta(hours=args.t), 'none']
        if args.r:
            timerange = args.r

        return self.timeCondition(timerange)

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
        except Exception:
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

        data['dateandtime'] = [dt.datetime.combine(date, time)
                               for date, time in zip(data.Date,
                                                     data.Time)]
        data.index = data['dateandtime']
        data = data.tz_localize(tz.gettz('EST'))
        data = data.tz_convert(self.to_tzone)
        data.drop(columns=['Date', 'Time'])

        data = pd.concat((data, self.calced_cols(data)), axis=1)

        return data

    def calced_cols(self,
                    frame):
        out_frame = pd.DataFrame()

        # Additional calculated columns
        out_frame['T_diff'] = frame.living_T - frame.outside_T
        cops = (((1.15 * 0.37 * frame.TAH_fpm)
                * (np.abs(frame.TAH_out_T - frame.TAH_in_T)))
                / (frame.HP_W / 1000))
        cops[cops > 12] = np.nan
        out_frame['COP'] = cops
        out_frame['well_W'] = ((0.0008517177 * 1e3) * 4.186
                               * (np.abs(frame.loop_out_T - frame.loop_in_T)))
        well_COP = out_frame.well_W / (frame.HP_W / 1000)
        well_COP[well_COP > 10] = np.nan
        out_frame['well_COP'] = well_COP

        return out_frame

    """
    Check if the last month's log has been downloaded, and download if not.

    month : specify month to download to db. If no month is specified, download
            the previous month.

    returns a string with the downloaded month.
    """
    def check_dl_db(self,
                    month=None,
                    forcedl=False):
        if not os.path.exists(self.dl_db_path):
            os.mkdir(self.dl_db_path)
        if month is None:
            month = self.now - relativedelta(months=1)
        prev_url = ('http://www.welserver.com/WEL1060/'
                    F'WEL_log_{month.year}_{month.month:02d}.zip')
        prev_db_path_zip = (self.dl_db_path + F'WEL_log_{month.year}'
                                              F'_{month.month:02d}.zip')
        prev_db_path_xls = (self.dl_db_path + F'WEL_log_{month.year}'
                                              F'_{month.month:02d}.xls')
        if (not os.path.exists(prev_db_path_xls)) or forcedl:
            try:
                # print(prev_db_path_zip)
                print(F'{month.year}-{month.month}:')
                download(prev_url, prev_db_path_zip)
                print()
                os.system(F'unzip {prev_db_path_zip} -d {self.dl_db_path}'
                          F';rm {prev_db_path_zip}')
                print()
            except Exception:
                print('Not available for download')

    """
    Redownload all months since 2020-3-1 to db.
    """
    def refresh_db(self):
        first = dt.date(2020, 3, 1)
        num_months = ((self.now.year - first.year) * 12
                      + self.now.month - first.month)
        monthlist = [first + relativedelta(months=x)
                     for x in range(num_months + 1)]
        [self.check_dl_db(month=month, forcedl=True) for month in monthlist]

    """
    Load correct months of data based on timerange.
    """
    def stitch(self):
        if self.data_source == 'WEL':
            load_new = False
            if self.data is not None:
                if ((self.data.dateandtime.iloc[0] > self.timerange[0]) or
                   (self.data.dateandtime.iloc[-1] < self.timerange[1])):
                    load_new = True
            else:
                load_new = True
            if load_new:
                num_months = ((self.timerange[1].year - self.timerange[0].year)
                              * 12 + self.timerange[1].month
                              - self.timerange[0].month)
                monthlist = [self.timerange[0] + relativedelta(months=x)
                             for x in range(num_months + 1)]
                loadedstring = [F'{month.year}-{month.month}'
                                for month in monthlist]
                print(F'loaded: {loadedstring}')
                datalist = [self.read_log(self.dl_db_path
                                          + F'WEL_log_{month.year}'
                                          + F'_{month.month:02d}.xls')
                            for month in monthlist]
                # print(datalist)
                self.data = pd.concat(datalist)

        if self.data_source == 'Pi':
            query = {'dateandtime': {'$gte': self.timerange[0]
                                     .astimezone(self.db_tzone),
                                     '$lte': self.timerange[1]
                                     .astimezone(self.db_tzone)}}
            # print(F"#DEBUG: query: {query}")
            self.data = pd.DataFrame(list(self.mongo_db.data.find(query)))
            if len(self.data) == 0:
                raise Exception("No data came back from mongo server.")
            self.data.index = self.data['dateandtime']
            self.data.drop(columns=['dateandtime'], inplace=True)
            # print(self.data.columns)
            self.data = self.data.tz_localize(self.db_tzone)
            self.data = self.data.tz_convert(self.to_tzone)
            # print(F"#DEBUG: timerange from: {self.data.index[-1]}"
            #       "to {self.data.index[0]}")
            # For now, calculate columns at data load
            self.data = pd.concat((self.data, self.calced_cols(self.data)),
                                  axis=1)

        # Shift power meter data by one sample for better alignment with others
        self.data.HP_W = self.data.HP_W.shift(-1)
        self.data.TAH_W = self.data.TAH_W.shift(-1)

    """
    Returns list of all column names.
    """
    def vars(self):
        return [col for col in self.data.columns]

    """
    Takes a list with a start and end time. If either is 'none', defaults to
    12 hours ago or latest time respectively. Converts iso strings to datetime,
    keeps datetime as datetime.
    """
    def timeCondition(self,
                      timerange):
        if timerange is None:
            timerange = [self.now - dt.timedelta(hours=12), self.now]
            return timerange
        if timerange[0] == 'none':
            timerange[0] = self.now - dt.timedelta(hours=12)
        else:
            if type(timerange[0]) is str:
                timerange[0] = dt.datetime.fromisoformat(timerange[0])
        if timerange[1] == 'none':
            timerange[1] = self.now
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
        splitString = re.split('(\\()|(\\))|(\\s)', string)
        splitString = [w for w in splitString if w is not None]

        expr = ""
        for word in splitString:
            possibleVars = [var for var in self.data.columns if var in word]
            if len(possibleVars) > 0:
                foundVar = max(possibleVars, key=len)
                if mask:
                    rst = ("self.remOffset(self.data['"
                           + foundVar + "'])")
                else:
                    rst = "self.data['" + foundVar + "']"
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
    def plotNighttime(self,
                      axes=None,
                      plot=True):
        dayList = [(self.timerange[0] + dt.timedelta(days=x - 1)).date()
                   for x in range((self.timerange[1]
                                   - self.timerange[0]).days + 3)]
        for day in dayList:
            day = dt.datetime.combine(day, dt.datetime.min.time())
            sunrise = sun.sunrise(self.loc.observer, date=day,
                                  tzinfo=self.to_tzone)
            sunset = sun.sunset(self.loc.observer, date=day,
                                tzinfo=self.to_tzone)
            # print(F"#DEBUG: sunrise: {sunrise}, sunset: {sunset}")
            timelist = [day, sunrise - dt.timedelta(seconds=1), sunrise,
                        sunset, sunset + dt.timedelta(seconds=1),
                        day + dt.timedelta(days=1)]

            if plot:
                axes.autoscale(enable=False)
                limits = axes.get_ylim()
                axes.fill_between(timelist, np.full(len(timelist), limits[0]),
                                  np.full(len(timelist), limits[1]),
                                  where=[True, True, False, False, True, True],
                                  facecolor='black', alpha=0.05)
        return timelist

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
                statusmask=None,
                maskghost=True,
                axes=None,
                nighttime=True,
                **kwargs):
        if type(y) is not list:
            y = [y]
        p_locals = locals()
        if statusmask is not None:
            smask = eval(self.varExprParse(statusmask, mask=True), p_locals)
        else:
            smask = np.full(np.shape(self.data.index), True)

        # plotx = eval(self.varExprParse(x), p_locals)
        ploty = [eval(self.varExprParse(expr), p_locals) for expr in y]

        if axes is None:
            fig = plt.figure(figsize=self.figsize)
            axes = plt.gca()

        if ('time' or 'date') in x:
            lines = {label: axes.plot_date(plotDatum.index, plotDatum * smask,
                                           '-', label=label, **kwargs)
                     for label, plotDatum in zip(y, ploty)}
            if statusmask is not None and maskghost:
                [axes.plot_date(plotDatum.index, plotDatum, fmt='-', alpha=0.3,
                                color=lines[label][0].get_color(), **kwargs)
                 for label, plotDatum in zip(y, ploty)]
            plt.setp(axes.get_xticklabels(), rotation=20, ha='right')
            axes.set_xlim(self.timerange)
            if nighttime:
                self.plotNighttime(axes=axes)
        # else:
        #     [plt.plot(plotx, plotDatum, '.', label=label, **kwargs)
        #      for label, plotDatum in zip(y, ploty)]
        #     axes.set_xlabel(xunits)
        #     axes.set_xlim((np.nanmin(plotx), np.nanmax(plotx)))

        if yunits == 'None':
            usedVars = [var for var in self.data.columns if var in y[0]]
            if usedVars[0][-1] == 'T':
                yunits = "Temperature / °C"
            if usedVars[0][-1] == 'W':
                yunits = "Power / W"
            if usedVars[0][-3:] == 'fpm':
                yunits = "Windspeed / m/s"
        axes.set_ylabel(yunits)
        axes.yaxis.set_label_position("right")
        axes.yaxis.tick_right()
        # axes.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',
        #             ncol=7, mode="expand", borderaxespad=0)
        # axes.legend(bbox_to_anchor=(-0.01, 1,), loc='upper right',
        #             borderaxespad=0)
        axes.legend(borderaxespad=0, loc='center left')
        axes.grid(True)
        plt.tight_layout()

        return {label: datum * smask for label, datum in zip(y, ploty)}

    """
    Plots all hardcoded status variables against time.

    optional timerange : 2 length array with start and end time as iso string,
                         datetime object or if 'none' defaults to start/end
                         time in that position.
    optional axes : axes to draw plot on instead of default figure.
    optional nighttime : adds day/night shading to plot.
    """
    def plotStatus(self,
                   axes=None,
                   nighttime=True,
                   status_list=['aux_heat_b',
                                'heat_1_b',
                                'heat_2_b',
                                'rev_valve_b',
                                'TAH_fan_b',
                                'zone_1_b',
                                'zone_2_b',
                                'humid_b']):
        labels = [stat[:-2] for stat in status_list]

        p_locals = locals()
        # plotx = eval(self.varExprParse('dateandtime'), p_locals)
        ploty = [eval(self.varExprParse(stat), p_locals)
                 for stat in status_list]

        if axes is None:
            fig = plt.figure(figsize=(self.figsize[0], self.figsize[1] * 0.75))
            axes = plt.gca()

        [axes.plot_date(plotDatum.index, plotDatum, fmt='-', label=label)
            for label, plotDatum in zip(labels, ploty)]

        axes.set_ylim((-0.75, 2 * (len(status_list) - 1) + 1.75))
        if nighttime:
            self.plotNighttime(axes=axes)

        plt.setp(axes.get_xticklabels(), rotation=20, ha='right')
        axes.set_yticks(np.arange(0, 16, 2))
        axes.set_yticklabels(labels)
        axes.yaxis.set_label_position("right")
        axes.yaxis.tick_right()
        axes.grid(True)
        axes.set_xlim(self.timerange)
        plt.tight_layout()
