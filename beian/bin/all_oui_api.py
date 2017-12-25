#!/usr/bin/env python3


import datetime
import os,sys
import OpenSSL
from . import log_date
from .all_defined_api import post_api_request, pg_exec_values


root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(root_dir)         #把备案脚本的目录放到环境变量中去



logs = log_date.Logger()

def import_service():
    from conf.setting import url_base_service

    #print(str(datetime.datetime.now()) + ": [import_service] processing...")
    logs.info(">>>>>> [ import_service ] <<<<<<   processing......")

    post_data = {'offline' : 0}
    res = post_api_request(url_base_service,post_data)

    service_values = []
    if res['status_code'] == 200:
        for line in res['data']:
            service_values.append((str(line['id']).strip(' \t\n\r'), str(line['dns_prefix']).strip(' \t\n\r')))

        insert_pg_command = "INSERT INTO oui_service_" + log_date.d_date + "(service_id, service_name) VALUES (%s, %s)"
        pg_exec_values(insert_pg_command,service_values)

        logs.info(">>>>>> [ import_service ] <<<<<<   ended.......")

    else:
        logs.exception("!!!!!! [ import_service ] !!!!!!   failed.......")
        raise Exception


def import_pop():
    from conf.setting import url_base_pop

    #print(str(datetime.datetime.now()) + ": [import_pop] processing...")
    logs.info(">>>>>> [ import_pop ] <<<<<<   processing......")

    post_data = {}
    res = post_api_request(url_base_pop, post_data)

    pop_values = []
    if res['status_code'] == 200:
        for line in res['data']:
            pop_values.append((str(line['id']).strip(' \t\n\r'), str(line['name']).strip(' \t\n\r')))
        insert_pg_command = "INSERT INTO oui_pop_" + log_date.d_date + " (pop_id, pop_name) VALUES (%s, %s)"
        pg_exec_values(insert_pg_command, pop_values)

        logs.info(">>>>>> [ import_pop ] <<<<<<    ended.......")

    else:
        logs.exception("!!!!!! [ import_pop ] !!!!!! failed.......")
        raise Exception



def import_sites():
    from conf.setting import url_base_all_site

    #print(str(datetime.datetime.now()) + ": [import_sites] processing...")
    logs.info(">>>>>> [ import_sites ] <<<<<< processing......")

    post_data = {'info': 1, 'prod': 1, 'fields': 'id,pad,pad_aliases,status'}
    res = post_api_request(url_base_all_site,post_data)

    sites_value = []
    if res['status_code'] == 200:
        for line in res['data']:
            if line['pad'] is not None and line['pad'] != "":
                str_pad = line['pad']
                if line['status']:
                    str_stat = '1'
                else:
                    str_stat = '0'

                if line['pad_aliases'] is None or line['pad_aliases'] == '':
                    sites_value.append((str(line['id']), str_pad, str_pad, str_stat))
                else:
                    sites_value.append((str(line['id']), str_pad, str_pad, str_stat))

                    str_aliases = line['pad_aliases'].replace('\r\n', ',').replace('\n', ',').split(',')
                    for single_alias in str_aliases:
                        if len(single_alias) > 0:
                            sites_value.append((str(line['id']).strip(' \t\n\r'), str(str_pad).strip(' \t\n\r'), \
                                                  str(single_alias).strip(' \t\n\r'), str_stat))

                str_pad = ""
                str_stat = ""
                str_aliases = ""

        insert_pg_command = "INSERT INTO oui_all_site_" + log_date.d_date + " (site_id, site_name, site_alias, site_status) \
                             VALUES (%s, %s, %s, %s)"

        pg_exec_values(insert_pg_command, sites_value)

        logs.info(">>>>>> [ import_sites ] <<<<<<   ended.......")

    else:
        logs.exception("!!!!!! [import_sites] !!!!!! failed.......")
        raise Exception



def import_customers():
    from conf.setting import url_base_customer

    #print(str(datetime.datetime.now()) + ": [import_customers] processing...")
    logs.info(">>>>>> [ import_customers ] <<<<<< processing......")

    post_data = {"active": 1, "info": 1}
    res = post_api_request(url_base_customer, post_data)

    customer_value = []
    if res['status_code'] == 200:
        for line in res['data']:
            if line['status'] or line['status'].lower() == 'true':
                str_stat = '1'
            else:
                str_stat = '0'

            customer_value.append((str(line['id']).strip(' \t\n\r'), str(line['name']).strip(' \t\n\r'), \
                                str_stat, str(line['local_name']).strip(' \t\n\r'), \
                                str(line['english_name']).strip(' \t\n\r'), str(line['sales_rep_id']).strip(' \t\n\r'),\
                                str(line['original_sales_rep_id']).strip(' \t\n\r'), str(line['description']).strip(' \t\n\r')))

        insert_into_command = "INSERT INTO oui_all_customer_" + log_date.d_date + \
                              " (customer_id, customer_name, customer_status, \
                                 customer_local_name, customer_eng_name, customer_sales_rep_id, \
                                 customer_ori_sales_rep_id, customer_des) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"

        pg_exec_values(insert_into_command, customer_value)

        logs.info(">>>>>> [ import_customers ] <<<<<<   ended.......")

    else:
        logs.exception("!!!!!! [import_customers] !!!!!! failed.......")
        raise Exception



#下面结合service组去创建先关的表
def import_service_domain(service_name):          #获取对应的service组下有哪些domian,及其一些客户、配置信息
    from conf.setting import url_base_pad_in_service

    #print(str(datetime.datetime.now()) + ": [import_oui_domain_with_service] processing...")
    logs.info(">>>>>> [ import_oui_domain_with_service :" + str(service_name) + "] <<<<<<   processing......")

    post_data = {"type": "service", "name": service_name}
    res = post_api_request(url_base_pad_in_service, post_data)
    print('service_name',service_name)

    service_domian_value = []
    if res['status_code'] == 200 and 'data' in res.keys() and 'details' not in res['data'] and len(res['data']) > 0:
        for line in res['data']:
            if line['status'] is None or (line['status'] is not None and line['status'] == '0'):
                str_stat = '0'
            else:
                str_stat = '1'

            service_domian_value.append((str(line['site_id']).strip(' \t\n\r'), str(line['domain']).strip(' \t\n\r'), \
                                str(line['service_id']).strip(' \t\n\r'), str(line['service_dns']).strip(' \t\n\r'), \
                                str_stat, str(line['customer_id']).strip(' \t\n\r')))

        insert_pg_command = "INSERT INTO oui_domain_with_service_" + log_date.d_date + \
                            " (site_id, site_name, service_id, service_name, site_status, customer_id)" + \
                            "VALUES (%s, %s, %s, %s, %s, %s)"

        pg_exec_values(insert_pg_command, service_domian_value)
        logs.info(">>>>>> [ import_service_domain :" + str(service_name) + " ] <<<<<<   ended.......")

    else:
        logs.warning("[import_service_domain] {" + str(service_name) + "}  has 0 record......")


def import_service_node(service_name):         #获取对应的service下有哪些node
    from conf.setting import url_base_node

    #print(str(datetime.datetime.now()) + ": [import_oui_domain_with_service] processing...")
    logs.info(">>>>>> [ import_oui_domain_with_service : " + str(service_name) + "] <<<<<<   processing......")

    post_data = {"info": 0, "service_dns_prefix": service_name}
    res = post_api_request(url_base_node, post_data)

    service_node_value = []
    if res['status_code'] == 200 and 'data' in res.keys() and 'details' not in res['data'] and len(res['data']) > 0:
        for line in res['data']:
            service_node_value.append((str(line['id']).strip(' \t\n\r'), str(line['hostname']).strip(' \t\n\r'), \
                                service_name))

        insert_pg_command = "INSERT INTO oui_node_with_service_" + log_date.d_date + \
                            " (node_id, node_name, service_name) VALUES (%s, %s, %s)"

        pg_exec_values(insert_pg_command, service_node_value)
        logs.info(">>>>>> [ import_service_node : " + str(service_name) + "] <<<<<< ended.......")

    else:
        logs.warning("[import_service_node] {" + str(service_name) + "} may has 0 record.")

if __name__ == '__main__':
    import_service_node('CL1')



















































































