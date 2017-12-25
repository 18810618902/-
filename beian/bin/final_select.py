#!/usr/bin/env python3
#conding:utf-8

from . import log_date
from . import all_defined_api
#pg_exec, pg_exec_values, return_pg_exec, get_zhuyu

logs = log_date.Logger()

def instead_zhuyu():              #把获取到的域名提取主域，然后放到数据库，用于后期的备案验证
    logs.info("{final_select()} processing......")
    logs.info("Create dup_domains.......")
    #查找包含国内pop的服务组
    service_selected = "SELECT DISTINCT lower(tnode.service_name) AS cn_service_name FROM oui_pop_" + log_date.d_date + " tpop \
                      FULL JOIN oui_node_with_service_"+ log_date.d_date +" tnode ON \
                      substring(tpop.pop_name, '([a-z][a-z][a-z]){1}') = substring(tnode.node_name, '([a-z][a-z][a-z]){1}') \
                      WHERE substring(tpop.pop_name, 1, 2) = 'cn' AND tnode.service_name != '' ORDER BY cn_service_name"

    #在oui_domain_with_service查找出客户、域名都在用,且使用到上面服务组的site_idq
    site_id_selected = "SELECT tdomain.site_id FROM oui_domain_with_service_"+ log_date.d_date+ " AS tdomain FULL JOIN \
                        oui_all_customer_"+ log_date.d_date +" AS tallcus ON tdomain.customer_id = tallcus.customer_id WHERE \
                        lower(tdomain.service_name) IN (" + service_selected + ") AND tdomain.site_status = 1 AND \
                        tallcus.customer_status = 1"


    #把筛选出来的域名放到dup_domains_ 表中
    insert_into_dup = "SELECT nextval('seq_" + log_date.d_date + "') AS no,tallsite.site_alias AS ori_domain,tallsite.site_alias AS \
                       pro_domain INTO TABLE dup_domains_"+ log_date.d_date +" FROM oui_all_site_"+ log_date.d_date +" AS tallsite WHERE \
                       tallsite.site_id IN (" + site_id_selected +") AND tallsite.site_status = 1"


    all_defined_api.pg_exec(insert_into_dup)
    logs.info("Create dup_domains done.......")
    logs.info('let us get zhuyu now ......')
    query_command = "SELECT no,ori_domain FROM dup_domains_" + log_date.d_date + " WHERE ori_domain != ''"
    all_domains = all_defined_api.return_pg_exec(query_command)

    update_pg_value = []
    for tuplee in all_domains:
        update_pg_value.append((all_defined_api.get_zhuyu(tuplee[1]), tuplee[0]))

    insert_pg_command = "UPDATE dup_domains_" + log_date.d_date + " SET pro_domain = (%s) WHERE no = (%s)"
    all_defined_api.pg_exec_values(insert_pg_command, update_pg_value)

    logs.info("{get_zhuyu()} ended.......")


if __name__ == "__main__":
    instead_zhuyu()