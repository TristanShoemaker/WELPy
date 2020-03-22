import WELServer
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('-a', action='store_true',
                    help='plot all data')
parser.add_argument('-t', type=int,
                    help='specify number of hours into past to '
                         'plot. Example: <-t 12> plots the past 12 hours.')
parser.add_argument('-r', type=str, action='store', nargs=2,
                    help='specify start and end time to plot as two strings '
                         'in iso format. Example: <-r \'2020-03-22 12:00\' '
                         '\'2020-03-22 15:00\'>')

args = parser.parse_args()

if args.t is not None:
    timerange = [datetime.now() - timedelta(hours=args.t), 'none']
if args.a is not None:
        timerange = ['none','none']
if args.r is not None:
    print(args.r)
    timerange = [datetime.fromisoformat(args.r[0]),
                 datetime.fromisoformat(args.r[1])]
if (args.t is None) and (args.a is None) and (args.r is None):
    timerange = [datetime.now() - timedelta(hours=12), 'none']


dat = WELServer.WELData()

fig, axes = plt.subplots(4, 1,
                         sharex=True,
                         figsize=(12,9),
                         gridspec_kw={'height_ratios': [1, 0.6, 1, 0.5]})
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

dat.plotVar(['desup_T',
             'desup_return_T',
             'house_hot_T',
             'buderus_h2o_T',
             'tank_h2o_T'],
             timerange=timerange,
             axes=axes[2])

dat.plotVar(['eff_ma',
            'eff_D'],
            yunits='Efficiency W/C',
            timerange=timerange,
            axes=axes[3])


plt.subplots_adjust(hspace=0)
plt.show()
