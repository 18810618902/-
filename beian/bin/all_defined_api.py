#!/usr/bin/env python3
#coding:utf-8
#defined some api

import os
import sys
import psycopg2
import requests
import json
import multiprocessing
from multiprocessing import Pool
import re
from . import log_date, send_email


root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(root_dir)         #把备案脚本的目录放到环境变量中去


logs = log_date.Logger()

root_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(root_dir)         #把备案脚本的目录放到环境变量中去

from conf.setting import db_conn_str




def pg_exec(exec_str):
    conn = psycopg2.connect(db_conn_str)
    cur = conn.cursor()
    cur.execute(exec_str)
    conn.commit()

    cur.close()
    conn.close()

def pg_exec_values(exec_str, command_values):
    conn = psycopg2.connect(db_conn_str)
    cur = conn.cursor()
    cur.executemany(exec_str, command_values)       #可传递多个value，一起操作
    conn.commit()

    cur.close()
    conn.close()

def post_api_request(api_url,post_data):
    r = requests.post(api_url, data = post_data)
    print(r.text)
    res = json.loads(r.text)
    return res


def return_pg_exec(exec_str):
    conn = psycopg2.connect(db_conn_str)
    cur = conn.cursor()
    cur.execute(exec_str)
    res =cur.fetchall()
    conn.commit()

    cur.close()
    conn.close()
    return res


def para_import_service(services):
    from . import all_oui_api
    all_oui_api.import_service_domain(services)
    all_oui_api.import_service_node(services)


def oui_service_with_domain():
    select_pg_command = "select service_name from oui_service_" + log_date.d_date + ";"
    services = return_pg_exec(select_pg_command)

    c_count = multiprocessing.cpu_count()
    if c_count <= 4:
        c_count = 3
    elif c_count >= 8:
        c_count = 6

    with Pool(processes = c_count) as pool:
        pool.map(para_import_service, services)
        pool.close()
        pool.join()

##########     beian   api   ###############

def api_beian(domains):                     #get the beian result
    from suds.client import Client
    import psycopg2
    from conf.setting import  wsdl_url

    client = Client(wsdl_url)
    client.set_options(timeout=300)

    query_params = json.dumps({"IcpRequest": {"domains": domains}})
    res = client.service.findDomainState(query_params)

    return res


def insert_beian_info(beian_res):
    res = json.loads(beian_res)
    insert_pg_value = []

    if "IcpRespone" in res and "domains" in res["IcpRespone"]:
        for domain in res["IcpRespone"]["domains"]:
            if 'phylicnum' not in domain.keys():
                domain['phylicnum'] = 'nothing'
            insert_pg_value.append((domain['domain'], domain['state'], domain['phylicnum']))

        insert_pg_command =  "INSERT INTO cd_beian_result_" + log_date.d_date + " (domain_name,domain_is_beian,beian_no) \
                    VALUES(%s,%s,%s)"

        pg_exec_values(insert_pg_command, insert_pg_value)

    return 'ok'


def update_beian_info(beian_res):
    res = json.loads(beian_res)
    update_pg_value = []

    if "IcpRespone" in res and "domains" in res["IcpRespone"]:
        for domain in res["IcpRespone"]["domains"]:
            if 'phylicnum' not in domain.keys():
                domain['phylicnum'] = 'nothing'
            update_pg_value.append((domain['state'], domain['phylicnum'], domain['domain']))

        update_pg_command = "UPDATE cd_beian_result_" + log_date.d_date + " SET domain_is_beian = %s, beian_no = %s \
                    WHERE domain_name = %s"

        pg_exec_values(update_pg_command, update_pg_value)

    return 'ok'


def do_check_beian(query, flag):

    domain_res = return_pg_exec(query)      #获取主域排序、去重


    from conf.setting import beian_batch_size
    loop_count = 0
    check_domains = []
    re_flag = None

    for domain in domain_res:
        if loop_count == beian_batch_size:
            logs.info("Requesting : " + str(check_domains) )

            try:
                res = api_beian(check_domains)
                if flag == 'ch':
                    re_flag = insert_beian_info(res)
                elif flag == 're':
                    re_flag = update_beian_info(res)
                if not re_flag:
                    logs.error(str(check_domains) + " DO NOT GET BEIAN DATA !!!")

            except Exception as e:
                logs.error(str(check_domains) + " DO NOT GET BEIAN DATA" + "ERROR" + e)
                continue
            finally:
                check_domains = []
                check_domains.append(str(domain[0]))
                loop_count = 1

        else:
            check_domains.append(str(domain[0]))
            loop_count += 1


    if len(check_domains) != 0:
        logs.info("Requesting : " + str(check_domains))

        try:
            res = api_beian(check_domains)
            if flag == 'ch':
                re_flag = insert_beian_info(res)
            elif flag == 're':
                re_flag = update_beian_info(res)
            if not re_flag:
                logs.error(str(check_domains) + " DO NOT GET BEIAN DATA !!!")

        except Exception as e:
            logs.error(str(check_domains) + " DO NOT GET BEIAN DATA" + "ERROR" + e)






def check_beian():
    logs.info("#########  {check_beian()}  ########  processing......")

    query_str = "SELECT DISTINCT(pro_domain) AS domains FROM dup_domains_" + log_date.d_date + " WHERE pro_domain != '' ORDER BY domains"

    do_check_beian(query_str, 'ch')

    logs.info("########  {check_beian()}  ########  ended.......")


def recheck_beian():
    logs.info("#########  {recheck_beian()}  ########  processing......")

    query_pg_command = "SELECT domain_name FROM cd_beian_result_" + log_date.d_date + " WHERE domain_is_beian = 4 or domain_is_beian = 5"

    do_check_beian(query_pg_command, 're')

    logs.info("########  {recheck_beian()}  ########  ended.......")


def ba_api_check():
    test_beian = ['baidu.com']
    try:
        api_beian(test_beian)
    except Exception as e:
        send_email.email_notice('备案api有问题，详见报错%s'%e)
        code = 1
    else:
        send_email.email_notice('备案api正常,开始备案查询并入库．．．．．．')
        code = 0

    return code

#############    beian  api   end ############



def get_zhuyu(input_domain):
    output_domain = ""

    if re.search(r"^([0-9a-zA-Z-])+\.([0-9a-zA-Z-])+$", input_domain):
        output_domain = input_domain
    elif re.search(r"\.(co|or|aaa|aarp|abb|abbott|abbvie|abogado|abudhabi|academy|accenture|accountant|accountants|\
                    aco|active|actor|adac|ads|adult|aeg|aero|afl|agakhan|agency|aig|airforce|airtel|akdn|allfinanz|\
                    ally|alsace|amica|amsterdam|analytics|android|anquan|apartments|app|aquarelle|aramco|archi|army|\
                    arpa|arte|asia|associates|attorney|auction|audi|audio|author|auto|autos|avianca|aws|axa|azure|\
                    baby|band|bank|bar|barcelona|barclaycard|barclays|barefoot|bargains|bauhaus|bayern|bbva|bcg|bcn|\
                    beats|beer|bentley|berlin|best|bet|bharti|bible|bid|bike|bing|bingo|bio|biz|black|blackfriday|bloomberg|\
                    blue|bms|bmw|bnl|bnpparibas|boats|boehringer|bom|bond|boo|book|boots|bosch|bostik|bot|boutique|bradesco|\
                    bridgestone|broadway|broker|brother|brussels|budapest|bugatti|build|builders|business|buy|buzz|bzh|\
                    cab|cafe|cal|call|camera|camp|cancerresearch|canon|capetown|capital|car|caravan|cards|care|career|careers|\
                    cars|cartier|casa|cash|casino|cat|catering|cba|cbn|ceb|center|ceo|cern|cfa|cfd|chanel|channel|chase|chat|\
                    cheap|chloe|christmas|chrome|church|cipriani|circle|cisco|citic|city|cityeats|claims|cleaning|click|clinic|\
                    clinique|clothing|cloud|club|clubmed|coach|codes|coffee|college|cologne|com|commbank|community|company|compare|\
                    computer|comsec|condos|construction|consulting|contact|contractors|cooking|cool|coop|corsica|country|coupon|coupons|\
                    courses|credit|creditcard|creditunion|cricket|crown|crs|cruises|csc|cuisinella|cymru|cyou|\
                    dabur|dad|dance|date|dating|datsun|day|dclk|dds|dealer|deals|degree|delivery|dell|deloitte|delta|democrat|\
                    dental|dentist|desi|design|dev|diamonds|diet|digital|direct|directory|discount|dnp|docs|dog|doha|domains|doosan|\
                    download|drive|dubai|durban|dvag|\
                    earth|eat|edeka|edu|education|email|emerck|energy|engineer|engineering|enterprises|equipment|erni|\
                    esq|estate|eurovision|eus|events|everbank|exchange|expert|exposed|express|extraspace|\
                    fage|fail|fairwinds|faith|family|fan|fans|farm|fashion|fast|feedback|ferrero|film|final|finance|\
                    financial|firestone|firmdale|fish|fishing|fit|fitness|flights|florist|flowers|flsmidth|fly|foo|football|\
                    ford|forex|forsale|forum|foundation|fox|fresenius|frl|frogans|frontier|ftr|fund|furniture|futbol|fyi|\
                    gal|gallery|gallo|gallup|game|garden|gbiz|gdn|gea|gent|genting|ggee|gift|gifts|gives|giving|glass|gle|global|\
                    globo|gmail|gmbh|gmo|gmx|gold|goldpoint|golf|goo|goog|gop|got|gov|grainger|graphics|gratis|green|gripe|group|\
                    gucci|guge|guide|guitars|guru|\
                    hamburg|hangout|haus|hdfcbank|health|healthcare|help|helsinki|here|hermes|hiphop|hitachi|hiv|hkt|hockey|\
                    holdings|holiday|homedepot|homes|honda|horse|host|hosting|hoteles|hotmail|house|how|hsbc|htc|hyundai|\
                    ibm|icbc|ice|icu|ifm|iinet|imamat|immo|immobilien|industries|infiniti|info|ing|ink|institute|insurance|\
                    insure|int|international|investments|ipiranga|irish|iselect|ismaili|ist|istanbul|itau|iwc|\
                    jaguar|java|jcb|jcp|jetzt|jewelry|jlc|jll|jmp|jnj|jobs|joburg|jot|jpmorgan|jprs|juegos|\
                    kaufen|kddi|kerryhotels|kerrylogistics|kerryproperties|kfh|kia|kim|kinder|kitchen|kiwi|koeln|komatsu|kpmg|\
                    kpn|krd|kred|kuokgroup|kyoto|\
                    lacaixa|lamborghini|lamer|lancaster|land|landrover|lanxess|lasalle|lat|latrobe|law|lawyer|lds|lease|\
                    leclerc|legal|lexus|lgbt|liaison|lidl|life|lifeinsurance|lifestyle|lighting|like|limited|limo|lincoln|linde|\
                    link|lipsy|live|living|lixil|loan|loans|locus|lol|london|lotte|lotto|love|ltd|ltda|lupin|luxe|luxury|\
                    madrid|maif|maison|makeup|man|management|mango|market|marketing|markets|marriott|mba|med|media|meet|melbourne|\
                    meme|memorial|men|menu|meo|miami|microsoft|mil|mini|mls|mma|mobi|mobily|moda|moe|moi|mom|monash|money|montblanc|\
                    mormon|mortgage|moscow|motorcycles|mov|movie|movistar|mtn|mtpc|mtr|museum|mutual|mutuelle|\
                    nadex|nagoya|name|natura|navy|nec|net|netbank|network|neustar|new|news|next|nextdirect|nexus|ngo|nhk|nico|nikon|\
                    ninja|nissan|nissay|nokia|northwesternmutual|norton|nowruz|nowtv|nra|nrw|ntt|nyc|\
                    obi|office|okinawa|olayan|olayangroup|omega|one|ong|onl|online|ooo|oracle|orange|org|organic|origins|osaka|\
                    otsuka|ovh|\
                    page|pamperedchef|panerai|paris|pars|partners|parts|party|passagens|pet|pharmacy|philips|photo|photography|\
                    photos|physio|piaget|pics|pictet|pictures|pid|pin|ping|pink|pizza|place|play|playstation|plumbing|plus|pohl|\
                    poker|porn|post|praxi|press|pro|prod|productions|prof|progressive|promo|properties|property|protection|pub|pwc|\
                    qpon|quebec|quest|\
                    racing|read|realtor|realty|recipes|red|redstone|redumbrella|rehab|reise|reisen|reit|ren|rent|rentals|repair|\
                    report|republican|rest|restaurant|review|reviews|rexroth|rich|ricoh|rio|rip|rocher|rocks|rodeo|room|rsvp|ruhr|\
                    run|rwe|ryukyu|\
                    saarland|safe|safety|sakura|sale|salon|sandvik|sandvikcoromant|sanofi|sap|sapo|sarl|sas|saxo|sbi|sbs|sca|scb|\
                    schaeffler|schmidt|scholarships|school|schule|schwarz|science|scor|scot|seat|security|seek|select|sener|services|\
                    seven|sew|sex|sexy|sfr|sharp|shaw|shell|shia|shiksha|shoes|shouji|show|shriram|singles|site|ski|skin|sky|skype|\
                    smile|sncf|soccer|social|softbank|software|sohu|solar|solutions|song|sony|soy|space|spiegel|spot|spreadbetting|srl|\
                    stada|star|starhub|statebank|statefarm|statoil|stc|stcgroup|stockholm|storage|store|stream|studio|study|style|sucks|\
                    supplies|supply|support|surf|surgery|suzuki|swatch|swiss|sydney|symantec|systems|\
                    tab|taipei|talk|taobao|tatamotors|tatar|tattoo|tax|taxi|tci|team|tech|technology|tel|telecity|telefonica|\
                    temasek|tennis|teva|thd|theater|theatre|tickets|tienda|tiffany|tips|tires|tirol|tmall|today|tokyo|tools|top|\
                    toray|toshiba|total|tours|town|toyota|toys|trade|trading|training|travel|travelers|travelersinsurance|trust|trv|\
                    tube|tui|tunes|tushu|tvs|\
                    ubs|unicom|university|uno|uol|\
                    vacations|vana|vegas|ventures|verisign|versicherung|vet|viajes|video|vig|viking|villas|vin|vip|virgin|vision|\
                    vista|vistaprint|viva|vlaanderen|vodka|volkswagen|vote|voting|voto|voyage|vuelos|\
                    wales|walter|wang|wanggou|warman|watch|watches|weather|weatherchannel|webcam|weber|website|wed|wedding|weir|whoswho\
                    |wien|wiki|williamhill|win|windows|wine|wme|wolterskluwer|work|works|world|wtc|wtf|\
                    xbox|xerox|xihuan|xin|орг|xperia|xxx|xyz|\
                    yachts|yahoo|yamaxun|yandex|yodobashi|yoga|yokohama|you|youtube|yun|\
                    zara|zero|zip|zone|zuerich){1}\.(ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|\
                    ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|bq|br|bs|bt|bv|bw|by|bz|\
                    ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cw|cx|cy|cz|\
                    de|dj|dk|dm|do|dz|\
                    ec|ee|eg|eh|er|es|et|eu|\
                    fi|fj|fk|fm|fo|fr|\
                    ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|\
                    hk|hm|hn|hr|ht|hu|\
                    id|ie|il|im|in|io|iq|ir|is|it|\
                    je|jm|jo|jp|\
                    ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|\
                    la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|\
                    ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|\
                    na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|\
                    om|\
                    pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|\
                    qa|\
                    re|ro|rs|ru|rw|\
                    sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|\
                    tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|\
                    ua|ug|uk|us|uy|uz|\
                    va|vc|ve|vg|vi|vn|vu|\
                    wf|ws|\
                    ye|yt|\
                    za|zm|zw){1}$", input_domain):
        match = re.search(r"\.{0,1}([0-9a-zA-Z-])+\.(co|or|\
                        aaa|aarp|abb|abbott|abbvie|abogado|abudhabi|academy|accenture|accountant|\
                        accountants|aco|active|actor|adac|ads|adult|aeg|aero|afl|agakhan|agency|\
                        aig|airforce|airtel|akdn|allfinanz|ally|alsace|amica|amsterdam|analytics|\
                        android|anquan|apartments|app|aquarelle|aramco|archi|army|arpa|arte|asia|associates|\
                        attorney|auction|audi|audio|author|auto|autos|avianca|aws|axa|azure|\
                        baby|band|bank|bar|barcelona|barclaycard|barclays|barefoot|bargains|bauhaus|bayern|\
                        bbva|bcg|bcn|beats|beer|bentley|berlin|best|bet|bharti|bible|bid|bike|bing|bingo|bio|biz|\
                        black|blackfriday|bloomberg|blue|bms|bmw|bnl|bnpparibas|boats|boehringer|bom|bond|boo|\
                        book|boots|bosch|bostik|bot|boutique|bradesco|bridgestone|broadway|broker|brother|brussels|\
                        budapest|bugatti|build|builders|business|buy|buzz|bzh|\
                        cab|cafe|cal|call|camera|camp|cancerresearch|canon|capetown|capital|car|caravan|cards|care|\
                        career|careers|cars|cartier|casa|cash|casino|cat|catering|cba|cbn|ceb|center|ceo|cern|cfa|cfd|\
                        chanel|channel|chase|chat|cheap|chloe|christmas|chrome|church|cipriani|circle|cisco|citic|city|\
                        cityeats|claims|cleaning|click|clinic|clinique|clothing|cloud|club|clubmed|coach|codes|coffee|\
                        college|cologne|com|commbank|community|company|compare|computer|comsec|condos|construction|\
                        consulting|contact|contractors|cooking|cool|coop|corsica|country|coupon|coupons|courses|credit|\
                        creditcard|creditunion|cricket|crown|crs|cruises|csc|cuisinella|cymru|cyou|\
                        dabur|dad|dance|date|dating|datsun|day|dclk|dds|dealer|deals|degree|delivery|dell|deloitte|\
                        delta|democrat|dental|dentist|desi|design|dev|diamonds|diet|digital|direct|directory|discount|\
                        dnp|docs|dog|doha|domains|doosan|download|drive|dubai|durban|dvag|\
                        earth|eat|edeka|edu|education|email|emerck|energy|engineer|engineering|enterprises|equipment|\
                        erni|esq|estate|eurovision|eus|events|everbank|exchange|expert|exposed|express|extraspace|\
                        fage|fail|fairwinds|faith|family|fan|fans|farm|fashion|fast|feedback|ferrero|film|final|finance|\
                        financial|firestone|firmdale|fish|fishing|fit|fitness|flights|florist|flowers|flsmidth|fly|foo|\
                        football|ford|forex|forsale|forum|foundation|fox|fresenius|frl|frogans|frontier|ftr|fund|furniture|\
                        futbol|fyi|\
                        gal|gallery|gallo|gallup|game|garden|gbiz|gdn|gea|gent|genting|ggee|gift|gifts|gives|giving|\
                        glass|gle|global|globo|gmail|gmbh|gmo|gmx|gold|goldpoint|golf|goo|goog|gop|got|gov|grainger|\
                        graphics|gratis|green|gripe|group|gucci|guge|guide|guitars|guru|\
                        hamburg|hangout|haus|hdfcbank|health|healthcare|help|helsinki|here|hermes|hiphop|hitachi|hiv|\
                        hkt|hockey|holdings|holiday|homedepot|homes|honda|horse|host|hosting|hoteles|hotmail|house|how|\
                        hsbc|htc|hyundai|\
                        ibm|icbc|ice|icu|ifm|iinet|imamat|immo|immobilien|industries|infiniti|info|ing|ink|institute|\
                        insurance|insure|int|international|investments|ipiranga|irish|iselect|ismaili|ist|istanbul|\
                        itau|iwc|\
                        jaguar|java|jcb|jcp|jetzt|jewelry|jlc|jll|jmp|jnj|jobs|joburg|jot|jpmorgan|jprs|juegos|\
                        kaufen|kddi|kerryhotels|kerrylogistics|kerryproperties|kfh|kia|kim|kinder|kitchen|kiwi|koeln|\
                        komatsu|kpmg|kpn|krd|kred|kuokgroup|kyoto|\
                        lacaixa|lamborghini|lamer|lancaster|land|landrover|lanxess|lasalle|lat|latrobe|law|lawyer|lds|\
                        lease|leclerc|legal|lexus|lgbt|liaison|lidl|life|lifeinsurance|lifestyle|lighting|like|limited|limo|\
                        lincoln|linde|link|lipsy|live|living|lixil|loan|loans|locus|lol|london|lotte|lotto|love|ltd|ltda|lupin|\
                        luxe|luxury|\
                        madrid|maif|maison|makeup|man|management|mango|market|marketing|markets|marriott|mba|med|media|\
                        meet|melbourne|meme|memorial|men|menu|meo|miami|microsoft|mil|mini|mls|mma|mobi|mobily|moda|moe|\
                        moi|mom|monash|money|montblanc|mormon|mortgage|moscow|motorcycles|mov|movie|movistar|mtn|mtpc|mtr|\
                        museum|mutual|mutuelle|\
                        nadex|nagoya|name|natura|navy|nec|net|netbank|network|neustar|new|news|next|nextdirect|nexus|ngo|\
                        nhk|nico|nikon|ninja|nissan|nissay|nokia|northwesternmutual|norton|nowruz|nowtv|nra|nrw|ntt|nyc|\
                        obi|office|okinawa|olayan|olayangroup|omega|one|ong|onl|online|ooo|oracle|orange|org|organic|\
                        origins|osaka|otsuka|ovh|\
                        page|pamperedchef|panerai|paris|pars|partners|parts|party|passagens|pet|pharmacy|philips|\
                        photo|photography|photos|physio|piaget|pics|pictet|pictures|pid|pin|ping|pink|pizza|place|play|\
                        playstation|plumbing|plus|pohl|poker|porn|post|praxi|press|pro|prod|productions|prof|progressive|promo|\
                        properties|property|protection|pub|pwc|\
                        qpon|quebec|quest|\
                        racing|read|realtor|realty|recipes|red|redstone|redumbrella|rehab|reise|reisen|reit|ren|rent|rentals|\
                        repair|report|republican|rest|restaurant|review|reviews|rexroth|rich|ricoh|rio|rip|rocher|rocks|rodeo|\
                        room|rsvp|ruhr|run|rwe|ryukyu|\
                        saarland|safe|safety|sakura|sale|salon|sandvik|sandvikcoromant|sanofi|sap|sapo|sarl|sas|saxo|sbi|sbs|\
                        sca|scb|schaeffler|schmidt|scholarships|school|schule|schwarz|science|scor|scot|seat|security|seek|\
                        select|sener|services|seven|sew|sex|sexy|sfr|sharp|shaw|shell|shia|shiksha|shoes|shouji|show|shriram|\
                        singles|site|ski|skin|sky|skype|smile|sncf|soccer|social|softbank|software|sohu|solar|solutions|song|\
                        sony|soy|space|spiegel|spot|spreadbetting|srl|stada|star|starhub|statebank|statefarm|statoil|stc|stcgroup|\
                        stockholm|storage|store|stream|studio|study|style|sucks|supplies|supply|support|surf|surgery|suzuki|swatch|\
                        swiss|sydney|symantec|systems|\
                        tab|taipei|talk|taobao|tatamotors|tatar|tattoo|tax|taxi|tci|team|tech|technology|tel|telecity|telefonica|\
                        temasek|tennis|teva|thd|theater|theatre|tickets|tienda|tiffany|tips|tires|tirol|tmall|today|tokyo|tools|top|\
                        toray|toshiba|total|tours|town|toyota|toys|trade|trading|training|travel|travelers|travelersinsurance|trust|\
                        trv|tube|tui|tunes|tushu|tvs|\
                        ubs|unicom|university|uno|uol|\
                        vacations|vana|vegas|ventures|verisign|versicherung|vet|viajes|video|vig|viking|villas|vin|vip|virgin|\
                        vision|vista|vistaprint|viva|vlaanderen|vodka|volkswagen|vote|voting|voto|voyage|vuelos|\
                        wales|walter|wang|wanggou|warman|watch|watches|weather|weatherchannel|webcam|weber|website|wed|wedding|\
                        weir|whoswho|wien|wiki|williamhill|win|windows|wine|wme|wolterskluwer|work|works|world|wtc|wtf|\
                        xbox|xerox|xihuan|xin|орг|xperia|xxx|xyz|\
                        yachts|yahoo|yamaxun|yandex|yodobashi|yoga|yokohama|you|youtube|yun|\
                        zara|zero|zip|zone|zuerich){1}\.(ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|\
                        ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|bq|br|bs|bt|bv|bw|by|bz|\
                        ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cw|cx|cy|cz|\
                        de|dj|dk|dm|do|dz|\
                        ec|ee|eg|eh|er|es|et|eu|\
                        fi|fj|fk|fm|fo|fr|\
                        ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|\
                        hk|hm|hn|hr|ht|hu|\
                        id|ie|il|im|in|io|iq|ir|is|it|\
                        je|jm|jo|jp|\
                        ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|\
                        la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|\
                        ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|\
                        na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|\
                        om|\
                        pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|\
                        qa|\
                        re|ro|rs|ru|rw|\
                        sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|\
                        tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|\
                        ua|ug|uk|us|uy|uz|\
                        va|vc|ve|vg|vi|vn|vu|\
                        wf|ws|\
                        ye|yt|\
                        za|zm|zw){1}$", input_domain)
        if (str(match.group(0))[0:1] == "."):
            output_domain = str(match.group(0))[1:]
        else:
            output_domain = str(match.group(0))
    elif re.search(r"\.(ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|\
                ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|bq|br|bs|bt|bv|bw|by|bz|\
                ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cw|cx|cy|cz|\
                de|dj|dk|dm|do|dz|\
                ec|ee|eg|eh|er|es|et|eu|\
                fi|fj|fk|fm|fo|fr|\
                ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|\
                hk|hm|hn|hr|ht|hu|\
                id|ie|il|im|in|io|iq|ir|is|it|\
                je|jm|jo|jp|\
                ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|\
                la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|\
                ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|\
                na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|\
                om|\
                pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|\
                qa|\
                re|ro|rs|ru|rw|\
                sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|\
                tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|\
                ua|ug|uk|us|uy|uz|\
                va|vc|ve|vg|vi|vn|vu|\
                wf|ws|\
                ye|yt|\
                za|zm|zw){1}$", input_domain):
        match = re.search(r"\.{0,1}([0-9a-zA-Z-])+\.(ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|\
                        ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|bq|br|bs|bt|bv|bw|by|bz|\
                        ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cu|cv|cw|cx|cy|cz|\
                        de|dj|dk|dm|do|dz|\
                        ec|ee|eg|eh|er|es|et|eu|\
                        fi|fj|fk|fm|fo|fr|\
                        ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|\
                        hk|hm|hn|hr|ht|hu|\
                        id|ie|il|im|in|io|iq|ir|is|it|\
                        je|jm|jo|jp|\
                        ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|\
                        la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|\
                        ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|\
                        na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|\
                        om|\
                        pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|\
                        qa|\
                        re|ro|rs|ru|rw|\
                        sa|sb|sc|sd|se|sg|sh|si|sj|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|\
                        tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|\
                        ua|ug|uk|us|uy|uz|\
                        va|vc|ve|vg|vi|vn|vu|\
                        wf|ws|\
                        ye|yt|\
                        za|zm|zw){1}$", input_domain)
        if (str(match.group(0))[0:1] == "."):
            output_domain = str(match.group(0))[1:]
        else:
            output_domain = str(match.group(0))
    elif re.search(r"\.([0-9a-zA-Z-])+\.([0-9a-zA-Z-])+$", input_domain):
        match = re.search(r"\.([0-9a-zA-Z-])+\.([0-9a-zA-Z-])+$", input_domain)
        output_domain = str(match.group(0))[1:]
    else:
        output_domain = input_domain

    return output_domain




if __name__ == '__main__':
    check_beian()
    recheck_beian()





























