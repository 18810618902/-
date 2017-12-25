#!/usr/bin/env python3

from bin.log_date import d_date
from bin.log_date import Logger
from bin.create_table import create_database_table
from bin.all_defined_api import oui_service_with_domain
from bin.final_select import instead_zhuyu
from bin.all_defined_api import check_beian, recheck_beian, ba_api_check
from bin.send_email import email_notice
import traceback
import sys
import time


logs = Logger()

def import_oui_base():
    from bin.all_oui_api import import_service, import_pop, import_sites, import_customers

    import_service()
    import_pop()
    import_sites()
    import_customers()



def main_func():
    logs.info("===========================  BEGIN  ===============================")

    try:
        create_database_table()
        import_oui_base()
        oui_service_with_domain()
        instead_zhuyu()
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        logs.exception(e)

    while True:
        res_beian = ba_api_check()
        if res_beian != 0:
            logs.info("==============beian api is not ok now !!!  ==============")
            time.sleep(600)

        elif res_beian == 0:
            logs.info(">>>>>>>>>>>>>>>>beian api is ok<<<<<<<<<<<<<<<<<<<<<<<<<")
            break


    try:
        check_beian()
        logs.info("=========================== Very lucky done  ===============================")
        for i in range(1, 3):
            recheck_beian()
            time.sleep(60)
        email_notice('BenAn data was puted into database complete，you can ckeck out now!')
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        logs.exception(e)

    finally:
        logs.info("=========================== no pain no gain  ===============================")





if __name__ == '__main__':
    main_func()