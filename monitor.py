import WELServer
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import argparse

dat = WELServer.WELData()

parser = argparse.ArgumentParser()
parser.add_argument('hours', type=int, nargs=1,
                    help='number of hours to plot')
parser.add_argumetn('-a', action='store_true')
args = parser.parse_args()

if not args.a:
    timerange = [datetime.now() - timedelta(hours=args.hours[0]), 'none']
else:
    timerange = ['none','none']
    
fig, axes = plt.subplots(3, 1,
                         sharex=True,
                         figsize=(12,8),
                         gridspec_kw={'height_ratios': [1, 0.6, 0.6]})

dat.plotVar([
             'TAH_in_T',
             'TAH_out_T',
             'gas_refrig_T',
             'liqu_refrig_T',
             'loop_in_T',
             'loop_out_T',
             'outside_T',
             'living_T',
             'base_T'],
            timerange=timerange,
            axes=axes[0])

dat.plotStatus(timerange=timerange,
               axes=axes[1])

dat.plotVar(['eff_ma',
            'eff_D'],
            yunits='Efficiency W/C',
            timerange=timerange,
            axes=axes[2])



plt.show()
