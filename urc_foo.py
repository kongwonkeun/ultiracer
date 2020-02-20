#
#
#
import sys

import zPipe
import zUtil

#================================
#
#
if  __name__ == '__main__':

    client = zPipe.PipeClient()

    zUtil.wait_user_input()
    client.quit()
    sys.exit()

#
#
#