import WELServer
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument('-a', action='store_true',
                    help='plot all data')
parser.add_argument('-t', type=int, action='store',
                    help='specify number of hours into past to '
                         'plot. Example: <-t 12> plots the past 12 hours.')
parser.add_argument('-r', type=str, action='store', nargs=2,
                    help='specify start and end time to plot as two strings '
                         'in iso format. Example: <-r \'2020-03-22 12:00\' '
                         '\'2020-03-22 15:00\'>')

args = parser.parse_args()

if args.t:
    timerange = [datetime.now() - timedelta(hours=args.t), 'none']
if args.a:
        timerange = ['none','none']
if args.r:
    print(args.r)
    timerange = [datetime.fromisoformat(args.r[0]),
                 datetime.fromisoformat(args.r[1])]
if len(sys.argv) < 2:
    timerange = [datetime.now() - timedelta(hours=12), 'none']

dat = WELServer.WELData()

fig, axes = plt.subplots(5, 1,
                         sharex=True,
                         figsize=(12,10),
                         gridspec_kw={'height_ratios': [1, 0.7, 0.7, 0.7, 0.7]})

dat.plotVar(['TAH_in_T',
             'TAH_out_T',
             'gas_refrig_T',
             'liqu_refrig_T',
             'loop_in_T',
             'loop_out_T',
             'outside_T',
             'living_T'],
            timerange=timerange,
            statusmask='heat_1_b',
            axes=axes[0])

dat.plotStatus(timerange=timerange,
               axes=axes[1])

dat.plotVar(['HP_W / 1000',
             'well_W'],
            yunits='kW',
            timerange=timerange,
            statusmask='heat_1_b',
            axes=axes[2])

dat.plotVar(['TAH_fpm'],
            timerange=timerange,
            yunits='Wind Speed [m/s]',
            statusmask='heat_1_b',
            axes=axes[3])

cops = dat.plotVar(['COP',
                    'well_COP'],
            yunits='COP',
            timerange=timerange,
            statusmask='heat_1_b',
            axes=axes[4])
axes[4].set_ylim((1, 5))

cop = np.nan_to_num(cops['COP'], nan=np.nan, posinf=np.nan, neginf=np.nan)
well_cop = np.nan_to_num(cops['well_COP'], nan=np.nan, posinf=np.nan,
                                           neginf=np.nan)

print(F'COPS mean: {np.nanmean(cop)}')
print(F'well COPS mean: {np.nanmean(well_cop)}')

plt.subplots_adjust(hspace=0.01)
plt.show()
