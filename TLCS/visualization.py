from matplotlib import pyplot as plt
import os

class Visualization:
    def __init__(self, path, dpi):
            self._path = path
            self._dpi = dpi


    def save_data_and_plot(self, data, filename, xlabel, ylabel):
        """
        Produce a plot of performance of the agent over the session and save the relative data to txt
        """
        min_val = min(data)
        max_val = max(data)

        plt.rcParams.update({'font.size': 24})  # set bigger font size

        plt.plot(data)
        plt.ylabel(ylabel)
        plt.xlabel(xlabel)
        plt.margins(0)
        plt.ylim(min_val - 0.05 * abs(min_val), max_val + 0.05 * abs(max_val))
        fig = plt.gcf()
        fig.set_size_inches(20, 11.25)
        fig.savefig(os.path.join(self._path, 'plot_'+filename+'.png'), dpi=self._dpi)
        plt.close("all")

        with open(os.path.join(self._path, 'plot_'+filename + '_data.txt'), "w") as file:
            for value in data:
                    file.write("%s\n" % value)
    

    def save_data_and_plot_2(self, data1, data2, filename, xlabel, ylabel, y2label):
        """
        Produce a plot of performance of the agent over the session and save the relative data to txt
        Supports dual y-axis if y2label is provided.
        """
        # min_val1, max_val1 = min(data1), max(data1)
        min_val2, max_val2 = min(data2), max(data2) if data2 else (None, None)

        plt.rcParams.update({'font.size': 24})  # set bigger font size

        fig, ax1 = plt.subplots()

        ax1.plot(data1, color='blue', label=ylabel)
        ax1.plot(data2, color='red', label=y2label)
        ax1.set_xlabel(xlabel)
        ax1.set_ylabel('Vehicles', color='black')
        ax1.margins(0)
        ax1.set_ylim(min_val2 - 0.05 * abs(min_val2), max_val2 + 0.05 * abs(max_val2))
        ax1.legend(loc='best')

        # if y2label and data2:
        #     ax2 = ax1.twinx()
        #     ax2.plot(data2, color='red', label=y2label)
        #     ax2.set_ylabel(y2label, color='red')
        #     ax2.set_ylim(min_val2 - 0.05 * abs(min_val2), max_val2 + 0.05 * abs(max_val2))

        fig.set_size_inches(20, 11.25)
        fig.savefig(os.path.join(self._path, 'plot_'+filename+'.png'), dpi=self._dpi)
        plt.close("all")

        with open(os.path.join(self._path, 'plot_'+filename + '_data.txt'), "w") as file:
            for value in zip(data1, data2 or []):
                file.write("%s %s\n" % value)