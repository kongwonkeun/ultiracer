#
#
#
import argparse
import os
import sys
import time

import zBt
import zConfig
import zPipe
import zProxy
import zTray
import zUtil

#================================
#
#
if  __name__ == '__main__':

    print('rdt driver')
    file = os.path.realpath(__file__)
    zUtil.add_lnk_to_startup(file)

    argp = argparse.ArgumentParser()
    argp.add_argument('-c', '--config', default=zConfig.CONFIG_FILE, help=f'default file is {zConfig.CONFIG_FILE}')
    argp.add_argument('-r', '--reset', action='store_true')
    args = argp.parse_args()

    conf = zConfig.Config(args.config)

    if args.reset:
        print(f'config file {args.config} is removed')
        os.remove(args.config)

    if not os.path.isfile(args.config):
        print(f'config file {args.config} is not exist')
        print('creating config file ...')
        conf.save()

    name = conf.dev_name
    print(f'{name}')

    pipe = zPipe.PipeServer()

    bt = zBt.Bt()
    bt.connect(target=name)
    time.sleep(1)

    tray = zTray.Tray(file, sys.argv)
    zUtil.hide_console()

    zUtil.wait_user_input()
    pipe.quit()
    if  zBt.G_connected:
        bt.quit()
    sys.exit()


#
#
#