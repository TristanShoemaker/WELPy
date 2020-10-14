import WELServer
import matplotlib.pyplot as plt
import numpy as np


dat = WELServer.WELData(data_source='WEL')

fig, axes = plt.subplots(4, 1,
                         sharex=True,
                         figsize=(9, 9.5),
                         gridspec_kw={'height_ratios': [0.3, 0.4, 0.6, 0.2]})

stat = dat.plotStatus(axes=axes[0])

dat.plotVar(['living_T',
             'trist_T',
             'base_T'],
            statusmask='heat_1_b',
            axes=axes[1])

dat.plotVar(['TAH_in_T',
             'TAH_out_T',
             'loop_in_T',
             'loop_out_T',
             'liqu_refrig_T',
             'gas_refrig_T'],
            statusmask='heat_1_b',
            axes=axes[2])
dat.plotVar(['outside_T'], axes=axes[2], nighttime=False)
outside_T_line = [x for x in axes[2].get_lines()
                  if x.get_label() == "outside_T"][0]
outside_T_line.set(lw=2.5)

full_range_delta = dat.timerange[1] - dat.timerange[0]
rolling_interval = np.clip(round((full_range_delta.total_seconds()
                                  / 3600) / 4), 1, 24)
dat.plotVar([F"COP.rolling('{rolling_interval}H').mean()"],
            yunits=F'COP {rolling_interval} Hr Mean',
            axes=axes[3])
axes[3].get_legend().remove()


plt.subplots_adjust(hspace=0.02)
plt.show()
