# -*- coding: utf-8 -*-

"""@package pydwg

    * Description
        DWGTools - A tool set for DWG file forensics using DWGParser
    * Author
        Hyunji Chung  (localchung@gmail.com)
        Jungheum Park (junghmi@gmail.com)
    * License
        MIT License
    * Tested Environment
        Python 3.5.1
"""

import os.path
import ntpath
import logging
from collections import OrderedDict

import numpy as np
import matplotlib.pyplot as plt

from .dwg_common import *
from .dwg_parser import DWGParser
from .dwg_utils import DWGUtils


class DWGToolSet:
    """DWGToolSet class
    """

    def __init__(self, target, output):
        """The constructor"""
        self.target_path = target  # dir or file
        self.output_path = output  # dir
        self.target_files = []

        self.utils = DWGUtils()
        self.logger = logging.getLogger(__name__)

        self.check_target_info()
        return

    def validate(self):
        """validate the file format of target files

        """
        for path in self.target_files:
            dp = DWGParser(path, DWGParsingMode.VALIDATION)
            if dp.parse() is False:
                continue

            self.logger.info("{}(): Validate the DWG format.".format(GET_MY_NAME()))

            # Check the validation results
            name = ntpath.basename(path)
            dp.get_result().report.print_summary(name)

            if dp.get_result().report.get_count() == 0:
                continue

            # (Pretty) Print the result
            vinfo = dp.get_result().report.get_vinfo()
            for item in vinfo:
                print(item)

            dp.close()

        return

    def get_metadata(self):
        """Get the metadata of target files

        """
        for path in self.target_files:
            dp = DWGParser(path)
            if dp.parse() is False:
                continue

            self.logger.info("{}(): Get the metadata.".format(GET_MY_NAME()))

            # (Pretty) Print the metadata to stdout
            self.utils.print_metadata(dp.get_result())

            dp.close()

        return

    def get_handle_distribution(self):
        """Get the handle distribution of target files

        """
        result_list = []

        for path in self.target_files:
            dp = DWGParser(path)
            if dp.parse() is False:
                continue

            self.logger.info("{}(): Extract the handle distribution.".format(GET_MY_NAME()))

            # Get the handle list from object map (from AcDb:Handle)
            # object_map = dp.get_result().dwg_object_map

            # Get the handle list from object list (from AcDb:AcDbObjects)
            objects = dp.get_result().dwg_objects

            # Build a handle list
            handles = self.build_handle_list(objects)

            # Save the result to a CSV file
            name = ntpath.basename(path)
            self.utils.write_to_csv_for_tool_set(
                handles,
                self.output_path + "//handle_distribution_({}).csv".format(name)
            )

            dp.close()
            # continue

            entry = dict()
            entry['name'] = name
            entry['data'] = handles
            result_list.append(entry)
            self.visualize_object_distribution_1st(entry)

        # Visualize the handles
        if len(result_list) != 0:
            self.visualize_handle_distribution_1st(result_list)
        return

    def get_drawing_history(self):
        """Get the drawing history of target files

        """
        result_list = []

        for path in self.target_files:
            dp = DWGParser(path)
            if dp.parse() is False:
                continue

            self.logger.info("{}(): Extract the handle distribution.".format(GET_MY_NAME()))

            # Get the handle list from object list (from AcDb:AcDbObjects)
            objects = dp.get_result().dwg_objects

            # Build a handle list
            handles = self.build_handle_list(objects)

            dp.close()

            entry = dict()
            entry['name'] = ntpath.basename(path)
            entry['data'] = handles
            result_list.append(entry)

            # Visualize the drawing history
            self.visualize_drawing_history_1st(entry)
            # self.visualize_drawing_history_2nd(entry)

        return

    def visualize_drawing_history_1st(self, entry):

        self.logger.info("{}(): Visualize the drawing history.".format(GET_MY_NAME()))

        data = entry.get('data')

        # Get maximum handle value
        handle_max = 0
        data = entry.get('data')  # list of handle dict
        if handle_max < data[-1].get('handle'):
            handle_max = data[-1].get('handle')

        if handle_max <= 0:
            return False

        handle_max += 1

        # Build custom list
        objects = dict()
        entities = dict()
        for idx in range(len(data)):
            if data[idx]['class'] == 'O':
                if objects.get(data[idx]['name']) is None:
                    objects[data[idx]['name']] = [data[idx]['handle']]
                else:
                    objects[data[idx]['name']].append(data[idx]['handle'])
            else:
                if entities.get(data[idx]['name']) is None:
                    entities[data[idx]['name']] = [data[idx]['handle']]
                else:
                    entities[data[idx]['name']].append(data[idx]['handle'])

        objects = OrderedDict(sorted(objects.items(), key=lambda t: t[0]))
        entities = OrderedDict(sorted(entities.items(), key=lambda t: t[0]))

        # Build a matrix (2D-array)
        c = 1
        array_2d = []
        for k, v in entities.items():
            array = [-1]*handle_max
            for handle in v:
                array[handle] = c
            # c += 1
            # array = np.ma.masked_array(array, array < 0)
            array_2d.append(array)

        m = np.vstack(array_2d)
        RELEASE_LIST(array_2d)
        m = np.ma.masked_array(m, m < 0)  # for transparency

        # Create a subplot
        fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(16, 9))

        # Set X and Y-tick labels
        y_ticklabels = list(entities.keys())

        # Draw the pcolormesh chart for each handle list
        ax.pcolormesh(m, vmin=0, vmax=1, cmap="RdYlBu")

        # Configure the chart
        ax.set_xticks(np.arange(0, handle_max, handle_max*0.20))
        ax.set_xticks(np.arange(0, handle_max, handle_max*0.05), minor=True)
        ax.set_yticks(np.arange(0, len(entities), 1))
        # ax.xaxis.set_ticklabels([])
        for tick in ax.xaxis.get_major_ticks():
            tick.label.set_fontsize(15)
        ax.yaxis.set_ticklabels(y_ticklabels, rotation=45, fontsize=15)
        ax.xaxis.grid(True, linestyle='--', which='minor', color='grey', alpha=.10)
        ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.20)
        # ax.set_xlim([0, handle_max])
        ax.set_xlim([-10, handle_max+10])
        ax.set_ylim([0, len(entities)])
        ax.invert_yaxis()
        ax.set_xlabel('Handle values (Last value is {})'.format(data[-1].get('handle')), fontsize=18)
        ax.set_title('Drawing history of {}'.format(entry.get('name')), fontsize=18)

        plt.tight_layout()
        # plt.show()
        path = self.output_path + "//drawing_history_({}).png".format(entry.get('name'))
        fig.savefig(path, format="png", dpi=300)
        return True

    def visualize_handle_distribution_1st(self, entries):
        def to_matrix(l, n):
            return [l[i:i+n] for i in range(0, len(l), n)]

        COLOR_OBJECT = 0
        # COLOR_OBJECT_LAST = 25
        COLOR_ENTITY = 50
        COLOR_UNUSED = -1

        # Get maximum handle value
        handle_max = 0
        for e in entries:
            data = e.get('data')  # list of handle dict
            if handle_max < data[-1].get('handle'):
                handle_max = data[-1].get('handle')
        handle_max += 1

        if handle_max <= 0:
            return False

        X_WIDTH = int(handle_max*0.05)
        handle_max = (int((handle_max + (X_WIDTH - 1)) / X_WIDTH) * X_WIDTH)

        # Create the pcolormesh chart for each handle list
        fig, axs = plt.subplots(ncols=len(entries), figsize=(16, 9))

        # Set Y-tick labels
        y_ticklabels = int(handle_max/X_WIDTH)*['']
        y_ticklabels[0] = 0
        y_ticklabels[-1] = handle_max-X_WIDTH

        for idx in range(len(entries)):
            data = entries[idx].get('data')  # list of handle dict

            # Build handle matrix
            handle_list  = handle_max*[COLOR_UNUSED]
            # handle_last = data[-1].get('handle')
            # total_count = (int((handle_last + (x_width - 1)) / x_width) * x_width)

            for e in data:
                if e['class'] == 'O':
                    handle_list[e.get('handle')-1] = COLOR_OBJECT
                else:
                    handle_list[e.get('handle')-1] = COLOR_ENTITY
            # handle_list[data[-1].get('handle')-1] = COLOR_OBJECT_LAST

            # Transform to matrix
            m = to_matrix(handle_list, X_WIDTH)
            array_2d = np.array(m)
            array_2d = np.ma.masked_array(array_2d, array_2d < 0)  # for transparency

            if isinstance(axs, np.ndarray):
                ax = axs[idx]
            else:
                ax = axs

            # Draw the chart
            ax.pcolormesh(array_2d, cmap='copper')

            # Configure the chart
            ax.set_xticks(np.arange(0, X_WIDTH, X_WIDTH/10))
            ax.set_yticks(np.arange(0, handle_max/X_WIDTH, 1))
            ax.xaxis.set_ticklabels([])
            ax.yaxis.set_ticklabels(y_ticklabels, fontsize=16)
            ax.xaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.15)
            ax.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.25)
            ax.invert_yaxis()
            ax.set_xlabel('Last handle value is {}'.format(data[-1].get('handle')), fontsize=18)
            ax.set_ylabel('Handle values', fontsize=18)
            # ax.set_title('{}'.format(entries[idx].get('name')), fontsize=5)

        # fig.colorbar(p)
        plt.tight_layout()
        # plt.show()
        path = self.output_path + "//handle_distribution.png"
        fig.savefig(path, format="png", dpi=300)
        return True

    def visualize_object_distribution_1st(self, entry):

        self.logger.info("{}(): Visualize the object distribution.".format(GET_MY_NAME()))

        data = entry.get('data')

        # Build custom list
        objects = dict()
        entities = dict()
        for idx in range(len(data)):
            if data[idx]['class'] == 'O':
                if objects.get(data[idx]['name']) is None:
                    objects[data[idx]['name']] = 1
                else:
                    objects[data[idx]['name']] += 1
            else:
                if entities.get(data[idx]['name']) is None:
                    entities[data[idx]['name']] = 1
                else:
                    entities[data[idx]['name']] += 1

        objects = OrderedDict(sorted(objects.items(), key=lambda t: t[0]))
        entities = OrderedDict(sorted(entities.items(), key=lambda t: t[0]))

        # Create a bar chart
        fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(16, 9))

        '''-----------------------------------------------------------------
        Bar chart for objects
        -----------------------------------------------------------------'''
        index = np.arange(len(objects))

        names  = objects.keys()
        values = objects.values()

        rects = ax1.bar(index, values,
                        width=0.5,
                        color='#FD0D0D',
                        align='center')

        (y_bottom, y_top) = ax1.get_ylim()
        y_height = y_top - y_bottom

        for rect in rects:
            height = int(rect.get_height())
            value_str = str(height)

            xloc = rect.get_x() + rect.get_width()/2.0
            yloc = height + (y_height * 0.01)

            label = ax1.text(xloc, yloc, value_str,
                             horizontalalignment='center',
                             verticalalignment='bottom',
                             color='black', weight='bold', fontsize=10)

        ax1.set_xticks(index)
        ax1.set_xticklabels(names, rotation=60, fontsize=10)
        for tick in ax1.yaxis.get_major_ticks():
            tick.label.set_fontsize(8)
        ax1.set_xlim([min(index) - 1, max(index) + 1])
        ax1.set_ylim([0, max(values) + max(values)*0.05])
        ax1.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.25)
        # ax1.set_xlabel(names, fontsize=8)
        ax1.set_ylabel('Counts', fontsize=11)
        ax1.set_title('Non-graphical objects (aka OBJECT)', fontsize=15)

        '''-----------------------------------------------------------------
        Bar chart for entities
        -----------------------------------------------------------------'''
        index = np.arange(len(entities))

        names  = entities.keys()
        values = entities.values()

        rects = ax2.bar(index, values,
                        width=0.5,
                        color='#0000FF',
                        align='center')

        (y_bottom, y_top) = ax2.get_ylim()
        y_height = y_top - y_bottom

        for rect in rects:
            height = int(rect.get_height())
            value_str = str(height)

            xloc = rect.get_x() + rect.get_width()/2.0
            yloc = height + (y_height * 0.01)

            label = ax2.text(xloc, yloc, value_str,
                             horizontalalignment='center',
                             verticalalignment='bottom',
                             color='black', weight='bold', fontsize=10)

        ax2.set_xticks(index)
        ax2.set_xticklabels(names, rotation=60, fontsize=10)
        for tick in ax2.yaxis.get_major_ticks():
            tick.label.set_fontsize(8)
        ax2.set_xlim([min(index) - 1, max(index) + 1])
        ax2.set_ylim([0, max(values) + max(values)*0.05])
        ax2.yaxis.grid(True, linestyle='--', which='major', color='grey', alpha=.25)
        ax2.set_ylabel('Counts', fontsize=11)
        ax2.set_title('Graphical objects (aka ENTITY)', fontsize=15)

        # plt.xlabel('Group')
        # plt.xticks(index, ('A', 'B', 'C', 'D', 'E'))
        # plt.ylabel('Object counts')
        # plt.legend()
        # plt.title('Counts of objects and entities')
        plt.tight_layout()
        # fig.suptitle('Counts of objects and entities', fontsize=20)
        # plt.show()

        path = self.output_path + "//object_distribution_({}).png".format(entry.get('name'))
        fig.savefig(path, format="png", dpi=300)
        return

    def build_handle_list(self, objects):
        """Build the handle list using parsed object info.

        Returns:
            list of handle + basic object info.
        """
        handles = []

        for obj in objects:
            body = obj.get('body')

            entry = OrderedDict()
            entry['handle'] = body.get('handle').get('value')
            entry['name'] = body.get('name')
            entry['class'] = body.get('class')

            # entry['handle_owned'] = []
            # if body.get('handle_owned') is not None:
            #     for h in body.get('handle_owned'):
            #         entry['handle_owned'].append(h.get('absolute_reference'))

            # entry['handle_inserts'] = []
            # if body.get('handle_inserts') is not None:
            #     for h in body.get('handle_inserts'):
            #         entry['handle_inserts'].append(h.get('absolute_reference'))
            #
            # entry['handle_from_object_map'] = obj.get('handle_from_object_map')

            entry['note'] = ""
            if body.get('entry_name') is not None:
                entry['note'] = body.get('entry_name')

            handles.append(entry)

        return handles

    def check_target_info(self):
        """Check the input information

        """
        # What is the target's type? directory or file
        if os.path.isdir(self.target_path):
            dir_mode = True
        else:
            dir_mode = False

        # Set the path list of target files
        if dir_mode:
            for dirpath, dirnames, files in os.walk(self.target_path):
                for name in files:
                    path = os.path.abspath(os.path.join(dirpath, name))
                    self.target_files.append(path)
        else:
            path = os.path.abspath(self.target_path)
            self.target_files.append(path)

        # Create the output path
        self.output_path += "//" + self.utils.create_name_with_time("pydwg-tools")
        # self.output_path += "//[DEBUG] pydwg-tools"
        self.output_path = os.path.abspath(self.output_path)

        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

