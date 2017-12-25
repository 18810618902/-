#! /usr/bin/env python3
#coding:utf-8

import datetime
from . import log_date
from . import all_defined_api


logs = log_date.Logger()

def create_database_table():
    logs.info("{create_base()/postgre sql} processing......")

    #创建表
    create_str = "CREATE TABLE oui_service_" + log_date.d_date + \
        "(service_id INT PRIMARY KEY,service_name VARCHAR(20)) TABLESPACE cdnetworks_beian;"

    create_str += "CREATE TABLE oui_pop_" + log_date.d_date + \
        "(pop_id INT PRIMARY KEY,pop_name VARCHAR(32)) TABLESPACE cdnetworks_beian;"

    create_str += "CREATE TABLE oui_all_site_" + log_date.d_date + \
        "(site_id INT,site_name TEXT,site_alias TEXT,site_status INT) TABLESPACE cdnetworks_beian;"

    create_str += "CREATE TABLE oui_all_customer_" + log_date.d_date + \
                  "(customer_id INT PRIMARY KEY,customer_name TEXT,customer_status SMALLINT,customer_local_name TEXT,\
                  customer_eng_name TEXT,customer_sales_rep_id INT,customer_ori_sales_rep_id INT,customer_des TEXT)\
                   TABLESPACE cdnetworks_beian;"

    create_str += "CREATE TABLE oui_domain_with_service_" + log_date.d_date + \
                  "(site_id INT,site_name TEXT,service_id INT,service_name VARCHAR(32),site_status INT,customer_id INT)\
                   TABLESPACE cdnetworks_beian;"

    create_str += "CREATE TABLE oui_node_with_service_" + log_date.d_date + \
                  "(node_id INT,node_name VARCHAR(64),service_name VARCHAR(32)) TABLESPACE cdnetworks_beian;"

    create_str += "CREATE SEQUENCE seq_" + log_date.d_date + ";"

    create_str += "CREATE TABLE cd_beian_result_" + log_date.d_date + \
                  "(id SERIAL PRIMARY KEY,domain_name TEXT,domain_is_beian SMALLINT,beian_no TEXT) TABLESPACE cdnetworks_beian;"

    all_defined_api.pg_exec(create_str)

    logs.info("{create_base()} ended......")


if __name__ == '__main__':
   create_database_table()
