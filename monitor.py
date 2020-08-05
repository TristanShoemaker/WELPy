import WELServer
import matplotlib.pyplot as plt
import numpy as np


dat = WELServer.WELData(data_source='Pi')

# timerange = dat.time_from_args()

fig, axes = plt.subplots(3, 1,
                         sharex=True,
                         figsize=(12,9),
                         gridspec_kw={'height_ratios': [1, 0.3, 0.3]})

dat.plotVar(['TAH_in_T',
             'TAH_out_T',
             # 'gas_refrig_T',
             # 'liqu_refrig_T',
             'loop_in_T',
             'loop_out_T',
             'outside_T',
             'living_T',
             'trist_T'],
            statusmask='heat_1_b',
            axes=axes[0])

dat.plotStatus(axes=axes[1])

full_range_delta = dat.timerange[1] - dat.timerange[0]
rolling_interval = np.clip(round((full_range_delta.total_seconds() / 3600) / 6), 1, 6)
dat.plotVar([F"COP.rolling('{rolling_interval}H').mean()"],
        yunits=F'COP {rolling_interval} Hr Rolling Mean',
        axes=axes[2])

# dat.plotVar(['TAH_fpm'],
#             timerange=timerange,
#             yunits='Wind Speed [m/s]',
#             # statusmask='heat_1_b',
#             axes=axes[2])

# dat.plotVar(['desup_T',
#              'desup_return_T',
#              'house_hot_T',
#              'buderus_h2o_T',
#              'tank_h2o_T'],
#              timerange=timerange,
#              axes=axes[2])

# dat.plotVar(['eff_ma',
#             'eff_D'],
#             yunits='Efficiency W/C',
#             timerange=timerange,
#             axes=axes[3])

# cops = dat.plotVar(['COP',
#                     'well_COP'],
#             yunits='COP',
#             timerange=timerange,
#             statusmask='heat_1_b',
#             axes=axes[3])


plt.subplots_adjust(hspace=0.01)
plt.show()
