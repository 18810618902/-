#!/usr/bin/env python3



# all api url info
url_base_service = "https://pantherapi.cdnetworks.com/rest/int/" + oui_rest_account + "/service/list/"
url_base_node = "https://pantherapi.cdnetworks.com/rest/int/" + oui_rest_account + "/node/list/"
url_base_pop = "https://pantherapi.cdnetworks.com/rest/int/" + oui_rest_account + "/pop/list/"
url_base_pad_in_service = "https://pantherapi.cdnetworks.com/rest/int/" + oui_rest_account + "/get_service_info/"
url_base_all_site = "https://pantherapi.cdnetworks.com/rest/cdn/" + oui_rest_account + "/site/list/"
url_base_customer = "https://pantherapi.cdnetworks.com/rest/int/" + oui_rest_account + "/customer/list/"
url_base_user = "https://pantherapi.cdnetworks.com/rest/cdn/" + oui_rest_account + "/user/list/"
url_base_vip_in_service = "https://pantherapi.cdnetworks.com/rest/int/" + oui_rest_account + "/get_service_vip/"

#beian api
wsdl_url = "http://60.00.000.74:43392/?wsdl"

#postgrep connect info
db_conn_str = "host=127.0.0.1 port=5432 dbname=cdnetworks_beian user=cdnetworks_beian password=cdnetworks_beian"


#the count for beian api query
beian_batch_size = 10





