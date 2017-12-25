#!/usr/bin/env python3

from bin.log_date import d_date

print(d_date)










c_count = multiprocessing.cpu_count()
if c_count <= 4:
    c_count = 3
elif c_count >= 8:
    c_count = 6

with Pool(processes=c_count) as pool:
    pool.map(all_serive_info_input_database, services)
    pool.close()
    pool.join()

def mul_cpu_get_info(all_ip):
    single_ip = ''.join(all_ip)
    replace_https = re.compile('https')
    url = replace_https.sub('http', post_data['check_url'])
    proxie = {}
    proxie['http'] = 'http://' + single_ip + ':80'
    print([n], '--', single_ip)
    n += 1

    try:
        r = s.head(url, headers=header, proxies=proxie, verify=False, timeout=10)
        reponse = r.headers
    except Exception as e:
        reponse = {'error': 'NODATA'}
        reponse['edge_Ip'] = single_ip
        get_all_headers.append(reponse)
        continue

    reponse['edge_Ip'] = single_ip
    reponse['status_code'] = r.status_code
    get_all_headers.append(reponse)