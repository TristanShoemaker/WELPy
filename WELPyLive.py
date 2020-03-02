class LiveWELData:
    url = "http://192.168.68.101:5150/wel.xml"
    http = urllib3.PoolManager()
    data = None
    beginTime = None


    def __init__(self):
        initData = self.getLiveData()
        row = {}
        for item in initData:
            row[item['name']] = item['value']

        row['date'] = dt.datetime.strptime(row['date'], "%m/%d/%Y")
        row['time'] = dt.datetime.strptime(row['time'], "%H:%M:%S")
        row['DateTime'] = dt.datetime.combine(row['date'].date(),
                                              row['time'].time())
        del row['date'], row['time']
        self.data = pd.DataFrame(row, index=[0])
        self.beginTime = row['DateTime']


    def getLiveData(self):
        response = self.http.request('GET', self.url)

        try:
            liveData = xmltodict.parse(response.data)['devices']['device']
        except:
            print("Failed to parse xml from response (%s)" % traceback.format_exc())

        return liveData


    def addData(self,
                liveData):
        row = {}
        for item in liveData:
            row[item['name']] = item['value']

        row['date'] = dt.datetime.strptime(row['date'], "%m/%d/%Y")
        row['time'] = dt.datetime.strptime(row['time'], "%H:%M:%S")
        row['DateTime'] = dt.datetime.combine(row['date'].date(),
                                              row['time'].time())
        del row['date'], row['time']
        self.data = self.data.append(row, ignore_index=True)


    def livePlot(self,
                 var,
                 unit,
                 delay):
        import matplotlib.animation as animation

        fig = plt.figure(figsize=(7,5))
        ax = fig.add_subplot(1,1,1)
        plt.xlabel("Time")
        plt.ylabel(unit)
        plt.grid(True)
        fig.autofmt_xdate()

        def animate(i):
            self.addData(self.getLiveData())
            ax.clear()
            ax.plot_date(self.data.DateTime, self.data[var])

        ani = animation.Animation(fig, animate, 1000 * delay)
        plt.show()
