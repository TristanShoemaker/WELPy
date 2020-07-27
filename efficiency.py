import WELServer
import matplotlib.pyplot as plt
import numpy as np


dat = WELServer.WELData()

timerange = dat.time_from_args()

fig, axes = plt.subplots(5, 1,
                         sharex=True,
                         figsize=(12,10),
                         gridspec_kw={'height_ratios': [1, 0.7, 0.7, 0.7, 0.7]})

temps = dat.plotVar(['TAH_in_T',
                     'TAH_out_T',
                     # 'gas_refrig_T',
                     # 'liqu_refrig_T',
                     'loop_in_T',
                     'loop_out_T',
                     'outside_T',
                     # 'living_T',
                     # 'wood_fire_T'
                     ],
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
            # statusmask='heat_1_b',
            axes=axes[3])

cops = dat.plotVar(['COP',
                    'well_COP',
                    "COP.rolling('1D').mean()"],
            yunits='COP',
            timerange=timerange,
            statusmask='heat_1_b',
            axes=axes[4])


cop = np.nan_to_num(cops['COP'], nan=np.nan, posinf=np.nan, neginf=np.nan)
well_cop = np.nan_to_num(cops['well_COP'], nan=np.nan, posinf=np.nan,
                                           neginf=np.nan)
mean_cop = np.nanmean(cop)
mean_well_cop = np.nanmean(well_cop)

print(F'COPS mean: {np.nanmean(mean_cop)}')
print(F'well COPS mean: {np.nanmean(mean_well_cop)}')

plt.subplots_adjust(hspace=0.01)
plt.show()
