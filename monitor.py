import WELServer
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

dat = WELServer.WELData()
timerange = [datetime.now() - timedelta(hours=24), 'none']
fig, axes = plt.subplots(2, 1,
                         sharex=True,
                         figsize=(11,7),
                         gridspec_kw={'height_ratios': [1, 0.7]})

dat.plotVar('dateandtime',
            ['gas_refrig_T',
             'liqu_refrig_T',
             'loop_in_T',
             'loop_out_T',
             'outside_T',
             'living_T',
             'base_T'],
            timerange=timerange,
            axes=axes[0])

# dat.plotVar('dateandtime',
#             'eff_D',
#             timerange=timerange,
#             axes=axes[1])

dat.plotStatus(timerange=timerange,
               axes=axes[1])

fig.show()
