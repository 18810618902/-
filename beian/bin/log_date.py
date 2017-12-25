#!/usr/bin/env python3
#coding:utf-8

import  datetime
import os
import logging


d_date = datetime.datetime.strftime(datetime.datetime.now(),"%Y%m%d%H%M%S")       #define date format


log_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
log_file = log_dir + '/log/access.log'       #the path of log

class Logger:
    def __init__(self,clevel = logging.DEBUG,Flevel = logging.DEBUG):
        self.logger = logging.getLogger('Logger')
        self.logger.setLevel(logging.DEBUG)
        fmt = logging.Formatter('%(asctime)s: %(name)s %(levelname)s: %(message)s', datefmt='%Y/%m/%d %H-%M-%S')

        #设置屏幕日志输出
        if not self.logger.handlers:
            sh = logging.StreamHandler()
            sh.setLevel(clevel)
            sh.setFormatter(fmt)
            self.logger.addHandler(sh)

            #设置日志文件
            fh = logging.FileHandler(log_file)
            fh.setFormatter(fmt)
            fh.setLevel(Flevel)
            self.logger.addHandler(fh)



    def debug(self,message):
        self.logger.debug(message)

    def info(self,message):
        self.logger.info(message)

    def warning(self,message):
        self.logger.warning(message)

    def error(self,message):
        self.logger.error(message)

    def critial(self,message):
        self.logger.critical(message)

    def exception(self,message):
        self.logger.exception(message)


if __name__ == '__main__':
    logtest = Logger()
    logtest.info('this is debug message')
    logtest.error('this is error message')