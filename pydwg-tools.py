# -*- coding: utf-8 -*-

"""pydwg-tools

    * Description
        A tool pack for AutoCAD (.DWG) file forensics using Pydwg
    * Author
        Hyunji Chung  (localchung@gmail.com)
        Jungheum Park (junghmi@gmail.com)
    * License
        MIT License
    * Tested Environment
        Python 3.5.1
"""

import argparse
import traceback
import time
import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-22s %(name)-25s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

from pydwg.dwg_tool_set import *


def main():
    default_od = '.'

    parser = argparse.ArgumentParser(description='pydwg-tools, DWG analysis tool set. (https://github.com/sarahchung/pydwg)')
    subparsers = parser.add_subparsers(dest='tool')

    # sub-parse for 'format validation'
    subparser1 = subparsers.add_parser('v', help='validate the DWG file format', formatter_class=argparse.RawTextHelpFormatter)
    subparser1.add_argument('target', help='path of target file or directory', type=str)
    subparser1.add_argument('-output', help='output dir\'s path, default:%s.'%default_od, type=str, default=default_od)

    # sub-parse for 'metadata'
    subparser2 = subparsers.add_parser('m', help='extract document properties', formatter_class=argparse.RawTextHelpFormatter)
    subparser2.add_argument('target', help='path of target file or directory', type=str)
    subparser2.add_argument('-output', help='output dir\'s path, default:%s'%default_od, type=str, default=default_od)

    # sub-parse for 'handle distribution'
    subparser3 = subparsers.add_parser('h', help='show the handle distribution', formatter_class=argparse.RawTextHelpFormatter)
    subparser3.add_argument('target', help='path of target file or directory', type=str)
    subparser3.add_argument('output', help='output dir\'s path, default:%s'%default_od, type=str, default=default_od)

    # sub-parse for 'drawing history'
    subparser4 = subparsers.add_parser('d', help='compare the solution with detected results', formatter_class=argparse.RawTextHelpFormatter)
    subparser4.add_argument('target', help='path of target file or directory', type=str)
    subparser4.add_argument('output', help='output dir\'s path, default:%s'%default_od, type=str, default=default_od)

    args = parser.parse_args()
    if args.tool is None:
        return

    t1 = time.clock()

    try:
        dwg = DWGToolSet(args.target, args.output)

        if args.tool == 'v':
            dwg.validate()
        elif args.tool == 'm':
            dwg.get_metadata()
        elif args.tool == 'h':  # experimental
            dwg.get_handle_distribution()
        elif args.tool == 'd':  # experimental
            dwg.get_drawing_history()
    except:
        print(traceback.format_exc())

    t2 = time.clock()
    # print('operation took %0.2f sec' % (t2-t1))


if __name__ == "__main__":
    main()

